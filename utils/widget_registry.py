from __future__ import annotations

from dataclasses import dataclass
from contextlib import suppress
import re
from typing import Optional
from weakref import WeakKeyDictionary

from validators import normalize_without_accents


@dataclass
class WidgetIdentity:
    logical_id: str
    role: Optional[str] = None
    label: Optional[str] = None


class WidgetIdRegistry:
    """Mantiene un registro estable de widgets y sus identificadores semánticos.

    Los IDs se normalizan para usarse en logs y analítica evitando depender de
    los nombres efímeros que Tkinter asigna a los widgets en tiempo de ejecución.
    """

    def __init__(self) -> None:
        self._registry: WeakKeyDictionary = WeakKeyDictionary()

    def normalize_identifier(self, value: str, *, role: Optional[str] = None) -> str:
        normalized = normalize_without_accents(value or "").lower()
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_") or "widget"
        if role:
            return f"{role}.{normalized}"
        return normalized

    def describe(self, widget) -> str:
        label = None
        if hasattr(widget, "cget"):
            with suppress(Exception):
                label = widget.cget("text")
        try:
            name = widget.winfo_name()
        except Exception:
            name = None
        widget_class = getattr(widget, "__class__", type("obj", (), {})).__name__
        parts = [part for part in (label, name, widget_class) if part]
        return " / ".join(parts) if parts else widget_class or "widget"

    def register(
        self,
        widget,
        logical_id: str,
        *,
        role: Optional[str] = None,
        label: Optional[str] = None,
    ) -> str:
        if widget is None:
            return self.normalize_identifier(logical_id, role=role)
        normalized = self.normalize_identifier(logical_id, role=role)
        self._registry[widget] = WidgetIdentity(normalized, role=role, label=label)
        return normalized

    def resolve(self, widget, *, fallback: Optional[str] = None) -> Optional[str]:
        if widget is None:
            return fallback
        identity = self._registry.get(widget)
        if identity is not None:
            return identity.logical_id
        return fallback or self.describe(widget)


__all__ = ["WidgetIdRegistry", "WidgetIdentity"]
