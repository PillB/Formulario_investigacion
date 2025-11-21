"""Pruebas unitarias para el servicio de herencia de productos."""

import copy

from inheritance_service import InheritanceService
from settings import TAXONOMIA


def _base_case_state():
    cat1 = list(TAXONOMIA.keys())[0]
    cat2 = list(TAXONOMIA[cat1].keys())[0]
    modalidad = TAXONOMIA[cat1][cat2][0]
    return {
        "categoria_1_caso": cat1,
        "categoria_2_caso": cat2,
        "modalidad_caso": modalidad,
        "fecha_de_ocurrencia_caso": "2024-01-01",
        "fecha_de_descubrimiento_caso": "2024-01-10",
    }


def test_happy_path_inherits_all_fields():
    case_state = _base_case_state()

    result = InheritanceService.inherit_product_fields_from_case(case_state)

    assert result.values == {
        "categoria1": case_state["categoria_1_caso"],
        "categoria2": case_state["categoria_2_caso"],
        "modalidad": case_state["modalidad_caso"],
        "fecha_ocurrencia": case_state["fecha_de_ocurrencia_caso"],
        "fecha_descubrimiento": case_state["fecha_de_descubrimiento_caso"],
    }
    assert not result.has_missing
    assert not result.has_invalid


def test_partial_case_only_copies_available_fields():
    case_state = _base_case_state()
    case_state["fecha_de_descubrimiento_caso"] = ""
    case_state["modalidad_caso"] = ""

    result = InheritanceService.inherit_product_fields_from_case(case_state)

    assert "fecha_descubrimiento" not in result.values
    assert "modalidad" not in result.values
    assert result.values["categoria1"] == case_state["categoria_1_caso"]
    assert result.values["categoria2"] == case_state["categoria_2_caso"]
    assert result.has_missing
    assert not result.has_invalid


def test_invalid_dates_are_not_copied_and_flagged():
    case_state = _base_case_state()
    case_state["fecha_de_ocurrencia_caso"] = "2024-03-01"
    case_state["fecha_de_descubrimiento_caso"] = "2024-02-01"

    result = InheritanceService.inherit_product_fields_from_case(case_state)

    assert "fecha_ocurrencia" not in result.values
    assert "fecha_descubrimiento" not in result.values
    assert result.has_invalid
    assert {"fecha_ocurrencia", "fecha_descubrimiento"} <= result.invalid_fields


def test_inheritance_creates_snapshot_not_reference():
    case_state = _base_case_state()

    result = InheritanceService.inherit_product_fields_from_case(case_state)
    copied_values = copy.deepcopy(result.values)

    case_state["categoria_1_caso"] = "otro valor"
    case_state["fecha_de_ocurrencia_caso"] = "2030-01-01"

    assert result.values == copied_values
