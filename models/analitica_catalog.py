"""Catálogo estático para analíticas contables y utilidades asociadas."""

from __future__ import annotations

from typing import Dict, List, Tuple

from validators import normalize_without_accents


ANALITICA_CATALOG: Dict[str, str] = {
    "4300000000": "Analítica crédito preventivo",
    "4300000001": "Analítica catálogo",
    "4300000002": "Analítica contingencia crédito",
    "4300000010": "Auto analítica",
    "4310000001": "Analítica H",
    "4500000001": "Analítica de fraude externo",
    "4500000002": "Analítica I",
    "4600000002": "Analítica contingencia crédito",
}


def get_analitica_catalog() -> Dict[str, str]:
    """Devuelve una copia superficial del catálogo código → nombre."""

    return dict(ANALITICA_CATALOG)


def get_analitica_codes() -> List[str]:
    """Lista de códigos ordenados para poblar combobox de códigos."""

    return sorted(ANALITICA_CATALOG.keys())


def get_analitica_names() -> List[str]:
    """Lista de nombres ordenada según los códigos del catálogo."""

    return [ANALITICA_CATALOG[code] for code in get_analitica_codes()]


def format_analitica_option(code: str) -> str:
    """Compone la etiqueta mostrable "código – nombre" si existe en el catálogo."""

    trimmed = (code or "").strip()
    name = ANALITICA_CATALOG.get(trimmed)
    return f"{trimmed} – {name}" if trimmed and name else trimmed


def get_analitica_display_options() -> List[str]:
    """Lista de opciones de cabecera que combinan código y nombre."""

    return [format_analitica_option(code) for code in get_analitica_codes()]


def _normalize_name(value: str) -> str:
    return normalize_without_accents(value).strip().lower()


def find_analitica_by_code(code: str) -> Tuple[str, str] | None:
    """Busca una analítica por código exacto."""

    trimmed = (code or "").strip()
    if not trimmed:
        return None
    name = ANALITICA_CATALOG.get(trimmed)
    if not name:
        return None
    return trimmed, name


def find_analitica_by_name(name: str) -> Tuple[str, str] | None:
    """Busca una analítica normalizando acentos y mayúsculas."""

    normalized = _normalize_name(name)
    if not normalized:
        return None
    for code, label in ANALITICA_CATALOG.items():
        if _normalize_name(label) == normalized:
            return code, label
    return None


def extract_code_from_display(value: str) -> str:
    """Obtiene solo el código desde una etiqueta "código – nombre"."""

    text = (value or "").strip()
    if not text:
        return ""
    if "–" in text:
        return text.split("–", 1)[0].strip()
    if "-" in text:
        return text.split("-", 1)[0].strip()
    return text


__all__ = [
    "ANALITICA_CATALOG",
    "extract_code_from_display",
    "find_analitica_by_code",
    "find_analitica_by_name",
    "format_analitica_option",
    "get_analitica_catalog",
    "get_analitica_codes",
    "get_analitica_display_options",
    "get_analitica_names",
]

