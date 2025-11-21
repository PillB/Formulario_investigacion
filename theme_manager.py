"""Headless theme coordinator for Tkinter/ttk widgets.

El administrador mantiene los temas claro y oscuro, aplica los colores
mediante ``ttk.Style`` y actualiza de forma recursiva los árboles de widgets
existentes, incluyendo ventanas ``Toplevel`` registradas. También expone
persistencia simple para recordar la preferencia activa entre sesiones.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional, Set

import tkinter as tk
from tkinter import scrolledtext, ttk


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

    PREFERENCE_FILE = Path(__file__).with_name(".theme_preference")

    _style: Optional[ttk.Style] = None
    _root: Optional[tk.Misc] = None
    _current: Dict[str, str] = LIGHT_THEME
    _base_style_configured: bool = False
    _tracked_toplevels: Set[tk.Toplevel] = set()

    THEMES: Dict[str, Dict[str, str]] = {
        LIGHT_THEME["name"]: LIGHT_THEME,
        DARK_THEME["name"]: DARK_THEME,
    }

    @classmethod
    def build_style(cls, root: tk.Misc) -> ttk.Style:
        """Return a ttk.Style bound to ``root`` with base fonts and paddings."""

        cls._root = root
        if cls._style is None or str(cls._style.master) != str(root):
            cls._style = ttk.Style(master=root)
            cls._base_style_configured = False
        if not cls._base_style_configured:
            cls._configure_base_style(cls._style)
            cls._base_style_configured = True
        return cls._style

    @classmethod
    def current(cls) -> Dict[str, str]:
        """Return the active theme dictionary."""

        return cls._current

    @classmethod
    def apply(
        cls, theme_name: str, root: Optional[tk.Misc] = None, style: Optional[ttk.Style] = None
    ) -> Dict[str, str]:
        """Apply the requested theme and refresh existing widgets."""

        normalized = (theme_name or "").lower()
        theme = cls.THEMES.get(normalized, LIGHT_THEME)

        if root is not None:
            cls._root = root
        if style is not None:
            cls._style = style
        ttk_style = cls._ensure_style()

        cls._current = theme
        cls._configure_palette(ttk_style, theme)
        cls._persist_theme(theme["name"])
        cls.refresh_all_widgets()
        return cls._current

    @classmethod
    def toggle(cls) -> Dict[str, str]:
        """Switch between light and dark themes and return the active palette."""

        next_theme = "dark" if cls._current["name"] == "light" else "light"
        return cls.apply(next_theme)

    @classmethod
    def apply_to_widget_tree(cls, root: Optional[tk.Misc]) -> None:
        """Recursively apply theme colors to ``root`` and its children."""

        if root is None:
            return

        cls._apply_widget_tree(root, cls._current)

    @classmethod
    def refresh_all_widgets(cls) -> None:
        """Update themed attributes for the root window and tracked ``Toplevel``s."""

        if cls._root is None and not cls._tracked_toplevels:
            return
        try:
            cls._ensure_style()
        except RuntimeError:
            return
        for window in cls._iter_theme_windows():
            cls._apply_widget_tree(window, cls._current)

    @classmethod
    def register_toplevel(cls, window: Optional[tk.Toplevel]) -> None:
        """Track a Toplevel so it gets refreshed when the theme changes."""

        if window is None:
            return
        cls._tracked_toplevels.add(window)
        try:
            window.bind("<Destroy>", lambda _evt, win=window: cls._tracked_toplevels.discard(win))
        except tk.TclError:
            pass
        cls.apply_to_widget_tree(window)

    @classmethod
    def load_saved_theme(cls) -> str:
        """Return persisted theme name or ``light`` when unavailable."""

        try:
            saved = cls.PREFERENCE_FILE.read_text(encoding="utf-8").strip().lower()
        except OSError:
            return LIGHT_THEME["name"]
        return saved if saved in cls.THEMES else LIGHT_THEME["name"]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @classmethod
    def _ensure_style(cls) -> ttk.Style:
        if cls._style is None:
            if cls._root is None:
                raise RuntimeError("ThemeManager requires a Tk root before applying styles.")
            cls._style = ttk.Style(master=cls._root)
            cls._base_style_configured = False
        if not cls._base_style_configured:
            cls._configure_base_style(cls._style)
            cls._base_style_configured = True
        return cls._style

    @classmethod
    def _iter_theme_windows(cls) -> Iterable[tk.Misc]:
        """Yield the root and active tracked Toplevel instances."""

        if cls._root is not None:
            yield cls._root

        stale: Set[tk.Toplevel] = set()
        for window in cls._tracked_toplevels:
            try:
                exists = bool(window.winfo_exists())
            except tk.TclError:
                exists = False
            if exists:
                yield window
            else:
                stale.add(window)
        cls._tracked_toplevels.difference_update(stale)

    @classmethod
    def _apply_widget_tree(cls, root: tk.Misc, theme: Dict[str, str]) -> None:
        """Recursively apply ttk style names and tk attributes to a widget tree."""

        def _update(widget: tk.Misc) -> None:
            cls._apply_widget_attributes(widget, theme)
            for child in widget.winfo_children():
                _update(child)

        _update(root)

    @classmethod
    def _apply_widget_attributes(cls, widget: tk.Misc, theme: Dict[str, str]) -> None:
        background = theme["background"]
        foreground = theme["foreground"]
        input_background = theme["input_background"]
        input_foreground = theme["input_foreground"]

        try:
            if isinstance(widget, (tk.Text, scrolledtext.ScrolledText, tk.Entry, tk.Spinbox, tk.Listbox)):
                widget.configure(
                    background=input_background,
                    foreground=input_foreground,
                    insertbackground=theme["accent"],
                    selectbackground=theme["select_background"],
                    selectforeground=theme["select_foreground"],
                )
            elif isinstance(widget, tk.LabelFrame):
                widget.configure(background=background, foreground=foreground)
            elif isinstance(widget, (tk.Frame, tk.Toplevel, tk.Tk, tk.Canvas)):
                widget.configure(background=background)
            elif isinstance(widget, (tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton)):
                widget.configure(
                    background=background,
                    foreground=foreground,
                    activebackground=theme["select_background"],
                    activeforeground=theme["select_foreground"],
                )
            elif isinstance(widget, ttk.Frame):
                widget.configure(style="TFrame")
            elif isinstance(widget, ttk.Label):
                widget.configure(style="TLabel")
            elif isinstance(widget, ttk.Entry):
                widget.configure(style="TEntry")
            elif isinstance(widget, ttk.Combobox):
                widget.configure(style="TCombobox")
            elif isinstance(widget, ttk.Button):
                widget.configure(style="TButton")
            elif isinstance(widget, ttk.Labelframe):
                widget.configure(style="TLabelframe")
            elif isinstance(widget, ttk.Treeview):
                widget.configure(style="Treeview")
                widget.tag_configure("", background=background, foreground=foreground)
        except tk.TclError:
            return

    @classmethod
    def _configure_base_style(cls, ttk_style: ttk.Style) -> None:
        from ui.config import FONT_BASE, FONT_HEADER

        ttk_style.configure("TLabel", font=FONT_BASE, padding=(2, 2))
        ttk_style.configure("TEntry", font=FONT_BASE, padding=(6, 6))
        ttk_style.configure("TCombobox", font=FONT_BASE, padding=(6, 6))
        ttk_style.configure("TButton", font=FONT_BASE, padding=(8, 6))
        ttk_style.configure("TLabelframe.Label", font=FONT_HEADER)

    @classmethod
    def _configure_palette(cls, ttk_style: ttk.Style, theme: Dict[str, str]) -> None:
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
    def _persist_theme(cls, theme_name: str) -> None:
        try:
            cls.PREFERENCE_FILE.write_text(theme_name, encoding="utf-8")
        except OSError:
            pass

    @classmethod
    def _refresh_toplevels(cls) -> None:
        for window in cls._iter_theme_windows():
            if isinstance(window, tk.Toplevel):
                cls._apply_widget_tree(window, cls._current)


__all__ = ["ThemeManager", "LIGHT_THEME", "DARK_THEME"]
