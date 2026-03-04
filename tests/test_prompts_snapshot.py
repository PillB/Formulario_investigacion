from report.alerta_temprana import _build_prompt


def test_alerta_temprana_prompt_snapshot_contains_schema_and_guardrails():
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
    assert '{"seccion":"<nombre>","contenido":"<texto>","palabras_objetivo":{"min":<int>,"max":<int>},"fuentes":["<campo_1>","<campo_2>"]}' in prompt
    assert "Extensión objetivo para la sección 'Análisis': entre 110 y 170 palabras." in prompt
    assert "Tipo de informe: Alerta temprana; Categoría: Tarjeta; Modalidad: Digital; Canal: App." in prompt


def test_alerta_temprana_prompt_snapshot_word_limits_by_section():
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

    assert "Extensión objetivo para la sección 'Resumen': entre 80 y 120 palabras." in prompt
    assert "fuentes" in prompt
