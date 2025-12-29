import csv

from app import _sanitize_csv_value
from report_builder import build_event_rows, CaseData
from utils.eventos_schema import EVENTOS_HEADER, EVENTOS_PLACEHOLDER


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

    expected_header = list(EVENTOS_HEADER)

    assert header == expected_header

    base_row = {field: EVENTOS_PLACEHOLDER for field in EVENTOS_HEADER}
    first_row = {
        **base_row,
        "case_id": "2024-1001",
        "tipo_informe": "Inicial",
        "categoria_1": "ProdCat1",
        "categoria_2": "ProdCat2",
        "modalidad": "Online",
        "tipo_de_producto": "Tarjeta",
        "canal": "App",
        "proceso_impactado": "Alta",
        "product_id": "=P1",
        "monto_investigado": "100.00",
        "tipo_moneda": "PEN",
        "matricula_colaborador_involucrado": "=COL1",
        "nombres_involucrado": "Juan",
        "division": "Riesgos",
        "area": "Analítica",
        "servicio": "Monitoreo",
        "nombre_agencia": "Agencia Central",
        "codigo_agencia": "000111",
        "puesto": "Analista",
        "tipo_de_falta": "Grave",
        "tipo_sancion": "Suspensión",
        "fecha_ocurrencia": "2024-01-05",
        "fecha_descubrimiento": "2024-01-06",
        "monto_falla_en_proceso_soles": "5.00",
        "monto_contingencia_soles": "20.00",
        "monto_recuperado_soles": "1.00",
        "monto_pagado_soles": "0.00",
        "comentario_breve": EVENTOS_PLACEHOLDER,
        "comentario_amplio": EVENTOS_PLACEHOLDER,
        "id_reclamo": "-RC1",
        "nombre_analitica": "Analítica P1",
        "codigo_analitica": "4300000001",
        "telefonos_cliente_relacionado": "=999",
        "correos_cliente_relacionado": "ana@example.com",
        "direcciones_cliente_relacionado": "Calle 1",
        "accionado_cliente_relacionado": "Sí",
        "id_caso": "2024-1001",
        "categoria1": "ProdCat1",
        "categoria2": "ProdCat2",
        "proceso": "Alta",
        "fecha_de_ocurrencia": "2024-01-01",
        "fecha_de_descubrimiento": "2024-01-02",
        "centro_costos": "CC-99",
        "matricula_investigador": "TM-0001",
        "investigador_nombre": "Lead Name",
        "investigador_cargo": "Lead Role",
        "id_producto": "=P1",
        "id_cliente": "CL1",
        "id_colaborador": "=COL1",
        "tipo_involucrado": "colaborador",
        "tipo_producto": "Tarjeta",
        "tipo_moneda": "PEN",
        "monto_perdida_fraude": "10.00",
        "monto_falla_procesos": "5.00",
        "monto_contingencia": "20.00",
        "monto_recuperado": "1.00",
        "monto_pago_deuda": "0.00",
        "codigo_analitica": "4300000001",
        "cliente_nombres": "Ana",
        "cliente_apellidos": "Gómez",
        "cliente_tipo_id": "DNI",
        "cliente_flag": "A",
        "cliente_telefonos": "=999",
        "cliente_correos": "ana@example.com",
        "cliente_direcciones": "Calle 1",
        "cliente_accionado": "Sí",
        "colaborador_flag": "B",
        "colaborador_nombres": "Juan",
        "colaborador_apellidos": "Pérez",
        "colaborador_division": "Riesgos",
        "colaborador_area": "Analítica",
        "colaborador_servicio": "Monitoreo",
        "colaborador_puesto": "Analista",
        "colaborador_fecha_carta_inmediatez": "2024-01-02",
        "colaborador_fecha_carta_renuncia": EVENTOS_PLACEHOLDER,
        "colaborador_nombre_agencia": "Agencia Central",
        "colaborador_codigo_agencia": "000111",
        "colaborador_tipo_falta": "Grave",
        "colaborador_tipo_sancion": "Suspensión",
        "monto_asignado": "50",
    }
    second_row = {
        **base_row,
        "case_id": "2024-1001",
        "tipo_informe": "Inicial",
        "categoria_1": "CaseCat1",
        "categoria_2": "CaseCat2",
        "modalidad": "CaseMod",
        "canal": "CaseChannel",
        "proceso_impactado": "CaseProcess",
        "product_id": "P2",
        "client_id_involucrado": "CL2",
        "nombres_cliente_involucrado": "Luis",
        "apellidos_cliente_involucrado": "Mora",
        "nombres_involucrado": "Luis",
        "fecha_ocurrencia": "2024-02-01",
        "comentario_breve": EVENTOS_PLACEHOLDER,
        "comentario_amplio": EVENTOS_PLACEHOLDER,
        "telefonos_cliente_relacionado": EVENTOS_PLACEHOLDER,
        "correos_cliente_relacionado": EVENTOS_PLACEHOLDER,
        "direcciones_cliente_relacionado": EVENTOS_PLACEHOLDER,
        "accionado_cliente_relacionado": EVENTOS_PLACEHOLDER,
        "id_caso": "2024-1001",
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
        "id_producto": "P2",
        "id_cliente": "CL2",
        "id_cliente_involucrado": "CL2",
        "tipo_involucrado": "cliente",
        "cliente_nombres": "Luis",
        "cliente_apellidos": "Mora",
        "monto_asignado": "15",
    }

    assert rows == [first_row, second_row]

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
    assert parsed[-1]["id_colaborador"] == _sanitize_csv_value(EVENTOS_PLACEHOLDER)
