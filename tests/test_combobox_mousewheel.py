import os
import tkinter as tk
from tkinter import ttk

import pytest

from theme_manager import ThemeManager


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)
def test_combobox_mousewheel_does_not_change_value():
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    try:
        previous_bound = ThemeManager._combobox_scroll_bound_root
        ThemeManager.build_style(root)
        windowing_system = root.tk.call("tk", "windowingsystem")
        if windowing_system in ("win32", "aqua"):
            sequence = "<MouseWheel>"
            event_kwargs = {"delta": -120}
        elif windowing_system == "x11":
            sequence = "<Button-4>"
            event_kwargs = {}
        else:
            pytest.skip("Sistema de ventanas no soportado en el entorno de pruebas")

        combobox = ttk.Combobox(root, values=("uno", "dos", "tres"), state="readonly")
        combobox.current(0)
        combobox.focus_set()
        root.update_idletasks()

        previous_value = combobox.get()
        combobox.event_generate(sequence, **event_kwargs)
        root.update()

        assert combobox.get() == previous_value
    finally:
        ThemeManager._combobox_scroll_bound_root = previous_bound
        root.destroy()
