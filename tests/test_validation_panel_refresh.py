from datetime import date, timedelta
from unittest.mock import Mock
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


def test_validation_panel_tracks_user_corrections(app_instance, monkeypatch):
    app = app_instance
    panel = app._validation_panel
    update_spy = Mock(wraps=panel.update_entry)
    monkeypatch.setattr(panel, "update_entry", update_spy)

    product = app.product_frames[0]
    future_date = (date.today() + timedelta(days=30)).isoformat()
    recent_date = (date.today() - timedelta(days=1)).isoformat()

    product.fecha_oc_var.set(future_date)
    product.fecha_desc_var.set(recent_date)
    product.monto_inv_var.set("100")
    product.monto_pago_var.set("150")

    for widget in (product.focc_entry, product.fdesc_entry, product.pago_entry):
        try:
            widget.event_generate("<FocusOut>")
        except tk.TclError:
            pass
    app.root.update()

    issue_label = panel._issue_count_var.get()
    assert issue_label.startswith("⚠️")
    assert int(issue_label.split()[1]) >= 2

    valid_occurrence = (date.today() - timedelta(days=3)).isoformat()
    valid_discovery = (date.today() - timedelta(days=2)).isoformat()
    product.fecha_oc_var.set(valid_occurrence)
    product.fecha_desc_var.set(valid_discovery)
    product.monto_inv_var.set("200")
    product.monto_perdida_var.set("100")
    product.monto_falla_var.set("50")
    product.monto_cont_var.set("50")
    product.monto_rec_var.set("0")
    product.monto_pago_var.set("150")

    for widget in (product.inv_entry, product.focc_entry, product.fdesc_entry, product.pago_entry):
        try:
            widget.event_generate("<FocusOut>")
        except tk.TclError:
            pass
    app.root.update()

    assert panel._issue_count_var.get() == "✅ 0"
    ok_origins = {
        "Producto 1 - Fecha ocurrencia",
        "Producto 1 - Fecha descubrimiento",
        "Producto 1 - Pago de deuda",
    }
    ok_updates = [
        call
        for call in update_spy.call_args_list
        if call.kwargs.get("origin") in ok_origins and call.kwargs.get("severity") == "ok"
    ]
    assert ok_updates
