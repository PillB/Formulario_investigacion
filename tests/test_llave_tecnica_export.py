import csv

from app import _sanitize_csv_value
from report_builder import CaseData, build_llave_tecnica_rows


def test_llave_tecnica_rows_and_csv(tmp_path):
    case_data = CaseData.from_mapping(
        {
            "caso": {
                "id_caso": "2024-0001",
                "tipo_informe": "Inicial",
                "categoria1": "Cat1",
                "categoria2": "Cat2",
                "modalidad": "Modal",
                "canal": "Digital",
                "proceso": "Onboarding",
                "fecha_de_ocurrencia": "2024-01-01",
                "fecha_de_descubrimiento": "2024-01-02",
                "centro_costos": "CC-01",
                "matricula_investigador": "T00001",
                "investigador_nombre": "Investigador Uno",
                "investigador_cargo": "Analista",
            },
            "productos": [
                {
                    "id_producto": "=P1",
                    "id_cliente": "+CLI1",
                    "fecha_ocurrencia": "2024-01-01",
                },
                {
                    "id_producto": "P2",
                    "id_cliente": "CLI2",
                    "fecha_ocurrencia": "2024-02-02",
                },
            ],
            "reclamos": [
                {"id_producto": "=P1", "id_reclamo": "-RC1"},
                {"id_producto": "=P1", "id_reclamo": "RC2"},
            ],
            "involucramientos": [
                {"id_producto": "=P1", "id_colaborador": "@TM1"},
                {"id_producto": "=P1", "id_colaborador": "TM-ALT"},
                {"id_producto": "P2", "id_colaborador": "TM2"},
                {"id_producto": "P2", "id_cliente_involucrado": "CL-EXT", "tipo_involucrado": "cliente"},
            ],
        }
    )

    rows, header = build_llave_tecnica_rows(case_data)

    expected_header = [
        "id_caso",
        "tipo_informe",
        "categoria1",
        "categoria2",
        "modalidad",
        "canal",
        "proceso",
        "fecha_de_ocurrencia",
        "fecha_de_descubrimiento",
        "centro_costos",
        "matricula_investigador",
        "investigador_nombre",
        "investigador_cargo",
        "id_producto",
        "id_cliente",
        "id_colaborador",
        "id_cliente_involucrado",
        "tipo_involucrado",
        "id_reclamo",
        "fecha_ocurrencia",
    ]
    assert header == expected_header

    base_row = {
        "id_caso": "2024-0001",
        "tipo_informe": "Inicial",
        "categoria1": "Cat1",
        "categoria2": "Cat2",
        "modalidad": "Modal",
        "canal": "Digital",
        "proceso": "Onboarding",
        "fecha_de_ocurrencia": "2024-01-01",
        "fecha_de_descubrimiento": "2024-01-02",
        "centro_costos": "CC-01",
        "matricula_investigador": "T00001",
        "investigador_nombre": "Investigador Uno",
        "investigador_cargo": "Analista",
    }

    assert rows == [
        {**base_row, "id_producto": "=P1", "id_cliente": "+CLI1", "id_colaborador": "@TM1", "id_cliente_involucrado": "", "tipo_involucrado": "colaborador", "id_reclamo": "-RC1", "fecha_ocurrencia": "2024-01-01"},
        {**base_row, "id_producto": "=P1", "id_cliente": "+CLI1", "id_colaborador": "@TM1", "id_cliente_involucrado": "", "tipo_involucrado": "colaborador", "id_reclamo": "RC2", "fecha_ocurrencia": "2024-01-01"},
        {**base_row, "id_producto": "=P1", "id_cliente": "+CLI1", "id_colaborador": "TM-ALT", "id_cliente_involucrado": "", "tipo_involucrado": "colaborador", "id_reclamo": "-RC1", "fecha_ocurrencia": "2024-01-01"},
        {**base_row, "id_producto": "=P1", "id_cliente": "+CLI1", "id_colaborador": "TM-ALT", "id_cliente_involucrado": "", "tipo_involucrado": "colaborador", "id_reclamo": "RC2", "fecha_ocurrencia": "2024-01-01"},
        {**base_row, "id_producto": "P2", "id_cliente": "CLI2", "id_colaborador": "TM2", "id_cliente_involucrado": "", "tipo_involucrado": "colaborador", "id_reclamo": "", "fecha_ocurrencia": "2024-02-02"},
        {**base_row, "id_producto": "P2", "id_cliente": "CLI2", "id_colaborador": "", "id_cliente_involucrado": "CL-EXT", "tipo_involucrado": "cliente", "id_reclamo": "", "fecha_ocurrencia": "2024-02-02"},
    ]

    csv_path = tmp_path / "caso_llave_tecnica.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _sanitize_csv_value(row.get(field, "")) for field in header})

    with csv_path.open("r", newline="", encoding="utf-8") as file:
        parsed_rows = list(csv.DictReader(file))

    assert parsed_rows[0]["id_producto"] == "'=P1"
    assert parsed_rows[0]["id_cliente"] == "'+CLI1"
    assert parsed_rows[0]["id_colaborador"] == "'@TM1"
    assert parsed_rows[0]["id_reclamo"] == "'-RC1"
    assert parsed_rows[-1]["id_reclamo"] == ""


def test_llave_tecnica_inherits_case_date_when_product_blank():
    case_data = CaseData.from_mapping(
        {
            "caso": {
                "id_caso": "2024-0002",
                "fecha_de_ocurrencia": "2024-02-15",
                "fecha_de_descubrimiento": "2024-02-16",
            },
            "productos": [
                {
                    "id_producto": "P-EMPTY",
                    "id_cliente": "CLI-EMPTY",
                }
            ],
            "reclamos": [],
            "involucramientos": [],
        }
    )

    rows, _header = build_llave_tecnica_rows(case_data)

    assert rows[0]["fecha_ocurrencia"] == "2024-02-15"
