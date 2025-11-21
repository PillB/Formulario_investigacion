"""Smoke test covering ThemeManager toggling across primary windows."""

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
def test_theme_toggle_roundtrip(monkeypatch, messagebox_spy, tmp_path):
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

    modal: tk.Toplevel | None = None
    try:
        style = ThemeManager.build_style(root)
        _app = FraudCaseApp(root)

        modal = tk.Toplevel(root)
        ThemeManager.register_toplevel(modal)

        applied = ThemeManager.apply("light", root=root, style=style)
        assert applied["name"] == "light"

        toggled_dark = ThemeManager.toggle()
        assert toggled_dark["name"] == "dark"

        toggled_back = ThemeManager.toggle()
        assert toggled_back["name"] == "light"
    finally:
        if modal is not None:
            try:
                modal.destroy()
            except Exception:
                pass
        root.destroy()
        ThemeManager._style = previous_style
        ThemeManager._root = previous_root
        ThemeManager._current = previous_current
        ThemeManager._base_style_configured = previous_base_configured
        ThemeManager._tracked_toplevels = previous_windows
