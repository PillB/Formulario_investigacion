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
    CHECKBUTTON_STYLE = "Themed.TCheckbutton"

    _style: Optional[ttk.Style] = None
    _root: Optional[tk.Misc] = None
    _current: Dict[str, str] = LIGHT_THEME
    _base_style_configured: bool = False
    _tracked_toplevels: Set[tk.Toplevel] = set()
    _tracked_menus: Set[tk.Menu] = set()

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
        cls._refresh_content_widgets()
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

        if cls._root is None and not cls._tracked_toplevels and not cls._tracked_menus:
            return
        try:
            cls._ensure_style()
        except RuntimeError:
            return
        cls._refresh_content_widgets()
        for window in cls._iter_theme_windows():
            cls._apply_widget_tree(window, cls._current)
        stale_menus: Set[tk.Menu] = set()
        for menu in cls._tracked_menus:
            try:
                exists = bool(menu.winfo_exists())
            except tk.TclError:
                exists = False
            if exists:
                cls._apply_widget_attributes(menu, cls._current)
            else:
                stale_menus.add(menu)
        cls._tracked_menus.difference_update(stale_menus)

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
    def register_menu(cls, menu: Optional[tk.Menu]) -> None:
        """Track a Menu so it inherits the active palette automatically."""

        if menu is None:
            return
        cls._tracked_menus.add(menu)
        try:
            menu.bind("<Destroy>", lambda _evt, m=menu: cls._tracked_menus.discard(m))
        except tk.TclError:
            pass
        cls._apply_widget_attributes(menu, cls._current)

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
    def _iter_window_children(cls, widget: tk.Misc) -> Iterable[tk.Misc]:
        """Yield ``widget`` and all of its descendants."""

        stack = [widget]
        while stack:
            current = stack.pop()
            yield current
            try:
                stack.extend(current.winfo_children())
            except tk.TclError:
                continue

    @classmethod
    def _refresh_content_widgets(cls) -> None:
        """Reapply tag colors for text and tree widgets after palette updates."""

        theme = cls._current
        try:
            theme["select_background"]
        except KeyError:
            return
        for window in cls._iter_theme_windows():
            for widget in cls._iter_window_children(window):
                if isinstance(widget, ttk.Treeview):
                    cls._reapply_treeview_tags(widget, theme)
                elif isinstance(widget, scrolledtext.ScrolledText):
                    text_area = getattr(widget, "text", None)
                    cls._reapply_text_tags(text_area or widget, theme)
                elif isinstance(widget, tk.Text):
                    cls._reapply_text_tags(widget, theme)

    @classmethod
    def _reapply_treeview_tags(cls, widget: ttk.Treeview, theme: Dict[str, str]) -> None:
        """Reset tag styling so existing rows reflect the current palette."""

        background = theme["background"]
        foreground = theme["foreground"]
        heading_background = theme["heading_background"]
        collected_tags = {""}
        stack = list(widget.get_children(""))
        while stack:
            item_id = stack.pop()
            tags = widget.item(item_id, "tags") or []
            if isinstance(tags, (list, tuple, set)):
                collected_tags.update(tags)
            else:
                collected_tags.add(tags)
            stack.extend(widget.get_children(item_id))
        for tag in collected_tags:
            try:
                widget.tag_configure(tag, background=background, foreground=foreground)
            except tk.TclError:
                continue
        try:
            widget.heading("#0", background=heading_background, foreground=foreground)
        except tk.TclError:
            pass
        for column in widget.cget("columns"):
            try:
                widget.heading(column, background=heading_background, foreground=foreground)
            except tk.TclError:
                continue

    @classmethod
    def _reapply_text_tags(cls, widget: tk.Text, theme: Dict[str, str]) -> None:
        """Reset default text colors and selection tag to match the palette."""

        if not isinstance(widget, tk.Text):
            return
        try:
            widget.configure(
                background=theme["input_background"],
                foreground=theme["input_foreground"],
                insertbackground=theme["accent"],
                selectbackground=theme["select_background"],
                selectforeground=theme["select_foreground"],
            )
            widget.tag_configure(
                "sel",
                background=theme["select_background"],
                foreground=theme["select_foreground"],
            )
        except tk.TclError:
            return
        for tag in widget.tag_names():
            if tag == "sel":
                continue
            try:
                if not widget.tag_cget(tag, "background"):
                    widget.tag_configure(tag, background=theme["input_background"])
                if not widget.tag_cget(tag, "foreground"):
                    widget.tag_configure(tag, foreground=theme["input_foreground"])
            except tk.TclError:
                continue

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
        heading_background = theme["heading_background"]
        input_background = theme["input_background"]
        input_foreground = theme["input_foreground"]

        try:
            if isinstance(widget, scrolledtext.ScrolledText):
                try:
                    widget.configure(background=background)
                except tk.TclError:
                    pass
                text_widget = getattr(widget, "text", None)
                if isinstance(text_widget, tk.Text):
                    text_widget.configure(
                        background=input_background,
                        foreground=input_foreground,
                        insertbackground=theme["accent"],
                        selectbackground=theme["select_background"],
                        selectforeground=theme["select_foreground"],
                    )
                for scrollbar in (getattr(widget, "vbar", None), getattr(widget, "hbar", None)):
                    if isinstance(scrollbar, tk.Scrollbar):
                        scrollbar.configure(
                            background=theme["accent"],
                            troughcolor=input_background,
                            activebackground=theme["select_background"],
                            elementborderwidth=1,
                        )
            elif isinstance(widget, (tk.Text, tk.Entry, tk.Spinbox, tk.Listbox)):
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
            elif isinstance(widget, tk.Scrollbar):
                widget.configure(
                    background=theme["accent"],
                    troughcolor=input_background,
                    activebackground=theme["select_background"],
                    elementborderwidth=1,
                )
            elif isinstance(widget, tk.Menu):
                widget.configure(
                    background=background,
                    foreground=foreground,
                    activebackground=theme["select_background"],
                    activeforeground=theme["select_foreground"],
                    borderwidth=1,
                    relief=tk.SOLID,
                )
            elif isinstance(widget, ttk.Frame):
                widget.configure(style="TFrame")
            elif isinstance(widget, ttk.Notebook):
                widget.configure(style="TNotebook")
            elif isinstance(widget, ttk.Panedwindow):
                widget.configure(style="TPanedwindow")
            elif isinstance(widget, ttk.Separator):
                widget.configure(style="TSeparator")
            elif isinstance(widget, ttk.Label):
                widget.configure(style="TLabel")
            elif isinstance(widget, ttk.Entry):
                widget.configure(style="TEntry")
            elif isinstance(widget, ttk.Combobox):
                widget.configure(style="TCombobox")
            elif isinstance(widget, ttk.Button):
                widget.configure(style="TButton")
            elif isinstance(widget, ttk.Progressbar):
                widget.configure(style="TProgressbar")
            elif isinstance(widget, ttk.Scrollbar):
                widget.configure(style="TScrollbar")
            elif isinstance(widget, ttk.Labelframe):
                widget.configure(style="TLabelframe")
            elif isinstance(widget, ttk.Checkbutton):
                widget.configure(style=cls.CHECKBUTTON_STYLE)
            elif isinstance(widget, ttk.Treeview):
                widget.configure(style="Treeview")
                collected_tags = {""}
                for item_id in widget.get_children(""):
                    tags = widget.item(item_id, "tags")
                    if not tags:
                        continue
                    if isinstance(tags, (list, tuple, set)):
                        collected_tags.update(tags)
                    else:
                        collected_tags.add(tags)
                for tag in collected_tags:
                    widget.tag_configure(tag, background=background, foreground=foreground)
                try:
                    widget.heading("#0", background=heading_background, foreground=foreground)
                except tk.TclError:
                    pass
                for column in widget.cget("columns"):
                    try:
                        widget.heading(column, background=heading_background, foreground=foreground)
                    except tk.TclError:
                        continue
            elif isinstance(widget, tk.Menu):
                widget.configure(
                    background=background,
                    foreground=foreground,
                    activebackground=theme["select_background"],
                    activeforeground=theme["select_foreground"],
                    selectcolor=theme["select_background"],
                    borderwidth=1,
                    relief="solid",
                )
        except tk.TclError:
            return

    @classmethod
    def _configure_base_style(cls, ttk_style: ttk.Style) -> None:
        from ui.config import FONT_BASE, FONT_HEADER

        text_padding = (6, 4)
        input_padding = (10, 8)
        button_padding = (12, 8)
        heading_padding = (10, 8)
        tab_padding = (12, 8)

        ttk_style.configure("TLabel", font=FONT_BASE, padding=text_padding)
        ttk_style.configure("TEntry", font=FONT_BASE, padding=input_padding)
        ttk_style.configure("TCombobox", font=FONT_BASE, padding=input_padding)
        ttk_style.configure("TSpinbox", font=FONT_BASE, padding=input_padding)
        ttk_style.configure("TButton", font=FONT_BASE, padding=button_padding)
        ttk_style.configure("TCheckbutton", font=FONT_BASE, padding=text_padding)
        ttk_style.configure(cls.CHECKBUTTON_STYLE, font=FONT_BASE, padding=text_padding)
        ttk_style.configure("TRadiobutton", font=FONT_BASE, padding=text_padding)
        ttk_style.configure("Treeview", font=FONT_BASE)
        ttk_style.configure("Treeview.Heading", font=FONT_BASE, padding=heading_padding)
        ttk_style.configure("TNotebook", font=FONT_BASE)
        ttk_style.configure("TNotebook.Tab", font=FONT_BASE, padding=tab_padding)
        ttk_style.configure("TLabelframe.Label", font=FONT_HEADER)

    @classmethod
    def _configure_palette(cls, ttk_style: ttk.Style, theme: Dict[str, str]) -> None:
        background = theme["background"]
        foreground = theme["foreground"]
        input_background = theme["input_background"]
        input_foreground = theme["input_foreground"]
        border = theme["border"]
        select_background = theme["select_background"]
        select_foreground = theme["select_foreground"]
        heading_background = theme["heading_background"]

        ttk_style.configure("TFrame", background=background)
        ttk_style.configure(
            "TPanedwindow",
            background=background,
            bordercolor=border,
        )
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
            selectbackground=select_background,
            selectforeground=select_foreground,
        )
        ttk_style.configure(
            cls.CHECKBUTTON_STYLE,
            background=background,
            foreground=foreground,
        )
        ttk_style.map(
            cls.CHECKBUTTON_STYLE,
            background=[("active", select_background), ("selected", background)],
            foreground=[("active", select_foreground), ("selected", foreground)],
            indicatorcolor=[
                ("selected", select_background),
                ("active", select_background),
                ("!selected", border),
            ],
        )
        ttk_style.configure(
            "TButton",
            background=theme["accent"],
            foreground=foreground,
            bordercolor=border,
            focusthickness=1,
        )
        ttk_style.map(
            "TButton",
            background=[("active", select_background), ("!active", theme["accent"])],
            foreground=[("pressed", foreground), ("active", foreground)],
        )
        ttk_style.configure(
            "TLabelframe",
            background=background,
            bordercolor=border,
        )
        ttk_style.configure(
            "TLabelframe.Label", background=background, foreground=foreground
        )
        ttk_style.configure(
            "Treeview",
            background=background,
            fieldbackground=background,
            foreground=foreground,
            bordercolor=border,
        )
        ttk_style.configure(
            "Treeview.Heading",
            background=heading_background,
            foreground=foreground,
        )
        ttk_style.map(
            "Treeview",
            background=[("selected", select_background)],
            foreground=[("selected", select_foreground)],
        )
        ttk_style.configure(
            "TNotebook",
            background=background,
            bordercolor=border,
            tabmargins=(8, 6, 8, 0),
        )
        ttk_style.configure(
            "TNotebook.Tab",
            background=heading_background,
            foreground=foreground,
            bordercolor=border,
            padding=(12, 8),
        )
        ttk_style.map(
            "TNotebook.Tab",
            background=[("selected", select_background), ("active", select_background)],
            foreground=[("selected", select_foreground), ("active", select_foreground)],
        )
        ttk_style.configure(
            "TScrollbar",
            background=theme["accent"],
            troughcolor=input_background,
            bordercolor=border,
            arrowcolor=foreground,
        )
        ttk_style.map(
            "TScrollbar",
            background=[("active", select_background), ("pressed", select_background)],
            arrowcolor=[("active", select_foreground), ("pressed", select_foreground)],
        )
        ttk_style.configure(
            "TProgressbar",
            background=theme["accent"],
            troughcolor=input_background,
            bordercolor=border,
            lightcolor=theme["accent"],
            darkcolor=theme["accent"],
        )
        ttk_style.map(
            "TProgressbar",
            background=[("active", select_background)],
        )
        ttk_style.configure("TSeparator", background=border)

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
