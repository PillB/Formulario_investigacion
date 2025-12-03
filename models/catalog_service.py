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


class CatalogService:
    """Encapsula la carga de catálogos y consultas temporales."""

    def __init__(self, base_dir: str | os.PathLike = BASE_DIR):
        self.base_dir = Path(base_dir)
        self.detail_catalogs: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.detail_lookup_by_id: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.team_snapshots: Dict[str, list[dict]] = {}
        self.team_hierarchy: TeamHierarchyCatalog = TeamHierarchyCatalog()

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
        if not path.exists():
            return {}, TeamHierarchyCatalog()

        rows = list(self._iter_rows(path))
        snapshots: Dict[str, list[dict]] = {}
        for row in rows:
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

        return snapshots, TeamHierarchyCatalog(rows)

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

    def __init__(self, rows: Iterable[dict] | None = None):
        self._divisions: dict[str, str] = {}
        self._areas: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
        self._area_labels: dict[str, dict[str, str]] = {}
        self._service_labels: dict[tuple[str, str], dict[str, str]] = {}
        self._role_labels: dict[tuple[str, str, str], dict[str, str]] = {}
        self._agencies_by_scope: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
        self._agencies_by_code: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
        for row in rows or ():
            self._ingest_row(row)

    @staticmethod
    def _normalize(value: str) -> str:
        return normalize_without_accents((value or "").strip()).lower()

    @property
    def has_data(self) -> bool:
        return bool(self._divisions)

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

