import pytest

from app import FraudCaseApp


def test_client_action_bar_uses_inline_controls_only():
    assert FraudCaseApp.CLIENT_ACTION_BUTTONS == (("Agregar cliente", "add"),)


def test_product_action_bar_exposes_creation_only():
    labels = [label for label, _ in FraudCaseApp.PRODUCT_ACTION_BUTTONS]
    keys = [key for _, key in FraudCaseApp.PRODUCT_ACTION_BUTTONS]

    assert labels == ["Crear producto nuevo (vacío)", "Crear producto heredando del caso"]
    assert "edit" not in keys
    assert "delete" not in keys


@pytest.mark.parametrize(
    "deprecated_attribute",
    [
        "_edit_selected_client",
        "_remove_selected_client",
        "_focus_active_product",
        "_remove_active_product",
        "_remove_active_product_from_action",
        "_active_product_frame",
    ],
)
def test_outdated_action_helpers_removed(deprecated_attribute):
    assert not hasattr(FraudCaseApp, deprecated_attribute)
