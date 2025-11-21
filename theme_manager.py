"""Gestor de temas ligero para la aplicación Tkinter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

import tkinter as tk
from tkinter import ttk

from settings import BASE_DIR

THEME_CONFIG_FILE = Path(BASE_DIR) / "theme_config.json"

LIGHT_THEME: Dict[str, str] = {
    "name": "light",
    "background": "#eaf0f7",
    "foreground": "#0f172a",
    "input_background": "#ffffff",
    "input_foreground": "#0f172a",
    "accent": "#2563eb",
    "border": "#cbd5e1",
    "select_background": "#1d4ed8",
    "select_foreground": "#f8fafc",
    "heading_background": "#dbeafe",
}

DARK_THEME: Dict[str, str] = {
    "name": "dark",
    "background": "#1f2933",
    "foreground": "#e5e7eb",
    "input_background": "#111827",
    "input_foreground": "#e5e7eb",
    "accent": "#38bdf8",
    "border": "#4b5563",
    "select_background": "#0ea5e9",
    "select_foreground": "#0b1320",
    "heading_background": "#111827",
}

THEMES: Dict[str, Dict[str, str]] = {
    LIGHT_THEME["name"]: LIGHT_THEME,
    DARK_THEME["name"]: DARK_THEME,
}


class ThemeManager:
    """Controla la aplicación y persistencia del tema."""

    _style: Optional[ttk.Style] = None
    _root: Optional[tk.Misc] = None
    current: str = "light"

    @classmethod
    def _load_saved_theme(cls) -> str:
        if THEME_CONFIG_FILE.exists():
            try:
                with THEME_CONFIG_FILE.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                saved = data.get("theme", "").lower()
                if saved in THEMES:
                    return saved
            except (json.JSONDecodeError, OSError):
                return "light"
        return "light"

    @classmethod
    def _persist_theme(cls, theme_name: str) -> None:
        try:
            THEME_CONFIG_FILE.write_text(
                json.dumps({"theme": theme_name}), encoding="utf-8"
            )
        except OSError:
            # No se bloquea la app si no se puede escribir el archivo.
            pass

    @classmethod
    def _ensure_style(cls, root: Optional[tk.Misc]) -> ttk.Style:
        if root is not None:
            cls._root = root
        if cls._style is None:
            if cls._root is None:
                raise RuntimeError("ThemeManager requires a Tk root to apply a theme.")
            cls._style = ttk.Style(cls._root)
        return cls._style

    @classmethod
    def apply(cls, theme_name: str, root: Optional[tk.Misc] = None, style: Optional[ttk.Style] = None) -> None:
        """Aplica el tema indicado y actualiza widgets existentes."""

        normalized = theme_name.lower()
        theme = THEMES.get(normalized)
        if theme is None:
            theme = THEMES["light"]
            normalized = "light"

        if style is not None:
            cls._style = style
        ttk_style = cls._ensure_style(root)
        cls.current = normalized

        cls._configure_style(ttk_style, theme)
        cls._refresh_widget_tree(theme)

    @classmethod
    def toggle(cls) -> str:
        """Alterna entre los temas claro y oscuro, guardando la preferencia."""

        next_theme = "dark" if cls.current == "light" else "light"
        cls.apply(next_theme)
        cls._persist_theme(next_theme)
        return next_theme

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
            insertcolor=foreground,
        )
        ttk_style.configure(
            "TCombobox",
            fieldbackground=input_background,
            background=input_background,
            foreground=input_foreground,
        )
        ttk_style.configure(
            "TButton",
            background=theme["accent"],
            foreground=foreground,
            focuscolor=theme["border"],
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

            for child in widget.winfo_children():
                _update(child)

        _update(cls._root)


ThemeManager.current = ThemeManager._load_saved_theme()
