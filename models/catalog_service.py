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
from validators import normalize_team_member_identifier

from .catalogs import (build_detail_catalog_id_index, load_detail_catalogs,
                       normalize_detail_catalog_key)


class CatalogService:
    """Encapsula la carga de catálogos y consultas temporales."""

    def __init__(self, base_dir: str | os.PathLike = BASE_DIR):
        self.base_dir = Path(base_dir)
        self.detail_catalogs: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.detail_lookup_by_id: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.team_snapshots: Dict[str, list[dict]] = {}

    def refresh(self) -> Tuple[Dict[str, Dict[str, Dict[str, str]]], Dict[str, Dict[str, Dict[str, str]]]]:
        raw_catalogs = load_detail_catalogs(self.base_dir)
        normalized, lookup_by_id = self._normalize_catalogs(raw_catalogs)
        self.detail_catalogs = normalized
        self.detail_lookup_by_id = lookup_by_id
        self.team_snapshots = self._build_team_snapshots()
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

    def _build_team_snapshots(self) -> Dict[str, list[dict]]:
        path = self.base_dir / "team_details.csv"
        if not path.exists():
            return {}
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
        return snapshots

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
    ) -> Tuple[Dict[str, str] | None, bool]:
        normalized_id = normalize_team_member_identifier(identifier)
        if not normalized_id:
            return None, False
        snapshots = self.team_snapshots.get(normalized_id)
        if not snapshots:
            return None, False
        case_date = self._parse_date(occurrence_date)
        valid = [snap for snap in snapshots if snap.get("fecha") is not None]
        chosen = None
        future_fallback = False
        if case_date and valid:
            history = [snap for snap in valid if snap["fecha"] <= case_date]
            if history:
                chosen = max(history, key=lambda snap: snap["fecha"])
            else:
                chosen = min(valid, key=lambda snap: snap["fecha"])
                future_fallback = True
        if chosen is None:
            chosen = max(valid, key=lambda snap: snap["fecha"]) if valid else snapshots[-1]
        return dict(chosen.get("data", {})), future_fallback


__all__ = ["CatalogService"]
