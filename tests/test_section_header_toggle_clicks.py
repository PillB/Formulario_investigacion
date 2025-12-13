import tkinter as tk

import pytest

from ui.frames.clients import ClientFrame
from ui.frames.norm import NormFrame
from ui.frames.products import ClaimRow, InvolvementRow, ProductFrame
from ui.frames.risk import RiskFrame
from ui.frames.team import TeamMemberFrame


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")
    yield root
    root.destroy()


def _make_tooltip():
    return lambda *_args, **_kwargs: None


def _client_section(root):
    frame = ClientFrame(
        tk.Frame(root),
        idx=0,
        remove_callback=lambda *_: None,
        update_client_options=lambda *_: None,
        logs=[],
        tooltip_register=_make_tooltip(),
    )
    return frame.section


def _product_section(root):
    owner = type(
        "_ProductSectionOwner",
        (),
        {
            "logs": [],
            "_sync_section_title": lambda self, *_args, **_kwargs: None,
        },
    )()
    return ProductFrame._create_section(owner, tk.Frame(root))


class _StubProductFrame:
    def __init__(self):
        self.idx = 0
        self.badges = None
        self.claim_fields_required = True

    def log_change(self, *_args, **_kwargs):
        return None

    def trigger_duplicate_check(self, *_, **__):
        return None

    def _schedule_product_summary_refresh(self, *_, **__):
        return None

    def _register_lookup_sync(self, *_args, **_kwargs):
        return None


def _involvement_section(root):
    product_frame = _StubProductFrame()
    row = InvolvementRow(
        tk.Frame(root),
        product_frame,
        idx=0,
        team_getter=lambda: [],
        remove_callback=lambda *_: None,
        logs=[],
        tooltip_register=_make_tooltip(),
    )
    return row.section


def _claim_section(root):
    product_frame = _StubProductFrame()
    row = ClaimRow(
        tk.Frame(root),
        product_frame,
        idx=0,
        remove_callback=lambda *_: None,
        logs=[],
        tooltip_register=_make_tooltip(),
    )
    return row.section


def _team_section(root):
    frame = TeamMemberFrame(
        tk.Frame(root),
        idx=0,
        remove_callback=lambda *_: None,
        update_team_options=lambda *_: None,
        team_lookup={},
        logs=[],
        tooltip_register=_make_tooltip(),
    )
    return frame.section


def _norm_section(root):
    frame = NormFrame(
        tk.Frame(root),
        idx=0,
        remove_callback=lambda *_: None,
        logs=[],
        tooltip_register=_make_tooltip(),
    )
    return frame.section


def _risk_section(root):
    frame = RiskFrame(
        tk.Frame(root),
        idx=0,
        remove_callback=lambda *_: None,
        logs=[],
        tooltip_register=_make_tooltip(),
    )
    return frame.section


@pytest.mark.parametrize(
    "section_builder",
    [
        _client_section,
        _product_section,
        _involvement_section,
        _claim_section,
        _team_section,
        _norm_section,
        _risk_section,
    ],
)
def test_header_click_toggles_sections(section_builder, tk_root):
    section = section_builder(tk_root)

    assert section.is_open is False

    section.toggle()
    assert section.is_open is True

    section.toggle()
    assert section.is_open is False
