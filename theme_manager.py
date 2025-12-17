"""Headless theme coordinator for Tkinter/ttk widgets.

El administrador mantiene los temas claro y oscuro, aplica los colores
mediante ``ttk.Style`` y actualiza de forma recursiva los árboles de widgets
existentes, incluyendo ventanas ``Toplevel`` registradas. También expone
persistencia simple para recordar la preferencia activa entre sesiones. Si la
plataforma no soporta la creación de elementos personalizados ``border``, el
administrador recurre automáticamente a una paleta de respaldo basada en Azure
definida en código y remapea los estilos modernos para conservar las
asignaciones utilizadas en la aplicación sin depender de activos externos.
"""

from __future__ import annotations

import logging
import weakref
from pathlib import Path
from typing import Dict, Iterable, Optional, Set

import tkinter as tk
from tkinter import scrolledtext, ttk

LIGHT_THEME: Dict[str, str] = {
    "name": "light",
    "background": "#FFFFFF",
    "foreground": "#000000",
    "input_background": "#FFFFFF",
    "input_foreground": "#000000",
    "accent": "#7d93b5",
    "border": "#c5d0df",
    "select_background": "#4e4e4e",
    "select_foreground": "#ffffff",
    "heading_background": "#d7e1ed",
}

DARK_THEME: Dict[str, str] = {
    "name": "dark",
    "background": "#121212",
    "foreground": "#FFFFFF",
    "input_background": "#1E1E1E",
    "input_foreground": "#FFFFFF",
    "accent": "#7a8aa6",
    "border": "#3a404b",
    "select_background": "#3e4a5a",
    "select_foreground": "#e9ecf1",
    "heading_background": "#181c22",
}

logger = logging.getLogger(__name__)


class ThemeManager:
    """Apply and toggle Tkinter ttk styles without coupling to a running UI."""

    PREFERENCE_FILE = Path(__file__).with_name(".theme_preference")
    CHECKBUTTON_STYLE = "Themed.TCheckbutton"
    FRAME_STYLE = "Card.TFrame"
    ENTRY_STYLE = "Modern.TEntry"
    COMBOBOX_STYLE = "Modern.TCombobox"
    SPINBOX_STYLE = "Modern.TSpinbox"
    BUTTON_STYLE = "Modern.TButton"
    BUTTON_HOVER_STYLE = "ModernHover.TButton"
    ENTRY_FOCUS_STYLE = "ModernFocus.TEntry"
    COMBOBOX_FOCUS_STYLE = "ModernFocus.TCombobox"
    SPINBOX_FOCUS_STYLE = "ModernFocus.TSpinbox"
    REQUIRED_LABEL_STYLE = "Required.TLabel"
    REQUIRED_ASTERISK_STYLE = "RequiredAsterisk.TLabel"

    _style: Optional[ttk.Style] = None
    _root: Optional[tk.Misc] = None
    _current: Dict[str, str] = LIGHT_THEME
    _base_style_configured: bool = False
    _tracked_toplevels: Set[tk.Toplevel] = set()
    _tracked_menus: Set[tk.Menu] = set()
    _use_azure_fallback: bool = False
    _azure_theme_loaded: bool = False
    _missing_text_child_warned: "weakref.WeakSet[scrolledtext.ScrolledText]" = weakref.WeakSet()

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
            try:
                cls._style.theme_use("clam")
            except tk.TclError:
                pass
            cls._use_cross_platform_theme(cls._style)
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
        cls._refresh_collapsible_styles()
        cls._refresh_content_widgets()
        cls._persist_theme(theme["name"])
        cls.refresh_all_widgets()
        reapply_all_badges()
        active_root = root or cls._root or getattr(ttk_style, "master", None)
        if active_root is not None:
            try:
                active_root.update_idletasks()
            except tk.TclError:
                pass
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
        reapply_all_badges()

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
            cls._use_cross_platform_theme(cls._style)
            cls._base_style_configured = True
        cls._style.configure('.', font=('Arial', 12))  # Sans-serif font for accessibility
        if not cls._base_style_configured:
            cls._configure_base_style(cls._style)
            cls._base_style_configured = True
        return cls._style

    @staticmethod
    def _use_cross_platform_theme(ttk_style: ttk.Style) -> None:
        """Apply a consistent ttk theme with fallbacks to avoid Tcl errors."""

        fallback_theme = ttk_style.theme_use()
        for theme_name in ("clam", "alt", "default"):
            try:
                ttk_style.theme_use(theme_name)
                return
            except tk.TclError:
                continue
        try:
            ttk_style.theme_use(fallback_theme)
        except tk.TclError:
            return

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
    def _register_window_menu(cls, widget: tk.Misc) -> None:
        """Register a menu attached to ``widget`` so it refreshes with the theme."""

        try:
            menu_ref = widget.cget("menu")
        except tk.TclError:
            return
        if not menu_ref:
            return
        menu_obj = None
        if isinstance(menu_ref, tk.Menu):
            menu_obj = menu_ref
        elif isinstance(menu_ref, str):
            try:
                menu_obj = widget.nametowidget(menu_ref)
            except tk.TclError:
                menu_obj = None
        if isinstance(menu_obj, tk.Menu):
            cls.register_menu(menu_obj)

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
                    if isinstance(text_area, tk.Text):
                        cls._reapply_text_tags(text_area, theme)
                    else:
                        cls._force_text_children_refresh(widget, theme)
                elif isinstance(widget, tk.Text):
                    cls._reapply_text_tags(widget, theme)

    @classmethod
    def _refresh_collapsible_styles(cls) -> None:
        """Ensure accordion/collapsible styles track the active palette."""

        try:
            from ui.layout.accordion import register_styles
        except Exception:
            return
        try:
            register_styles()
        except Exception:
            return

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
        except tk.TclError as exc:
            logger.warning("No se pudieron reconfigurar los tags de texto: %s", exc)
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
    def _configure_text_widget(
        cls, widget: tk.Text, theme: Dict[str, str], focus_outline: Optional[Dict[str, object]] = None
    ) -> bool:
        """Configure base colors for ``tk.Text`` widgets, logging failures."""

        if not isinstance(widget, tk.Text):
            return False
        try:
            options = dict(
                background=theme["input_background"],
                foreground=theme["input_foreground"],
                insertbackground=theme["accent"],
                selectbackground=theme["select_background"],
                selectforeground=theme["select_foreground"],
            )
            if focus_outline:
                options.update(focus_outline)
            widget.configure(**options)
            cls._reapply_text_tags(widget, theme)
            return True
        except tk.TclError as exc:
            logger.warning("No se pudo configurar el widget Text: %s", exc)
            return False

    @classmethod
    def _force_text_children_refresh(
        cls, widget: tk.Misc, theme: Dict[str, str], focus_outline: Optional[Dict[str, object]] = None
    ) -> bool:
        """Find child ``tk.Text`` widgets when ScrolledText lacks ``.text``."""

        if not cls._widget_exists(widget):
            return False
        try:
            children = widget.winfo_children()
        except tk.TclError:
            return False
        handled = False
        for child in children:
            if isinstance(child, tk.Text) and cls._widget_exists(child):
                if cls._configure_text_widget(child, theme, focus_outline):
                    handled = True
        return handled

    @classmethod
    def _widget_exists(cls, widget: Optional[tk.Misc]) -> bool:
        if widget is None:
            return False
        exists_method = getattr(widget, "winfo_exists", None)
        if exists_method is None:
            return True
        if not callable(exists_method):
            return False
        try:
            return bool(exists_method())
        except tk.TclError:
            return False

    @classmethod
    def _log_missing_text_child(cls, widget: scrolledtext.ScrolledText) -> None:
        if widget in cls._missing_text_child_warned:
            return
        cls._missing_text_child_warned.add(widget)
        logger.warning("ScrolledText sin hijos Text configurables: %s", widget)

    @classmethod
    def _apply_widget_tree(cls, root: tk.Misc, theme: Dict[str, str]) -> None:
        """Recursively apply ttk style names and tk attributes to a widget tree."""

        def _update(widget: tk.Misc) -> None:
            if not cls._widget_exists(widget):
                return
            cls._apply_widget_attributes(widget, theme)
            try:
                children = widget.winfo_children()
            except tk.TclError:
                return
            for child in children:
                _update(child)

        _update(root)

    @classmethod
    def _apply_widget_attributes(cls, widget: tk.Misc, theme: Dict[str, str]) -> None:
        background = theme["background"]
        foreground = theme["foreground"]
        heading_background = theme["heading_background"]
        input_background = theme["input_background"]
        input_foreground = theme["input_foreground"]

        if not cls._widget_exists(widget):
            return

        try:
            focus_outline = {
                "highlightbackground": theme["border"],
                "highlightcolor": theme["accent"],
                "highlightthickness": 1,
                "borderwidth": 1,
                "relief": tk.SOLID,
            }
            if isinstance(widget, scrolledtext.ScrolledText):
                try:
                    widget.configure(background=background, **focus_outline)
                except tk.TclError as exc:
                    logger.warning("No se pudo actualizar el contenedor ScrolledText: %s", exc)
                if not cls._widget_exists(widget):
                    return
                text_widget = getattr(widget, "text", None)
                handled = False
                if isinstance(text_widget, tk.Text) and cls._widget_exists(text_widget):
                    handled = cls._configure_text_widget(text_widget, theme, focus_outline)
                if not handled:
                    handled = cls._force_text_children_refresh(widget, theme, focus_outline)
                if not handled:
                    cls._log_missing_text_child(widget)
                    return
                for scrollbar in (getattr(widget, "vbar", None), getattr(widget, "hbar", None)):
                    if isinstance(scrollbar, tk.Scrollbar) and cls._widget_exists(scrollbar):
                        scrollbar.configure(
                            background=theme["accent"],
                            troughcolor=input_background,
                            activebackground=theme["select_background"],
                            elementborderwidth=1,
                        )
            elif isinstance(widget, tk.Text):
                cls._configure_text_widget(widget, theme, focus_outline)
            elif isinstance(widget, (tk.Entry, tk.Spinbox)):
                widget.configure(
                    background=input_background,
                    foreground=input_foreground,
                    insertbackground=theme["accent"],
                    selectbackground=theme["select_background"],
                    selectforeground=theme["select_foreground"],
                    **focus_outline,
                )
            elif isinstance(widget, tk.Listbox):
                widget.configure(
                    background=input_background,
                    foreground=input_foreground,
                    selectbackground=theme["select_background"],
                    selectforeground=theme["select_foreground"],
                    **focus_outline,
                )
            elif isinstance(widget, tk.LabelFrame):
                widget.configure(background=background, foreground=foreground, **focus_outline)
            elif isinstance(widget, (tk.Frame, tk.Toplevel, tk.Tk, tk.Canvas)):
                widget.configure(background=background, **focus_outline)
                if isinstance(widget, (tk.Toplevel, tk.Tk)):
                    cls._register_window_menu(widget)
            elif isinstance(widget, (tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton)):
                widget.configure(
                    background=background,
                    foreground=foreground,
                    activebackground=theme["select_background"],
                    activeforeground=theme["select_foreground"],
                    **focus_outline,
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
                    selectcolor=theme["select_background"],
                    borderwidth=1,
                    relief=tk.SOLID,
                )
            elif isinstance(widget, ttk.Frame):
                widget.configure(style=cls.FRAME_STYLE)
            elif isinstance(widget, ttk.Notebook):
                widget.configure(style="TNotebook")
                try:
                    widget.bind("<<NotebookTabChanged>>", lambda _evt: reapply_all_badges(), add="+")
                except tk.TclError:
                    pass
            elif isinstance(widget, ttk.Panedwindow):
                widget.configure(style="TPanedwindow")
            elif isinstance(widget, ttk.Separator):
                widget.configure(style="TSeparator")
            elif isinstance(widget, ttk.Label):
                widget.configure(style="TLabel")
            elif isinstance(widget, ttk.Entry):
                widget.configure(style=cls.ENTRY_STYLE)
                cls._register_focus_glow(widget)
            elif isinstance(widget, ttk.Spinbox):
                widget.configure(style=cls.SPINBOX_STYLE)
                cls._register_focus_glow(widget)
            elif isinstance(widget, ttk.Combobox):
                widget.configure(style=cls.COMBOBOX_STYLE)
                cls._register_focus_glow(widget)
            elif isinstance(widget, ttk.Button):
                widget.configure(style=cls.BUTTON_STYLE)
                cls._register_button_animation(widget)
            elif isinstance(widget, ttk.Progressbar):
                widget.configure(style="TProgressbar")
            elif isinstance(widget, ttk.Scrollbar):
                widget.configure(style="TScrollbar")
            elif isinstance(widget, ttk.Labelframe):
                widget.configure(style="TLabelframe")
            elif isinstance(widget, ttk.Checkbutton):
                widget.configure(style=cls.CHECKBUTTON_STYLE)
            elif isinstance(widget, ttk.Radiobutton):
                widget.configure(style="TRadiobutton")
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
        except tk.TclError:
            return

    @classmethod
    def _register_button_animation(cls, widget: tk.Misc) -> None:
        if not isinstance(widget, ttk.Button):
            return
        if getattr(widget, "_theme_button_bound", False):
            return
        widget._theme_button_bound = True
        widget._tm_pulse_after_id = None

        def cancel_pulse() -> None:
            after_id = getattr(widget, "_tm_pulse_after_id", None)
            if after_id:
                try:
                    widget.after_cancel(after_id)
                except tk.TclError:
                    pass
                widget._tm_pulse_after_id = None

        def start_pulse(_event=None) -> None:
            cancel_pulse()
            if not cls._widget_is_valid(widget):
                return
            try:
                widget.configure(style=cls.BUTTON_HOVER_STYLE)
            except tk.TclError:
                return

        def end_pulse(_event=None) -> None:
            cancel_pulse()
            cls._reset_button_style(widget)

        widget.bind("<Enter>", start_pulse, add="+")
        widget.bind("<Leave>", end_pulse, add="+")
        widget.bind("<FocusOut>", end_pulse, add="+")

    @classmethod
    def _reset_button_style(cls, widget: tk.Misc) -> None:
        try:
            widget.configure(style=cls.BUTTON_STYLE)
        except tk.TclError:
            pass

    @classmethod
    def _register_focus_glow(cls, widget: tk.Misc) -> None:
        if not isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Spinbox)):
            return
        if getattr(widget, "_theme_focus_bound", False):
            return
        widget._theme_focus_bound = True

        def apply_focus(_event=None) -> None:
            if not cls._widget_is_valid(widget):
                return
            try:
                widget.configure(style=cls._focus_style_for_widget(widget))
            except tk.TclError:
                return

        def remove_focus(_event=None) -> None:
            cls._reset_input_style(widget)

        widget.bind("<FocusIn>", apply_focus, add="+")
        widget.bind("<FocusOut>", remove_focus, add="+")

        try:
            remove_focus()
            if widget.focus_get() == widget and cls._widget_is_valid(widget):
                apply_focus()
        except tk.TclError:
            pass

    @classmethod
    def _reset_input_style(cls, widget: tk.Misc) -> None:
        try:
            widget.configure(style=cls._base_style_for_widget(widget))
        except tk.TclError:
            pass

    @classmethod
    def _base_style_for_widget(cls, widget: tk.Misc) -> str:
        if isinstance(widget, ttk.Entry):
            return cls.ENTRY_STYLE
        if isinstance(widget, ttk.Combobox):
            return cls.COMBOBOX_STYLE
        if isinstance(widget, ttk.Spinbox):
            return cls.SPINBOX_STYLE
        return str(widget.cget("style")) if hasattr(widget, "cget") else ""

    @classmethod
    def _focus_style_for_widget(cls, widget: tk.Misc) -> str:
        if isinstance(widget, ttk.Entry):
            return cls.ENTRY_FOCUS_STYLE
        if isinstance(widget, ttk.Combobox):
            return cls.COMBOBOX_FOCUS_STYLE
        if isinstance(widget, ttk.Spinbox):
            return cls.SPINBOX_FOCUS_STYLE
        return cls._base_style_for_widget(widget)

    @staticmethod
    def _widget_is_valid(widget: tk.Misc) -> bool:
        state_getter = getattr(widget, "state", None)
        if callable(state_getter):
            try:
                states = set(state_getter())
            except tk.TclError:
                return False
            return "invalid" not in states
        return True

    @classmethod
    def _configure_base_style(cls, ttk_style: ttk.Style) -> None:
        from ui.config import FONT_BASE, FONT_HEADER

        text_padding = (6, 4)
        input_padding = (10, 8)
        button_padding = (12, 8)
        heading_padding = (10, 8)
        tab_padding = (12, 8)

        ttk_style.configure("TLabel", font=FONT_BASE, padding=text_padding)
        ttk_style.configure(cls.REQUIRED_LABEL_STYLE, font=FONT_BASE, padding=text_padding)
        ttk_style.configure(
            cls.REQUIRED_ASTERISK_STYLE, font=FONT_BASE, padding=text_padding
        )
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
        ttk_style.configure(cls.ENTRY_STYLE, font=FONT_BASE, padding=input_padding)
        ttk_style.configure(cls.COMBOBOX_STYLE, font=FONT_BASE, padding=input_padding)
        ttk_style.configure(cls.SPINBOX_STYLE, font=FONT_BASE, padding=input_padding)
        ttk_style.configure(cls.BUTTON_STYLE, font=FONT_BASE, padding=button_padding)

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
        disabled_background = border
        disabled_foreground = select_foreground

        input_background_map = [
            ("disabled", disabled_background),
            ("readonly", heading_background),
            ("pressed", select_background),
            ("active", input_background),
            ("focus", input_background),
            ("!disabled", input_background),
        ]
        input_foreground_map = [
            ("disabled", disabled_foreground),
            ("readonly", foreground),
            ("pressed", select_foreground),
            ("active", input_foreground),
            ("focus", input_foreground),
            ("!disabled", input_foreground),
        ]
        border_map = [
            ("disabled", border),
            ("readonly", border),
            ("pressed", select_background),
            ("active", select_background),
            ("focus", theme["accent"]),
            ("!focus", border),
        ]

        cls._configure_modern_elements(
            ttk_style,
            theme,
            input_background_map,
            input_foreground_map,
            border_map,
        )

        ttk_style.configure("TFrame", background=background)
        ttk_style.configure(cls.FRAME_STYLE, background=background, padding=(12, 10))
        ttk_style.configure(
            "TPanedwindow",
            background=background,
            bordercolor=border,
        )
        ttk_style.configure("TLabel", background=background, foreground=foreground)
        ttk_style.configure(
            cls.REQUIRED_LABEL_STYLE, background=background, foreground=foreground
        )
        ttk_style.configure(
            cls.REQUIRED_ASTERISK_STYLE,
            background=background,
            foreground="#d32f2f",
        )
        ttk_style.configure(
            "TEntry",
            fieldbackground=input_background,
            foreground=input_foreground,
            insertcolor=theme["accent"],
        )
        ttk_style.map(
            "TEntry",
            fieldbackground=input_background_map,
            foreground=input_foreground_map,
            bordercolor=border_map,
        )
        ttk_style.configure(
            "TSpinbox",
            fieldbackground=input_background,
            foreground=input_foreground,
            insertcolor=theme["accent"],
            bordercolor=border,
        )
        ttk_style.map(
            "TSpinbox",
            fieldbackground=input_background_map,
            foreground=input_foreground_map,
            bordercolor=border_map,
            arrowcolor=[
                ("disabled", disabled_foreground),
                ("readonly", foreground),
                ("active", select_foreground),
                ("pressed", select_foreground),
                ("!disabled", foreground),
            ],
            background=[
                ("disabled", disabled_background),
                ("readonly", heading_background),
                ("pressed", select_background),
                ("active", input_background),
                ("focus", input_background),
                ("!disabled", input_background),
            ],
        )
        ttk_style.configure(
            "TCombobox",
            fieldbackground=input_background,
            background=input_background,
            foreground=input_foreground,
            selectbackground=select_background,
            selectforeground=select_foreground,
        )
        ttk_style.map(
            "TCombobox",
            fieldbackground=input_background_map,
            foreground=input_foreground_map,
            bordercolor=border_map,
            background=[
                ("disabled", disabled_background),
                ("readonly", heading_background),
                ("pressed", select_background),
                ("active", input_background),
                ("focus", input_background),
                ("!disabled", input_background),
            ],
            arrowcolor=[
                ("disabled", disabled_foreground),
                ("readonly", foreground),
                ("active", select_foreground),
                ("pressed", select_foreground),
                ("!disabled", foreground),
            ],
        )
        ttk_style.configure(
            cls.CHECKBUTTON_STYLE,
            background=background,
            foreground=foreground,
        )
        ttk_style.configure(
            "TRadiobutton",
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
        ttk_style.map(
            "TRadiobutton",
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
            background=[
                ("disabled", disabled_background),
                ("readonly", theme["accent"]),
                ("pressed", select_background),
                ("active", select_background),
                ("focus", theme["accent"]),
                ("!disabled", theme["accent"]),
            ],
            foreground=[
                ("disabled", disabled_foreground),
                ("readonly", foreground),
                ("pressed", select_foreground),
                ("active", select_foreground),
                ("focus", foreground),
                ("!disabled", foreground),
            ],
            bordercolor=border_map,
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
            background=[
                ("disabled", disabled_background),
                ("selected", select_background),
                ("active", select_background),
                ("!disabled", heading_background),
            ],
            foreground=[
                ("disabled", disabled_foreground),
                ("selected", select_foreground),
                ("active", select_foreground),
                ("!disabled", foreground),
            ],
            bordercolor=border_map,
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
    def _configure_modern_elements(
        cls,
        ttk_style: ttk.Style,
        theme: Dict[str, str],
        input_background_map,
        input_foreground_map,
        border_map,
    ) -> None:
        """Build rounded, shadowed layouts for core controls."""

        background = theme["background"]
        input_background = theme["input_background"]
        foreground = theme["foreground"]
        input_foreground = theme["input_foreground"]
        accent = theme["accent"]
        select_background = theme["select_background"]
        select_foreground = theme["select_foreground"]
        disabled_foreground = select_foreground
        disabled_background = theme["border"]
        shadow = cls._shade_color(theme["border"], -0.18)
        glow = cls._shade_color(accent, 0.12)

        if cls._use_azure_fallback:
            cls._apply_azure_fallback(ttk_style, theme)
            return

        try:
            element_names = set(ttk_style.element_names())
            if "Modern.Card.border" not in element_names:
                ttk_style.element_create(
                    "Modern.Card.border",
                    "border",
                    border=12,
                    borderwidth=1,
                    relief="flat",
                    padding=10,
                    sticky="nswe",
                )
            if "Modern.Entry.border" not in element_names:
                ttk_style.element_create(
                    "Modern.Entry.border",
                    "border",
                    border=8,
                    borderwidth=1,
                    relief="flat",
                    padding=6,
                    sticky="nswe",
                )
            if "Modern.Button.border" not in element_names:
                ttk_style.element_create(
                    "Modern.Button.border",
                    "border",
                    border=10,
                    borderwidth=1,
                    relief="flat",
                    padding=8,
                    sticky="nswe",
                )

            ttk_style.layout(
                cls.FRAME_STYLE,
                [
                    (
                        "Modern.Card.border",
                        {
                            "sticky": "nswe",
                            "children": [
                                (
                                    "Frame.padding",
                                    {
                                        "sticky": "nswe",
                                        "children": [("Frame.background", {"sticky": "nswe"})],
                                    },
                                )
                            ],
                        },
                    )
                ],
            )
            ttk_style.layout(
                cls.ENTRY_STYLE,
                [
                    (
                        "Modern.Entry.border",
                        {
                            "sticky": "nswe",
                            "children": [
                                (
                                    "Entry.padding",
                                    {
                                        "sticky": "nswe",
                                        "children": [
                                            (
                                                "Entry.background",
                                                {
                                                    "sticky": "nswe",
                                                    "children": [("Entry.textarea", {"sticky": "nswe"})],
                                                },
                                            )
                                        ],
                                    },
                                )
                            ],
                        },
                    )
                ],
            )
            ttk_style.layout(
                cls.COMBOBOX_STYLE,
                [
                    (
                        "Modern.Entry.border",
                        {
                            "sticky": "nswe",
                            "children": [
                                (
                                    "Combobox.padding",
                                    {
                                        "sticky": "nswe",
                                        "children": [
                                            ("Combobox.textarea", {"sticky": "nswe"}),
                                            ("Combobox.downarrow", {"side": "right", "sticky": ""}),
                                        ],
                                    },
                                )
                            ],
                        },
                    )
                ],
            )
            ttk_style.layout(
                cls.SPINBOX_STYLE,
                [
                    (
                        "Modern.Entry.border",
                        {
                            "sticky": "nswe",
                            "children": [
                                (
                                    "Spinbox.field",
                                    {
                                        "side": "left",
                                        "sticky": "nswe",
                                        "children": [
                                            (
                                                "Spinbox.padding",
                                                {
                                                    "sticky": "nswe",
                                                    "children": [("Spinbox.textarea", {"sticky": "nswe"})],
                                                },
                                            )
                                        ],
                                    },
                                ),
                                ("Spinbox.uparrow", {"side": "top", "sticky": "e"}),
                                ("Spinbox.downarrow", {"side": "bottom", "sticky": "e"}),
                            ],
                        },
                    )
                ],
            )
            ttk_style.layout(
                cls.BUTTON_STYLE,
                [
                    (
                        "Modern.Button.border",
                        {
                            "sticky": "nswe",
                            "children": [
                                (
                                    "Button.focus",
                                    {
                                        "sticky": "nswe",
                                        "children": [
                                            (
                                                "Button.padding",
                                                {
                                                    "sticky": "nswe",
                                                    "children": [("Button.label", {"sticky": "nswe"})],
                                                },
                                            )
                                        ],
                                    },
                                )
                            ],
                        },
                    )
                ],
            )

            ttk_style.configure(
                cls.ENTRY_STYLE,
                fieldbackground=input_background,
                background=input_background,
                foreground=input_foreground,
                bordercolor=shadow,
                lightcolor=shadow,
                darkcolor=shadow,
                insertcolor=accent,
            )
            ttk_style.map(
                cls.ENTRY_STYLE,
                fieldbackground=input_background_map,
                foreground=input_foreground_map,
                bordercolor=[("focus", glow), ("active", glow), ("!focus", shadow)],
            )

            ttk_style.configure(
                cls.COMBOBOX_STYLE,
                fieldbackground=input_background,
                background=input_background,
                foreground=input_foreground,
                bordercolor=shadow,
                lightcolor=shadow,
                darkcolor=shadow,
                selectbackground=select_background,
                selectforeground=select_foreground,
            )
            ttk_style.map(
                cls.COMBOBOX_STYLE,
                fieldbackground=input_background_map,
                foreground=input_foreground_map,
                bordercolor=[("focus", glow), ("active", glow), ("!focus", shadow)],
                background=[
                    ("disabled", disabled_background),
                    ("readonly", theme["heading_background"]),
                    ("pressed", select_background),
                    ("active", input_background),
                    ("focus", input_background),
                    ("!disabled", input_background),
                ],
                arrowcolor=[
                    ("disabled", disabled_foreground),
                    ("readonly", foreground),
                    ("active", select_foreground),
                    ("pressed", select_foreground),
                    ("!disabled", foreground),
                ],
            )

            ttk_style.configure(
                cls.SPINBOX_STYLE,
                fieldbackground=input_background,
                background=input_background,
                foreground=input_foreground,
                bordercolor=shadow,
                lightcolor=shadow,
                darkcolor=shadow,
                insertcolor=accent,
            )
            ttk_style.map(
                cls.SPINBOX_STYLE,
                fieldbackground=input_background_map,
                foreground=input_foreground_map,
                bordercolor=[("focus", glow), ("active", glow), ("!focus", shadow)],
                arrowcolor=[
                    ("disabled", disabled_foreground),
                    ("readonly", foreground),
                    ("active", select_foreground),
                    ("pressed", select_foreground),
                    ("!disabled", foreground),
                ],
                background=[
                    ("disabled", disabled_background),
                    ("readonly", theme["heading_background"]),
                    ("pressed", select_background),
                    ("active", input_background),
                    ("focus", input_background),
                    ("!disabled", input_background),
                ],
            )

            ttk_style.configure(
                cls.BUTTON_STYLE,
                background=accent,
                foreground=foreground,
                bordercolor=shadow,
                lightcolor=shadow,
                darkcolor=shadow,
            )
            ttk_style.map(
                cls.BUTTON_STYLE,
                background=[
                    ("disabled", disabled_background),
                    ("pressed", select_background),
                    ("active", glow),
                    ("focus", glow),
                    ("!disabled", accent),
                ],
                foreground=[
                    ("disabled", disabled_foreground),
                    ("pressed", select_foreground),
                    ("active", select_foreground),
                    ("!disabled", foreground),
                ],
                bordercolor=[("focus", glow), ("active", glow), ("!focus", shadow)],
            )

            ttk_style.configure(
                cls.FRAME_STYLE,
                background=background,
                bordercolor=shadow,
                lightcolor=shadow,
                darkcolor=shadow,
                relief="flat",
            )
            ttk_style.map(
                cls.FRAME_STYLE,
                bordercolor=[("focus", glow), ("active", glow), ("!focus", shadow)],
                background=[("active", background), ("!active", background)],
            )

            cls._configure_interaction_variants(
                ttk_style,
                theme,
                glow,
                shadow,
                disabled_background,
                disabled_foreground,
                select_background,
                select_foreground,
            )
        except tk.TclError as exc:  # pragma: no cover - branch exercised in dedicated fallback test
            message = str(exc).lower()
            if "border" in message:
                cls._activate_azure_fallback(ttk_style, theme, exc)
                return
            raise

    @classmethod
    def _activate_azure_fallback(
        cls, ttk_style: ttk.Style, theme: Dict[str, str], exc: tk.TclError
    ) -> None:
        """Log and initialize the Azure ttk theme when native borders are missing."""

        if not cls._use_azure_fallback:
            print(
                "ThemeManager: custom border element unavailable; switching to Azure fallback."
            )
            print(f"ThemeManager: original ttk error: {exc}")
        cls._use_azure_fallback = True
        cls._apply_azure_fallback(ttk_style, theme)

    @classmethod
    def _apply_azure_fallback(cls, ttk_style: ttk.Style, theme: Dict[str, str]) -> None:
        """Configure an Azure-inspired fallback palette without external assets."""

        background = theme["background"]
        foreground = theme["foreground"]
        input_background = theme["input_background"]
        input_foreground = theme["input_foreground"]
        heading_background = theme["heading_background"]
        select_background = theme["select_background"]
        select_foreground = theme["select_foreground"]
        disabled_background = theme["border"]
        disabled_foreground = select_foreground
        accent = theme["accent"]
        shadow = cls._shade_color(theme["border"], -0.18)
        glow = cls._shade_color(accent, 0.12)

        input_background_map = [
            ("disabled", disabled_background),
            ("readonly", heading_background),
            ("pressed", select_background),
            ("active", input_background),
            ("focus", input_background),
            ("!disabled", input_background),
        ]
        input_foreground_map = [
            ("disabled", disabled_foreground),
            ("readonly", foreground),
            ("pressed", select_foreground),
            ("active", input_foreground),
            ("focus", input_foreground),
            ("!disabled", input_foreground),
        ]
        focus_border_map = [("focus", glow), ("active", glow), ("!focus", shadow)]

        if not cls._azure_theme_loaded:
            try:
                ttk_style.theme_use("clam")
            except tk.TclError:
                pass
            cls._azure_theme_loaded = True

        ttk_style.configure(
            ".",
            background=background,
            foreground=foreground,
            fieldbackground=input_background,
            selectbackground=select_background,
            selectforeground=select_foreground,
        )

        ttk_style.configure("TFrame", background=background)
        ttk_style.configure(
            cls.FRAME_STYLE,
            background=background,
            bordercolor=shadow,
            relief="flat",
            borderwidth=1,
            padding=(12, 10),
        )
        ttk_style.map(cls.FRAME_STYLE, bordercolor=focus_border_map)

        for style_name in ("TLabel", cls.REQUIRED_LABEL_STYLE, cls.REQUIRED_ASTERISK_STYLE):
            ttk_style.configure(style_name, background=background, foreground=foreground)

        ttk_style.configure(
            cls.ENTRY_STYLE,
            fieldbackground=input_background,
            foreground=input_foreground,
            bordercolor=shadow,
            lightcolor=shadow,
            darkcolor=shadow,
            insertcolor=accent,
        )
        ttk_style.map(
            cls.ENTRY_STYLE,
            fieldbackground=input_background_map,
            foreground=input_foreground_map,
            bordercolor=focus_border_map,
        )
        cls._clone_style(
            ttk_style,
            cls.ENTRY_STYLE,
            cls.ENTRY_FOCUS_STYLE,
            map_overrides={"bordercolor": focus_border_map},
        )

        ttk_style.configure(
            cls.COMBOBOX_STYLE,
            fieldbackground=input_background,
            foreground=input_foreground,
            bordercolor=shadow,
            lightcolor=shadow,
            darkcolor=shadow,
            arrowsize=12,
        )
        ttk_style.map(
            cls.COMBOBOX_STYLE,
            fieldbackground=input_background_map,
            foreground=input_foreground_map,
            bordercolor=focus_border_map,
            arrowcolor=[
                ("disabled", disabled_foreground),
                ("readonly", foreground),
                ("active", select_foreground),
                ("pressed", select_foreground),
                ("!disabled", foreground),
            ],
        )
        cls._clone_style(
            ttk_style,
            cls.COMBOBOX_STYLE,
            cls.COMBOBOX_FOCUS_STYLE,
            map_overrides={"bordercolor": focus_border_map},
        )

        ttk_style.configure(
            cls.SPINBOX_STYLE,
            fieldbackground=input_background,
            foreground=input_foreground,
            bordercolor=shadow,
            lightcolor=shadow,
            darkcolor=shadow,
            insertcolor=accent,
        )
        ttk_style.map(
            cls.SPINBOX_STYLE,
            fieldbackground=input_background_map,
            foreground=input_foreground_map,
            bordercolor=focus_border_map,
            arrowcolor=[
                ("disabled", disabled_foreground),
                ("readonly", foreground),
                ("active", select_foreground),
                ("pressed", select_foreground),
                ("!disabled", foreground),
            ],
        )
        cls._clone_style(
            ttk_style,
            cls.SPINBOX_STYLE,
            cls.SPINBOX_FOCUS_STYLE,
            map_overrides={"bordercolor": focus_border_map},
        )

        ttk_style.configure(
            cls.BUTTON_STYLE,
            background=accent,
            foreground=foreground,
            bordercolor=shadow,
            lightcolor=shadow,
            darkcolor=shadow,
        )
        ttk_style.map(
            cls.BUTTON_STYLE,
            background=[
                ("disabled", disabled_background),
                ("pressed", select_background),
                ("active", glow),
                ("focus", glow),
                ("!disabled", accent),
            ],
            foreground=[
                ("disabled", disabled_foreground),
                ("pressed", select_foreground),
                ("active", select_foreground),
                ("!disabled", foreground),
            ],
            bordercolor=focus_border_map,
        )

        ttk_style.configure(
            cls.CHECKBUTTON_STYLE,
            background=background,
            foreground=foreground,
            focuscolor=glow,
        )

        cls._configure_interaction_variants(
            ttk_style,
            theme,
            glow,
            shadow,
            disabled_background,
            disabled_foreground,
            select_background,
            select_foreground,
        )

    @classmethod
    def _configure_interaction_variants(
        cls,
        ttk_style: ttk.Style,
        theme: Dict[str, str],
        glow: str,
        shadow: str,
        disabled_background: str,
        disabled_foreground: str,
        select_background: str,
        select_foreground: str,
    ) -> None:
        """Create hover/focus variants so bindings can toggle subtle animations."""

        hover_background = cls._shade_color(theme["accent"], 0.12)
        base_button_padding = ttk_style.configure(cls.BUTTON_STYLE).get("padding", (12, 8))
        padded_hover = base_button_padding

        cls._clone_style(
            ttk_style,
            cls.BUTTON_STYLE,
            cls.BUTTON_HOVER_STYLE,
            configure_overrides={
                "background": hover_background,
                "lightcolor": glow,
                "darkcolor": glow,
                "bordercolor": glow,
                "padding": padded_hover,
            },
            map_overrides={
                "background": [
                    ("disabled", disabled_background),
                    ("pressed", select_background),
                    ("active", hover_background),
                    ("focus", hover_background),
                    ("!disabled", hover_background),
                ],
                "foreground": [
                    ("disabled", disabled_foreground),
                    ("pressed", select_foreground),
                    ("active", select_foreground),
                    ("!disabled", theme["foreground"]),
                ],
                "bordercolor": [("focus", glow), ("active", glow), ("!focus", shadow)],
            },
        )

        focus_overrides = {
            "bordercolor": glow,
            "lightcolor": glow,
            "darkcolor": glow,
        }
        cls._clone_style(ttk_style, cls.ENTRY_STYLE, cls.ENTRY_FOCUS_STYLE, configure_overrides=focus_overrides)
        cls._clone_style(
            ttk_style,
            cls.COMBOBOX_STYLE,
            cls.COMBOBOX_FOCUS_STYLE,
            configure_overrides=focus_overrides,
        )
        cls._clone_style(
            ttk_style,
            cls.SPINBOX_STYLE,
            cls.SPINBOX_FOCUS_STYLE,
            configure_overrides=focus_overrides,
        )

    @staticmethod
    def _bump_padding(padding, delta: int) -> tuple:
        if isinstance(padding, (list, tuple)):
            try:
                values = [int(float(value)) for value in padding]
                return tuple(value + delta for value in values)
            except (TypeError, ValueError):
                return tuple(padding)
        if isinstance(padding, str):
            try:
                numeric = int(float(padding))
                return (numeric + delta, numeric + delta)
            except ValueError:
                return (delta, delta)
        return (delta, delta)

    @classmethod
    def _clone_style(
        cls,
        ttk_style: ttk.Style,
        source: str,
        target: str,
        *,
        configure_overrides: Optional[Dict[str, str]] = None,
        map_overrides: Optional[Dict[str, list]] = None,
    ) -> None:
        """Copy layout/configuration from ``source`` into ``target`` with overrides."""

        try:
            layout = ttk_style.layout(source)
            if layout:
                ttk_style.layout(target, layout)
        except tk.TclError:
            layout = None

        try:
            config = ttk_style.configure(source)
        except tk.TclError:
            config = {}
        if configure_overrides:
            config.update(configure_overrides)
        if config:
            ttk_style.configure(target, **config)

        try:
            mapped = ttk_style.map(source)
        except tk.TclError:
            mapped = {}
        if map_overrides:
            mapped.update(map_overrides)
        if mapped:
            ttk_style.map(target, **mapped)

    @staticmethod
    def _shade_color(color: str, factor: float) -> str:
        color = color.lstrip("#")
        if len(color) != 6:
            return color
        try:
            channels = [int(color[i : i + 2], 16) for i in range(0, 6, 2)]
        except ValueError:
            return "#000000"
        adjusted = [
            min(255, max(0, int(channel + (255 - channel) * factor if factor > 0 else channel * (1 + factor))))
            for channel in channels
        ]
        return "#" + "".join(f"{value:02x}" for value in adjusted)

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


def reapply_all_badges() -> None:
    """Re-render every live ``ValidationBadge`` using the active palette."""

    try:
        from validation_badge import iter_active_badges
    except Exception:
        return
    for badge in iter_active_badges():
        try:
            badge.reapply_style()
        except Exception:
            continue


__all__ = ["ThemeManager", "LIGHT_THEME", "DARK_THEME", "reapply_all_badges"]
