import os
import tkinter as tk

import pytest

from app import FraudCaseApp


pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)


def test_apply_text_tag_toggles_and_preserves_cursor(messagebox_spy):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    try:
        app = FraudCaseApp(root)
        widget = app.antecedentes_text
        widget.delete("1.0", tk.END)
        widget.insert("1.0", "Texto de prueba")
        widget.mark_set("insert", "1.5")
        widget.tag_add("sel", "1.0", "1.5")

        initial_insert = widget.index("insert")

        app._apply_text_tag(widget, "bold")
        ranges = widget.tag_ranges("bold")

        assert len(ranges) == 2
        assert widget.index(ranges[0]) == "1.0"
        assert widget.index(ranges[1]) == "1.5"
        assert widget.index("insert") == initial_insert

        widget.tag_add("sel", "1.0", "1.5")
        app._apply_text_tag(widget, "bold")

        assert widget.tag_ranges("bold") == ()
        assert widget.index("insert") == initial_insert
    finally:
        root.destroy()


def test_analysis_tags_survive_save_and_reload(messagebox_spy):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    try:
        app = FraudCaseApp(root)
        widget = app.antecedentes_text
        widget.delete("1.0", tk.END)
        widget.insert("1.0", "Etiqueta en negrita")
        widget.tag_add("bold", "1.10", "1.17")

        saved = app.gather_data().as_dict()
        saved["analisis"] = app._normalize_analysis_texts(saved["analisis"])

        reload_root = tk.Tk()
        reload_root.withdraw()
        try:
            reloaded_app = FraudCaseApp(reload_root)
            reloaded_app.populate_from_data(saved)
            ranges = reloaded_app.antecedentes_text.tag_ranges("bold")

            assert len(ranges) == 2
            assert reloaded_app.antecedentes_text.index(ranges[0]) == "1.10"
            assert reloaded_app.antecedentes_text.index(ranges[1]) == "1.17"
        finally:
            reload_root.destroy()
    finally:
        root.destroy()
