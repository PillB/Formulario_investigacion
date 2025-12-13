import os
import tkinter as tk

import pytest

from ui.frames.clients import ClientFrame
from ui.frames.products import ProductFrame
from ui.frames.team import TeamMemberFrame


pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)


def _build_root():
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")
    return root


def test_client_section_starts_closed_and_opens_on_toggle():
    root = _build_root()
    try:
        frame = ClientFrame(
            tk.Frame(root),
            idx=0,
            remove_callback=lambda *_: None,
            update_client_options=lambda *_: None,
            logs=[],
            tooltip_register=lambda *_1, **_2: None,
        )

        assert frame.section.is_open is False

        frame.section.toggle()

        assert frame.section.is_open is True
    finally:
        root.destroy()


def test_team_section_starts_closed_and_opens_on_toggle():
    root = _build_root()
    try:
        frame = TeamMemberFrame(
            tk.Frame(root),
            idx=0,
            remove_callback=lambda *_: None,
            update_team_options=lambda *_: None,
            team_lookup={},
            logs=[],
            tooltip_register=lambda *_1, **_2: None,
        )

        assert frame.section.is_open is False

        frame.section.toggle()

        assert frame.section.is_open is True
    finally:
        root.destroy()


def test_product_section_starts_closed_and_opens_on_toggle():
    root = _build_root()
    try:
        frame = ProductFrame(
            tk.Frame(root),
            idx=0,
            remove_callback=lambda *_: None,
            get_client_options=lambda: [],
            get_team_options=lambda: [],
            logs=[],
            product_lookup={},
            tooltip_register=lambda *_1, **_2: None,
            initialize_rows=False,
        )

        assert frame.section.is_open is False

        frame.section.toggle()

        assert frame.section.is_open is True
    finally:
        root.destroy()
