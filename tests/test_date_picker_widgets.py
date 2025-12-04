"""Garantiza que los campos de fecha utilicen el selector de calendario."""

import os
import tkinter as tk
from datetime import date

import pytest
from tkcalendar import DateEntry

from settings import TAXONOMIA
from ui.frames.case import CaseFrame
from ui.frames.norm import NormFrame
from ui.frames.products import ProductFrame
from ui.frames.team import TeamMemberFrame
from ui.frames.utils import create_date_entry


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


class _CaseOwnerStub:
    def __init__(self, root):
        self.logs = []
        self.validators = []
        self.register_tooltip = lambda *_args, **_kwargs: None
        default_cat1 = list(TAXONOMIA.keys())[0] if TAXONOMIA else ""
        default_cat2 = list(TAXONOMIA.get(default_cat1, {}).keys())[0] if default_cat1 else ""
        self.id_caso_var = tk.StringVar(master=root)
        self.tipo_informe_var = tk.StringVar(master=root)
        self.cat_caso1_var = tk.StringVar(master=root, value=default_cat1)
        self.cat_caso2_var = tk.StringVar(master=root, value=default_cat2)
        self.mod_caso_var = tk.StringVar(master=root)
        self.canal_caso_var = tk.StringVar(master=root)
        self.proceso_caso_var = tk.StringVar(master=root)
        self.investigator_id_var = tk.StringVar(master=root)
        self.investigator_nombre_var = tk.StringVar(master=root)
        self.investigator_cargo_var = tk.StringVar(master=root)
        self.fecha_caso_var = tk.StringVar(master=root)
        self.fecha_descubrimiento_caso_var = tk.StringVar(master=root)
        self.centro_costo_caso_var = tk.StringVar(master=root)
        self._case_inputs = {}

    def on_case_cat1_change(self):
        return None

    def on_case_cat2_change(self):
        return None

    def _autofill_investigator(self, show_errors=False):
        del show_errors
        return None

    def _validate_case_occurrence_date(self):
        return None

    def _validate_case_discovery_date(self):
        return None

    def _validate_cost_centers(self, text=""):
        del text
        return None


@pytest.fixture
def product_frame(tk_root):
    return ProductFrame(
        parent=tk_root,
        idx=0,
        remove_callback=lambda *_args, **_kwargs: None,
        get_client_options=lambda: ["CL1"],
        get_team_options=lambda: ["T12345"],
        logs=[],
        product_lookup={},
        tooltip_register=lambda *_args, **_kwargs: None,
        initialize_rows=False,
    )


@pytest.fixture
def team_frame(tk_root):
    return TeamMemberFrame(
        parent=tk_root,
        idx=0,
        remove_callback=lambda *_args, **_kwargs: None,
        update_team_options=lambda *_args, **_kwargs: None,
        team_lookup={},
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
    )


def test_create_date_entry_uses_calendar_when_available(tk_root):
    var = tk.StringVar(master=tk_root)
    widget = create_date_entry(tk_root, textvariable=var)

    widget.set_date(date(2024, 1, 2))
    widget.event_generate("<<DateEntrySelected>>")

    assert isinstance(widget, DateEntry)
    assert var.get() == "2024-01-02"


def test_case_frame_date_fields_use_date_entry(tk_root):
    owner = _CaseOwnerStub(tk_root)
    frame = CaseFrame(owner, tk_root)
    tk_root.update_idletasks()

    assert isinstance(owner._case_inputs["fecha_case_entry"], DateEntry)
    assert isinstance(owner._case_inputs["fecha_desc_entry"], DateEntry)
    assert frame is not None


def test_product_frame_date_fields_use_date_entry(product_frame, tk_root):
    tk_root.update_idletasks()

    assert isinstance(product_frame.focc_entry, DateEntry)
    assert isinstance(product_frame.fdesc_entry, DateEntry)


def test_team_frame_date_fields_use_date_entry(team_frame, tk_root):
    tk_root.update_idletasks()

    assert isinstance(team_frame.fecha_inm_entry, DateEntry)
    assert isinstance(team_frame.fecha_ren_entry, DateEntry)


def test_norm_frame_date_field_uses_date_entry(tk_root):
    norm_frame = NormFrame(
        parent=tk_root,
        idx=0,
        remove_callback=lambda *_args, **_kwargs: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
    )
    tk_root.update_idletasks()

    assert isinstance(norm_frame.fecha_entry, DateEntry)
