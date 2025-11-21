"""Pruebas rápidas para la aplicación de temas de la ventana principal."""

import os
import tkinter as tk

import pytest

from app import FraudCaseApp
from theme_manager import ThemeManager
from ui.config import init_styles


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)
def test_theme_application_on_main_window(messagebox_spy):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    previous_style = ThemeManager._style
    previous_root = ThemeManager._root
    previous_current = ThemeManager.current

    try:
        style = init_styles(root)
        _app = FraudCaseApp(root)

        ThemeManager.apply("light", root=root, style=style)
        ThemeManager.apply("dark", root=root, style=style)
    finally:
        root.destroy()
        ThemeManager._style = previous_style
        ThemeManager._root = previous_root
        ThemeManager.current = previous_current
