"""Servicios de carga y consulta de catálogos."""

from __future__ import annotations

import csv
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Iterable, Tuple

try:  # pragma: no cover - dependencia opcional
    import pandas as pd
except Exception:  # pragma: no cover - evita fallar si no está instalado
    pd = None

from settings import BASE_DIR, DETAIL_LOOKUP_ALIASES
from validators import normalize_team_member_identifier, normalize_without_accents

from .catalogs import (build_detail_catalog_id_index, load_detail_catalogs,
                       normalize_detail_catalog_key)
from .static_team_catalog import TEAM_HIERARCHY_CATALOG, build_team_catalog_rows


class CatalogService:
    """Encapsula la carga de catálogos y consultas temporales."""

    def __init__(self, base_dir: str | os.PathLike = BASE_DIR):
        self.base_dir = Path(base_dir)
        self.detail_catalogs: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.detail_lookup_by_id: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.team_snapshots: Dict[str, list[dict]] = {}
        self.team_hierarchy: TeamHierarchyCatalog = TeamHierarchyCatalog(
            build_team_catalog_rows()
        )

    def refresh(self) -> Tuple[Dict[str, Dict[str, Dict[str, str]]], Dict[str, Dict[str, Dict[str, str]]]]:
        raw_catalogs = load_detail_catalogs(self.base_dir)
        normalized, lookup_by_id = self._normalize_catalogs(raw_catalogs)
        self.detail_catalogs = normalized
        self.detail_lookup_by_id = lookup_by_id
        self.team_snapshots, self.team_hierarchy = self._build_team_resources()
        return self.detail_catalogs, self.detail_lookup_by_id

    def _normalize_catalogs(
        self, raw_catalogs: Dict[str, Dict[str, Dict[str, str]]]
    ) -> Tuple[Dict[str, Dict[str, Dict[str, str]]], Dict[str, Dict[str, Dict[str, str]]]]:
        normalized = {
            normalize_detail_catalog_key(key): dict(value or {})
            for key, value in (raw_catalogs or {}).items()
        }
        lookup_by_id = build_detail_catalog_id_index(normalized)
        for canonical_key, aliases in (DETAIL_LOOKUP_ALIASES or {}).items():
            canonical = normalize_detail_catalog_key(canonical_key)
            lookup = normalized.get(canonical) or lookup_by_id.get(canonical)
            if not lookup:
                for alias in aliases or ():
                    alias_key = normalize_detail_catalog_key(alias)
                    alias_lookup = normalized.get(alias_key)
                    if alias_lookup:
                        lookup = alias_lookup
                        break
            if not lookup:
                continue
            normalized[canonical] = lookup
            lookup_by_id[canonical] = lookup
            for alias in aliases or ():
                alias_key = normalize_detail_catalog_key(alias)
                if not alias_key:
                    continue
                normalized[alias_key] = lookup
                lookup_by_id[alias_key] = lookup
        return normalized, lookup_by_id

    def _build_team_resources(self) -> tuple[Dict[str, list[dict]], "TeamHierarchyCatalog"]:
        path = self.base_dir / "team_details.csv"
        static_rows = build_team_catalog_rows()
        snapshots: Dict[str, list[dict]] = {}

        csv_rows: list[dict] = []
        if path.exists():
            csv_rows = list(self._iter_rows(path))
            for row in csv_rows:
                normalized_id = normalize_team_member_identifier(row.get("id_colaborador", ""))
                if not normalized_id:
                    continue
                parsed_date = self._parse_date(row.get("fecha_actualizacion"))
                snapshots.setdefault(normalized_id, []).append(
                    {
                        "data": row,
                        "fecha": parsed_date,
                    }
                )

        merged_rows = static_rows + csv_rows
        return snapshots, TeamHierarchyCatalog(merged_rows)

    def _iter_rows(self, path: Path) -> Iterable[Dict[str, str]]:
        if pd is not None:
            try:
                dataframe = pd.read_csv(path, dtype=str)
                for row in dataframe.fillna("").to_dict("records"):
                    yield self._clean_row(row.items())
                return
            except Exception:
                pass
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(line for line in handle if line.strip())
            for row in reader:
                yield self._clean_row(row.items())

    @staticmethod
    def _clean_row(items: Iterable[Tuple[str, str]]) -> Dict[str, str]:
        cleaned: Dict[str, str] = {}
        for key, value in items:
            if key is None:
                continue
            key = (key or "").strip()
            cleaned[key] = "" if value is None else str(value).strip()
        return cleaned

    @staticmethod
    def _parse_date(raw: str | date | None) -> date | None:
        if isinstance(raw, date):
            return raw
        text = (raw or "").strip()
        if not text:
            return None
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

    def lookup_team_member(
        self, identifier: str, occurrence_date: str | date | None
    ) -> Tuple[Dict[str, str] | None, Dict[str, object]]:
        meta: Dict[str, object] = {
            "selected_date": None,
            "fallback_used": False,
            "reason": None,
        }
        normalized_id = normalize_team_member_identifier(identifier)
        if not normalized_id:
            return None, meta
        snapshots = self.team_snapshots.get(normalized_id)
        if not snapshots:
            return None, meta
        case_date = self._parse_date(occurrence_date)
        valid = [snap for snap in snapshots if snap.get("fecha") is not None]
        chosen = None
        if case_date and valid:
            history = [snap for snap in valid if snap["fecha"] <= case_date]
            if history:
                chosen = max(history, key=lambda snap: snap["fecha"])
            else:
                chosen = min(valid, key=lambda snap: snap["fecha"])
                meta["fallback_used"] = True
                meta["reason"] = "no_past_snapshot"
        else:
            if valid:
                chosen = max(valid, key=lambda snap: snap["fecha"])
            else:
                chosen = snapshots[-1]
            meta["fallback_used"] = True
            meta["reason"] = "case_date_missing_or_invalid"
        if chosen is None:
            chosen = max(valid, key=lambda snap: snap["fecha"]) if valid else snapshots[-1]
        meta["selected_date"] = chosen.get("fecha") if chosen else None
        return dict(chosen.get("data", {})), meta


__all__ = ["CatalogService", "TeamHierarchyCatalog"]


class TeamHierarchyCatalog:
    """Catálogo en memoria derivado de ``team_details.csv``.

    Construye una jerarquía división → área → servicio → puesto, además de
    catálogos de agencias asociados a la combinación división/área. Las búsquedas
    son insensibles a mayúsculas y acentos para facilitar coincidencias en
    formularios.
    """

    def __init__(
        self,
        rows: Iterable[dict] | None = None,
        hierarchy: dict | None = None,
    ):
        self._divisions: dict[str, str] = {}
        self._areas: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
        self._area_labels: dict[str, dict[str, str]] = {}
        self._service_labels: dict[tuple[str, str], dict[str, str]] = {}
        self._role_labels: dict[tuple[str, str, str], dict[str, str]] = {}
        self._agencies_by_scope: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
        self._agencies_by_code: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
        self._hierarchy_dict: dict = hierarchy or TEAM_HIERARCHY_CATALOG
        for row in rows or ():
            self._ingest_row(row)

    @staticmethod
    def _normalize(value: str) -> str:
        return normalize_without_accents((value or "").strip()).lower()

    @property
    def has_data(self) -> bool:
        return bool(self._divisions or self._hierarchy_dict)

    @property
    def hierarchy_dict(self) -> dict:
        return self._hierarchy_dict

    @staticmethod
    def _label_for(entry: dict, key: str) -> str:
        if not isinstance(entry, dict):
            return str(entry).strip()
        return (entry.get("nbr") or entry.get("abr") or str(key)).strip()

    def _sorted_option_pairs(self, mapping: dict[str, dict]) -> list[tuple[str, str]]:
        return sorted(
            ((key, self._label_for(data or {}, key)) for key, data in (mapping or {}).items()),
            key=lambda item: item[1].casefold(),
        )

    def _match_entry(self, mapping: dict[str, dict], value: str) -> tuple[str, dict, str] | tuple[None, None, None]:
        normalized_value = self._normalize(value)
        for key, data in (mapping or {}).items():
            label = self._label_for(data or {}, key)
            if normalized_value in {self._normalize(key), self._normalize(label)}:
                return key, data or {}, label
        return None, None, None

    def list_hierarchy_divisions(self) -> list[tuple[str, str]]:
        pairs = self._sorted_option_pairs(self._hierarchy_dict)
        if not self._divisions:
            return pairs

        known = {self._normalize(label) for _, label in pairs}
        extras = sorted(
            (
                (label, label)
                for label in self._divisions.values()
                if self._normalize(label) not in known
            ),
            key=lambda item: item[1].casefold(),
        )
        return pairs + extras

    def hierarchy_contains_division(self, division: str) -> bool:
        key, _, _ = self._match_entry(self._hierarchy_dict, division)
        return bool(key)

    def list_hierarchy_areas(self, division: str) -> list[tuple[str, str]]:
        div_key, entry, _ = self._match_entry(self._hierarchy_dict, division)
        if not div_key or entry is None:
            if self.contains_division(division):
                return sorted(
                    ((label, label) for label in self.list_areas(division)),
                    key=lambda item: item[1].casefold(),
                )
            return []
        areas = entry.get("areas") or {}
        services = entry.get("services") or {}
        if areas:
            return self._sorted_option_pairs(areas)
        if services:
            return self._sorted_option_pairs(services)
        return []

    def hierarchy_contains_area(self, division: str, area: str) -> bool:
        div_key, entry, _ = self._match_entry(self._hierarchy_dict, division)
        if not div_key:
            return False
        areas = entry.get("areas") or {}
        services = entry.get("services") or {}
        if areas:
            area_key, _, _ = self._match_entry(areas, area)
            return bool(area_key)
        area_key, _, _ = self._match_entry(services, area)
        return bool(area_key)

    def list_hierarchy_services(self, division: str, area: str) -> list[tuple[str, str]]:
        div_key, entry, _ = self._match_entry(self._hierarchy_dict, division)
        if not div_key:
            if self.contains_division(division):
                return sorted(
                    ((label, label) for label in self.list_services(division, area)),
                    key=lambda item: item[1].casefold(),
                )
            return []
        areas = entry.get("areas") or {}
        services = entry.get("services") or {}
        if areas:
            area_key, area_entry, _ = self._match_entry(areas, area)
            if not area_key:
                return sorted(
                    ((label, label) for label in self.list_services(division, area)),
                    key=lambda item: item[1].casefold(),
                )
            nested_services = area_entry.get("services") or {}
            if nested_services:
                return self._sorted_option_pairs(nested_services)
            if area_entry.get("positions"):
                return [(area_key, self._label_for(area_entry, area_key))]
        fallback_services = self.list_services(division, area)
        if fallback_services:
            fallback_pairs = [(label, label) for label in fallback_services]
            if services:
                static_pairs = self._sorted_option_pairs(services)
                known = {self._normalize(label) for _, label in static_pairs}
                extras = [
                    (value, value)
                    for value in fallback_services
                    if self._normalize(value) not in known
                ]
                return sorted(static_pairs + extras, key=lambda item: item[1].casefold())
            return sorted(fallback_pairs, key=lambda item: item[1].casefold())
        return self._sorted_option_pairs(services)

    def hierarchy_contains_service(self, division: str, area: str, servicio: str) -> bool:
        div_key, entry, _ = self._match_entry(self._hierarchy_dict, division)
        if not div_key:
            return False
        areas = entry.get("areas") or {}
        services = entry.get("services") or {}
        if areas:
            area_key, area_entry, _ = self._match_entry(areas, area)
            if not area_key:
                return False
            nested_services = area_entry.get("services") or {}
            serv_key, _, _ = self._match_entry(nested_services, servicio)
            if serv_key:
                return True
            return bool(area_entry.get("positions") and self._normalize(area) == self._normalize(servicio))
        serv_key, _, _ = self._match_entry(services, servicio)
        return bool(serv_key)

    def list_hierarchy_roles(self, division: str, area: str, servicio: str) -> list[tuple[str, str]]:
        div_key, entry, _ = self._match_entry(self._hierarchy_dict, division)
        if not div_key:
            return []
        areas = entry.get("areas") or {}
        services = entry.get("services") or {}
        positions: dict[str, str] = {}
        if areas:
            area_key, area_entry, _ = self._match_entry(areas, area)
            if not area_key:
                return []
            nested_services = area_entry.get("services") or {}
            if nested_services:
                serv_key, service_entry, _ = self._match_entry(nested_services, servicio)
                if not serv_key:
                    return []
                positions = service_entry.get("positions") or {}
            else:
                positions = area_entry.get("positions") or {}
        else:
            serv_key, service_entry, _ = self._match_entry(services, servicio or area)
            if not serv_key:
                return []
            nested_services = service_entry.get("services") or {}
            if nested_services:
                nested_key, nested_entry, _ = self._match_entry(nested_services, servicio)
                if nested_key:
                    positions = nested_entry.get("positions") or {}
            else:
                positions = service_entry.get("positions") or {}
        return self._sorted_option_pairs(positions)

    def _remember(self, container: dict[str, str], key: str, label: str) -> str:
        if key not in container and label:
            container[key] = label
        return container.get(key, label)

    def _ingest_row(self, row: dict) -> None:
        division = (row.get("division") or "").strip()
        area = (row.get("area") or "").strip()
        servicio = (row.get("servicio") or "").strip()
        puesto = (row.get("puesto") or "").strip()
        agency_name = (row.get("nombre_agencia") or "").strip()
        agency_code = (row.get("codigo_agencia") or "").strip()

        div_key = self._normalize(division)
        area_key = self._normalize(area)
        serv_key = self._normalize(servicio)
        puesto_key = self._normalize(puesto)

        if div_key:
            division_label = self._remember(self._divisions, div_key, division)
            areas = self._areas.setdefault(div_key, {})
            if area_key:
                area_label = self._remember(self._area_labels.setdefault(div_key, {}), area_key, area)
                servicios = areas.setdefault(area_key, {})
                if serv_key:
                    self._remember(
                        self._service_labels.setdefault((div_key, area_key), {}),
                        serv_key,
                        servicio,
                    )
                    puestos = servicios.setdefault(serv_key, {})
                    if puesto_key:
                        self._remember(
                            self._role_labels.setdefault((div_key, area_key, serv_key), {}),
                            puesto_key,
                            puesto,
                        )
                if agency_name or agency_code:
                    self._remember_agency(div_key, area_key, area_label, agency_name, agency_code)

    def _remember_agency(
        self,
        div_key: str,
        area_key: str,
        area_label: str,
        agency_name: str,
        agency_code: str,
    ) -> None:
        scope = (div_key, area_key)
        normalized_name = self._normalize(agency_name)
        normalized_code = agency_code.strip()
        if normalized_name:
            agencies = self._agencies_by_scope.setdefault(scope, {})
            current = agencies.get(normalized_name)
            if not current:
                agencies[normalized_name] = {
                    "nombre": agency_name,
                    "codigo": agency_code,
                    "area": area_label,
                }
            elif agency_code and not current.get("codigo"):
                current["codigo"] = agency_code
        if normalized_code:
            code_map = self._agencies_by_code.setdefault(scope, {})
            current = code_map.get(normalized_code)
            if not current:
                code_map[normalized_code] = {
                    "nombre": agency_name,
                    "codigo": agency_code,
                    "area": area_label,
                }
            elif agency_name and not current.get("nombre"):
                current["nombre"] = agency_name

    def _sorted_labels(self, mapping: dict[str, str]) -> list[str]:
        return sorted(mapping.values(), key=str.casefold)

    def list_divisions(self) -> list[str]:
        return self._sorted_labels(self._divisions)

    def list_areas(self, division: str) -> list[str]:
        div_key = self._normalize(division)
        return self._sorted_labels(self._area_labels.get(div_key, {}))

    def list_services(self, division: str, area: str) -> list[str]:
        div_key = self._normalize(division)
        area_key = self._normalize(area)
        services = self._service_labels.get((div_key, area_key), {})
        return self._sorted_labels(services)

    def list_roles(self, division: str, area: str, servicio: str) -> list[str]:
        div_key = self._normalize(division)
        area_key = self._normalize(area)
        serv_key = self._normalize(servicio)
        puestos = self._role_labels.get((div_key, area_key, serv_key), {})
        return self._sorted_labels(puestos)

    def list_agency_names(self, division: str, area: str) -> list[str]:
        scope = (self._normalize(division), self._normalize(area))
        agencies = self._agencies_by_scope.get(scope, {})
        return self._sorted_labels({key: value.get("nombre", "") for key, value in agencies.items() if value.get("nombre")})

    def list_agency_codes(self, division: str, area: str) -> list[str]:
        scope = (self._normalize(division), self._normalize(area))
        agencies = self._agencies_by_code.get(scope, {})
        return sorted({value.get("codigo", "") for value in agencies.values() if value.get("codigo")})

    def contains_division(self, division: str) -> bool:
        return bool(self._normalize(division) and self._normalize(division) in self._divisions)

    def contains_area(self, division: str, area: str) -> bool:
        div_key = self._normalize(division)
        area_key = self._normalize(area)
        return bool(div_key and area_key and area_key in self._area_labels.get(div_key, {}))

    def contains_service(self, division: str, area: str, servicio: str) -> bool:
        div_key = self._normalize(division)
        area_key = self._normalize(area)
        serv_key = self._normalize(servicio)
        return bool(
            div_key
            and area_key
            and serv_key
            and serv_key in self._service_labels.get((div_key, area_key), {})
        )

    def contains_role(self, division: str, area: str, servicio: str, puesto: str) -> bool:
        div_key = self._normalize(division)
        area_key = self._normalize(area)
        serv_key = self._normalize(servicio)
        puesto_key = self._normalize(puesto)
        roles = self._role_labels.get((div_key, area_key, serv_key), {})
        return bool(div_key and area_key and serv_key and puesto_key and puesto_key in roles)

    def match_agency_by_name(self, division: str, area: str, name: str) -> dict[str, str] | None:
        scope = (self._normalize(division), self._normalize(area))
        normalized_name = self._normalize(name)
        return self._agencies_by_scope.get(scope, {}).get(normalized_name)

    def match_agency_by_code(self, division: str, area: str, code: str) -> dict[str, str] | None:
        scope = (self._normalize(division), self._normalize(area))
        normalized_code = (code or "").strip()
        return self._agencies_by_code.get(scope, {}).get(normalized_code)

