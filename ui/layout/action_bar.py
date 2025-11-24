"""Reusable action bar with primary CRUD controls for list views."""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Mapping
from tkinter import ttk

from theme_manager import ThemeManager

_action_bar_theme: str | None = None


class ActionBar(ttk.Frame):
    """Bottom-aligned toolbar with common record actions.

    Parameters
    ----------
    parent:
        Widget parent that will contain the action bar.
    commands:
        Optional mapping of command keys (``add``, ``edit``, ``delete``,
        ``export`` or custom keys) to callback callables. Missing commands
        default to a no-op.
    buttons:
        Optional iterable of ``(label, key)`` tuples to customize the
        buttons rendered. Use ``None`` as the label to insert a separator.
        Defaults to :attr:`_BUTTONS`.
    pack_kwargs:
        Optional ``pack`` options to customize placement. Defaults to
        ``{"side": "bottom", "fill": "x"}``.
    """

    _BUTTONS: tuple[tuple[str | None, str | None], ...] = (
        ("Agregar cliente", "add"),
        ("Editar seleccionado", "edit"),
        ("Eliminar", "delete"),
        (None, None),
        ("Exportar Informe", "export"),
    )

    def __init__(
        self,
        parent: tk.Misc,
        *,
        commands: Mapping[str, Callable[[], None]] | None = None,
        buttons: tuple[tuple[str | None, str | None], ...] | None = None,
        pack_kwargs: Mapping[str, object] | None = None,
        **kwargs,
    ) -> None:
        register_action_bar_styles()
        super().__init__(parent, style="ActionBar.TFrame", **kwargs)

        defaults = {"side": "bottom", "fill": "x"}
        merged_pack = {**defaults, **(pack_kwargs or {})}
        self.pack(**merged_pack)

        self._button_commands = dict(commands or {})
        self.buttons: dict[str, ttk.Button] = {}
        self._buttons = buttons or self._BUTTONS

        for label, key in self._buttons:
            if label is None:
                separator = ttk.Separator(self, orient=tk.VERTICAL, style="ActionBar.TSeparator")
                separator.pack(side="left", fill="y", padx=(6, 6), pady=4)
                continue
            command = self._button_commands.get(key, lambda: None)
            button = ttk.Button(self, text=label, command=command, style="ActionBar.TButton")
            button.pack(side="left", padx=(0, 8), pady=6)
            if key:
                self.buttons[key] = button


def register_action_bar_styles() -> None:
    """Register ttk styles for :class:`ActionBar` widgets."""

    global _action_bar_theme
    palette = ThemeManager.current()
    theme_name = palette.get("name")
    if _action_bar_theme == theme_name:
        return

    background = palette.get("heading_background", palette.get("background", "#FFFFFF"))
    foreground = palette.get("foreground", "#000000")
    accent = palette.get("accent", foreground)
    border = palette.get("border", accent)
    active_bg = palette.get("select_background", accent)
    active_fg = palette.get("select_foreground", foreground)

    try:
        style = ThemeManager._ensure_style()  # type: ignore[attr-defined]
    except RuntimeError:
        style = ttk.Style()

    style.configure(
        "ActionBar.TFrame",
        background=background,
        borderwidth=1,
        relief=tk.FLAT,
        padding=(10, 8),
    )
    style.map(
        "ActionBar.TFrame",
        bordercolor=[("focus", accent), ("active", border), ("!focus", border)],
    )

    style.configure(
        "ActionBar.TSeparator",
        background=background,
    )

    style.configure(
        "ActionBar.TButton",
        padding=(10, 6),
        font=("Arial", 10, "bold"),
        foreground=foreground,
        background=background,
        bordercolor=border,
    )
    style.map(
        "ActionBar.TButton",
        background=[("active", active_bg), ("pressed", active_bg)],
        foreground=[("active", active_fg), ("pressed", active_fg)],
        bordercolor=[("active", accent), ("pressed", accent)],
    )

    _action_bar_theme = theme_name
