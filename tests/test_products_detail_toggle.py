import os
import tkinter as tk

import pytest

from app import FraudCaseApp

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


def test_products_detail_toggle_updates_button_text():
    root, app = _build_app()
    try:
        assert app._products_detail_visible is True
        assert app.products_toggle_btn["text"] == "Ocultar formulario"

        app.hide_products_detail()
        assert app._products_detail_visible is False
        assert app.products_toggle_btn["text"] == "Mostrar formulario"

        app.show_products_detail()
        assert app._products_detail_visible is True
        assert app.products_toggle_btn["text"] == "Ocultar formulario"
    finally:
        root.destroy()


def test_first_product_add_shows_detail_when_hidden():
    root, app = _build_app()
    try:
        app.hide_products_detail()
        for frame in list(app.product_frames):
            app.remove_product(frame)

        assert not app.product_frames

        prod = app.add_product(initialize_rows=False)
        assert app._products_detail_visible is True
        assert app.products_toggle_btn["text"] == "Ocultar formulario"
        assert app.product_frames and app.product_frames[0] is prod
    finally:
        root.destroy()
