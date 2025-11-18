from dataclasses import dataclass
from typing import Callable
import types

import pytest

import app as app_module
from app import FraudCaseApp
from settings import (ACCIONADO_OPTIONS, CRITICIDAD_LIST, FLAG_CLIENTE_LIST,
                      TIPO_ID_LIST, TIPO_SANCION_LIST)
from tests.stubs import (ClientFrameStub, NormFrameStub, ProductFrameStub,
                         RiskFrameStub, TeamFrameStub, build_involvement_slot,
                         build_populate_method, build_slot_factory)


class MessageboxSpy:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def showinfo(self, title, message):
        self.infos.append((title, message))

    def showwarning(self, title, message):
        self.warnings.append((title, message))

    def showerror(self, title, message):
        self.errors.append((title, message))


@pytest.fixture
def messagebox_spy(monkeypatch):
    spy = MessageboxSpy()
    monkeypatch.setattr(app_module.messagebox, "showinfo", spy.showinfo)
    monkeypatch.setattr(app_module.messagebox, "showwarning", spy.showwarning)
    monkeypatch.setattr(app_module.messagebox, "showerror", spy.showerror)
    monkeypatch.setattr(app_module.messagebox, "askyesno", lambda *_, **__: True)
    return spy


class SummaryTableStub:
    def get_children(self):
        return []

    def delete(self, *_args, **_kwargs):
        return None

    def insert(self, *_args, **_kwargs):
        return None


@dataclass
class SummaryPasteCase:
    key: str
    columns: list[tuple[str, str]]
    valid_row: list[str]
    invalid_row: list[str]
    state_getter: Callable[[FraudCaseApp], list]
    expected_state: list
    error_fragment: str


def _columns(count):
    return [(f"c{i}", f"Col {i}") for i in range(count)]


def _collect_ids(frames):
    return [frame.id_var.get() for frame in frames if frame.id_var.get()]


def _collect_claim_ids(app):
    claim_ids = []
    for frame in app.product_frames:
        for claim in frame.claims:
            if claim.data:
                claim_ids.append(claim.data.get('id_reclamo'))
    return claim_ids


def _collect_involvements(app):
    values = []
    for frame in app.product_frames:
        product_id = frame.id_var.get()
        if not product_id:
            continue
        for inv in frame.involvements:
            team = inv.team_var.get()
            amount = inv.monto_var.get()
            if team:
                values.append((product_id, team, amount))
    return values


SUMMARY_CASES = [
    SummaryPasteCase(
        key="clientes",
        columns=_columns(7),
        valid_row=[
            "12345678",
            TIPO_ID_LIST[0],
            FLAG_CLIENTE_LIST[0],
            "999888777",
            "cli@example.com",
            "Av. Principal 123",
            ACCIONADO_OPTIONS[0],
        ],
        invalid_row=[
            "12345678",
            TIPO_ID_LIST[0],
            FLAG_CLIENTE_LIST[0],
            "999888777",
            "correo-invalido",
            "Av. Principal 123",
            ACCIONADO_OPTIONS[0],
        ],
        state_getter=lambda app: _collect_ids(app.client_frames),
        expected_state=["12345678"],
        error_fragment="correo",
    ),
    SummaryPasteCase(
        key="colaboradores",
        columns=_columns(4),
        valid_row=["T67890", "Division B", "Area B", TIPO_SANCION_LIST[0]],
        invalid_row=["bad", "Division B", "Area B", "Inválida"],
        state_getter=lambda app: _collect_ids(app.team_frames),
        expected_state=["T67890"],
        error_fragment="colaborador",
    ),
    SummaryPasteCase(
        key="productos",
        columns=_columns(4),
        valid_row=["1234567890123", "12345678", "Crédito personal", "1500.00"],
        invalid_row=["1234567890123", "12345678", "Crédito personal", "abc"],
        state_getter=lambda app: _collect_ids(app.product_frames),
        expected_state=["1234567890123"],
        error_fragment="monto",
    ),
    SummaryPasteCase(
        key="reclamos",
        columns=_columns(4),
        valid_row=["C12345678", "1234567890123", "Analítica", "4300000000"],
        invalid_row=["123", "", "", "000"],
        state_getter=_collect_claim_ids,
        expected_state=["C12345678"],
        error_fragment="reclamo",
    ),
    SummaryPasteCase(
        key="riesgos",
        columns=_columns(4),
        valid_row=["RSK-000001", "Líder", CRITICIDAD_LIST[0], "100.00"],
        invalid_row=["RSK-000001", "Líder", "INVÁLIDO", "abc"],
        state_getter=lambda app: _collect_ids(app.risk_frames),
        expected_state=["RSK-000001"],
        error_fragment="criticidad",
    ),
    SummaryPasteCase(
        key="normas",
        columns=_columns(3),
        valid_row=["2024.001.01.01", "Descripción", "2024-01-01"],
        invalid_row=["2024.001.01.01", "Descripción", "2024/01/01"],
        state_getter=lambda app: _collect_ids(app.norm_frames),
        expected_state=["2024.001.01.01"],
        error_fragment="fecha",
    ),
    SummaryPasteCase(
        key="involucramientos",
        columns=_columns(3),
        valid_row=["1234567890123", "T22222", "250.75"],
        invalid_row=["1234567890123", "T22222", "10.5"],
        state_getter=_collect_involvements,
        expected_state=[("1234567890123", "T22222", "250.75")],
        error_fragment="dos decimales",
    ),
]


def _build_summary_app(monkeypatch, messagebox_spy):
    app = FraudCaseApp.__new__(FraudCaseApp)
    app._suppress_messagebox = True
    app.logs = []
    app.client_frames = []
    app.team_frames = []
    app.product_frames = []
    app._client_frames_by_id = {}
    app._team_frames_by_id = {}
    app._product_frames_by_id = {}
    app.risk_frames = []
    app.norm_frames = []
    app.detail_catalogs = {}
    app.detail_lookup_by_id = {
        'id_producto': {
            '1234567890123': {
                'id_producto': '1234567890123',
                'id_cliente': '12345678',
                'tipo_producto': 'Crédito personal',
                'monto_investigado': '0.00',
            }
        },
        'id_colaborador': {
            'T22222': {
                'id_colaborador': 'T22222',
                'division': 'Division resumen',
                'area': 'Area resumen',
                'tipo_sancion': TIPO_SANCION_LIST[0],
            }
        },
        'id_cliente': {
            '12345678': {
                'id_cliente': '12345678',
                'tipo_id': TIPO_ID_LIST[0],
            }
        },
    }
    app.client_lookup = {}
    app.team_lookup = {}
    app.product_lookup = {}
    app.summary_tables = {}
    app.summary_config = {}
    app._schedule_summary_refresh = lambda *_args, **_kwargs: None
    app._notify_taxonomy_warning = lambda *_args, **_kwargs: None
    app._report_missing_detail_ids = lambda *_args, **_kwargs: None
    app._notify_products_created_without_details = lambda *_args, **_kwargs: None
    app._sync_product_lookup_claim_fields = lambda *_args, **_kwargs: None
    app._notify_dataset_changed = lambda *_args, **_kwargs: None
    app.save_auto = lambda: None
    app.sync_main_form_after_import = lambda *_args, **_kwargs: None

    app._obtain_client_slot_for_import = types.MethodType(
        build_slot_factory(
            app.client_frames,
            ClientFrameStub,
            on_create=lambda self, frame: setattr(frame, 'id_change_callback', self._handle_client_id_change),
        ),
        app,
    )
    app._obtain_team_slot_for_import = types.MethodType(
        build_slot_factory(
            app.team_frames,
            TeamFrameStub,
            on_create=lambda self, frame: setattr(frame, 'id_change_callback', self._handle_team_id_change),
        ),
        app,
    )
    app._obtain_product_slot_for_import = types.MethodType(
        build_slot_factory(
            app.product_frames,
            ProductFrameStub,
            on_create=lambda self, frame: setattr(frame, 'id_change_callback', self._handle_product_id_change),
        ),
        app,
    )
    app._obtain_involvement_slot = types.MethodType(build_involvement_slot(), app)
    app._populate_client_frame_from_row = types.MethodType(
        build_populate_method('id_cliente'),
        app,
    )
    app._populate_team_frame_from_row = types.MethodType(
        build_populate_method('id_colaborador'),
        app,
    )
    app._populate_product_frame_from_row = types.MethodType(
        build_populate_method('id_producto'),
        app,
    )

    def _identity_merge(self, frame, payload):
        return dict(payload or {})

    app._merge_client_payload_with_frame = types.MethodType(_identity_merge, app)
    app._merge_team_payload_with_frame = types.MethodType(_identity_merge, app)
    app._merge_product_payload_with_frame = types.MethodType(_identity_merge, app)

    def _add_risk(self):
        frame = RiskFrameStub()
        self.risk_frames.append(frame)
        return frame

    def _add_norm(self):
        frame = NormFrameStub()
        self.norm_frames.append(frame)
        return frame

    app.add_risk = types.MethodType(_add_risk, app)
    app.add_norm = types.MethodType(_add_norm, app)
    return app


@pytest.mark.parametrize("case", SUMMARY_CASES, ids=lambda case: case.key)
def test_handle_summary_paste_accepts_valid_rows(monkeypatch, messagebox_spy, case):
    app = _build_summary_app(monkeypatch, messagebox_spy)
    app.summary_tables[case.key] = SummaryTableStub()
    app.summary_config[case.key] = case.columns
    app.clipboard_get = lambda row=case.valid_row: "\t".join(row)

    result = app._handle_summary_paste(case.key)

    assert result == "break"
    assert case.state_getter(app) == case.expected_state
    assert messagebox_spy.errors == []


@pytest.mark.parametrize("case", SUMMARY_CASES, ids=lambda case: f"invalid_{case.key}")
def test_handle_summary_paste_rejects_invalid_rows(monkeypatch, messagebox_spy, case):
    app = _build_summary_app(monkeypatch, messagebox_spy)
    app.summary_tables[case.key] = SummaryTableStub()
    app.summary_config[case.key] = case.columns
    app.clipboard_get = lambda row=case.invalid_row: "\t".join(row)

    result = app._handle_summary_paste(case.key)

    assert result == "break"
    assert messagebox_spy.errors
    assert any(
        case.error_fragment.lower() in (message or "").lower()
        for _title, message in messagebox_spy.errors
    )
    assert case.state_getter(app) == []


def test_ingest_summary_rows_create_frames_with_normalized_values(monkeypatch, messagebox_spy):
    app = _build_summary_app(monkeypatch, messagebox_spy)

    client_row = [
        "12345678",
        TIPO_ID_LIST[0],
        FLAG_CLIENTE_LIST[0],
        "+51999888777",
        "cli@example.com",
        "Av. Principal 123",
        ACCIONADO_OPTIONS[0],
    ]
    client_rows = app._transform_clipboard_clients([client_row])
    assert app.ingest_summary_rows("clientes", client_rows) == 1
    assert [frame.id_var.get() for frame in app.client_frames] == ["12345678"]

    team_row = ["T67890", "Division B", "Área Comercial", TIPO_SANCION_LIST[0]]
    team_rows = app._transform_clipboard_colaboradores([team_row])
    assert app.ingest_summary_rows("colaboradores", team_rows) == 1
    assert [frame.id_var.get() for frame in app.team_frames] == ["T67890"]

    product_row = ["1234567890123", "12345678", "credito personal", "2500.50"]
    product_rows = app._transform_clipboard_productos([product_row])
    assert product_rows[0][2] == "Crédito personal"
    assert product_rows[0][3] == "2500.50"
    assert app.ingest_summary_rows("productos", product_rows) == 1
    assert [frame.id_var.get() for frame in app.product_frames] == ["1234567890123"]
    assert app.product_frames[0].populated_rows[-1]["tipo_producto"] == "Crédito personal"

    risk_row = ["rsk-000001", "Líder", CRITICIDAD_LIST[1], "100.00"]
    risk_rows = app._transform_clipboard_riesgos([risk_row])
    assert risk_rows[0][0] == "RSK-000001"
    assert app.ingest_summary_rows("riesgos", risk_rows) == 1
    assert [frame.id_var.get() for frame in app.risk_frames] == ["RSK-000001"]
    assert app.risk_frames[0].criticidad_var.get() == CRITICIDAD_LIST[1]
    assert app.risk_frames[0].exposicion_var.get() == "100.00"

    norm_row = ["2024.001.01.01", "Nueva norma", "2024-01-01"]
    norm_rows = app._transform_clipboard_normas([norm_row])
    assert app.ingest_summary_rows("normas", norm_rows) == 1
    assert [frame.id_var.get() for frame in app.norm_frames] == ["2024.001.01.01"]
    assert app.norm_frames[0].descripcion_var.get() == "Nueva norma"


@pytest.mark.parametrize(
    "transform_name, rows, expected_message",
    [
        (
            "_transform_clipboard_clients",
            [["12345678", "INVALID", "", "", "", "", ""]],
            "Cliente fila 1: el tipo de ID 'INVALID' no está en el catálogo CM. Corrige la hoja de Excel antes de volver a intentarlo.",
        ),
        (
            "_transform_clipboard_productos",
            [["1234567890123", "12345678", "Crédito personal", "abc"]],
            "Producto fila 1: el monto investigado debe ser un número válido.",
        ),
    ],
)
def test_transform_clipboard_rows_invalid_inputs(monkeypatch, messagebox_spy, transform_name, rows, expected_message):
    app = _build_summary_app(monkeypatch, messagebox_spy)
    transform = getattr(app, transform_name)
    with pytest.raises(ValueError) as excinfo:
        transform(rows)
    assert str(excinfo.value) == expected_message


@pytest.mark.parametrize(
    "section, frame_attr, row, warning_title, log_fragment",
    [
        (
            "riesgos",
            "risk_frames",
            ["RSK-000010", "Líder", CRITICIDAD_LIST[0], "50.00"],
            "Riesgos duplicados",
            "Riesgo duplicado RSK-000010",
        ),
        (
            "normas",
            "norm_frames",
            ["2024.001.02.01", "Descripción", "2024-01-01"],
            "Normas duplicadas",
            "Norma duplicada 2024.001.02.01",
        ),
    ],
)
def test_ingest_summary_rows_warn_on_duplicates(monkeypatch, messagebox_spy, section, frame_attr, row, warning_title, log_fragment):
    app = _build_summary_app(monkeypatch, messagebox_spy)
    existing_frame = RiskFrameStub() if section == "riesgos" else NormFrameStub()
    existing_frame.id_var.set(row[0])
    getattr(app, frame_attr).append(existing_frame)

    transform = getattr(app, f"_transform_clipboard_{section}")
    sanitized_rows = transform([row])
    processed = app.ingest_summary_rows(section, sanitized_rows)

    assert processed == 0
    assert len(getattr(app, frame_attr)) == 1
    assert messagebox_spy.warnings
    title, message = messagebox_spy.warnings[-1]
    assert title == warning_title
    assert row[0] in message
    assert any(log_fragment in entry.get("mensaje", "") for entry in app.logs)
