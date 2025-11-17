"""Funciones para cargar catálogos y archivos masivos."""

from __future__ import annotations

import csv
import os
from typing import Dict, Iterable, Iterator, List, Tuple

from settings import (
    BASE_DIR,
    CLIENT_DETAILS_FILE,
    PRODUCT_DETAILS_FILE,
    TEAM_DETAILS_FILE,
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


def load_team_details() -> Dict[str, Dict[str, str]]:
    """Carga los datos de colaboradores desde ``team_details.csv`` si existe."""

    lookup: Dict[str, Dict[str, str]] = {}
    try:
        with open(TEAM_DETAILS_FILE, newline='', encoding="utf-8-sig") as file_handle:
            reader = csv.DictReader(line for line in file_handle if line.strip())
            for row in reader:
                key = row.get("id_colaborador") or row.get("IdTeamMember") or row.get("Id")
                if key:
                    lookup[key.strip()] = {
                        "division": row.get("division", "").strip(),
                        "area": row.get("area", "").strip(),
                        "servicio": row.get("servicio", "").strip(),
                        "puesto": row.get("puesto", "").strip(),
                        "nombre_agencia": row.get("nombre_agencia", "").strip(),
                        "codigo_agencia": row.get("codigo_agencia", "").strip(),
                    }
    except FileNotFoundError:
        pass
    return lookup


def load_client_details() -> Dict[str, Dict[str, str]]:
    """Carga los datos de clientes desde ``client_details.csv`` si existe."""

    lookup: Dict[str, Dict[str, str]] = {}
    try:
        with open(CLIENT_DETAILS_FILE, newline='', encoding="utf-8-sig") as file_handle:
            reader = csv.DictReader(line for line in file_handle if line.strip())
            for row in reader:
                key = row.get("id_cliente") or row.get("IdCliente") or row.get("IDCliente")
                if key:
                    lookup[key.strip()] = {
                        "tipo_id": row.get("tipo_id", row.get("TipoID", "")).strip(),
                        "flag": row.get("flag", row.get("Flag", "")).strip(),
                        "telefonos": row.get("telefonos", row.get("Telefono", "")).strip(),
                        "correos": row.get("correos", row.get("Correo", "")).strip(),
                        "direcciones": row.get("direcciones", row.get("Direccion", "")).strip(),
                        "accionado": row.get("accionado", row.get("Accionado", "")).strip(),
                    }
    except FileNotFoundError:
        pass
    return lookup


def load_product_details() -> Dict[str, Dict[str, str]]:
    """Carga detalles de productos desde ``productos_masivos.csv`` si existe."""

    lookup: Dict[str, Dict[str, str]] = {}
    try:
        with open(PRODUCT_DETAILS_FILE, newline='', encoding="utf-8-sig") as file_handle:
            reader = csv.DictReader(line for line in file_handle if line.strip())
            for row in reader:
                key = row.get("id_producto") or row.get("IdProducto") or row.get("IDProducto")
                if key:
                    lookup[key.strip()] = {
                        k: (v or "").strip() for k, v in row.items()
                    }
    except FileNotFoundError:
        pass
    return lookup


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
    "iter_massive_csv_rows",
    "load_client_details",
    "load_detail_catalogs",
    "load_product_details",
    "load_team_details",
    "normalize_detail_catalog_key",
    "parse_involvement_entries",
]
