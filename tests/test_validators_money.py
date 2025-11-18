"""Regression tests for monetary validation rules."""

from decimal import Decimal

import pytest

from validators import validate_money_bounds


@pytest.mark.parametrize(
    "value,expected",
    [
        ("999999999999.99", Decimal("999999999999.99")),
        ("0.00", Decimal("0.00")),
    ],
)
def test_validate_money_bounds_allows_up_to_twelve_integer_digits(value, expected):
    error, amount = validate_money_bounds(value, "Monto")
    assert error is None
    assert amount == expected


def test_validate_money_bounds_rejects_more_than_twelve_integer_digits():
    error, amount = validate_money_bounds("1000000000000.00", "Monto")
    assert error is not None
    assert amount is None
    assert "12 dígitos" in error
