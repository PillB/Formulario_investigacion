from types import SimpleNamespace

import pytest

from ui.frames import products
from tests import test_products_frame as tpf


class FocusDummyWidget(tpf.DummyWidget):
    def bind_all(self, sequence, callback, add=None):
        return self.bind(sequence, callback, add)


@pytest.fixture(autouse=True)
def patch_tk_components(monkeypatch):
    monkeypatch.setattr(products.tk, "StringVar", tpf.DummyVar)
    monkeypatch.setattr(products.ttk, "LabelFrame", FocusDummyWidget)
    monkeypatch.setattr(products.ttk, "Frame", FocusDummyWidget)
    monkeypatch.setattr(products.ttk, "Label", FocusDummyWidget)
    monkeypatch.setattr(products.ttk, "Entry", FocusDummyWidget)
    monkeypatch.setattr(products.ttk, "Combobox", FocusDummyWidget)
    monkeypatch.setattr(products.ttk, "Button", FocusDummyWidget)
    monkeypatch.setattr(products.ttk, "Scrollbar", FocusDummyWidget)
    monkeypatch.setattr(products.ttk, "Treeview", None)
    tpf.RecordingValidator.instances.clear()
    monkeypatch.setattr(products, "FieldValidator", tpf.RecordingValidator)
    yield
    tpf.RecordingValidator.instances.clear()


def _build_owner():
    return SimpleNamespace(inline_summary_trees={}, product_summary_tree=None)


def _build_product_frame(idx=0, owner=None, product_lookup=None):
    return products.ProductFrame(
        parent=FocusDummyWidget(),
        idx=idx,
        remove_callback=lambda _frame: None,
        get_client_options=lambda: ["CL1"],
        get_team_options=lambda: ["T12345"],
        logs=[],
        product_lookup=product_lookup or {},
        tooltip_register=lambda *_args, **_kwargs: None,
        claim_lookup={},
        initialize_rows=False,
        owner=owner,
        summary_parent=FocusDummyWidget(),
    )


def test_product_frame_sets_summary_owner_on_creation_and_open_toggle():
    owner = _build_owner()
    product = _build_product_frame(owner=owner)

    assert owner._product_summary_owner is product

    owner._product_summary_owner = None
    product.section.is_open = False
    product.section.toggle(None)

    assert owner._product_summary_owner is product


def test_tree_selection_targets_focused_product_without_id_focus(monkeypatch):
    owner = _build_owner()
    product_lookup = {
        "P1": {
            "id_cliente": "CL1",
            "tipo_producto": "Tipo1",
            "canal": "Canal1",
            "fecha_ocurrencia": "2023-01-01",
        },
        "P2": {
            "id_cliente": "CL2",
            "tipo_producto": "Tipo2",
            "canal": "Canal2",
            "fecha_ocurrencia": "2023-02-01",
        },
    }

    product_a = _build_product_frame(idx=0, owner=owner, product_lookup=product_lookup)
    product_b = _build_product_frame(idx=1, owner=owner, product_lookup=product_lookup)

    assert owner.product_summary_tree is product_a.header_tree
    assert product_b.header_tree is owner.product_summary_tree

    owner._product_summary_owner = product_a
    focus_callback = next(
        cb for seq, cb, _add in product_b.client_cb._bindings if seq == "<FocusIn>"
    )
    focus_callback(SimpleNamespace(widget=product_b.client_cb))

    assert owner._product_summary_owner is product_b

    tree = owner.product_summary_tree
    tree.selection = lambda: ("P2",)
    product_a._on_tree_select()
    assert product_b.id_var.get() == "P2"

    product_b.id_var.set("")
    tree.selection = lambda: ("P1",)
    product_b._on_tree_double_click()
    assert product_b.id_var.get() == "P1"
