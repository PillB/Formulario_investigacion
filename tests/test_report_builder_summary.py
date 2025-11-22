from report_builder import CaseData, PLACEHOLDER, _build_report_context


def test_header_table_aggregates_amounts_and_metadata():
    payload = {
        'caso': {'categoria1': 'Categoria A', 'categoria2': 'Categoria B'},
        'encabezado': {},
        'clientes': [],
        'colaboradores': [],
        'productos': [
            {'monto_investigado': '100.00', 'monto_contingencia': '20.50'},
            {'monto_investigado': '50.25', 'monto_perdida_fraude': '10'},
        ],
        'reclamos': [{'codigo_analitica': '4300000002'}],
        'involucramientos': [],
        'riesgos': [],
        'normas': [],
        'analisis': {},
        'operaciones': [],
        'anexos': [],
        'firmas': [],
        'recomendaciones_categorias': {},
    }

    context = _build_report_context(CaseData.from_mapping(payload))
    header = dict(zip(context['header_headers'], context['header_row']))

    assert header['Importe investigado'] == '150.25'
    assert header['Contingencia'] == '20.50'
    assert header['Pérdida total'] == '10.00'
    assert header['Analítica Contable'] == '4300000002'


def test_status_amounts_require_manual_input():
    payload = {
        'caso': {},
        'encabezado': {},
        'clientes': [],
        'colaboradores': [],
        'productos': [
            {
                'monto_normal': '12.34',
                'monto_vencido': '1.00',
                'monto_judicial': '2.00',
                'monto_castigo': '3.00',
            }
        ],
        'reclamos': [],
        'involucramientos': [],
        'riesgos': [],
        'normas': [],
        'analisis': {},
        'operaciones': [],
        'anexos': [],
        'firmas': [],
        'recomendaciones_categorias': {},
    }

    context = _build_report_context(CaseData.from_mapping(payload))
    header = dict(zip(context['header_headers'], context['header_row']))

    assert header['Normal'] == PLACEHOLDER
    assert header['Vencido'] == PLACEHOLDER
    assert header['Judicial'] == PLACEHOLDER
    assert header['Castigo'] == PLACEHOLDER


def test_status_amounts_use_user_supplied_values():
    payload = {
        'caso': {},
        'encabezado': {
            'normal': '100',
            'vencido': '200',
            'judicial': '300',
            'castigo': '400',
        },
        'clientes': [],
        'colaboradores': [],
        'productos': [
            {
                'monto_normal': '0',
                'monto_vencido': '0',
                'monto_judicial': '0',
                'monto_castigo': '0',
            }
        ],
        'reclamos': [],
        'involucramientos': [],
        'riesgos': [],
        'normas': [],
        'analisis': {},
        'operaciones': [],
        'anexos': [],
        'firmas': [],
        'recomendaciones_categorias': {},
    }

    context = _build_report_context(CaseData.from_mapping(payload))
    header = dict(zip(context['header_headers'], context['header_row']))

    assert header['Normal'] == '100.00'
    assert header['Vencido'] == '200.00'
    assert header['Judicial'] == '300.00'
    assert header['Castigo'] == '400.00'


def test_operation_rows_include_totals_row():
    payload = {
        'caso': {},
        'encabezado': {},
        'clientes': [],
        'colaboradores': [],
        'productos': [],
        'reclamos': [],
        'involucramientos': [],
        'riesgos': [],
        'normas': [],
        'analisis': {},
        'operaciones': [
            {'importe_desembolsado': '10.00', 'saldo_deudor': '5.00'},
            {'importe_desembolsado': '2.50', 'saldo_deudor': '1.00'},
        ],
        'anexos': [],
        'firmas': [],
        'recomendaciones_categorias': {},
    }

    context = _build_report_context(CaseData.from_mapping(payload))
    assert context['operation_rows'][-1][0] == 'Totales'
    assert context['operation_rows'][-1][8] == '12.50'
    assert context['operation_rows'][-1][9] == '6.00'
