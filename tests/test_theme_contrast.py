"""Accessibility-focused checks for theme color contrast and application."""

from __future__ import annotations

import os
import tkinter as tk
from typing import Iterable, Tuple

import pytest

from app import FraudCaseApp
from theme_manager import DARK_THEME, LIGHT_THEME, ThemeManager


ColorPair = Tuple[str, str]


def _hex_to_rgb(color: str) -> Tuple[float, float, float]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _relative_luminance(rgb: Iterable[float]) -> float:
    def channel_lum(component: float) -> float:
        return component / 12.92 if component <= 0.03928 else ((component + 0.055) / 1.055) ** 2.4

    r, g, b = (_hex_component for _hex_component in rgb)
    return 0.2126 * channel_lum(r) + 0.7152 * channel_lum(g) + 0.0722 * channel_lum(b)


def _contrast_ratio(color_a: str, color_b: str) -> float:
    lum_a = _relative_luminance(_hex_to_rgb(color_a))
    lum_b = _relative_luminance(_hex_to_rgb(color_b))
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def _theme_color_keys() -> Iterable[Tuple[str, Tuple[str, str], bool]]:
    return [
        ("Label/Frame foreground vs background", ("foreground", "background"), False),
        ("Entry foreground vs input background", ("input_foreground", "input_background"), False),
        ("Treeview row foreground vs background", ("foreground", "background"), False),
        ("Treeview selection foreground vs background", ("select_foreground", "select_background"), False),
        ("Treeview heading foreground vs header", ("foreground", "heading_background"), True),
    ]


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME], ids=["light", "dark"])
@pytest.mark.parametrize(
    "description,key_pair,is_large_text",
    _theme_color_keys(),
)
def test_theme_colors_meet_contrast(
    description: str, key_pair: Tuple[str, str], is_large_text: bool, theme: dict
) -> None:
    pair = (theme[key_pair[0]], theme[key_pair[1]])
    contrast = _contrast_ratio(*pair)
    minimum = 3.0 if is_large_text else 4.5
    assert contrast >= minimum, (
        f"{description} for {theme['name']} theme below WCAG threshold: {contrast:.2f} < {minimum}"
    )


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)
def test_theme_application_smoke(messagebox_spy, tmp_path, monkeypatch) -> None:
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
        _app = FraudCaseApp(root)

        ThemeManager.apply("light", root=root, style=style)
        ThemeManager.apply("dark", root=root, style=style)
    finally:
        root.destroy()
        ThemeManager._style = previous_style
        ThemeManager._root = previous_root
        ThemeManager._current = previous_current
        ThemeManager._base_style_configured = previous_base_configured
        ThemeManager._tracked_toplevels = previous_windows
