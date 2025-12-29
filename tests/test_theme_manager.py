from __future__ import annotations

import os
import tkinter as tk

import pytest

from app import FraudCaseApp
from theme_manager import ThemeManager


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)
def test_norm_frame_scrolledtext_uses_dark_theme(monkeypatch, messagebox_spy, tmp_path):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    del messagebox_spy
    monkeypatch.setattr(ThemeManager, "PREFERENCE_FILE", tmp_path / "theme_pref.txt")

    previous_style = ThemeManager._style
    previous_root = ThemeManager._root
    previous_current = ThemeManager._current
    previous_base_configured = ThemeManager._base_style_configured
    previous_windows = set(ThemeManager._tracked_toplevels)

    try:
        style = ThemeManager.build_style(root)
        ThemeManager.apply("dark", root=root, style=style)

        app = FraudCaseApp(root)
        ThemeManager.apply("dark")

        app.add_norm()
        norm_frame = app.norm_frames[-1]

        text_area = getattr(norm_frame.detalle_text, "text", norm_frame.detalle_text)
        dark_palette = ThemeManager.current()
        assert norm_frame.detalle_text.cget("background") == dark_palette["background"]
        assert text_area.cget("background") == dark_palette["input_background"]
        assert text_area.cget("foreground") == dark_palette["input_foreground"]
    finally:
        root.destroy()
        ThemeManager._style = previous_style
        ThemeManager._root = previous_root
        ThemeManager._current = previous_current
        ThemeManager._base_style_configured = previous_base_configured
        ThemeManager._tracked_toplevels = previous_windows
