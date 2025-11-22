import os
import tkinter as tk
import pytest

from app import FraudCaseApp
from settings import FLAG_CLIENTE_LIST, TIPO_ID_LIST, TIPO_PRODUCTO_LIST


def _force_user_validation(widget):
    widget.event_generate("<KeyRelease>")
    widget.event_generate("<FocusOut>")


pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)


def _build_app():
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")
    return root, FraudCaseApp(root)


def test_real_gui_post_edit_validations_and_claim_requirements(messagebox_spy):
    root, app = _build_app()
    try:
        occ_validator = next(
            v for v in app.validators if "Caso - Fecha de ocurrencia" in v.field_name
        )
        disc_validator = next(
            v for v in app.validators if "Caso - Fecha de descubrimiento" in v.field_name
        )

        app.fecha_caso_var.set("2099-01-01")
        _force_user_validation(occ_validator.widget)
        assert any("no puede estar en el futuro" in error for _title, error in messagebox_spy.errors)

        app.fecha_caso_var.set("2024-01-02")
        app.fecha_descubrimiento_caso_var.set("2024-01-01")
        _force_user_validation(disc_validator.widget)
        assert any("posterior" in error for _title, error in messagebox_spy.errors)

        app.fecha_descubrimiento_caso_var.set("2024-01-05")
        _force_user_validation(occ_validator.widget)
        _force_user_validation(disc_validator.widget)
        assert occ_validator.last_error is None
        assert disc_validator.last_error is None

        client = app.client_frames[0]
        client.tipo_id_var.set(TIPO_ID_LIST[0])
        client.id_var.set("12345678")
        _force_user_validation(client.validators[0].widget)
        client.nombres_var.set("Nombre")
        client.apellidos_var.set("Apellido")
        client.flag_var.set(FLAG_CLIENTE_LIST[0])
        _force_user_validation(client.validators[1].widget)

        product = app.product_frames[0]
        product.tipo_prod_var.set(
            next((p for p in TIPO_PRODUCTO_LIST if "crédito" in p.lower()), TIPO_PRODUCTO_LIST[0])
        )
        product.id_var.set("PROD001")
        product.client_var.set(client.id_var.get())
        product.fecha_oc_var.set("2024-01-10")
        product.fecha_desc_var.set("2024-01-11")

        product.monto_inv_var.set("100")
        product.monto_perdida_var.set("10")
        product.monto_falla_var.set("5")
        product.monto_cont_var.set("0")
        product.monto_rec_var.set("0")
        product.monto_pago_var.set("120")

        consistency_validator = next(
            v
            for v in product.validators
            if "Consistencia de montos (Monto investigado)" in v.field_name
        )
        contingency_validator = next(
            v
            for v in product.validators
            if "Consistencia de montos (Monto contingencia)" in v.field_name
        )

        _force_user_validation(consistency_validator.widget)
        _force_user_validation(contingency_validator.widget)
        assert any("monto investigado" in error for _title, error in messagebox_spy.errors)
        assert any("contingencia" in error for _title, error in messagebox_spy.errors)

        claim_validator = product.claims[0].validators[0]
        _force_user_validation(claim_validator.widget)
        assert any("reclamo" in error.lower() for _title, error in messagebox_spy.errors)

        product.monto_cont_var.set("100")
        product.monto_perdida_var.set("0")
        product.monto_falla_var.set("0")
        product.monto_rec_var.set("0")
        product.monto_pago_var.set("80")

        _force_user_validation(consistency_validator.widget)
        _force_user_validation(contingency_validator.widget)
        assert consistency_validator.last_error is None
        assert contingency_validator.last_error is None

        product.claims[0].id_var.set("C12345678")
        _force_user_validation(claim_validator.widget)
        assert claim_validator.last_error is None
    finally:
        root.destroy()


def test_duplicate_prevention_and_header_autosave(messagebox_spy):
    root, app = _build_app()
    try:
        app.id_caso_var.set("2024-0001")
        id_validator = next(v for v in app.validators if "Número de caso" in v.field_name)
        _force_user_validation(id_validator.widget)

        client = app.client_frames[0]
        client.tipo_id_var.set(TIPO_ID_LIST[0])
        client.id_var.set("87654321")
        _force_user_validation(client.validators[0].widget)
        client.nombres_var.set("Jane")
        client.apellidos_var.set("Doe")
        client.flag_var.set(FLAG_CLIENTE_LIST[0])
        _force_user_validation(client.validators[1].widget)

        base_product = app.product_frames[0]
        base_product.id_var.set("P-001")
        base_product.client_var.set(client.id_var.get())
        base_product.fecha_oc_var.set("2024-03-01")
        base_product.fecha_desc_var.set("2024-03-02")
        _force_user_validation(base_product.validators[0].widget)
        _force_user_validation(
            next(v for v in base_product.validators if "Fecha ocurrencia" in v.field_name).widget
        )

        duplicate = app.add_product(initialize_rows=True)
        duplicate.id_var.set(base_product.id_var.get())
        duplicate.client_var.set(client.id_var.get())
        duplicate.fecha_oc_var.set(base_product.fecha_oc_var.get())
        duplicate.fecha_desc_var.set(base_product.fecha_desc_var.get())
        _force_user_validation(
            next(v for v in duplicate.validators if "Fecha ocurrencia" in v.field_name).widget
        )
        _force_user_validation(duplicate.validators[0].widget)

        assert any("Registro duplicado" in title for title, _msg in messagebox_spy.errors)

        app._autosave_dirty = False
        cost_center_validator = next(
            v for v in app._post_edit_validators if v.field_label == "Centro de costos"
        )
        app._encabezado_vars["centro_costos"].set("12; ABC")
        _force_user_validation(cost_center_validator.widget)
        assert any("costos" in error for _title, error in messagebox_spy.errors)

        app._encabezado_vars["centro_costos"].set("12345;67890")
        _force_user_validation(cost_center_validator.widget)
        assert app._encabezado_data["centro_costos"] == "12345; 67890"
        assert app._autosave_dirty is True
    finally:
        root.destroy()
