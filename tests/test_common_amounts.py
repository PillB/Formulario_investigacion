from decimal import Decimal

from report.common_amounts import aggregate_product_amounts


def test_aggregate_product_amounts_with_complete_products():
    products = [
        {
            "monto_investigado": "100.50",
            "monto_perdida_fraude": "10.00",
            "monto_falla_procesos": "20.25",
            "monto_contingencia": "30.00",
            "monto_recuperado": "5.15",
            "monto_pago_deuda": "1.10",
        },
        {
            "monto_investigado": "50",
            "monto_perdida_fraude": "0.75",
            "monto_falla_procesos": "1.00",
            "monto_contingencia": "2",
            "monto_recuperado": "0.35",
            "monto_pago_deuda": "3.90",
        },
    ]

    assert aggregate_product_amounts(products) == {
        "investigado": Decimal("150.50"),
        "perdida_fraude": Decimal("10.75"),
        "falla_procesos": Decimal("21.25"),
        "contingencia": Decimal("32.00"),
        "recuperado": Decimal("5.50"),
        "pago_deuda": Decimal("5.00"),
    }


def test_aggregate_product_amounts_with_partial_products():
    products = [
        {
            "monto_investigado": "100",
            "monto_perdida_fraude": "",
            "monto_falla_procesos": None,
            "monto_contingencia": "invalido",
            "monto_recuperado": "4.50",
        },
        {"monto_pago_deuda": "3.25", "monto_recuperado": "0.50"},
        "fila-invalida",
    ]

    assert aggregate_product_amounts(products) == {
        "investigado": Decimal("100"),
        "perdida_fraude": Decimal("0"),
        "falla_procesos": Decimal("0"),
        "contingencia": Decimal("0"),
        "recuperado": Decimal("5.00"),
        "pago_deuda": Decimal("3.25"),
    }


def test_aggregate_product_amounts_with_empty_or_none_products():
    expected = {
        "investigado": Decimal("0"),
        "perdida_fraude": Decimal("0"),
        "falla_procesos": Decimal("0"),
        "contingencia": Decimal("0"),
        "recuperado": Decimal("0"),
        "pago_deuda": Decimal("0"),
    }

    assert aggregate_product_amounts([]) == expected
    assert aggregate_product_amounts(None) == expected
