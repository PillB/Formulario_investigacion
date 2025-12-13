"""Reusable validation badge widget with cycling states."""
from __future__ import annotations

import tkinter as tk
import weakref
from dataclasses import dataclass
from tkinter import TclError, ttk
from typing import Any, Callable, Iterable

from theme_manager import ThemeManager
from ui.config import COL_PADX, ROW_PADY
from ui.frames.utils import ensure_grid_support

WARNING_STYLE = "WarningBadge.TLabel"
SUCCESS_STYLE = "SuccessBadge.TLabel"
NEUTRAL_STYLE = "NeutralBadge.TLabel"

WARNING_ICON = "⚠️"
SUCCESS_ICON = "✅"
NEUTRAL_ICON = "⏳"


@dataclass
class _Palette:
    foreground: str
    background: str


class _FallbackVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value

    def trace_add(self, *_args):  # noqa: ANN001
        return None


class _FallbackLabel:
    def __init__(self, *_args, textvariable=None, **kwargs):  # noqa: ANN001
        self._config = {"textvariable": textvariable, **kwargs}
        self._bindings: list = []
        self._mapped = False
        self._manager = ""
        self._geometry_options: dict = {}

    def grid(self, *args, **kwargs):  # noqa: ANN001
        self._mapped = True
        self._manager = "grid"
        self._geometry_options = dict(kwargs)
        self._config.update(kwargs)

    def pack(self, *args, **kwargs):  # noqa: ANN001
        self._mapped = True
        self._manager = "pack"
        self._geometry_options = dict(kwargs)
        self._config.update(kwargs)

    def place(self, *args, **kwargs):  # noqa: ANN001
        self._mapped = True
        self._manager = "place"
        self._geometry_options = dict(kwargs)
        self._config.update(kwargs)

    def grid_remove(self, *args, **kwargs):  # noqa: ANN001
        self._mapped = False

    def pack_forget(self, *args, **kwargs):  # noqa: ANN001
        self._mapped = False

    def place_forget(self, *args, **kwargs):  # noqa: ANN001
        self._mapped = False

    def winfo_ismapped(self):  # noqa: ANN001
        return self._mapped

    def winfo_manager(self):  # noqa: ANN001
        return self._manager if self._mapped else ""

    def grid_info(self):
        return self._geometry_options

    def pack_info(self):
        return self._geometry_options

    def place_info(self):
        return self._geometry_options

    def bind(self, *args, **kwargs):  # noqa: ANN001
        self._bindings.append((args, kwargs))

    def configure(self, **kwargs):  # noqa: ANN001
        self._config.update(kwargs)

    def winfo_exists(self):
        return True

    def winfo_children(self):
        return []


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

    instances: set["ValidationBadge"] = set()

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
        self._geometry_manager: str | None = None
        self._geometry_options: dict[str, Any] | None = None
        try:
            self._text_var = self._tk.StringVar()
        except Exception:
            self._text_var = _FallbackVar()
        self._textvariable = textvariable

        ensure_grid_support(parent)
        try:
            self._label = self._ttk.Label(parent, textvariable=self._text_var, anchor="w", wraplength=wraplength)
        except Exception:
            self._label = _FallbackLabel(textvariable=self._text_var, anchor="w", wraplength=wraplength)
        ensure_grid_support(self._label)
        self._label.bind("<Button-1>", self._cycle_display, add="+")

        _register_badge(self)
        self.instances.add(self)
        try:
            self._label.bind("<Destroy>", lambda _evt, badge=self: _unregister_badge(badge), add="+")
        except Exception:
            pass

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
        result = self._label.grid(*args, **kwargs)
        self._remember_geometry()
        return result

    def pack(self, *args, **kwargs):  # noqa: ANN001
        result = self._label.pack(*args, **kwargs)
        self._remember_geometry()
        return result

    def place(self, *args, **kwargs):  # noqa: ANN001
        result = self._label.place(*args, **kwargs)
        self._remember_geometry()
        return result

    def hide(self) -> None:
        self._remember_geometry()
        manager = self._geometry_manager or self._label.winfo_manager()
        if manager == "grid":
            remover = getattr(self._label, "grid_remove", None)
        elif manager == "pack":
            remover = getattr(self._label, "pack_forget", None)
        else:
            remover = getattr(self._label, "place_forget", None)
        if callable(remover):
            remover()

    def show(self) -> None:
        manager = self._geometry_manager or self._label.winfo_manager()
        if manager == "grid":
            shower = getattr(self._label, "grid", None)
        elif manager == "pack":
            shower = getattr(self._label, "pack", None)
        elif manager == "place":
            shower = getattr(self._label, "place", None)
        else:
            shower = getattr(self._label, "grid", None) or getattr(self._label, "pack", None)
        if callable(shower):
            options = self._geometry_options or {}
            if manager in {"grid", "pack", "place"} and options:
                shower(**options)
            else:
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

    def set_error(self, message: str | None) -> None:
        self.set_warning(message)

    def set_success(self, message: str | None = None) -> None:
        self.update_state("success", message, success_text=message)

    def set_neutral(self, message: str | None = None) -> None:
        self.update_state("neutral", message, neutral_text=message)

    def set_message(self, message: str | None, *, expand: bool | None = None) -> None:
        self.set_warning(message or "")
        if self._textvariable is not None:
            setter = getattr(self._textvariable, "set", None)
            if callable(setter):
                setter(message or "")
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
        layout = getattr(self._style, "layout", None)
        if callable(layout):
            try:
                if not layout(base_name):
                    layout(base_name, layout("TLabel"))
            except Exception:
                pass
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
        if getattr(self, "_is_destroyed", False):
            return
        if not self._widget_exists():
            self._mark_destroyed()
            return
        style_name = self._style_name()
        emoji = self.ICON_MAP.get(self._state, NEUTRAL_ICON)
        if self._display_mode == "emoji":
            text = emoji
        elif self._display_mode == "full":
            text = self._message_full or emoji
        else:
            text = self._message_short or self._message_full or emoji
        self._text_var.set(text)
        if getattr(self, "_is_destroyed", False) or not self._widget_exists():
            self._mark_destroyed()
            return
        try:
            self._label.configure(style=style_name)
        except TclError:
            self._mark_destroyed()
        except Exception:
            self._mark_destroyed()

    def __getattr__(self, item: str):
        return getattr(self._label, item)

    def reapply_style(self) -> None:
        """Recompute the badge style so it reflects the active theme palette."""

        self._configured_styles.clear()
        self._apply_render()

    def _remember_geometry(self) -> None:
        manager = self._label.winfo_manager()
        if manager == "grid":
            info_fn = getattr(self._label, "grid_info", None)
        elif manager == "pack":
            info_fn = getattr(self._label, "pack_info", None)
        elif manager == "place":
            info_fn = getattr(self._label, "place_info", None)
        else:
            return

        if callable(info_fn):
            info = info_fn()
            if info is not None:
                self._geometry_manager = manager
                self._geometry_options = dict(info)

    def _mark_destroyed(self) -> None:
        self._is_destroyed = True
        _unregister_badge(self)

    def _widget_exists(self) -> bool:
        try:
            return bool(self._label.winfo_exists())
        except Exception:
            return False


class ValidationBadgeRegistry:
    """Central registry that creates and updates validation badges."""

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
        self._labels: dict[str, tuple[str, str]] = {}
        self._updaters: dict[str, Callable[[], str | None]] = {}
        _REGISTRIES.add(self)

    def claim(
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
        return badge

    def register_badge(
        self,
        key: str,
        badge: ValidationBadge,
        *,
        pending_text: str | None = None,
        success_text: str | None = None,
    ) -> None:
        pending_label = pending_text or self.pending_text
        success_label = success_text or self.success_text
        self._registry[key] = badge
        self._labels[key] = (pending_label, success_label)
        badge.set_neutral(pending_label)

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
        if not self._badge_exists(badge):
            self._purge_badge(badge)
            return
        pending_label, success_label = self._labels.get(key, (self.pending_text, self.success_text))
        success_label = success_text or success_label
        pending_label = pending_text or pending_label
        if is_ok:
            badge.set_success(success_label)
        elif message:
            badge.set_error(message)
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

    def _badge_exists(self, badge: ValidationBadge) -> bool:
        try:
            return bool(badge.widget.winfo_exists())
        except Exception:
            return False

    def _purge_badge(self, badge: ValidationBadge) -> None:
        stale_keys = [key for key, registered in self._registry.items() if registered is badge]
        for key in stale_keys:
            self._registry.pop(key, None)
            self._labels.pop(key, None)
            self._updaters.pop(key, None)


class ValidationBadgeGroup(ValidationBadgeRegistry):
    """Backward compatible alias for the badge registry."""

    create_and_register = ValidationBadgeRegistry.claim


_ACTIVE_BADGES: set[ValidationBadge] = set()
_REGISTRIES: weakref.WeakSet[ValidationBadgeRegistry] = weakref.WeakSet()


def _register_badge(badge: ValidationBadge) -> None:
    _ACTIVE_BADGES.add(badge)


def _unregister_badge(badge: ValidationBadge) -> None:
    _ACTIVE_BADGES.discard(badge)
    try:
        ValidationBadge.instances.discard(badge)
    except Exception:
        pass
    for registry in list(_REGISTRIES):
        try:
            registry._purge_badge(badge)
        except Exception:
            continue


def iter_active_badges() -> Iterable[ValidationBadge]:
    """Yield ValidationBadge instances that are still alive."""

    stale: set[ValidationBadge] = set()
    for badge in _ACTIVE_BADGES:
        try:
            exists = bool(badge.widget.winfo_exists())
        except Exception:
            exists = False
        if exists:
            yield badge
        else:
            stale.add(badge)
    _ACTIVE_BADGES.difference_update(stale)


badge_registry = ValidationBadgeRegistry()
