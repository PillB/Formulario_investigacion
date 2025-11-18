"""Funciones para cargar catálogos y archivos masivos."""

from __future__ import annotations

import csv
import os
from typing import Dict, Iterable, Iterator, List, Tuple

from settings import (
    BASE_DIR,
    DETAIL_LOOKUP_ALIASES,
)


def normalize_detail_catalog_key(key: str) -> str:
    """Normaliza una clave de catálogo de detalle a minúsculas sin espacios."""

    return (key or "").strip().lower()


def load_detail_catalogs() -> Dict[str, Dict[str, Dict[str, str]]]:
    """Lee todos los archivos ``*_details.csv`` disponibles en la carpeta base."""

    catalogs: Dict[str, Dict[str, Dict[str, str]]] = {}
    try:
        filenames = [
            name
            for name in os.listdir(BASE_DIR)
            if name.lower().endswith("details.csv")
        ]
    except OSError:
        return catalogs

    for filename in filenames:
        path = os.path.join(BASE_DIR, filename)
        entity_name = filename[:-len("_details.csv")].lower()
        try:
            with open(path, newline='', encoding="utf-8-sig") as file_handle:
                reader = csv.DictReader(line for line in file_handle if line.strip())
                fieldnames = reader.fieldnames or []
                key_field = next(
                    (field for field in fieldnames if field and field.lower().startswith("id_")),
                    None,
                )
                if not key_field:
                    continue
                for row in reader:
                    key = (row.get(key_field) or "").strip()
                    if not key:
                        continue
                    catalogs.setdefault(entity_name, {})[key] = {
                        (k or ""): (v or "").strip() for k, v in row.items()
                    }
        except (FileNotFoundError, OSError):
            continue
    return catalogs


def build_detail_catalog_id_index(
    catalogs: Dict[str, Dict[str, Dict[str, str]]]
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """Construye un índice por columnas ``id_*`` reutilizando los catálogos cargados."""

    if not catalogs:
        return {}

    index: Dict[str, Dict[str, Dict[str, str]]] = {}
    for canonical_key, aliases in (DETAIL_LOOKUP_ALIASES or {}).items():
        normalized_canonical = normalize_detail_catalog_key(canonical_key)
        candidate_keys = [normalized_canonical]
        candidate_keys.extend(
            normalize_detail_catalog_key(alias)
            for alias in aliases or ()
        )
        seen = set()
        for candidate in candidate_keys:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            lookup = catalogs.get(candidate)
            if lookup is not None:
                index[normalized_canonical] = lookup
                break
    return index


def iter_massive_csv_rows(filename: str) -> Iterator[Dict[str, str]]:
    """Itera sobre los CSV masivos eliminando filas vacías y espacios extra."""

    with open(filename, newline='', encoding="utf-8-sig") as handle:
        reader = csv.DictReader(line for line in handle if line.strip())
        for row in reader:
            cleaned: Dict[str, str] = {}
            for key, value in row.items():
                if key is None:
                    continue
                key = key.strip()
                if isinstance(value, str):
                    value = value.strip()
                cleaned[key] = value
            if cleaned:
                yield cleaned


def parse_involvement_entries(raw_value: str | Iterable[str]) -> List[Tuple[str, str]]:
    """Parsea la columna de involucramientos proveniente del CSV combinado."""

    if not raw_value:
        return []
    entries: List[Tuple[str, str]] = []
    if isinstance(raw_value, (list, tuple)):
        raw_value = ";".join(raw_value)
    for chunk in str(raw_value).split(';'):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ':' in chunk:
            collaborator, amount = chunk.split(':', 1)
        else:
            collaborator, amount = chunk, ''
        collaborator = collaborator.strip()
        amount = amount.strip()
        if collaborator:
            entries.append((collaborator, amount))
    return entries


__all__ = [
    "build_detail_catalog_id_index",
    "iter_massive_csv_rows",
    "load_detail_catalogs",
    "normalize_detail_catalog_key",
    "parse_involvement_entries",
]
