import tkinter as tk

import pytest

from app import FraudCaseApp


@pytest.fixture
def app_instance(monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter requiere una pantalla para esta prueba")
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)
    app = FraudCaseApp(root)
    app._suppress_messagebox = True
    try:
        yield app
    finally:
        root.destroy()


def _lookup_status(panel, origin_substring: str) -> str | None:
    for key, status in panel._entry_status.items():
        if origin_substring in key:
            return status
    return None


def test_date_validation_panel_recovers_after_autofill(app_instance):
    product = app_instance.product_frames[0]
    product.fecha_oc_var.set("2025-01-10")
    product.fecha_desc_var.set("2024-01-01")

    error = product.fecha_desc_validator.validate_callback()
    product.fecha_desc_validator.show_custom_error(error)
    app_instance.root.update_idletasks()

    assert _lookup_status(app_instance._validation_panel, "Fecha descubrimiento") == "error"

    product.fecha_oc_var.set("2024-01-01")
    product.fecha_desc_var.set("2024-01-02")
    product._refresh_date_validation_after_programmatic_update()
    app_instance.root.update_idletasks()

    assert _lookup_status(app_instance._validation_panel, "Fecha descubrimiento") == "ok"


def test_amount_validation_panel_recovers_after_paste(app_instance):
    product = app_instance.product_frames[0]
    product.monto_inv_var.set("100")
    product.monto_pago_var.set("150")

    error = product.monto_pago_validator.validate_callback()
    product.monto_pago_validator.show_custom_error(error)
    app_instance.root.update_idletasks()

    assert _lookup_status(app_instance._validation_panel, "Pago de deuda") == "error"

    product.monto_pago_var.set("80")
    try:
        product.pago_entry.event_generate("<<Paste>>")
    except tk.TclError:
        pass
    product._refresh_amount_validation_after_programmatic_update()
    app_instance.root.update_idletasks()

    assert _lookup_status(app_instance._validation_panel, "Pago de deuda") == "ok"
