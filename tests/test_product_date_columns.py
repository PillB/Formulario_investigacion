"""Layout safeguards for ProductFrame date fields."""

import os
import tkinter as tk
import tkinter.font as tkfont

import pytest

from ui.config import COL_PADX
from ui.frames.products import ProductFrame


pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)


@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


def _build_product(root):
    return ProductFrame(
        parent=root,
        idx=0,
        remove_callback=lambda *_args, **_kwargs: None,
        get_client_options=lambda: ["CL1"],
        get_team_options=lambda: ["T12345"],
        logs=[],
        product_lookup={},
        tooltip_register=lambda *_args, **_kwargs: None,
        initialize_rows=False,
    )


def test_date_columns_reserve_space_for_labels_and_entries(tk_root):
    product = _build_product(tk_root)
    tk_root.update_idletasks()

    font = tkfont.nametofont("TkDefaultFont")
    required_width = max(
        font.measure("0" * 12),
        font.measure("Fecha de ocurrencia:"),
        font.measure("Fecha de descubrimiento:"),
        font.measure("(YYYY-MM-DD)"),
    ) + COL_PADX

    for column in range(4):
        config = product.frame.grid_columnconfigure(column)
        assert config["minsize"] >= required_width


def test_badges_do_not_shrink_date_entries(tk_root):
    product = _build_product(tk_root)

    product.fecha_oc_var.set("2030-01-01")
    product.fecha_desc_var.set("2029-01-01")
    product.fecha_oc_validator.validate_callback()
    product.fecha_desc_validator.validate_callback()

    tk_root.update_idletasks()

    font = tkfont.nametofont("TkDefaultFont")
    min_pixel_width = font.measure("0" * 12)

    for entry in (product.focc_entry, product.fdesc_entry):
        assert entry.winfo_width() >= min_pixel_width

    for badge_column in (4, 5):
        config = product.frame.grid_columnconfigure(badge_column)
        assert config["weight"] == 0
