"""Utilidades de estilo reutilizables para la generación de reportes DOCX.

Este módulo centraliza la aplicación de tipografías, sombreados y bordes
para que ``build_docx`` mantenga una apariencia consistente y fácil de
probar.
"""

from __future__ import annotations

from typing import Iterable, Optional, Set

try:  # ``python-docx`` es opcional
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    from docx.shared import RGBColor, Pt
except ImportError:  # pragma: no cover - la comprobación se valida en pruebas
    WD_ALIGN_PARAGRAPH = None
    parse_xml = None
    nsdecls = None
    RGBColor = None
    Pt = None

DOCX_STYLING_AVAILABLE = all([parse_xml, nsdecls, RGBColor, Pt, WD_ALIGN_PARAGRAPH])

# Paleta corporativa utilizada en los reportes
BCP_DARK_BLUE = RGBColor(0, 48, 135) if DOCX_STYLING_AVAILABLE else None
WHITE = RGBColor(255, 255, 255) if DOCX_STYLING_AVAILABLE else None
LIGHT_GRAY = "F5F5F5"
BORDER_GRAY = "D9D9D9"


def _require_docx() -> None:
    if not DOCX_STYLING_AVAILABLE:
        raise ModuleNotFoundError(
            "La dependencia opcional 'python-docx' es requerida para aplicar estilos."
        )


def _set_run_style(run, *, font_name: str, font_size: Pt, color: RGBColor, bold: bool = False) -> None:
    _require_docx()
    font = run.font
    font.name = font_name
    font.size = font_size
    font.color.rgb = color
    font.bold = bold


def style_title(paragraph) -> None:
    """Aplica la tipografía principal de títulos."""

    _require_docx()
    for run in paragraph.runs:
        _set_run_style(run, font_name="Segoe UI", font_size=Pt(20), color=BCP_DARK_BLUE)


def style_section_heading(paragraph) -> None:
    """Aplica la tipografía para subtítulos de sección."""

    _require_docx()
    for run in paragraph.runs:
        _set_run_style(
            run,
            font_name="Segoe UI Semibold",
            font_size=Pt(14),
            color=BCP_DARK_BLUE,
            bold=True,
        )


def apply_cell_shading(cell, fill: str) -> None:
    """Agrega sombreado a una celda usando un código hexadecimal."""

    _require_docx()
    shading = parse_xml(rf'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{fill}" />')
    cell._tc.get_or_add_tcPr().append(shading)


def apply_header_style(table, *, fill: str = "003087") -> None:
    """Colorea la fila de encabezado con texto claro y negrita."""

    _require_docx()
    if not table.rows:
        return
    for cell in table.rows[0].cells:
        apply_cell_shading(cell, fill)
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                _set_run_style(run, font_name="Segoe UI Semibold", font_size=Pt(11), color=WHITE, bold=True)


def apply_header_band(rows: Iterable, *, alignment: WD_ALIGN_PARAGRAPH | None = None) -> None:
    """Colorea filas con la banda azul corporativa y texto claro alineado."""

    _require_docx()
    effective_alignment = alignment or WD_ALIGN_PARAGRAPH.LEFT
    for row in rows:
        cells = getattr(row, "cells", row)
        for cell in cells:
            apply_cell_shading(cell, "003087")
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.alignment = effective_alignment
                for run in paragraph.runs:
                    _set_run_style(
                        run,
                        font_name="Segoe UI Semibold",
                        font_size=Pt(11),
                        color=WHITE,
                        bold=True,
                    )


def apply_zebra_striping(table, *, skip_rows: Optional[Set[int]] = None, fill: str = LIGHT_GRAY) -> None:
    """Aplica franjas alternas a la tabla, omitiendo los índices indicados."""

    _require_docx()
    skip_rows = skip_rows or set()
    for row_idx, row in enumerate(table.rows[1:], start=1):
        if row_idx in skip_rows:
            continue
        if row_idx % 2 == 0:
            for cell in row.cells:
                apply_cell_shading(cell, fill)


def apply_table_borders(table, *, color: str = BORDER_GRAY) -> None:
    """Dibuja bordes discretos alrededor de la tabla."""

    _require_docx()
    borders_xml = (
        r'<w:tblBorders {decl}>'
        r'<w:top w:val="single" w:sz="4" w:space="0" w:color="{color}" />'
        r'<w:left w:val="single" w:sz="4" w:space="0" w:color="{color}" />'
        r'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{color}" />'
        r'<w:right w:val="single" w:sz="4" w:space="0" w:color="{color}" />'
        r'</w:tblBorders>'
    ).format(decl=nsdecls("w"), color=color)

    tbl_pr = table._tbl.tblPr
    if tbl_pr is None:
        tbl_pr = parse_xml(rf'<w:tblPr {nsdecls("w")} />')
        table._tbl.append(tbl_pr)
    tbl_pr.append(parse_xml(borders_xml))


def style_table(table, *, zebra_skip_rows: Optional[Iterable[int]] = None) -> None:
    """Compone los estilos de tabla: encabezado, zebra y bordes."""

    zebra_rows = set(zebra_skip_rows or [])
    apply_header_style(table)
    apply_zebra_striping(table, skip_rows=zebra_rows)
    apply_table_borders(table)
