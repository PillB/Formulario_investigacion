from report.alerta_temprana import _build_prompt


def test_alerta_temprana_prompt_snapshot_contains_json_contract_by_section():
    prompt = _build_prompt(
        "Análisis",
        "Resumen: 40 suplantaciones detectadas.\nRiesgos: debilidad en autenticación.",
        {
            "categoria1": "Tarjeta",
            "modalidad": "Digital",
            "canal": "App",
            "tipo_informe": "Alerta temprana",
        },
    )

    assert "Enfócate en fallas de control/proceso (no en culpas individuales)." in prompt
    assert "Devuelve SIEMPRE un JSON válido" in prompt
    assert '"resumen":{"texto":"<texto>","fuentes":["<campo>"]}' in prompt
    assert '"cronologia":{"texto":"<texto>","fuentes":["<campo>"]}' in prompt
    assert '"analisis":{"texto":"<texto>","fuentes":["<campo>"]}' in prompt
    assert '"riesgos_identificados":{"texto":"<texto>","fuentes":["<campo>"]}' in prompt
    assert '"recomendaciones":{"texto":"<texto>","fuentes":["<campo>"]}' in prompt
    assert '"responsables":{"texto":"<texto>","fuentes":["<campo>"]}' in prompt
    assert '"resumen_ejecutivo":{"mensaje_clave":"<texto>"' in prompt
    assert "Extensión objetivo para la sección 'Análisis': entre 110 y 170 palabras." in prompt
    assert "Tipo de informe: Alerta temprana; Categoría: Tarjeta; Modalidad: Digital; Canal: App." in prompt


def test_alerta_temprana_prompt_snapshot_includes_examples_and_na_rule():
    prompt = _build_prompt(
        "Resumen",
        "Contexto base",
        {
            "categoria1": "Consumo",
            "modalidad": "Presencial",
            "canal": "Oficina",
            "tipo_informe": "Fraude",
        },
    )

    assert "Ejemplo mínimo de estructura válida" in prompt
    assert '"cronologia":{"texto":"N/A"' in prompt
    assert "usa exactamente 'N/A'" in prompt
    assert "(o ['N/A'] para listas)" in prompt
    assert "Todas las llaves son obligatorias." in prompt
    assert "Extensión objetivo para la sección 'Resumen': entre 80 y 120 palabras." in prompt
