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
        catalog_entry, used_future_snapshot = self.catalog_service.lookup_team_member(
            identifier, case_date
        )
        if not catalog_entry:
            return AutofillResult(False, False, {})

        applied: Dict[str, str] = {}
        for key, current_value in current_values.items():
            if dirty_fields.get(key):
                continue
            value = (catalog_entry.get(key) or "").strip()
            if value and should_autofill_field(current_value, preserve_existing):
                applied[key] = value

        if used_future_snapshot:
            self.warning_handler(
                "La fecha de ocurrencia es anterior a la última actualización del colaborador; se usará el registro disponible más reciente."
            )
        return AutofillResult(True, used_future_snapshot, applied)


__all__ = ["AutofillResult", "AutofillService"]
