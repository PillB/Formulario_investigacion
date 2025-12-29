"""Ensure validation badge state changes do not shift entry geometry."""

import os
import tkinter as tk

import pytest

from validation_badge import ValidationBadge


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


def _assert_geometry_stable(widget, base_geometry, *, tolerance=1):
    width, height = base_geometry
    assert abs(widget.winfo_width() - width) <= tolerance
    assert abs(widget.winfo_height() - height) <= tolerance


def test_validation_badge_state_changes_keep_entry_geometry(tk_root):
    frame = tk.Frame(tk_root)
    frame.grid(row=0, column=0, padx=10, pady=10)

    entry = tk.Entry(frame)
    entry.grid(row=0, column=0, padx=5, pady=5, sticky="w")

    badge = ValidationBadge(frame, preview_lines=1)
    badge.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    badge.set_neutral("Pendiente")
    tk_root.update_idletasks()

    base_entry_geometry = (entry.winfo_width(), entry.winfo_height())
    base_frame_geometry = (frame.winfo_width(), frame.winfo_height())

    badge.set_warning(
        "Se requiere una explicación extensa para validar correctamente el campo."
    )
    tk_root.update_idletasks()

    _assert_geometry_stable(entry, base_entry_geometry)
    _assert_geometry_stable(frame, base_frame_geometry)

    badge.set_success("Listo")
    tk_root.update_idletasks()

    _assert_geometry_stable(entry, base_entry_geometry)
    _assert_geometry_stable(frame, base_frame_geometry)
