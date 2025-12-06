import pytest

from validators import validate_risk_id


@pytest.mark.parametrize(
    "value,expected",
    [
        ("RSK-000123", None),
        ("riesgo libre", None),
    ],
)
def test_validate_risk_id_allows_flexible_inputs(value, expected):
    assert validate_risk_id(value) == expected


def test_validate_risk_id_rejects_blank_and_non_printable():
    assert validate_risk_id("") == "Debe ingresar el ID de riesgo."
    assert (
        validate_risk_id("ID\x00MAL")
        == "El ID de riesgo solo puede usar caracteres imprimibles."
    )


def test_validate_risk_id_rejects_overlong_values():
    long_value = "R" * 61
    assert (
        validate_risk_id(long_value)
        == "El ID de riesgo no puede tener más de 60 caracteres."
    )
