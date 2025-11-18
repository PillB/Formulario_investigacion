import types

import pytest

import app as app_module
from app import FraudCaseApp
from settings import FLAG_CLIENTE_LIST, TIPO_ID_LIST, TIPO_SANCION_LIST
from tests.stubs import (ClientFrameStub, ProductFrameStub, TeamFrameStub,
                         build_involvement_slot, build_populate_method,
                         build_slot_factory)


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
    return spy


def _prepare_import_app(monkeypatch, messagebox_spy):
    app = FraudCaseApp.__new__(FraudCaseApp)
    app._suppress_messagebox = True
    app.logs = []
    app.client_frames = []
    app.team_frames = []
    app.product_frames = []
    app.detail_catalogs = {
        'id_cliente': {},
        'id_colaborador': {},
        'id_producto': {},
    }
    app.detail_lookup_by_id = {}
    app.client_lookup = {}
    app.team_lookup = {}
    app.product_lookup = {}
    app.summary_tables = {}
    app.summary_config = {}
    app._schedule_summary_refresh = lambda *_args, **_kwargs: None
    app._notify_taxonomy_warning = lambda *_args, **_kwargs: None
    app._notify_products_created_without_details = lambda *_args, **_kwargs: None
    app.report_calls = []

    def _report(self, label, ids):
        self.report_calls.append((label, list(ids)))

    app._report_missing_detail_ids = types.MethodType(_report, app)

    app.save_auto_called = False
    app.save_auto = lambda: setattr(app, 'save_auto_called', True)
    app.sync_calls = []
    app.sync_main_form_after_import = lambda section, **kwargs: app.sync_calls.append(section)

    app._obtain_client_slot_for_import = types.MethodType(
        build_slot_factory(app.client_frames, ClientFrameStub),
        app,
    )
    app._obtain_team_slot_for_import = types.MethodType(
        build_slot_factory(app.team_frames, TeamFrameStub),
        app,
    )
    app._obtain_product_slot_for_import = types.MethodType(
        build_slot_factory(app.product_frames, ProductFrameStub),
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
    return app


def test_import_combined_creates_entities_and_prevents_duplicates(monkeypatch, messagebox_spy):
    app = _prepare_import_app(monkeypatch, messagebox_spy)
    valid_rows = [
        {
            'id_cliente': '12345678',
            'tipo_id': TIPO_ID_LIST[0],
            'flag_cliente': FLAG_CLIENTE_LIST[0],
            'telefonos': '999888777',
            'correos': 'demo@example.com',
            'direcciones': 'Av. Principal 123',
            'accionado': 'Fiscalía',
            'id_colaborador': 'T12345',
            'division': 'Division A',
            'area': 'Area Comercial',
            'tipo_sancion': TIPO_SANCION_LIST[0],
            'id_producto': '1234567890123',
            'tipo_producto': 'Crédito personal',
            'monto_investigado': '1000.00',
            'involucramiento': 'T12345:120.00;T54321:80.00',
        },
        {
            'id_cliente': '12345678',
            'id_colaborador': 'T12345',
            'tipo_sancion': TIPO_SANCION_LIST[0],
            'id_producto': '1234567890123',
            'tipo_producto': 'Crédito personal',
            'monto_investigado': '1000.00',
            'involucramiento': '',
            'monto_asignado': '150.50',
        },
    ]
    monkeypatch.setattr(
        app_module,
        "iter_massive_csv_rows",
        lambda _filename: iter(valid_rows),
    )

    app.import_combined(filename="dummy.csv")

    client_ids = [frame.id_var.get() for frame in app.client_frames if frame.id_var.get()]
    team_ids = [frame.id_var.get() for frame in app.team_frames if frame.id_var.get()]
    product_ids = [frame.id_var.get() for frame in app.product_frames if frame.id_var.get()]

    assert client_ids == ['12345678']
    assert sorted(team_ids) == ['T12345', 'T54321']
    assert product_ids == ['1234567890123']

    involvement_records = []
    for frame in app.product_frames:
        if frame.id_var.get() != '1234567890123':
            continue
        for inv in frame.involvements:
            if not inv.team_var.get():
                continue
            involvement_records.append((inv.team_var.get(), inv.monto_var.get()))
    assert sorted(involvement_records) == [('T12345', '150.50'), ('T54321', '80.00')]

    assert app.save_auto_called is True
    assert app.sync_calls == ['datos combinados']
    assert messagebox_spy.errors == []
    assert any("Datos combinados importados" in msg for _title, msg in messagebox_spy.infos)

    reported = {label: ids for label, ids in app.report_calls}
    assert 'clientes' in reported and '12345678' in reported['clientes']
    assert 'colaboradores' in reported and set(reported['colaboradores']) == {'T12345', 'T54321'}
    assert 'productos' in reported and '1234567890123' in reported['productos']

    assert sum(1 for frame in app.team_frames if frame.id_var.get() == 'T12345') == 1
    assert len(app.product_frames) == 1
