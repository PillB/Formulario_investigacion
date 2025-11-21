from report_builder import CaseData, _build_report_context


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
