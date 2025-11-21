"""Utilities to style Tkinter widgets with a consistent light/dark palette.

Palette rationale:
- Light: background #e9f1f7 (off-white with a cool blue tint to reduce glare), text #2b2f36 (dark gray for contrast), accents #7d93b5 (muted blue-gray for focus without harshness).
- Dark: background #1f242b (soft charcoal that keeps contrast high), text #e3e6eb (light gray that avoids pure white bloom), accents #7a8aa6 (desaturated blue-gray that reads well on dark surfaces).
"""

from __future__ import annotations

from typing import Dict, Optional

import tkinter as tk
from tkinter import ttk


LIGHT_THEME: Dict[str, str] = {
    "name": "light",
    "background": "#e9f1f7",
    "foreground": "#2b2f36",
    "input_background": "#ffffff",
    "input_foreground": "#2b2f36",
    "accent": "#7d93b5",
    "border": "#c5d0df",
    "select_background": "#b8c7dd",
    "select_foreground": "#1f242b",
    "heading_background": "#d7e1ed",
}

DARK_THEME: Dict[str, str] = {
    "name": "dark",
    "background": "#1f242b",
    "foreground": "#e3e6eb",
    "input_background": "#151920",
    "input_foreground": "#e3e6eb",
    "accent": "#7a8aa6",
    "border": "#3a404b",
    "select_background": "#3e4a5a",
    "select_foreground": "#e9ecf1",
    "heading_background": "#181c22",
}


class ThemeManager:
    """Apply and toggle Tkinter ttk styles without coupling to a running UI."""

    _style: Optional[ttk.Style] = None
    _root: Optional[tk.Misc] = None
    _current: Dict[str, str] = LIGHT_THEME

    THEMES: Dict[str, Dict[str, str]] = {
        LIGHT_THEME["name"]: LIGHT_THEME,
        DARK_THEME["name"]: DARK_THEME,
    }

    @classmethod
    def current(cls) -> Dict[str, str]:
        """Return the active theme dictionary."""

        return cls._current

    @classmethod
    def apply(
        cls, theme_name: str, root: Optional[tk.Misc] = None, style: Optional[ttk.Style] = None
    ) -> None:
        """Apply the requested theme and refresh existing widgets."""

        normalized = (theme_name or "").lower()
        theme = cls.THEMES.get(normalized, LIGHT_THEME)

        if root is not None:
            cls._root = root
        if style is not None:
            cls._style = style
        ttk_style = cls._ensure_style()

        cls._current = theme
        cls._configure_style(ttk_style, theme)
        cls._refresh_widget_tree(theme)

    @classmethod
    def toggle(cls) -> Dict[str, str]:
        """Switch between light and dark themes and return the active palette."""

        next_theme = "dark" if cls._current["name"] == "light" else "light"
        cls.apply(next_theme)
        return cls._current

    @classmethod
    def _ensure_style(cls) -> ttk.Style:
        if cls._style is None:
            if cls._root is None:
                raise RuntimeError("ThemeManager requires a Tk root before applying styles.")
            cls._style = ttk.Style(master=cls._root)
        return cls._style

    @classmethod
    def _configure_style(cls, ttk_style: ttk.Style, theme: Dict[str, str]) -> None:
        background = theme["background"]
        foreground = theme["foreground"]
        input_background = theme["input_background"]
        input_foreground = theme["input_foreground"]

        ttk_style.configure("TFrame", background=background)
        ttk_style.configure("TLabel", background=background, foreground=foreground)
        ttk_style.configure(
            "TEntry",
            fieldbackground=input_background,
            foreground=input_foreground,
            insertcolor=theme["accent"],
        )
        ttk_style.configure(
            "TCombobox",
            fieldbackground=input_background,
            background=input_background,
            foreground=input_foreground,
            selectbackground=theme["select_background"],
            selectforeground=theme["select_foreground"],
        )
        ttk_style.configure(
            "TButton",
            background=theme["accent"],
            foreground=foreground,
            bordercolor=theme["border"],
            focusthickness=1,
        )
        ttk_style.map(
            "TButton",
            background=[("active", theme["select_background"]), ("!active", theme["accent"])],
            foreground=[("pressed", foreground), ("active", foreground)],
        )
        ttk_style.configure(
            "TLabelframe",
            background=background,
            bordercolor=theme["border"],
        )
        ttk_style.configure(
            "TLabelframe.Label", background=background, foreground=foreground
        )
        ttk_style.configure(
            "Treeview",
            background=background,
            fieldbackground=background,
            foreground=foreground,
            bordercolor=theme["border"],
        )
        ttk_style.configure(
            "Treeview.Heading",
            background=theme["heading_background"],
            foreground=foreground,
        )
        ttk_style.map(
            "Treeview",
            background=[("selected", theme["select_background"])],
            foreground=[("selected", theme["select_foreground"])],
        )

    @classmethod
    def _refresh_widget_tree(cls, theme: Dict[str, str]) -> None:
        if cls._root is None:
            return

        background = theme["background"]
        foreground = theme["foreground"]

        try:
            cls._root.configure(background=background)
        except tk.TclError:
            pass

        def _update(widget: tk.Misc) -> None:
            if isinstance(widget, (tk.Text, tk.Entry, tk.Spinbox, tk.Listbox)):
                try:
                    widget.configure(
                        background=theme["input_background"],
                        foreground=theme["input_foreground"],
                        insertbackground=theme["accent"],
                        selectbackground=theme["select_background"],
                        selectforeground=theme["select_foreground"],
                    )
                except tk.TclError:
                    pass
            elif isinstance(widget, (tk.Frame, tk.Toplevel, tk.Canvas, tk.LabelFrame)):
                try:
                    widget.configure(background=background)
                except tk.TclError:
                    pass
            elif isinstance(widget, (tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton)):
                try:
                    widget.configure(background=background, foreground=foreground)
                except tk.TclError:
                    pass
            elif isinstance(widget, ttk.Treeview):
                try:
                    widget.tag_configure("", background=background, foreground=foreground)
                except tk.TclError:
                    pass

            for child in widget.winfo_children():
                _update(child)

        _update(cls._root)

