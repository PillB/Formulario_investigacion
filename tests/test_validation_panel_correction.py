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


def test_correction_recreates_claim_row_without_losing_ui(app_instance):
    app = app_instance
    product = app.product_frames[0] if app.product_frames else app.add_product()
    claim = product.claims[0] if product.claims else product.add_claim()

    claim.id_var.set("C12345678")
    claim.name_var.set("Analítica de prueba")
    claim.code_var.set("4300000000")
    claim.frame.destroy()
    if claim in product.claims:
        product.claims.remove(claim)

    origin = f"Producto {product.idx+1} - Reclamo 1 ID"
    app._validation_panel.update_entry(
        "field:test-correction", "Dato faltante", severity="error", origin=origin, widget=claim.id_entry
    )

    app._validation_panel.focus_selected()

    refreshed_claim = product.claims[0]
    assert refreshed_claim.id_var.get() == ""
    assert refreshed_claim.name_var.get() == ""
    assert refreshed_claim.code_var.get() == ""
    assert refreshed_claim.id_entry.winfo_exists()
