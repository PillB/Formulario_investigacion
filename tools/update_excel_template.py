"""Actualiza la plantilla normalizada de Excel con campos de normas y validaciones."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Sequence

from openpyxl import load_workbook

from app import EXPORT_HEADERS, FraudCaseApp

NORMAS_COLUMNS: Sequence[str] = tuple(EXPORT_HEADERS["detalles_norma.csv"])

NORMAS_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "id_norma": ("Clave primaria", "Identificador de la norma transgredida (formato XXXX.XXX.XX.XX)."),
    "id_caso": ("Clave foránea", "Identificador del caso; referencia CASOS.id_caso."),
    "descripcion": ("Atributo", "Descripción de la norma transgredida."),
    "fecha_vigencia": ("Atributo", "Fecha de vigencia de la norma (YYYY-MM-DD)."),
    "acapite_inciso": ("Atributo", "Referencia del acápite o inciso aplicable."),
    "detalle_norma": ("Atributo", "Amplía la explicación de la transgresión."),
}

NORMAS_VALIDATIONS: Sequence[tuple[str, str, str, str]] = (
    ("DETALLES_NORMA", "id_norma", "validate_norm_id", "Formato requerido: XXXX.XXX.XX.XX."),
    (
        "DETALLES_NORMA",
        "fecha_vigencia",
        "validate_date_text",
        "Formato YYYY-MM-DD; no debe ser futura.",
    ),
    (
        "DETALLES_NORMA",
        "acapite_inciso",
        "validate_required_text",
        "Campo requerido para registrar la norma.",
    ),
    (
        "DETALLES_NORMA",
        "detalle_norma",
        "validate_required_text",
        "Campo requerido; detalle narrativo de la transgresión.",
    ),
)

SHEET_HEADERS: dict[str, Sequence[str]] = {
    "CASOS": EXPORT_HEADERS["casos.csv"],
    "CLIENTES": EXPORT_HEADERS["clientes.csv"],
    "COLABORADORES": EXPORT_HEADERS["colaboradores.csv"],
    "PRODUCTOS": EXPORT_HEADERS["productos.csv"],
    "PRODUCTO_RECLAMO": EXPORT_HEADERS["producto_reclamo.csv"],
    "INVOLUCRAMIENTO": EXPORT_HEADERS["involucramiento.csv"],
    "DETALLES_RIESGO": EXPORT_HEADERS["detalles_riesgo.csv"],
    "DETALLES_NORMA": EXPORT_HEADERS["detalles_norma.csv"],
    "ANALISIS": EXPORT_HEADERS["analisis.csv"],
}


def _set_header_row(sheet, columns: Sequence[str]) -> None:
    for idx, name in enumerate(columns, start=1):
        sheet.cell(row=1, column=idx, value=name)
    for idx in range(len(columns) + 1, sheet.max_column + 1):
        sheet.cell(row=1, column=idx, value=None)


def _rewrite_rows(sheet, rows: Iterable[Sequence[str]]) -> None:
    max_row = sheet.max_row
    if max_row and max_row > 1:
        sheet.delete_rows(2, max_row - 1)
    for row_idx, row in enumerate(rows, start=2):
        for col_idx, value in enumerate(row, start=1):
            sheet.cell(row=row_idx, column=col_idx, value=value)


def _update_description_sheet(sheet) -> None:
    existing_rows = [
        row
        for row in sheet.iter_rows(min_row=2, values_only=True)
        if row and row[0] != "DETALLES_NORMA"
    ]
    normas_rows = [
        ("DETALLES_NORMA", col, *NORMAS_DESCRIPTIONS[col]) for col in NORMAS_COLUMNS
    ]
    _rewrite_rows(sheet, [*existing_rows, *normas_rows])


def _update_validation_sheet(workbook, rows: Sequence[tuple[str, str, str, str]]) -> None:
    if "VALIDACIONES" in workbook.sheetnames:
        sheet = workbook["VALIDACIONES"]
    else:
        sheet = workbook.create_sheet(title="VALIDACIONES")
    sheet.cell(row=1, column=1, value="Hoja")
    sheet.cell(row=1, column=2, value="Columna")
    sheet.cell(row=1, column=3, value="Validador")
    sheet.cell(row=1, column=4, value="Regla")

    existing_rows = [
        row
        for row in sheet.iter_rows(min_row=2, values_only=True)
        if row and row[0] != "DETALLES_NORMA"
    ]
    _rewrite_rows(sheet, [*existing_rows, *rows])


def _update_summary_sheet(workbook) -> None:
    summary_config = FraudCaseApp.build_summary_table_config()
    if "RESUMEN" in workbook.sheetnames:
        sheet = workbook["RESUMEN"]
    else:
        sheet = workbook.create_sheet(title="RESUMEN")
    if sheet.max_row:
        sheet.delete_rows(1, sheet.max_row)
    row_idx = 1
    for _key, title, columns in summary_config:
        sheet.cell(row=row_idx, column=1, value=title)
        row_idx += 1
        for col_idx, (_field, label) in enumerate(columns, start=1):
            sheet.cell(row=row_idx, column=col_idx, value=label)
        row_idx += 2


def update_template(path: Path) -> None:
    workbook = load_workbook(path)
    for sheet_name, headers in SHEET_HEADERS.items():
        if sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
        else:
            sheet = workbook.create_sheet(title=sheet_name)
        _set_header_row(sheet, headers)

    description_sheet = workbook["DESCRIPCION_COLUMNAS"]
    _update_description_sheet(description_sheet)
    _update_validation_sheet(workbook, NORMAS_VALIDATIONS)
    _update_summary_sheet(workbook)

    workbook.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Actualiza la plantilla normalizada con campos de normas y validaciones."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("plantilla_normalizada_convalidaciones.xlsx"),
        help="Ruta del archivo Excel a actualizar.",
    )
    args = parser.parse_args()
    update_template(args.path)


if __name__ == "__main__":
    main()
