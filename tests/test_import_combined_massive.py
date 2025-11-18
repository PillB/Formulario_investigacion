import app as app_module

from settings import FLAG_CLIENTE_LIST, TIPO_SANCION_LIST
from tests.app_factory import build_import_app


def _collect_ids(frames):
    return sorted({frame.id_var.get() for frame in frames if frame.id_var.get()})


def test_import_combined_hydrates_entities_and_deduplicates(monkeypatch, messagebox_spy):
    app = build_import_app(monkeypatch)
    app.detail_catalogs = {
        'id_cliente': {
            'CLI-001': {
                'id_cliente': 'CLI-001',
                'flag': FLAG_CLIENTE_LIST[0],
                'telefonos': '555-1111',
            },
        },
        'id_colaborador': {
            'T2000': {
                'id_colaborador': 'T2000',
                'division': 'Div catálogo',
                'area': 'Área catálogo',
                'tipo_sancion': TIPO_SANCION_LIST[0],
            },
            'T3000': {
                'id_colaborador': 'T3000',
                'division': 'Div catálogo',
                'area': 'Área catálogo',
                'tipo_sancion': TIPO_SANCION_LIST[0],
            },
        },
        'id_producto': {
            'PRD-100': {
                'id_producto': 'PRD-100',
                'id_cliente': 'CLI-001',
                'tipo_producto': 'Tarjeta de crédito',
                'monto_investigado': '5000.00',
            },
        },
    }
    app.detail_lookup_by_id = dict(app.detail_catalogs)

    combined_rows = [
        {
            'id_cliente': 'CLI-001',
            'id_colaborador': 'T2000',
            'id_producto': 'PRD-100',
            'involucramiento': 'T2000:200.00;T3000:100.00',
        },
        {
            'id_cliente': 'CLI-001',
            'id_colaborador': 'T2000',
            'id_producto': 'PRD-100',
            'monto_asignado': '50.75',
        },
        {
            'id_cliente': 'CLI-002',
            'id_colaborador': 'T4000',
            'id_producto': 'PRD-200',
            'involucramiento': '',
        },
    ]
    monkeypatch.setattr(
        app_module,
        'iter_massive_csv_rows',
        lambda _filename: iter(combined_rows),
    )

    app.import_combined(filename='dummy.csv')

    assert _collect_ids(app.client_frames) == ['CLI-001', 'CLI-002']
    assert _collect_ids(app.team_frames) == ['T2000', 'T3000', 'T4000']
    assert _collect_ids(app.product_frames) == ['PRD-100', 'PRD-200']

    product = app._find_product_frame('PRD-100')
    assert product is not None
    assert product.populated_rows[-1]['tipo_producto'] == 'Tarjeta de crédito'
    client = app._find_client_frame('CLI-001')
    assert client.populated_rows[-1]['telefonos'] == '555-1111'

    involvement_values = sorted(
        (inv.team_var.get(), inv.monto_var.get())
        for inv in product.involvements
        if inv.team_var.get()
    )
    assert involvement_values == [('T2000', '50.75'), ('T3000', '100.00')]

    reported = {label: tuple(ids) for label, ids in app.report_calls}
    assert 'clientes' in reported and 'CLI-002' in reported['clientes']
    assert 'colaboradores' in reported and 'T4000' in reported['colaboradores']
    assert 'productos' in reported and 'PRD-200' in reported['productos']


def test_import_combined_handles_large_datasets_with_id_indexing(monkeypatch, messagebox_spy):
    app = build_import_app(monkeypatch)
    client_count = 50
    collaborator_count = 60
    product_count = 40
    total_rows = 400

    rows = []
    for idx in range(total_rows):
        client_id = f"CLI-{idx % client_count:05d}"
        product_id = f"PRD-{idx % product_count:05d}"
        collaborator_id = f"T{idx % collaborator_count:05d}"
        rows.append(
            {
                'id_cliente': client_id,
                'id_producto': product_id,
                'id_colaborador': collaborator_id,
                'tipo_producto': 'Crédito personal',
                'monto_investigado': '100.00',
                'monto_asignado': f"{100 + idx:.2f}",
            }
        )

    monkeypatch.setattr(
        app_module,
        'iter_massive_csv_rows',
        lambda _filename: iter(rows),
    )

    app.import_combined(filename='dummy.csv')

    assert len(_collect_ids(app.client_frames)) == client_count
    assert len(_collect_ids(app.team_frames)) == collaborator_count
    assert len(_collect_ids(app.product_frames)) == product_count

    assert len(app._client_frames_by_id) == client_count
    assert len(app._team_frames_by_id) == collaborator_count
    assert len(app._product_frames_by_id) == product_count

    total_involvements = sum(
        1 for frame in app.product_frames for inv in frame.involvements if inv.team_var.get()
    )
    assert total_involvements >= collaborator_count  # cada ID queda vinculado al menos una vez
