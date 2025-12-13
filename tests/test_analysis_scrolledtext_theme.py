from __future__ import annotations

import os
import tkinter as tk
from tkinter import scrolledtext

import pytest

from app import FraudCaseApp
from theme_manager import ThemeManager


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)
def test_analysis_scrolledtext_theme_refresh(monkeypatch, messagebox_spy, tmp_path):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    monkeypatch.setattr(ThemeManager, "PREFERENCE_FILE", tmp_path / "theme_pref.txt")

    previous_style = ThemeManager._style
    previous_root = ThemeManager._root
    previous_current = ThemeManager._current
    previous_base_configured = ThemeManager._base_style_configured
    previous_windows = set(ThemeManager._tracked_toplevels)

    try:
        style = ThemeManager.build_style(root)
        ThemeManager.apply("light", root=root, style=style)

        app = FraudCaseApp(root)
        assert isinstance(app.antecedentes_text, scrolledtext.ScrolledText)

        text_area = getattr(app.antecedentes_text, "text", app.antecedentes_text)

        light_palette = ThemeManager.current()
        assert app.antecedentes_text.cget("background") == light_palette["background"]
        assert text_area.cget("background") == light_palette["input_background"]
        assert text_area.cget("foreground") == light_palette["input_foreground"]
        assert text_area.cget("insertbackground") == light_palette["accent"]
        assert text_area.cget("selectbackground") == light_palette["select_background"]
        assert text_area.cget("selectforeground") == light_palette["select_foreground"]

        ThemeManager.apply("dark")
        ThemeManager.apply_to_widget_tree(app._analysis_group)

        dark_palette = ThemeManager.current()
        assert app.antecedentes_text.cget("background") == dark_palette["background"]
        assert text_area.cget("background") == dark_palette["input_background"]
        assert text_area.cget("foreground") == dark_palette["input_foreground"]
        assert text_area.cget("insertbackground") == dark_palette["accent"]
        assert text_area.cget("selectbackground") == dark_palette["select_background"]
        assert text_area.cget("selectforeground") == dark_palette["select_foreground"]
    finally:
        root.destroy()
        ThemeManager._style = previous_style
        ThemeManager._root = previous_root
        ThemeManager._current = previous_current
        ThemeManager._base_style_configured = previous_base_configured
        ThemeManager._tracked_toplevels = previous_windows
