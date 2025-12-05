"""Reusable validation badge widget with cycling states."""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable

from theme_manager import ThemeManager
from ui.config import COL_PADX, ROW_PADY
from ui.frames.utils import ensure_grid_support

WARNING_STYLE = "warning.badge"
SUCCESS_STYLE = "success.badge"
NEUTRAL_STYLE = "neutral.badge"

WARNING_ICON = "⚠️"
SUCCESS_ICON = "✅"
NEUTRAL_ICON = "⏳"


@dataclass
class _Palette:
    foreground: str
    background: str


def _coalesce_color(style: ttk.Style | None, style_name: str, option: str, fallback: str) -> str:
    if style is None:
        return fallback
    try:
        value = style.lookup(style_name, option)
    except Exception:
        value = ""
    return value or fallback


def _resolve_palette(style: ttk.Style | None, style_name: str, *, role: str) -> _Palette:
    theme = ThemeManager.current()
    defaults = {
        "warning": _Palette(
            foreground=theme.get("warning_foreground", "#664d03"),
            background=theme.get("warning_background", "#fff3cd"),
        ),
        "success": _Palette(
            foreground=theme.get("select_foreground", "#ffffff"),
            background=theme.get("accent", "#2e7d32"),
        ),
        "neutral": _Palette(
            foreground=theme.get("foreground", "#000000"),
            background=theme.get("secondary", "#e0e0e0"),
        ),
    }
    base = defaults.get(role, defaults["neutral"])
    return _Palette(
        foreground=_coalesce_color(style, style_name, "foreground", base.foreground),
        background=_coalesce_color(style, style_name, "background", base.background),
    )


def build_message_preview(message: str, *, max_chars_per_line: int = 18, max_lines: int = 2) -> str:
    """Compact a message to a multi-line preview with ellipsis."""

    if max_chars_per_line <= 0 or max_lines <= 0:
        return message or ""

    text = " ".join((message or "").split())
    if not text:
        return ""

    segments: list[str] = []
    cursor = 0
    while cursor < len(text) and len(segments) < max_lines:
        segments.append(text[cursor : cursor + max_chars_per_line])
        cursor += max_chars_per_line

    if cursor < len(text):
        trimmed = segments[-1][: max_chars_per_line - 3].rstrip()
        segments[-1] = f"{trimmed}..." if trimmed else "..."

    return "\n".join(segments)


class ValidationBadge:
    """Displays validation feedback with cycling view modes."""

    STYLE_MAP = {
        "warning": WARNING_STYLE,
        "success": SUCCESS_STYLE,
        "neutral": NEUTRAL_STYLE,
    }

    ICON_MAP = {
        "warning": WARNING_ICON,
        "success": SUCCESS_ICON,
        "neutral": NEUTRAL_ICON,
    }

    def __init__(
        self,
        parent,
        *,
        textvariable: tk.StringVar | None = None,
        wraplength: int = 360,
        preview_chars: int = 18,
        preview_lines: int = 2,
        default_state: str = "neutral",
        initial_display: str = "short",
        tk_module=None,
        ttk_module=None,
    ) -> None:
        self._tk = tk_module or tk
        self._ttk = ttk_module or ttk
        try:
            self._style = self._ttk.Style(master=parent)
        except Exception:
            try:
                self._style = ttk.Style(master=parent)
            except Exception:
                self._style = None
        self._configured_styles: set[str] = set()
        self._wraplength = wraplength
        self._preview_chars = preview_chars
        self._preview_lines = preview_lines
        self._state = default_state if default_state in self.STYLE_MAP else "neutral"
        self._display_mode = initial_display if initial_display in {"short", "full", "emoji"} else "short"
        self._message_full = ""
        self._message_short = ""
        self._text_var = self._tk.StringVar()
        self._textvariable = textvariable

        ensure_grid_support(parent)
        self._label = self._ttk.Label(parent, textvariable=self._text_var, anchor="w", wraplength=wraplength)
        ensure_grid_support(self._label)
        self._label.bind("<Button-1>", self._cycle_display, add="+")

        initial_message = textvariable.get() if textvariable is not None else ""
        if textvariable is not None:
            tracer = getattr(textvariable, "trace_add", None)
            if callable(tracer):
                tracer("write", lambda *_: self._sync_with_textvariable())
        self.update_state(self._state, initial_message)

    @property
    def widget(self):
        return self._label

    def grid(self, *args, **kwargs):  # noqa: ANN001
        return self._label.grid(*args, **kwargs)

    def pack(self, *args, **kwargs):  # noqa: ANN001
        return self._label.pack(*args, **kwargs)

    def place(self, *args, **kwargs):  # noqa: ANN001
        return self._label.place(*args, **kwargs)

    def hide(self) -> None:
        manager = self._label.winfo_manager()
        if manager == "grid":
            remover = getattr(self._label, "grid_remove", None)
        elif manager == "pack":
            remover = getattr(self._label, "pack_forget", None)
        else:
            remover = getattr(self._label, "place_forget", None)
        if callable(remover):
            remover()

    def show(self) -> None:
        manager = self._label.winfo_manager()
        if manager == "grid":
            shower = getattr(self._label, "grid", None)
        elif manager == "pack":
            shower = getattr(self._label, "pack", None)
        else:
            shower = getattr(self._label, "grid", None) or getattr(self._label, "pack", None)
        if callable(shower):
            shower()

    def update_state(
        self,
        state: str,
        message: str | None = None,
        *,
        success_text: str | None = None,
        neutral_text: str | None = None,
    ) -> None:
        if state not in self.STYLE_MAP:
            state = "neutral"
        self._state = state
        if state == "success":
            self._message_full = success_text or SUCCESS_ICON
        elif state == "neutral":
            self._message_full = message or neutral_text or NEUTRAL_ICON
        else:
            self._message_full = message or ""
        self._message_short = build_message_preview(
            self._message_full,
            max_chars_per_line=self._preview_chars,
            max_lines=self._preview_lines,
        )
        self._apply_render()

    def set_warning(self, message: str | None) -> None:
        self.update_state("warning", message)

    def set_success(self, message: str | None = None) -> None:
        self.update_state("success", message, success_text=message)

    def set_neutral(self, message: str | None = None) -> None:
        self.update_state("neutral", message, neutral_text=message)

    def set_message(self, message: str | None, *, expand: bool | None = None) -> None:
        self.set_warning(message or "")
        if expand:
            self._display_mode = "full"
        elif expand is False:
            self._display_mode = "short"
        self._apply_render()

    def expand(self, *, animate: bool = False) -> None:  # noqa: ARG002
        self._display_mode = "full"
        self._apply_render()

    def collapse(self, *, animate: bool = False, compact_mode: str = "short") -> None:  # noqa: ARG002
        self._display_mode = "emoji" if compact_mode == "icon" else "short"
        self._apply_render()

    def winfo_ismapped(self):  # noqa: ANN001
        return self._label.winfo_ismapped()

    def winfo_manager(self):  # noqa: ANN001
        return self._label.winfo_manager()

    def bind(self, *args, **kwargs):  # noqa: ANN001
        return self._label.bind(*args, **kwargs)

    def _sync_with_textvariable(self) -> None:
        if self._textvariable is None:
            return
        value = self._textvariable.get()
        self.set_warning(value)

    def _cycle_display(self, _event=None):  # noqa: ANN001
        next_mode = {"short": "full", "full": "emoji", "emoji": "short"}
        self._display_mode = next_mode.get(self._display_mode, "short")
        self._apply_render()

    def _style_name(self) -> str:
        role = self._state if self._state in self.STYLE_MAP else "neutral"
        base_name = self.STYLE_MAP[role]
        if base_name in self._configured_styles:
            return base_name
        if self._style is None:
            return base_name
        palette = _resolve_palette(self._style, base_name, role=role)
        self._style.configure(
            base_name,
            background=palette.background,
            foreground=palette.foreground,
            padding=(6, 2),
            borderwidth=1,
            relief="solid",
            font=("TkDefaultFont", 9, "bold"),
            wraplength=self._wraplength,
        )
        self._configured_styles.add(base_name)
        return base_name

    def _apply_render(self) -> None:
        style_name = self._style_name()
        emoji = self.ICON_MAP.get(self._state, NEUTRAL_ICON)
        if self._display_mode == "emoji":
            text = emoji
        elif self._display_mode == "full":
            text = self._message_full or emoji
        else:
            text = self._message_short or self._message_full or emoji
        self._text_var.set(text)
        self._label.configure(style=style_name)

    def __getattr__(self, item: str):
        return getattr(self._label, item)


class ValidationBadgeGroup:
    """Registers and updates multiple validation badges."""

    def __init__(
        self,
        *,
        parent=None,
        pending_text: str = NEUTRAL_ICON,
        success_text: str = SUCCESS_ICON,
        tk_module=None,
        ttk_module=None,
    ):
        self.parent = parent
        self.pending_text = pending_text
        self.success_text = success_text
        self._tk = tk_module
        self._ttk = ttk_module
        self._registry: dict[str, ValidationBadge] = {}
        self._updaters: dict[str, Callable[[], str | None]] = {}

    def create_and_register(
        self,
        key: str,
        parent,
        *,
        row: int,
        column: int,
        pending_text: str | None = None,
        success_text: str | None = None,
    ) -> ValidationBadge:
        badge = ValidationBadge(
            parent,
            default_state="neutral",
            tk_module=self._tk,
            ttk_module=self._ttk,
        )
        badge.grid(row=row, column=column, padx=COL_PADX, pady=ROW_PADY, sticky="w")
        self.register_badge(
            key,
            badge,
            pending_text=pending_text or self.pending_text,
            success_text=success_text or self.success_text,
        )
        badge.set_neutral(pending_text or self.pending_text)
        return badge

    def register_badge(
        self,
        key: str,
        badge: ValidationBadge,
        *,
        pending_text: str | None = None,
        success_text: str | None = None,
    ) -> None:
        self._registry[key] = badge
        badge.set_neutral(pending_text or self.pending_text)
        badge._success_text = success_text or self.success_text  # type: ignore[attr-defined]

    def update_badge(
        self,
        key: str,
        is_ok: bool,
        message: str | None,
        *,
        success_text: str | None = None,
        pending_text: str | None = None,
    ) -> None:
        badge = self._registry.get(key)
        if badge is None:
            return
        success_label = success_text or getattr(badge, "_success_text", self.success_text)
        pending_label = pending_text or self.pending_text
        if is_ok:
            badge.set_success(success_label)
        elif message:
            badge.set_warning(message)
        else:
            badge.set_neutral(pending_label)

    def wrap_validation(
        self,
        key: str,
        validate_fn,
        *,
        success_text: str | None = None,
        pending_text: str | None = None,
    ):
        def _wrapped():
            message = validate_fn()
            self.update_badge(
                key,
                message is None,
                message,
                success_text=success_text,
                pending_text=pending_text,
            )
            return message

        self._updaters[key] = _wrapped
        return _wrapped

    def refresh(self) -> None:
        for updater in self._updaters.values():
            updater()
