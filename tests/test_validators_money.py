"""Regression tests for monetary validation rules."""

from decimal import Decimal

import pytest

from validators import validate_money_bounds


@pytest.mark.parametrize(
    "value,expected",
    [
        ("999999999999.99", Decimal("999999999999.99")),
        ("999999999999.9", Decimal("999999999999.90")),
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


def test_validate_money_bounds_rejects_scientific_notation_over_limit():
    error, amount, normalized = validate_money_bounds("1e12", "Monto")
    assert error is not None
    assert amount is None
    assert "12 dígitos" in error
    assert normalized == ""


@pytest.mark.parametrize(
    "value,expected_decimal,expected_normalized",
    [
        ("100", Decimal("100.00"), "100.00"),
        ("100.5", Decimal("100.50"), "100.50"),
        ("0", Decimal("0.00"), "0.00"),
        ("2500.0", Decimal("2500.00"), "2500.00"),
    ],
)
def test_validate_money_bounds_quantizes_inputs_with_less_than_two_decimals(
    value, expected_decimal, expected_normalized
):
    error, amount, normalized = validate_money_bounds(value, "Monto")
    assert error is None
    assert amount == expected_decimal
    assert normalized == expected_normalized


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
