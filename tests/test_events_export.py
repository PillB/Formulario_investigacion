import csv
import types
from pathlib import Path

import pytest

import settings
from app import FraudCaseApp, _sanitize_csv_value
from report_builder import CaseData, build_report_filename


def _build_export_app():
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    app._docx_available = False
    app._suppress_messagebox = True
    app._normalize_analysis_texts = types.MethodType(lambda self, payload: payload or {}, app)
    app._build_export_definitions = types.MethodType(lambda self, data: [], app)
    app._update_architecture_diagram = types.MethodType(lambda self, defs: None, app)
    app._mirror_exports_to_external_drive = types.MethodType(
        lambda self, files, case_id, notify_user=False, consolidation_timestamp=None: [], app
    )
    return app


def _build_case_payload(case_id: str, *, with_relations: bool) -> CaseData:
    product_id = "=P-1" if with_relations else "P-EMPTY"
    client_id = "CL1" if with_relations else "CL2"
    collaborator_id = "=COL1" if with_relations else ""
    payload = {
        "caso": {
            "id_caso": case_id,
            "tipo_informe": "Inicial",
            "categoria1": "CatA",
            "categoria2": "CatB",
            "modalidad": "CaseMod",
            "canal": "Canal",
            "proceso": "Proceso",
            "fecha_de_ocurrencia": "2024-01-10",
            "fecha_de_descubrimiento": "2024-01-11",
            "centro_costos": "CC-1",
            "matricula_investigador": "TM-1234",
            "investigador_nombre": "Lead",
            "investigador_cargo": "Cargo",
        },
        "clientes": [
            {
                "id_cliente": client_id,
                "nombres": "Ana" if with_relations else "",
                "apellidos": "Gómez" if with_relations else "",
                "tipo_id": "DNI" if with_relations else "",
                "flag": "A" if with_relations else "",
                "telefonos": "=999" if with_relations else "",
                "correos": "ana@example.com" if with_relations else "",
                "direcciones": "Calle 1" if with_relations else "",
                "accionado": "Sí" if with_relations else "",
            }
        ],
        "colaboradores": [] if not with_relations else [
            {
                "id_colaborador": collaborator_id,
                "flag": "B",
                "nombres": "Juan",
                "apellidos": "Pérez",
                "division": "Riesgos",
                "area": "Analítica",
                "servicio": "Monitoreo",
                "puesto": "Analista",
                "fecha_carta_inmediatez": "2024-01-09",
                "nombre_agencia": "Agencia Central",
                "codigo_agencia": "000111",
                "tipo_falta": "Grave",
                "tipo_sancion": "Suspensión",
            }
        ],
        "productos": [
            {
                "id_producto": product_id,
                "id_cliente": client_id,
                "categoria1": "ProdCat" if with_relations else "",
                "categoria2": "ProdSub" if with_relations else "",
                "modalidad": "Online" if with_relations else "",
                "canal": "App" if with_relations else "",
                "proceso": "Alta" if with_relations else "",
                "fecha_ocurrencia": "2024-02-01",
                "fecha_descubrimiento": "2024-02-02" if with_relations else "",
                "tipo_producto": "Tarjeta" if with_relations else "",
                "tipo_moneda": "PEN" if with_relations else "",
                "monto_investigado": "100.00",
                "monto_perdida_fraude": "10.00" if with_relations else "",
                "monto_falla_procesos": "5.00" if with_relations else "",
                "monto_contingencia": "20.00" if with_relations else "",
                "monto_recuperado": "1.00" if with_relations else "",
                "monto_pago_deuda": "0.00" if with_relations else "",
            }
        ],
        "reclamos": [] if not with_relations else [
            {
                "id_producto": product_id,
                "id_reclamo": "-RC1",
                "nombre_analitica": "Analítica P1",
                "codigo_analitica": "4300000001",
            }
        ],
        "involucramientos": [] if not with_relations else [
            {
                "id_producto": product_id,
                "id_colaborador": collaborator_id,
                "cliente_flag": "colaborador",
                "monto_asignado": "50",
            },
            {
                "id_producto": product_id,
                "id_cliente_involucrado": client_id,
                "cliente_flag": "cliente",
                "monto_asignado": "25",
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
    return CaseData.from_mapping(payload)


@pytest.mark.parametrize("with_relations", [True, False])
def test_save_exports_writes_event_rows(tmp_path, with_relations):
    case_id = "2024-0001" if with_relations else "2024-0002"
    app = _build_export_app()
    export_dir = tmp_path / case_id
    export_dir.mkdir()
    case_data = _build_case_payload(case_id, with_relations=with_relations)

    result = app._perform_save_exports(case_data, export_dir, case_id)

    prefix = Path(build_report_filename("Inicial", case_id, "csv")).stem
    expected_path = export_dir / f"{prefix}_eventos.csv"
    assert expected_path.exists()
    assert expected_path in result["created_files"]

    rows = list(csv.DictReader(expected_path.open("r", newline="", encoding="utf-8")))
    expected_count = 2 if with_relations else 1
    assert len(rows) == expected_count

    placeholder = settings.EVENTOS_PLACEHOLDER
    collaborator_row = next((row for row in rows if row.get("cliente_flag") == "colaborador"), rows[0])
    assert collaborator_row["id_caso"] == case_id
    assert collaborator_row["id_producto"] == _sanitize_csv_value("=P-1" if with_relations else "P-EMPTY")
    assert collaborator_row["id_cliente"] == ("CL1" if with_relations else "CL2")
    assert collaborator_row["fecha_ocurrencia"] == "2024-02-01"
    assert collaborator_row["monto_investigado"] == "100.00"
    assert collaborator_row["cod_operation"] == placeholder

    if with_relations:
        assert collaborator_row["id_colaborador"] == _sanitize_csv_value("=COL1")
        assert collaborator_row["id_reclamo"] == _sanitize_csv_value("-RC1")
        assert collaborator_row["cliente_telefonos"] == _sanitize_csv_value("=999")
        assert collaborator_row["monto_contingencia"] == "20.00"
        assert collaborator_row["colaborador_tipo_falta"] == "Grave"
        client_row = next(row for row in rows if row.get("cliente_flag") == "cliente")
        assert client_row["id_cliente_involucrado"] == "CL1"
        assert client_row["id_colaborador"] == placeholder
    else:
        assert collaborator_row["id_colaborador"] == placeholder
        assert collaborator_row["id_reclamo"] == placeholder
        assert collaborator_row["cliente_telefonos"] == placeholder
        assert collaborator_row["nombre_analitica"] == placeholder
        assert collaborator_row["colaborador_flag"] == placeholder

    history_path = export_dir / "h_eventos.csv"
    assert history_path.exists()
    history_rows = list(csv.DictReader(history_path.open("r", newline="", encoding="utf-8")))
    assert len(history_rows) == expected_count
    history_row = history_rows[0]
    assert history_row["case_id"] == case_id
    assert history_row["fecactualizacion"]
