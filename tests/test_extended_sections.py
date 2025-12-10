"""Cobertura para las secciones extendidas del informe."""

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk

import pytest

import app as app_module
from app import FraudCaseApp
from models.analitica_catalog import format_analitica_option, get_analitica_display_options
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


@pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="Tk display not available")
def test_header_analitica_combobox_uses_catalog():
    app = FraudCaseApp.__new__(FraudCaseApp)
    app._encabezado_vars = {}
    app._encabezado_data = {"analitica_contable": "4300000000"}
    app._encabezado_autofill_keys = set()
    app._syncing_case_to_header = False
    app._notify_dataset_changed = lambda: None
    app._register_post_edit_validation = lambda *args, **kwargs: None
    app.register_tooltip = lambda *args, **kwargs: None
    root = tk.Tk()
    root.withdraw()
    try:
        app._build_header_fields(root)
        header_group = root.winfo_children()[0]
        combos = [child for child in header_group.winfo_children() if isinstance(child, ttk.Combobox)]
        assert combos, "Se esperaba un combobox para analítica contable"
        analitica_combo = combos[0]
        assert list(analitica_combo["values"]) == get_analitica_display_options()
        assert app._encabezado_vars["analitica_contable"].get() == format_analitica_option("4300000000")
    finally:
        root.destroy()


@pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="Tk display not available")
def test_header_analitica_updates_dataset():
    app = FraudCaseApp.__new__(FraudCaseApp)
    app._encabezado_vars = {}
    app._encabezado_data = {"analitica_contable": ""}
    app._encabezado_autofill_keys = set()
    app._syncing_case_to_header = False
    app._notify_dataset_changed = lambda: None
    app._register_post_edit_validation = lambda *args, **kwargs: None
    app.register_tooltip = lambda *args, **kwargs: None
    root = tk.Tk()
    root.withdraw()
    try:
        app._build_header_fields(root)
        app._encabezado_vars["analitica_contable"].set(format_analitica_option("4300000002"))
        app._update_header_analitica_value()
        assert app._encabezado_data["analitica_contable"] == "4300000002"
    finally:
        root.destroy()
