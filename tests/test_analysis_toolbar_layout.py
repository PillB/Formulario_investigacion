import os

import tkinter as tk
from tkinter import ttk

import pytest

from app import FraudCaseApp

pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)


def _find_button_by_text(parent, text):
    for child in parent.winfo_children():
        if isinstance(child, ttk.Button) and child.cget("text") == text:
            return child
        nested = _find_button_by_text(child, text)
        if nested is not None:
            return nested
    return None


def test_auto_redact_button_uses_grid(messagebox_spy):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    try:
        app = FraudCaseApp(root)
        button = _find_button_by_text(app.root, "Auto-redactar")
        assert button is not None
        assert button.winfo_manager() == "grid"
    finally:
        root.destroy()
