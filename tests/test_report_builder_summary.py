from report_builder import CaseData, _build_report_context


def test_summary_paragraphs_include_counts_and_modalities():
    payload = {
        'caso': {'modalidad': 'Modalidad X', 'categoria1': 'Categoria A', 'categoria2': 'Categoria B'},
        'clientes': [{'tipo_id': 'DNI', 'id_cliente': '001'}],
        'colaboradores': [{'id_colaborador': 'T12345'}],
        'productos': [
            {'id_producto': 'P001', 'id_cliente': '001', 'modalidad': 'Modalidad X', 'monto_investigado': '150.25'}
        ],
        'reclamos': [],
        'involucramientos': [],
        'riesgos': [],
        'normas': [],
        'analisis': {},
    }

    context = _build_report_context(CaseData.from_mapping(payload))

    assert context['summary_paragraphs'][0] == (
        "Resumen cuantitativo: Se registran 1 clientes, 1 colaboradores y 1 productos vinculados. "
        "Monto afectado total 150.25."
    )
    assert context['summary_paragraphs'][1] == (
        "Modalidades y tipificación: Modalidades destacadas: Modalidad X. Tipificación: Categoria A / Categoria B."
    )


def test_summary_paragraphs_handle_empty_data_with_placeholder():
    empty_payload = {
        'caso': {},
        'clientes': [],
        'colaboradores': [],
        'productos': [],
        'reclamos': [],
        'involucramientos': [],
        'riesgos': [],
        'normas': [],
        'analisis': {},
    }

    context = _build_report_context(CaseData.from_mapping(empty_payload))

    assert context['summary_paragraphs'] == [
        "Resumen cuantitativo: Sin información registrada.",
        "Modalidades y tipificación: Sin información registrada.",
    ]
