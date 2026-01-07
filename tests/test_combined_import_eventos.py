"""Cobertura de regresión para PRs recientes de importación de eventos."""

import csv
from threading import Event

from settings import (
    CANAL_LIST,
    EVENTOS_HEADER_CANONICO,
    EVENTOS_PLACEHOLDER,
    FLAG_CLIENTE_LIST,
    PROCESO_LIST,
    TAXONOMIA,
    TIPO_ID_LIST,
    TIPO_INFORME_LIST,
)
from report_builder import CaseData, build_event_rows
from tests.app_factory import build_import_app
from tests.stubs import DummyVar


def _write_eventos_csv(tmp_path, headers, row):
    file_path = tmp_path / "eventos_canonico.csv"
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerow([row.get(header, "") for header in headers])
    return file_path


def test_combined_import_eventos_canonical_placeholder_keeps_ids_clean(tmp_path, monkeypatch):
    app = build_import_app(monkeypatch)
    app.import_status_var = DummyVar("")
    cat1 = list(TAXONOMIA.keys())[0]
    cat2 = list(TAXONOMIA[cat1].keys())[0]
    modalidad = TAXONOMIA[cat1][cat2][0]
    row = {header: EVENTOS_PLACEHOLDER for header in EVENTOS_HEADER_CANONICO}
    row.update(
        {
            "case_id": "2025-0004",
            "tipo_informe": TIPO_INFORME_LIST[0],
            "categoria_1": cat1,
            "categoria_2": cat2,
            "modalidad": modalidad,
            "canal": CANAL_LIST[0],
            "proceso_impactado": PROCESO_LIST[0],
            "product_id": "PRD-001",
            "tipo_de_producto": "Crédito personal",
            "monto_investigado": "100.00",
            "tipo_moneda": "Soles",
            "tipo_id_cliente_involucrado": TIPO_ID_LIST[0],
            "client_id_involucrado": "CLI-001",
            "flag_cliente_involucrado": FLAG_CLIENTE_LIST[0],
            "matricula_colaborador_involucrado": "T12345",
            "fecha_ocurrencia": "2024-01-10",
            "fecha_descubrimiento": "2024-01-11",
        }
    )
    file_path = _write_eventos_csv(tmp_path, EVENTOS_HEADER_CANONICO, row)

    worker = app._build_combined_worker(str(file_path))
    payload = worker(lambda *_args: None, Event())

    app._apply_combined_import_payload(
        payload,
        manager=app.mass_import_manager,
        file_path=str(file_path),
    )

    client_ids = [frame.id_var.get() for frame in app.client_frames if frame.id_var.get()]
    team_ids = [frame.id_var.get() for frame in app.team_frames if frame.id_var.get()]
    product_ids = [frame.id_var.get() for frame in app.product_frames if frame.id_var.get()]

    assert client_ids == ["CLI-001"]
    assert team_ids == ["T12345"]
    assert product_ids == ["PRD-001"]

    product_frame = app._find_product_frame("PRD-001")
    assert product_frame is not None

    client_involvement_ids = {
        inv.client_var.get()
        for inv in product_frame.client_involvements
        if inv.client_var.get()
    }
    team_involvement_ids = {
        inv.team_var.get()
        for inv in product_frame.involvements
        if inv.team_var.get()
    }
    assert client_involvement_ids == {"CLI-001"}
    assert team_involvement_ids == {"T12345"}

    ids_to_check = client_ids + team_ids + product_ids
    ids_to_check.extend(client_involvement_ids)
    ids_to_check.extend(team_involvement_ids)
    assert EVENTOS_PLACEHOLDER not in ids_to_check


def test_combined_export_import_restores_involved_details(tmp_path, monkeypatch, messagebox_spy):
    cat1 = list(TAXONOMIA.keys())[0]
    cat2 = list(TAXONOMIA[cat1].keys())[0]
    modalidad = TAXONOMIA[cat1][cat2][0]
    case_data = CaseData.from_mapping(
        {
            "caso": {
                "id_caso": "2025-0006",
                "tipo_informe": TIPO_INFORME_LIST[0],
                "categoria1": cat1,
                "categoria2": cat2,
                "modalidad": modalidad,
                "canal": CANAL_LIST[0],
                "proceso": PROCESO_LIST[0],
                "fecha_de_ocurrencia": "2024-01-10",
                "fecha_de_descubrimiento": "2024-01-11",
            },
            "clientes": [
                {
                    "id_cliente": "CLI-BASE",
                    "nombres": "Base",
                    "apellidos": "Cliente",
                    "tipo_id": TIPO_ID_LIST[0],
                    "flag": FLAG_CLIENTE_LIST[0],
                },
                {
                    "id_cliente": "CLI-INV",
                    "nombres": "Ana",
                    "apellidos": "Pérez",
                    "tipo_id": TIPO_ID_LIST[0],
                    "flag": FLAG_CLIENTE_LIST[0],
                    "telefonos": "999888777",
                    "correos": "ana@example.com",
                    "direcciones": "Calle 123",
                    "accionado": "Fiscalía",
                },
            ],
            "colaboradores": [
                {
                    "id_colaborador": "T54321",
                    "nombres": "Luis",
                    "apellidos": "Gomez Diaz",
                    "division": "Division X",
                    "area": "Area Comercial",
                    "servicio": "Ventas",
                    "puesto": "Analista",
                    "nombre_agencia": "Agencia Centro",
                    "codigo_agencia": "123456",
                }
            ],
            "productos": [
                {
                    "id_producto": "PRD-INV",
                    "id_cliente": "CLI-BASE",
                    "tipo_producto": "Crédito personal",
                    "monto_investigado": "100.00",
                    "tipo_moneda": "Soles",
                    "fecha_ocurrencia": "2024-01-10",
                    "fecha_descubrimiento": "2024-01-11",
                }
            ],
            "reclamos": [],
            "involucramientos": [
                {
                    "id_producto": "PRD-INV",
                    "tipo_involucrado": "cliente",
                    "id_cliente_involucrado": "CLI-INV",
                    "monto_asignado": "50.00",
                },
                {
                    "id_producto": "PRD-INV",
                    "tipo_involucrado": "colaborador",
                    "id_colaborador": "T54321",
                    "monto_asignado": "25.00",
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
    file_path = tmp_path / "eventos_roundtrip.csv"
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    app = build_import_app(monkeypatch)
    app.import_status_var = DummyVar("")
    worker = app._build_combined_worker(str(file_path))
    payload = worker(lambda *_args: None, Event())

    app._apply_combined_import_payload(
        payload,
        manager=app.mass_import_manager,
        file_path=str(file_path),
    )

    involved_client = app._find_client_frame("CLI-INV")
    assert involved_client is not None
    client_payload = involved_client.populated_rows[0]
    assert client_payload["nombres"] == "Ana"
    assert client_payload["apellidos"] == "Pérez"
    assert client_payload["tipo_id"] == TIPO_ID_LIST[0]
    assert client_payload["flag"] == FLAG_CLIENTE_LIST[0]

    team_frame = app._find_team_frame("T54321")
    assert team_frame is not None
    assert team_frame.nombres_var.get() == "Luis"
    assert team_frame.apellidos_var.get() == "Gomez Diaz"
    assert team_frame.division_var.get() == "Division X"
    assert team_frame.area_var.get() == "Area Comercial"
    assert team_frame.servicio_var.get() == "Ventas"
    assert team_frame.puesto_var.get() == "Analista"
    assert team_frame.nombre_agencia_var.get() == "Agencia Centro"
    assert team_frame.codigo_agencia_var.get() == "123456"
    assert messagebox_spy.errors == []
