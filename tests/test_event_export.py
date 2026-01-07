import csv

import settings
from app import _sanitize_csv_value
from report_builder import CaseData, build_event_rows
from tests.app_factory import build_import_app


def test_event_rows_merge_entities_and_fill_gaps(tmp_path):
    case_data = CaseData.from_mapping(
        {
            "caso": {
                "id_caso": "2024-1001",
                "tipo_informe": "Inicial",
                "categoria1": "CaseCat1",
                "categoria2": "CaseCat2",
                "modalidad": "CaseMod",
                "canal": "CaseChannel",
                "proceso": "CaseProcess",
                "fecha_de_ocurrencia": "2024-01-01",
                "fecha_de_descubrimiento": "2024-01-02",
                "centro_costos": "CC-99",
                "matricula_investigador": "TM-0001",
                "investigador_nombre": "Lead Name",
                "investigador_cargo": "Lead Role",
            },
            "clientes": [
                {
                    "id_cliente": "CL1",
                    "nombres": "Ana",
                    "apellidos": "Gómez",
                    "tipo_id": "DNI",
                    "flag": "A",
                    "telefonos": "=999",
                    "correos": "ana@example.com",
                    "direcciones": "Calle 1",
                    "accionado": "Sí",
                },
                {
                    "id_cliente": "CL2",
                    "nombres": "Luis",
                    "apellidos": "Mora",
                },
            ],
            "colaboradores": [
                {
                    "id_colaborador": "=COL1",
                    "flag": "B",
                    "nombres": "Juan",
                    "apellidos": "Pérez",
                    "division": "Riesgos",
                    "area": "Analítica",
                    "servicio": "Monitoreo",
                    "puesto": "Analista",
                    "fecha_carta_inmediatez": "2024-01-02",
                    "nombre_agencia": "Agencia Central",
                    "codigo_agencia": "000111",
                    "tipo_falta": "Grave",
                    "tipo_sancion": "Suspensión",
                }
            ],
            "productos": [
                {
                    "id_producto": "=P1",
                    "id_cliente": "CL1",
                    "categoria1": "ProdCat1",
                    "categoria2": "ProdCat2",
                    "modalidad": "Online",
                    "canal": "App",
                    "proceso": "Alta",
                    "fecha_ocurrencia": "2024-01-05",
                    "fecha_descubrimiento": "2024-01-06",
                    "tipo_producto": "Tarjeta",
                    "tipo_moneda": "PEN",
                    "monto_investigado": "100.00",
                    "monto_perdida_fraude": "10.00",
                    "monto_falla_procesos": "5.00",
                    "monto_contingencia": "20.00",
                    "monto_recuperado": "1.00",
                    "monto_pago_deuda": "0.00",
                },
                {
                    "id_producto": "P2",
                    "id_cliente": "CL2",
                    "fecha_ocurrencia": "2024-02-01",
                },
            ],
            "reclamos": [
                {
                    "id_producto": "=P1",
                    "id_reclamo": "-RC1",
                    "nombre_analitica": "Analítica P1",
                    "codigo_analitica": "4300000001",
                }
            ],
            "involucramientos": [
                {
                    "id_producto": "=P1",
                    "id_colaborador": "=COL1",
                    "monto_asignado": "50",
                },
                {
                    "id_producto": "P2",
                    "id_cliente_involucrado": "CL2",
                    "tipo_involucrado": "cliente",
                    "monto_asignado": "15",
                },
            ],
            "riesgos": [],
            "normas": [],
            "analisis": {},
            "encabezado": {},
            "operaciones": [],
            "anexos": [],
            "firmas": [],
            "recomendaciones_categorias": {},
        }
    )

    rows, header = build_event_rows(case_data)

    assert header == settings.EVENTOS_HEADER_CANONICO

    placeholder = settings.EVENTOS_PLACEHOLDER
    colaborador_row = next(row for row in rows if row["product_id"] == "=P1")
    assert colaborador_row["case_id"] == "2024-1001"
    assert colaborador_row["categoria_1"] == "ProdCat1"
    assert colaborador_row["tipo_de_producto"] == "Tarjeta"
    assert colaborador_row["monto_falla_en_proceso_soles"] == "5.00"
    assert colaborador_row["monto_fraude_externo_soles"] == placeholder
    assert colaborador_row["cod_operation"] == placeholder
    assert colaborador_row["matricula_colaborador_involucrado"] == "=COL1"
    assert colaborador_row["nombres_involucrado"] == "Juan"
    assert colaborador_row["telefonos_cliente_relacionado"] == "=999"
    assert colaborador_row["id_caso"] == "2024-1001"
    assert colaborador_row["cliente_telefonos"] == "=999"
    assert colaborador_row["codigo_analitica"] == "4300000001"

    cliente_row = next(row for row in rows if row["product_id"] == "P2")
    assert cliente_row["client_id_involucrado"] == "CL2"
    assert cliente_row["matricula_colaborador_involucrado"] == placeholder
    assert cliente_row["division"] == placeholder
    assert cliente_row["tipo_de_producto"] == placeholder
    assert cliente_row["id_colaborador"] == placeholder

    csv_path = tmp_path / "caso_eventos.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _sanitize_csv_value(row.get(field, "")) for field in header})

    parsed = list(csv.DictReader(csv_path.open("r", newline="", encoding="utf-8")))
    assert parsed[0]["id_producto"] == "'=P1"
    assert parsed[0]["id_colaborador"] == "'=COL1"
    assert parsed[0]["cliente_telefonos"] == "'=999"
    assert parsed[-1]["id_colaborador"] == settings.EVENTOS_PLACEHOLDER


def test_event_round_trip_prefers_case_dates_over_product_dates(monkeypatch):
    case_data = CaseData.from_mapping(
        {
            "caso": {
                "id_caso": "2024-2001",
                "fecha_de_ocurrencia": "2024-01-01",
                "fecha_de_descubrimiento": "2024-01-03",
            },
            "productos": [
                {
                    "id_producto": "P-CASE",
                    "id_cliente": "CL-CASE",
                    "fecha_ocurrencia": "2024-02-01",
                    "fecha_descubrimiento": "2024-02-02",
                }
            ],
            "clientes": [],
            "colaboradores": [],
            "reclamos": [],
            "involucramientos": [],
            "riesgos": [],
            "normas": [],
            "analisis": {},
            "encabezado": {},
            "operaciones": [],
            "anexos": [],
            "firmas": [],
            "recomendaciones_categorias": {},
        }
    )

    rows, _header = build_event_rows(case_data)
    app = build_import_app(monkeypatch)
    normalized = app._normalize_eventos_row(rows[0], "canonical")

    app._apply_eventos_case_row(normalized)

    assert app.fecha_caso_var.get() == "2024-01-01"
    assert app.fecha_descubrimiento_caso_var.get() == "2024-01-03"
