from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Mapping

from validators import parse_decimal_amount

AMOUNT_FIELD_MAP: tuple[tuple[str, str], ...] = (
    ("investigado", "monto_investigado"),
    ("perdida_fraude", "monto_perdida_fraude"),
    ("falla_procesos", "monto_falla_procesos"),
    ("contingencia", "monto_contingencia"),
    ("recuperado", "monto_recuperado"),
    ("pago_deuda", "monto_pago_deuda"),
)


def aggregate_product_amounts(products: Iterable[Mapping[str, object]] | None) -> dict[str, Decimal]:
    """Suma los montos de productos con salida normalizada por clave de negocio."""
    totals = {key: Decimal("0") for key, _ in AMOUNT_FIELD_MAP}
    for product in products or []:
        if not isinstance(product, Mapping):
            continue
        for total_key, field_name in AMOUNT_FIELD_MAP:
            amount = parse_decimal_amount(product.get(field_name))
            if amount is not None:
                totals[total_key] += amount
    return totals

