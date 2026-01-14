"""Consolidación histórica de exportaciones.

Antes de este módulo, el flujo de exportación generaba un único CSV por
entidad y sobrescribía su contenido en cada guardado, sin una ruta para
conservar históricamente los casos procesados. Este helper agrega la
persistencia de anexos ``h_*.csv`` con metadatos obligatorios ``case_id`` y
``fecactualizacion`` para auditar los incrementos.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import settings
from validators import sanitize_rich_text

SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _sanitize_value(value: object) -> str:
    sanitized = sanitize_rich_text("" if value is None else str(value), max_chars=None)
    if sanitized == settings.EVENTOS_PLACEHOLDER:
        return sanitized
    if sanitized.startswith(SPREADSHEET_FORMULA_PREFIXES):
        return f"'{sanitized}"
    return sanitized


def append_historical_records(
    table_name: str,
    rows: Iterable[Mapping[str, object]],
    header: Sequence[str],
    base_dir: Path,
    case_id: str,
    *,
    timestamp: datetime | None = None,
    placeholder: str | None = None,
    encoding: str = "utf-8",
):
    """Adjunta registros a ``h_<tabla>.csv`` con metadatos de caso y hora.

    Crea el archivo con encabezados si aún no existe y añade las columnas
    ``case_id`` y ``fecactualizacion`` a cada fila antes de escribirla.
    Devuelve la ruta escrita o ``None`` cuando no hay filas de entrada.
    La codificación se controla con ``encoding``.
    """

    normalized_rows = list(rows or [])
    if not normalized_rows:
        return None

    target_dir = Path(base_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    history_path = target_dir / f"h_{table_name}.csv"
    effective_timestamp = (timestamp or datetime.now()).isoformat()
    full_header = list(header) + ["case_id", "fecactualizacion"]
    should_write_header = not history_path.exists()
    empty_placeholder = placeholder if placeholder is not None else settings.EVENTOS_PLACEHOLDER

    with history_path.open("a", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=full_header)
        if should_write_header:
            writer.writeheader()
        for row in normalized_rows:
            sanitized_row = {
                field: _sanitize_value(row.get(field, empty_placeholder)) for field in header
            }
            sanitized_row["case_id"] = _sanitize_value(case_id)
            sanitized_row["fecactualizacion"] = _sanitize_value(effective_timestamp)
            writer.writerow(sanitized_row)

    return history_path
