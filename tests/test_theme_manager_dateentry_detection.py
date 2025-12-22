"""Cobertura: identificación estricta de DateEntry y tolerancia a errores."""

import os
import tkinter as tk

import pytest

from theme_manager import ThemeManager


pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)


def test_is_date_entry_ignores_calendar_widget():
    tkcalendar = pytest.importorskip("tkcalendar")
    Calendar = getattr(tkcalendar, "Calendar", None)
    if Calendar is None:
        pytest.skip("tkcalendar.Calendar no disponible")

    root = tk.Tk()
    root.withdraw()
    try:
        widget = Calendar(root)
        assert ThemeManager._is_date_entry(widget) is False
    finally:
        root.destroy()


def test_apply_widget_tree_survives_attribute_errors(monkeypatch):
    root = tk.Tk()
    root.withdraw()
    try:
        widget = tk.Frame(root)
        widget.pack()

        def boom(*_args, **_kwargs):
            raise AttributeError("boom")

        monkeypatch.setattr(ThemeManager, "_apply_widget_attributes", boom)
        ThemeManager._apply_widget_tree(root, ThemeManager.current())
    finally:
        root.destroy()
