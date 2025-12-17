"""Regresión: aplicar el tema a DateEntry no debe fallar ni romper estilos."""

import os
import tkinter as tk

import pytest
from tkcalendar import DateEntry

from theme_manager import ThemeManager


pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)


def test_theme_manager_handles_dateentry_without_crashing():
    root = tk.Tk()
    root.withdraw()
    try:
        widget = DateEntry(root)

        ThemeManager.apply("light", root)
        ThemeManager.apply_to_widget_tree(root)

        assert widget.cget("style") == ThemeManager.COMBOBOX_STYLE
        calendar = getattr(widget, "_calendar", None)
        if calendar is not None:
            assert calendar.cget("selectbackground") == ThemeManager.current()["select_background"]
    finally:
        root.destroy()
