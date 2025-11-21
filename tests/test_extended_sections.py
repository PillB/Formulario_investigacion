"""Cobertura para las secciones extendidas del informe."""

import json
from pathlib import Path

import app as app_module
from app import FraudCaseApp
from tests.test_validation import build_headless_app


def test_reset_extended_sections_sets_empty_defaults():
    app = FraudCaseApp.__new__(FraudCaseApp)

    app._reset_extended_sections()

    assert app._encabezado_data == {}
    assert app._operaciones_data == []
    assert app._anexos_data == []
    assert app._firmas_data == []
    assert app._recomendaciones_categorias == {}


def test_normalization_helpers_sanitize_payloads():
    encabezado = FraudCaseApp._normalize_mapping_strings(
        {"dirigido_a": "  Director  ", "otro": None},
        ["dirigido_a", "referencia"],
    )
    assert encabezado["dirigido_a"] == "Director"
    assert encabezado["referencia"] == ""
    assert encabezado["otro"] == ""

    rows = FraudCaseApp._normalize_table_rows(
        [
            {"cliente": "  Ana "},
            {"cliente": None},
            "ignorar",  # Valores no mapeables deben descartarse
        ]
    )
    assert rows == [{"cliente": "Ana"}, {"cliente": ""}]

    categorias = FraudCaseApp._normalize_recommendation_categories(
        {"operativo": ["  Mejorar control  ", ""], "legal": " ", "extra": ["", " Otra "]}
    )
    assert categorias["operativo"] == ["Mejorar control"]
    assert categorias["legal"] == []
    assert categorias["extra"] == ["Otra"]


def test_gather_data_preserves_extended_sections():
    app = build_headless_app("Crédito personal")
    app._encabezado_data = {"dirigido_a": "  Auditoría  ", "analitica_contable": None}
    app._operaciones_data = [{"cliente": "  Carlos "}, {"cliente": None}]
    app._anexos_data = [{"titulo": "  Anexo A "}]
    app._firmas_data = [{"nombre": "  Firmante "}]
    app._recomendaciones_categorias = {"operativo": ["  Ajuste  "], "legal": "", "extra": " Nota "}

    gathered = app.gather_data()

    assert gathered["encabezado"]["dirigido_a"] == "Auditoría"
    assert gathered["encabezado"]["analitica_contable"] == ""
    assert gathered["operaciones"][0]["cliente"] == "Carlos"
    assert gathered["operaciones"][1]["cliente"] == ""
    assert gathered["anexos"] == [{"titulo": "Anexo A"}]
    assert gathered["firmas"] == [{"nombre": "Firmante"}]
    assert gathered["recomendaciones_categorias"]["operativo"] == ["Ajuste"]
    assert gathered["recomendaciones_categorias"]["legal"] == []
    assert gathered["recomendaciones_categorias"]["extra"] == ["Nota"]


def test_autosave_persists_extended_sections(tmp_path, monkeypatch):
    app = build_headless_app("Crédito personal")
    autosave_path = Path(tmp_path) / "autosave.json"
    monkeypatch.setattr(app_module, "AUTOSAVE_FILE", autosave_path)
    app.inline_summary_trees = {}
    app.summary_tables = {}

    app._encabezado_data = {"dirigido_a": "  Auditoría  ", "analitica_contable": None}
    app._operaciones_data = [{"cliente": "  Carlos "}, {"cliente": None}]
    app._anexos_data = [{"titulo": "  Anexo A "}]
    app._firmas_data = [{"nombre": "  Firmante "}]
    app._recomendaciones_categorias = {"operativo": ["  Ajuste  "], "legal": "", "extra": " Nota "}

    dataset = app.save_auto()

    saved = json.loads(autosave_path.read_text(encoding="utf-8"))
    assert saved["encabezado"]["dirigido_a"] == "Auditoría"
    assert saved["operaciones"][0]["cliente"] == "Carlos"
    assert saved["anexos"] == [{"titulo": "Anexo A"}]
    assert saved["firmas"] == [{"nombre": "Firmante"}]
    assert saved["recomendaciones_categorias"]["extra"] == ["Nota"]
    assert dataset.get("encabezado", {}).get("analitica_contable") == ""
