"""Accordion-like collapsible section widget with themed styling."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from theme_manager import ThemeManager


_INDICATOR_OPEN = "\u25BE"  # ▼
_INDICATOR_CLOSED = "\u25B8"  # ▸

_registered_theme: str | None = None


class CollapsibleSection(ttk.Frame):
    """Frame that can collapse/expand its inner content with a header toggle."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        *,
        open: bool = True,
        on_toggle: Optional[Callable[["CollapsibleSection"], None]] = None,
        **kwargs,
    ) -> None:
        register_styles()
        super().__init__(parent, style="AccordionCard.TFrame", **kwargs)
        self._is_open = open
        self._hovering = False
        self._on_toggle = on_toggle

        self.header = ttk.Frame(self, style="AccordionHeader.TFrame")
        self.header.pack(fill="x")

        self.indicator = ttk.Label(
            self.header, text=self._indicator_symbol, style="AccordionIndicator.TLabel"
        )
        self.indicator.pack(side="left", padx=(6, 4))

        self.title_label = ttk.Label(
            self.header, text=title, style="AccordionTitle.TLabel", anchor="w"
        )
        self.title_label.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.content = ttk.Frame(self, style="AccordionContent.TFrame")
        if open:
            self._show_content()

        for widget in (self.header, self.title_label, self.indicator):
            widget.configure(takefocus=True)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<ButtonPress-1>", self._on_press)
            widget.bind("<ButtonRelease-1>", self._on_button_release)
            widget.bind("<KeyPress-space>", self._on_press)
            widget.bind("<KeyRelease-space>", self._on_key_activate)
            widget.bind("<KeyPress-Return>", self._on_press)
            widget.bind("<KeyRelease-Return>", self._on_key_activate)

    @property
    def is_open(self) -> bool:
        """Return whether the content frame is currently visible."""

        return self._is_open

    @property
    def _indicator_symbol(self) -> str:
        return _INDICATOR_OPEN if self._is_open else _INDICATOR_CLOSED

    def set_title(self, title: str) -> None:
        """Update the header title label text."""

        self.title_label.configure(text=title)

    def toggle(self, _event: tk.Event | None = None) -> None:
        """Toggle the visibility of the content frame."""

        if self._is_open:
            self._hide_content()
        else:
            self._show_content()
        self.indicator.configure(text=self._indicator_symbol)
        if callable(self._on_toggle):
            self._on_toggle(self)

    def pack_content(self, widget: tk.Widget, **pack_kwargs) -> tk.Widget:
        """Pack ``widget`` into the content frame with sensible defaults.

        Parameters default to ``fill="both"`` and ``expand=True`` to aid
        layout of nested frames. Returns the widget for chaining.
        """

        defaults = {"fill": "both", "expand": True}
        defaults.update(pack_kwargs)
        widget.pack(**defaults)
        return widget

    def _show_content(self) -> None:
        self.content.pack(fill="both", expand=True)
        self._is_open = True

    def _hide_content(self) -> None:
        self.content.pack_forget()
        self._is_open = False

    def _set_header_style(self, state: str) -> None:
        frame_style = {
            "hover": "AccordionHeader.Hover.TFrame",
            "active": "AccordionHeader.Active.TFrame",
        }.get(state, "AccordionHeader.TFrame")
        label_style = {
            "hover": "AccordionTitle.Hover.TLabel",
            "active": "AccordionTitle.Active.TLabel",
        }.get(state, "AccordionTitle.TLabel")
        indicator_style = {
            "hover": "AccordionIndicator.Hover.TLabel",
            "active": "AccordionIndicator.Active.TLabel",
        }.get(state, "AccordionIndicator.TLabel")
        self.header.configure(style=frame_style)
        self.title_label.configure(style=label_style)
        self.indicator.configure(style=indicator_style)

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        self._hovering = True
        self._set_header_style("hover")

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        self._hovering = False
        self._set_header_style("normal")

    def _on_press(self, _event: tk.Event | None = None) -> None:
        self._set_header_style("active")

    def _on_release(self, _event: tk.Event | None = None) -> None:
        self._set_header_style("hover" if self._hovering else "normal")

    def _on_button_release(self, event: tk.Event | None = None) -> None:
        self._on_release(event)
        self.toggle(event)

    def _on_key_activate(self, event: tk.Event | None = None) -> str:
        self._on_release(event)
        self.toggle(event)
        return "break"


def register_styles() -> None:
    """Register themed styles for the accordion components.

    Uses ``ThemeManager`` colors so palettes update alongside the rest of the
    application when toggling themes.
    """

    global _registered_theme
    palette = ThemeManager.current()
    theme_name = palette.get("name")
    if _registered_theme == theme_name:
        return

    background = palette.get("background", "#FFFFFF")
    foreground = palette.get("foreground", "#000000")
    heading_background = palette.get("heading_background", background)
    accent = palette.get("accent", heading_background)
    border = palette.get("border", accent)
    active_background = palette.get("select_background", accent)
    active_foreground = palette.get("select_foreground", foreground)

    try:
        style = ThemeManager._ensure_style()  # type: ignore[attr-defined]
    except RuntimeError:
        style = ttk.Style()

    if "Modern.Card.border" in style.element_names():
        style.layout(
            "AccordionCard.TFrame",
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
    style.configure(
        "AccordionCard.TFrame",
        background=background,
        bordercolor=border,
        lightcolor=border,
        darkcolor=border,
        relief=tk.FLAT,
        padding=4,
    )
    style.map(
        "AccordionCard.TFrame",
        bordercolor=[("focus", accent), ("active", accent), ("!focus", border)],
    )
    style.configure(
        "AccordionContent.TFrame",
        background=background,
        padding=(8, 6, 8, 10),
    )

    header_base = {
        "padding": (12, 10),
        "borderwidth": 0,
        "bordercolor": border,
        "relief": tk.FLAT,
    }
    style.configure("AccordionHeader.TFrame", background=heading_background, **header_base)
    style.configure("AccordionHeader.Hover.TFrame", background=accent, **header_base)
    style.configure("AccordionHeader.Active.TFrame", background=active_background, **header_base)

    label_base = {"font": ("Arial", 12, "bold")}
    style.configure(
        "AccordionTitle.TLabel",
        background=heading_background,
        foreground=foreground,
        **label_base,
    )
    style.configure(
        "AccordionTitle.Hover.TLabel",
        background=accent,
        foreground=foreground,
        **label_base,
    )
    style.configure(
        "AccordionTitle.Active.TLabel",
        background=active_background,
        foreground=active_foreground,
        **label_base,
    )

    indicator_base = {"font": ("Arial", 12)}
    style.configure(
        "AccordionIndicator.TLabel",
        background=heading_background,
        foreground=foreground,
        **indicator_base,
    )
    style.configure(
        "AccordionIndicator.Hover.TLabel",
        background=accent,
        foreground=foreground,
        **indicator_base,
    )
    style.configure(
        "AccordionIndicator.Active.TLabel",
        background=active_background,
        foreground=active_foreground,
        **indicator_base,
    )

    _registered_theme = theme_name


__all__ = ["CollapsibleSection", "register_styles"]
