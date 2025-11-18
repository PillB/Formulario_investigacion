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
    error, amount, normalized = validate_money_bounds(value, "Monto")
    assert error is None
    assert amount == expected
    assert normalized == f"{expected:.2f}"


def test_validate_money_bounds_rejects_more_than_twelve_integer_digits():
    error, amount, normalized = validate_money_bounds("1000000000000.00", "Monto")
    assert error is not None
    assert amount is None
    assert "12 dígitos" in error
    assert normalized == ""


@pytest.mark.parametrize("value", ["100", "100.5", "0", "2500.0"])
def test_validate_money_bounds_rejects_missing_decimal_places(value):
    error, amount, normalized = validate_money_bounds(value, "Monto")
    assert error == "Monto debe tener dos decimales exactos."
    assert amount is None
    assert normalized == ""


@pytest.mark.parametrize("value", ["0.00", "10.50", "999999999999.99"])
def test_validate_money_bounds_accepts_exact_two_decimals(value):
    error, amount, normalized = validate_money_bounds(value, "Monto")
    assert error is None
    assert normalized == value
    assert f"{amount:.2f}" == value


def test_validate_money_bounds_rejects_more_than_two_decimal_places():
    error, amount, normalized = validate_money_bounds("1.234", "Monto")
    assert error is not None
    assert "dos decimales" in error
    assert amount is None
    assert normalized == ""
