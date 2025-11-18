import types

import pytest

import app as app_module
from app import FraudCaseApp
from settings import (CRITICIDAD_LIST, FLAG_CLIENTE_LIST, TIPO_ID_LIST,
                      TIPO_SANCION_LIST)
from tests.stubs import (ClientFrameStub, NormFrameStub, ProductFrameStub,
                         RiskFrameStub, TeamFrameStub, build_frame_finder,
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
    app._autosave_job_id = None
    app._autosave_dirty = False

    def _report(self, label, ids):
        self.report_calls.append((label, list(ids)))

    app._report_missing_detail_ids = types.MethodType(_report, app)

    app.save_auto_called = False
    app.save_auto = lambda: setattr(app, 'save_auto_called', True)
    app.request_autosave = lambda: app.save_auto()

    def _notify(self, summary_sections=None):
        self.request_autosave()
        self._schedule_summary_refresh(sections=summary_sections)

    app._notify_dataset_changed = types.MethodType(_notify, app)
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
    app.risk_frames = []
    app.norm_frames = []

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
    app._find_client_frame = types.MethodType(build_frame_finder('client_frames'), app)
    app._find_team_frame = types.MethodType(build_frame_finder('team_frames'), app)
    app._find_product_frame = types.MethodType(build_frame_finder('product_frames'), app)
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


def test_import_combined_hydrates_and_reports_missing_ids(monkeypatch, messagebox_spy):
    app = _prepare_import_app(monkeypatch, messagebox_spy)
    app.detail_catalogs = {
        'id_cliente': {
            'CLI-001': {
                'id_cliente': 'CLI-001',
                'telefonos': '555-1000',
                'flag': FLAG_CLIENTE_LIST[0],
            },
        },
        'id_colaborador': {
            'T0001': {
                'id_colaborador': 'T0001',
                'area': 'Comercial',
                'tipo_sancion': TIPO_SANCION_LIST[0],
            },
        },
        'id_producto': {
            'PRD-001': {
                'id_producto': 'PRD-001',
                'id_cliente': 'CLI-001',
                'tipo_producto': 'Tarjeta de crédito',
                'monto_investigado': '2000.00',
            },
        },
    }
    app.detail_lookup_by_id = dict(app.detail_catalogs)
    combined_rows = [
        {
            'id_cliente': ' CLI-001 ',
            'telefonos': '',
            'correos': '',
            'id_colaborador': ' T0001 ',
            'id_producto': ' PRD-001 ',
            'involucramiento': ' T0001 : 200.50 ; T9999 : 30 ',
        },
        {
            'id_cliente': 'CLI-002',
            'id_colaborador': 'T1111',
            'id_producto': 'PRD-001',
            'involucramiento': '',
        },
        {
            'id_cliente': 'CLI-001',
            'id_colaborador': 'T0001',
            'id_producto': 'PRD-001',
            'involucramiento': '',
            'monto_asignado': ' 50.75 ',
        },
    ]
    monkeypatch.setattr(
        app_module,
        "iter_massive_csv_rows",
        lambda _filename: iter(combined_rows),
    )

    app.import_combined(filename="dummy.csv")

    client_ids = sorted(frame.id_var.get() for frame in app.client_frames if frame.id_var.get())
    assert client_ids == ['CLI-001', 'CLI-002']
    product_frame = app._find_product_frame('PRD-001')
    assert product_frame is not None
    assert product_frame.populated_rows[0]['tipo_producto'] == 'Tarjeta de crédito'
    client_frame = app._find_client_frame('CLI-001')
    assert client_frame.populated_rows[0]['telefonos'] == '555-1000'

    involvement_records = sorted(
        (
            inv.team_var.get(),
            inv.monto_var.get(),
        )
        for inv in product_frame.involvements
        if inv.team_var.get()
    )
    assert involvement_records == [('T0001', '50.75'), ('T9999', '30')]

    reported = {label: ids for label, ids in app.report_calls}
    assert set(reported.get('clientes', [])) == {'CLI-002'}
    assert set(reported.get('colaboradores', [])) == {'T1111', 'T9999'}


def test_import_risks_and_norms_hydrate_from_catalogs(monkeypatch, messagebox_spy):
    app = _prepare_import_app(monkeypatch, messagebox_spy)
    app.detail_catalogs.update(
        {
            'id_riesgo': {
                'RSK-900': {
                    'id_riesgo': 'RSK-900',
                    'lider': 'Alice',
                    'descripcion': 'Desde catálogo',
                    'criticidad': CRITICIDAD_LIST[-1],
                    'exposicion_residual': '1000',
                    'planes_accion': 'Mitigar',
                }
            },
            'id_norma': {
                'NOR-01': {
                    'id_norma': 'NOR-01',
                    'descripcion': 'Regla catálogo',
                    'fecha_vigencia': '2023-01-01',
                }
            },
        }
    )
    app.detail_lookup_by_id = dict(app.detail_catalogs)

    risk_rows = [
        {'id_riesgo': 'RSK-900'},
        {'id_riesgo': 'RSK-900'},
    ]
    monkeypatch.setattr(
        app_module,
        "iter_massive_csv_rows",
        lambda _filename: iter(risk_rows),
    )

    app.import_risks(filename="dummy.csv")

    assert len([frame for frame in app.risk_frames if frame.id_var.get()]) == 1
    risk_frame = app.risk_frames[0]
    assert risk_frame.descripcion_var.get() == 'Desde catálogo'
    assert risk_frame.criticidad_var.get() == CRITICIDAD_LIST[-1]
    assert risk_frame.planes_var.get() == 'Mitigar'
    assert risk_frame.lider_var.get() == 'Alice'
    assert risk_frame.exposicion_var.get() == '1000'

    norm_rows = [
        {'id_norma': 'NOR-01'},
        {'id_norma': 'NOR-01'},
    ]
    monkeypatch.setattr(
        app_module,
        "iter_massive_csv_rows",
        lambda _filename: iter(norm_rows),
    )

    app.import_norms(filename="dummy.csv")

    assert len([frame for frame in app.norm_frames if frame.id_var.get()]) == 1
    norm_frame = app.norm_frames[0]
    assert norm_frame.descripcion_var.get() == 'Regla catálogo'
    assert norm_frame.fecha_var.get() == '2023-01-01'


def test_import_claims_uses_catalogs_and_reports_missing_products(monkeypatch, messagebox_spy):
    app = _prepare_import_app(monkeypatch, messagebox_spy)
    existing_product = ProductFrameStub()
    existing_product.id_var.set('PRD-EXIST')
    app.product_frames.append(existing_product)
    app.detail_catalogs = {
        'id_cliente': {
            'CLI-NEW': {
                'id_cliente': 'CLI-NEW',
                'telefonos': '555-2000',
            }
        },
        'id_colaborador': {},
        'id_producto': {
            'PRD-NEW': {
                'id_producto': 'PRD-NEW',
                'id_cliente': 'CLI-NEW',
                'nombre_analitica': 'Cat claim',
                'codigo_analitica': '4300000001',
            }
        },
    }
    app.detail_lookup_by_id = dict(app.detail_catalogs)

    claim_rows = [
        {
            'id_producto': 'PRD-EXIST',
            'id_reclamo': ' C00001234 ',
            'nombre_analitica': 'Manual',
            'codigo_analitica': '4300000000',
        },
        {
            'id_producto': 'PRD-NEW',
            'id_reclamo': ' c00005678 ',
            'nombre_analitica': '',
            'codigo_analitica': '',
        },
        {
            'id_producto': 'PRD-MISSING',
            'id_reclamo': ' C00009999 ',
            'nombre_analitica': 'Manual',
            'codigo_analitica': '4300000002',
        },
    ]
    monkeypatch.setattr(
        app_module,
        "iter_massive_csv_rows",
        lambda _filename: iter(claim_rows),
    )

    app.import_claims(filename="dummy.csv")

    existing_claim_ids = [claim.data.get('id_reclamo') for claim in existing_product.claims if claim.data]
    assert existing_claim_ids == ['C00001234']
    assert existing_product.persisted_lookups == 1
    new_product = app._find_product_frame('PRD-NEW')
    assert new_product is not None
    assert new_product.populated_rows[0]['id_cliente'] == 'CLI-NEW'
    assert new_product.claims[0].data['id_reclamo'] == 'c00005678'
    assert new_product.persisted_lookups == 1
    assert any(frame.id_var.get() == 'CLI-NEW' for frame in app.client_frames)
    assert app.product_lookup['PRD-EXIST']['reclamos'][0]['id_reclamo'] == 'C00001234'

    reported = {label: ids for label, ids in app.report_calls}
    assert 'productos' in reported and 'PRD-MISSING' in reported['productos']
    assert 'reclamos' in app.sync_calls
