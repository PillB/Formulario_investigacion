import pytest

import app as app_module
from settings import (CRITICIDAD_LIST, FLAG_CLIENTE_LIST, TIPO_ID_LIST,
                      TIPO_SANCION_LIST)
from tests.app_factory import build_import_app
from tests.stubs import ClientFrameStub, ProductFrameStub, TeamFrameStub


def test_import_combined_creates_entities_and_prevents_duplicates(monkeypatch, messagebox_spy):
    app = build_import_app(monkeypatch)
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
    app = build_import_app(monkeypatch)
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
                'involucramiento': ' T0001 : 200.50 ; T9999 : 30.00 ',
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
    assert involvement_records == [('T0001', '50.75'), ('T9999', '30.00')]

    reported = {label: ids for label, ids in app.report_calls}
    assert set(reported.get('clientes', [])) == {'CLI-002'}
    assert set(reported.get('colaboradores', [])) == {'T1111', 'T9999'}


@pytest.mark.parametrize(
    "row_overrides,expected_fragment",
    [
        (
            {'involucramiento': 'T12345:10.123'},
            "solo puede tener dos decimales como máximo.",
        ),
        (
            {'involucramiento': 'T12345:abc'},
            "debe ser un número válido.",
        ),
        (
            {'involucramiento': 'T12345:1000000000000.00'},
            "no puede tener más de 12 dígitos en la parte entera.",
        ),
    ],
    ids=[
        "parsed_entry_extra_decimals",
        "parsed_entry_non_numeric",
        "parsed_entry_oversized",
    ],
)
def test_import_combined_invalid_involvement_amount_raises_value_error(
    monkeypatch,
    messagebox_spy,
    row_overrides,
    expected_fragment,
):
    app = build_import_app(monkeypatch)
    base_row = {
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
        'id_producto': 'PRD-123',
        'tipo_producto': 'Crédito personal',
        'monto_investigado': '1000.00',
        'involucramiento': 'T12345:120.00',
    }
    invalid_row = dict(base_row)
    invalid_row.update(row_overrides)
    monkeypatch.setattr(
        app_module,
        "iter_massive_csv_rows",
        lambda _filename: iter([invalid_row]),
    )

    with pytest.raises(ValueError) as excinfo:
        app.import_combined(filename="dummy.csv")
    assert expected_fragment in str(excinfo.value)

    assert messagebox_spy.errors
    title, message = messagebox_spy.errors[-1]
    assert 'No se pudo importar' in (message or '')


def test_import_combined_normalizes_involvement_amounts_without_two_decimals(
    monkeypatch,
    messagebox_spy,
):
    app = build_import_app(monkeypatch)
    normalized_rows = [
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
            'id_producto': 'PRD-123',
            'tipo_producto': 'Crédito personal',
            'monto_investigado': '1000.00',
            'involucramiento': 'T12345:99',
        },
        {
            'id_cliente': '12345678',
            'tipo_id': TIPO_ID_LIST[0],
            'flag_cliente': FLAG_CLIENTE_LIST[0],
            'telefonos': '999888777',
            'correos': 'demo@example.com',
            'direcciones': 'Av. Principal 123',
            'accionado': 'Fiscalía',
            'id_colaborador': 'T54321',
            'division': 'Division A',
            'area': 'Area Comercial',
            'tipo_sancion': TIPO_SANCION_LIST[0],
            'id_producto': 'PRD-123',
            'tipo_producto': 'Crédito personal',
            'monto_investigado': '1000.00',
            'involucramiento': '',
            'monto_asignado': '99',
        },
    ]
    monkeypatch.setattr(
        app_module,
        "iter_massive_csv_rows",
        lambda _filename: iter(normalized_rows),
    )

    app.import_combined(filename="dummy.csv")

    product_frame = app._find_product_frame('PRD-123')
    amounts = {
        inv.team_var.get(): inv.monto_var.get()
        for inv in product_frame.involvements
        if inv.team_var.get()
    }

    assert amounts['T12345'] == '99.00'
    assert amounts['T54321'] == '99.00'
    assert messagebox_spy.errors == []


def test_import_risks_and_norms_hydrate_from_catalogs(monkeypatch, messagebox_spy):
    app = build_import_app(monkeypatch)
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
    app = build_import_app(monkeypatch)
    existing_product = ProductFrameStub()
    existing_product.id_var.set('PRD-EXIST')
    existing_product.id_change_callback = app._handle_product_id_change
    app._handle_product_id_change(existing_product, None, 'PRD-EXIST')
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


@pytest.mark.parametrize(
    "index_attr,finder_name,frames_attr,frame_factory,identifier",
    [
        ("_client_frames_by_id", "_find_client_frame", "client_frames", ClientFrameStub, "CLI-999"),
        ("_team_frames_by_id", "_find_team_frame", "team_frames", TeamFrameStub, "T55555"),
        ("_product_frames_by_id", "_find_product_frame", "product_frames", ProductFrameStub, "PRD-555"),
    ],
)
def test_frame_lookups_scale_constant_time(monkeypatch, messagebox_spy, index_attr, finder_name, frames_attr, frame_factory, identifier):
    app = build_import_app(monkeypatch)

    class ExplodingVar:
        def get(self):
            raise AssertionError("Lookup should not scan frame list")

        def set(self, _value):
            raise AssertionError("Lookup should not mutate exploding frames")

    class ExplodingFrame:
        def __init__(self):
            self.id_var = ExplodingVar()

    exploding_frames = [ExplodingFrame() for _ in range(2000)]
    getattr(app, frames_attr).extend(exploding_frames)

    target = frame_factory()
    target.id_var.set(identifier)
    getattr(app, frames_attr).append(target)
    getattr(app, index_attr)[identifier] = target

    finder = getattr(app, finder_name)
    assert finder(f"  {identifier}  ") is target
