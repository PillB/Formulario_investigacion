import tkinter as tk
from tkinter import ttk

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


def test_validation_panel_resizes_with_sash(app_instance):
    app = app_instance
    panel = app._validation_panel
    panes = getattr(app, "_content_panes", None)

    assert panes is not None
    assert panel in [app._validation_panel]

    panel.expand()
    app.root.update_idletasks()
    initial_width = panel.winfo_width()

    sash_position = panes.sashpos(0)
    panes.sashpos(0, sash_position + 180)
    app.root.update_idletasks()

    assert panel.winfo_width() > initial_width


def test_content_panes_initialized_without_unsupported_options(app_instance):
    panes = getattr(app_instance, "_content_panes", None)

    assert isinstance(panes, ttk.Panedwindow)

    pane_ids = panes.panes()
    assert len(pane_ids) == 2
    assert str(app_instance._validation_panel) in pane_ids
