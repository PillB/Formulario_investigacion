"""Servicios de autopoblado basados en catálogos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from validators import should_autofill_field

from .catalog_service import CatalogService


@dataclass
class AutofillResult:
    found: bool
    used_future_snapshot: bool
    applied: Dict[str, str]
    meta: Dict[str, object]


class AutofillService:
    """Aplica reglas de autopoblado respetando campos modificados por el usuario."""

    def __init__(self, catalog_service: CatalogService, warning_handler=None):
        self.catalog_service = catalog_service
        self.warning_handler = warning_handler or (lambda _message: None)

    def lookup_team_autofill(
        self,
        identifier: str,
        current_values: Mapping[str, str],
        dirty_fields: Mapping[str, bool] | None,
        preserve_existing: bool,
        case_date: str | None,
    ) -> AutofillResult:
        dirty_fields = dirty_fields or {}
        catalog_entry, meta = self.catalog_service.lookup_team_member(identifier, case_date)
        meta = meta or {"selected_date": None, "fallback_used": False, "reason": None}
        fallback_reason = meta.get("reason")
        used_future_snapshot = bool(fallback_reason == "no_past_snapshot")
        if not catalog_entry:
            return AutofillResult(False, False, {}, meta)

        applied: Dict[str, str] = {}
        for key, current_value in current_values.items():
            if dirty_fields.get(key):
                continue
            value = self._resolve_team_value(key, catalog_entry)
            if value and should_autofill_field(current_value, preserve_existing):
                applied[key] = value

        if meta.get("fallback_used"):
            message = self._build_fallback_warning(fallback_reason)
            if message:
                self.warning_handler(message)
        return AutofillResult(True, used_future_snapshot, applied, meta)

    @staticmethod
    def _resolve_team_value(key: str, catalog_entry: Mapping[str, str]) -> str:
        value = (catalog_entry.get(key) or "").strip()
        if value:
            return value
        if key == "fecha_carta_renuncia":
            return (catalog_entry.get("fecha_cese") or "").strip()
        return ""

    @staticmethod
    def _build_fallback_warning(reason: str | None) -> str | None:
        if reason == "no_past_snapshot":
            return (
                "La fecha de ocurrencia es anterior a la última actualización del colaborador; "
                "se usará el registro disponible más reciente."
            )
        if reason == "case_date_missing_or_invalid":
            return (
                "No se pudo interpretar la fecha de ocurrencia; se usará el registro más reciente "
                "disponible del colaborador."
            )
        if reason:
            return f"Se usó un registro alternativo del colaborador ({reason})."
        return None


__all__ = ["AutofillResult", "AutofillService"]
