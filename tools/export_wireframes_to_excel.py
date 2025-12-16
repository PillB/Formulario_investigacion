"""Exporta un wireframe aproximado de la interfaz Tkinter a Excel.

El script instancia la aplicación real, recorre los widgets colocados en las
seis pestañas principales y los proyecta a una cuadrícula de Excel usando
``openpyxl``. Cada celda queda etiquetada con el tipo de control (texto,
número, selección única, multiselección o autocompletar), su estado (por
ejemplo, readonly) y la sección a la que pertenece. Se aplican colores y una
leyenda para distinguir rápidamente campos, botones y badges de validación.

Ejemplo de uso::

    python tools/export_wireframes_to_excel.py \
        --output wireframes/Formulario_UI_wireframe.xlsx

El recorrido evita modificar datos persistentes utilizando el modo de arranque
de pruebas y seleccionando la opción de "nuevo caso" para construir la UI sin
diálogos.
"""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import tkinter as tk
from tkinter import TclError, scrolledtext, ttk

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, range_boundaries

from app import FraudCaseApp
from validation_badge.validation_badge import (
    NEUTRAL_STYLE,
    SUCCESS_STYLE,
    WARNING_STYLE,
    ValidationBadge,
)


CELL_WIDTH_PX = 48
CELL_HEIGHT_PX = 26

STYLE_MAP = {
    "text": PatternFill("solid", fgColor="DDEBF7"),
    "number": PatternFill("solid", fgColor="FFE699"),
    "single-select": PatternFill("solid", fgColor="E2EFDA"),
    "multi-select": PatternFill("solid", fgColor="DDD9C3"),
    "autocomplete": PatternFill("solid", fgColor="C6E0B4"),
    "action": PatternFill("solid", fgColor="D9D9D9"),
    "badge": PatternFill("solid", fgColor="F8CBAD"),
    "label": PatternFill("solid", fgColor="F2F2F2"),
}


@dataclass
class WidgetRecord:
    label: str
    widget_type: str
    control_kind: str
    state: str | None
    sticky: str | None
    section_path: tuple[str, ...]
    x: int
    y: int
    width: int
    height: int
    grid_row: int | None
    grid_column: int | None
    grid_rowspan: int | None
    grid_colspan: int | None


def _safe_grid_info(widget) -> dict:
    try:
        info = widget.grid_info()
        return info or {}
    except Exception:
        return {}


def _widget_text(widget) -> str:
    getter = getattr(widget, "cget", None)
    if callable(getter):
        try:
            text = getter("text")
        except Exception:
            text = ""
        if text:
            return str(text)
    return ""


def _infer_label_for_widget(widget) -> str:
    parent = getattr(widget, "master", None)
    if parent is None:
        return ""
    target_info = _safe_grid_info(widget)
    if not target_info:
        return ""
    try:
        target_row = int(target_info.get("row", 0))
        target_col = int(target_info.get("column", 0))
    except Exception:
        return ""

    for sibling in parent.winfo_children():
        if sibling is widget:
            continue
        if not isinstance(sibling, (ttk.Label, tk.Label)):
            continue
        info = _safe_grid_info(sibling)
        try:
            row = int(info.get("row", 0))
            col = int(info.get("column", 0))
        except Exception:
            continue
        if col == target_col and row in {target_row, target_row - 1}:
            text = _widget_text(sibling)
            if text:
                return text
    return ""


def _control_kind(widget, label: str) -> str:
    lower_label = label.lower()
    if isinstance(widget, ValidationBadge):
        return "badge"
    if isinstance(widget, ttk.Combobox):
        state = _safe_cget(widget, "state")
        return "single-select" if state == "readonly" else "autocomplete"
    if isinstance(widget, (ttk.Treeview,)):
        return "multi-select"
    if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
        return "multi-select"
    if isinstance(widget, (ttk.Checkbutton, ttk.Radiobutton)):
        return "single-select"
    if isinstance(widget, ttk.Button):
        return "action"
    if isinstance(widget, (ttk.Label, tk.Label)):
        style = (_safe_cget(widget, "style") or "").strip()
        if style in {WARNING_STYLE, SUCCESS_STYLE, NEUTRAL_STYLE}:
            return "badge"
        return "label"
    if isinstance(widget, (ttk.Entry, tk.Entry)):
        if any(token in lower_label for token in ("monto", "importe", "pago", "%")):
            return "number"
        if any(token in lower_label for token in ("código", "codigo", "id", "número", "numero")):
            return "text"
        return "text"
    return "text"


def _safe_cget(widget, option: str) -> str | None:
    getter = getattr(widget, "cget", None)
    if callable(getter):
        try:
            return getter(option)
        except Exception:
            return None
    return None


def _resolve_state(widget) -> str | None:
    for option in ("state", "values"):
        value = _safe_cget(widget, option)
        if value not in (None, "", ()):  # type: ignore[comparison-overlap]
            if option == "values" and isinstance(widget, ttk.Combobox):
                continue
            return str(value)
    return None


def _measure_widget(widget, origin_x: int, origin_y: int) -> tuple[int, int, int, int]:
    x = max(0, widget.winfo_rootx() - origin_x)
    y = max(0, widget.winfo_rooty() - origin_y)
    width = widget.winfo_width() or widget.winfo_reqwidth()
    height = widget.winfo_height() or widget.winfo_reqheight()
    return x, y, width, height


def _iter_widget_records(
    root_widget, origin_x: int, origin_y: int, section_stack: tuple[str, ...]
) -> Iterator[WidgetRecord]:
    for child in root_widget.winfo_children():
        try:
            mapped = child.winfo_ismapped()
        except Exception:
            mapped = True
        if not mapped:
            continue

        if isinstance(child, (ttk.LabelFrame, tk.LabelFrame)):
            text = _widget_text(child)
            next_stack = (*section_stack, text) if text else section_stack
            yield from _iter_widget_records(child, origin_x, origin_y, next_stack)
            continue

        text = _widget_text(child) or _infer_label_for_widget(child)
        is_relevant = isinstance(
            child,
            (
                ttk.Entry,
                tk.Entry,
                ttk.Combobox,
                tk.Text,
                scrolledtext.ScrolledText,
                ttk.Treeview,
                ttk.Button,
                ttk.Label,
                tk.Label,
                ttk.Checkbutton,
                ttk.Radiobutton,
                ValidationBadge,
            ),
        )
        if not is_relevant:
            yield from _iter_widget_records(child, origin_x, origin_y, section_stack)
            continue

        x, y, width, height = _measure_widget(child, origin_x, origin_y)
        if width <= 1 or height <= 1:
            continue

        grid_info = _safe_grid_info(child)
        record = WidgetRecord(
            label=text or child.__class__.__name__,
            widget_type=child.__class__.__name__,
            control_kind=_control_kind(child, text),
            state=_resolve_state(child),
            sticky=grid_info.get("sticky"),
            section_path=section_stack,
            x=x,
            y=y,
            width=width,
            height=height,
            grid_row=int(grid_info.get("row", 0)) if grid_info else None,
            grid_column=int(grid_info.get("column", 0)) if grid_info else None,
            grid_rowspan=int(grid_info.get("rowspan", 1)) if grid_info else None,
            grid_colspan=int(grid_info.get("columnspan", 1)) if grid_info else None,
        )
        yield record
        yield from _iter_widget_records(child, origin_x, origin_y, section_stack)


def _normalize_to_cells(record: WidgetRecord, *, row_offset: int) -> tuple[int, int, int, int]:
    row = row_offset + math.floor(record.y / CELL_HEIGHT_PX) + 1
    column = math.floor(record.x / CELL_WIDTH_PX) + 1
    row_span = max(1, math.ceil(record.height / CELL_HEIGHT_PX))
    column_span = max(1, math.ceil(record.width / CELL_WIDTH_PX))
    return row, column, row_span, column_span


def _add_legend(sheet, start_row: int = 1) -> int:
    sheet.cell(row=start_row, column=1, value="Leyenda de controles").font = Font(bold=True)
    row = start_row + 1
    border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
    for label, fill in STYLE_MAP.items():
        cell = sheet.cell(row=row, column=1, value=label)
        cell.fill = fill
        cell.border = border
        cell.alignment = Alignment(horizontal="center")
        row += 1
    sheet.cell(row=row, column=1, value="Las celdas incluyen estado y sticky en comentarios.")
    return row + 1


def _place_records(sheet, records: Iterable[WidgetRecord], *, row_offset: int) -> None:
    merged_ranges = []
    max_col = 1
    border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
    for record in records:
        row, col, row_span, col_span = _normalize_to_cells(record, row_offset=row_offset)
        max_col = max(max_col, col + col_span)
        cell = sheet.cell(row=row, column=col, value=record.label)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = border
        style = STYLE_MAP.get(record.control_kind)
        if style:
            cell.fill = style
        comment_lines = [f"Widget: {record.widget_type}", f"Tipo de control: {record.control_kind}"]
        if record.state:
            comment_lines.append(f"Estado: {record.state}")
        if record.section_path:
            comment_lines.append(f"Sección: {' > '.join(filter(None, record.section_path))}")
        comment_lines.append(
            f"Grid(row={record.grid_row}, col={record.grid_column}, rowspan={record.grid_rowspan}, colspan={record.grid_colspan}, sticky={record.sticky})"
        )
        cell.comment = Comment("\n".join(comment_lines), "wireframe")
        if row_span > 1 or col_span > 1:
            target = f"{get_column_letter(col)}{row}:{get_column_letter(col + col_span - 1)}{row + row_span - 1}"
            conflict = any(_ranges_overlap(rng.coord, target) for rng in merged_ranges)
            if not conflict:
                sheet.merge_cells(target)
                merged_ranges.append(sheet.merged_cells.ranges[-1])
    for column in range(1, max_col + 2):
        sheet.column_dimensions[get_column_letter(column)].width = 18


def _ranges_overlap(existing: str, target: str) -> bool:
    min_col, min_row, max_col, max_row = range_boundaries(existing)
    t_min_col, t_min_row, t_max_col, t_max_row = range_boundaries(target)
    rows_overlap = not (max_row < t_min_row or t_max_row < min_row)
    cols_overlap = not (max_col < t_min_col or t_max_col < min_col)
    return rows_overlap and cols_overlap


def _build_app() -> FraudCaseApp:
    os.environ.setdefault("PYTEST_CURRENT_TEST", "wireframe_export")
    os.environ.setdefault("APP_START_CHOICE", "new")
    try:
        root = tk.Tk()
        root.withdraw()
        root.geometry("1400x900")
    except TclError as exc:  # pragma: no cover - entornos sin display
        raise SystemExit("Tkinter no disponible en el entorno actual") from exc
    return FraudCaseApp(root)


def _collect_tab_records(app: FraudCaseApp) -> dict[str, list[WidgetRecord]]:
    records: dict[str, list[WidgetRecord]] = {}
    for tab_id in app.notebook.tabs():
        title = app.notebook.tab(tab_id, "text")
        tab_widget = app.notebook.nametowidget(tab_id)
        try:
            app.notebook.select(tab_id)
        except Exception:
            pass
        app.root.update_idletasks()
        origin_x, origin_y = tab_widget.winfo_rootx(), tab_widget.winfo_rooty()
        tab_records = list(_iter_widget_records(tab_widget, origin_x, origin_y, (title,)))
        records[title] = tab_records
    return records


def export_wireframes(output_path: Path) -> Path:
    app = _build_app()
    try:
        app.root.update_idletasks()
        tab_records = _collect_tab_records(app)
    finally:
        try:
            app.root.destroy()
        except Exception:
            pass

    wb = Workbook()
    default_sheet = wb.active
    wb.remove(default_sheet)

    for tab_name, records in tab_records.items():
        sheet = wb.create_sheet(title=tab_name[:31])
        next_row = _add_legend(sheet)
        header_row = next_row + 1
        sheet.cell(row=header_row, column=1, value=f"Tab: {tab_name}").font = Font(bold=True)
        _place_records(sheet, records, row_offset=header_row + 1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("wireframes/Formulario_UI_wireframe.xlsx"),
        help="Ruta del archivo Excel a generar.",
    )
    args = parser.parse_args()
    output = export_wireframes(args.output)
    print(f"Wireframe exportado en: {output}")


if __name__ == "__main__":  # pragma: no cover - punto de entrada manual
    main()
