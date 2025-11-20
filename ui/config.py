"""Configuración compartida de estilo y espaciados para la interfaz."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

FONT_BASE = ("TkDefaultFont", 11)
FONT_HEADER = ("TkHeadingFont", 12, "bold")
ROW_PADY = 6
COL_PADX = 8


def init_styles(root: tk.Misc) -> ttk.Style:
    """Inicializa los estilos ttk para usar fuentes y rellenos consistentes."""
    style = ttk.Style(root)
    style.configure("TLabel", font=FONT_BASE, padding=(2, 2))
    style.configure("TEntry", font=FONT_BASE, padding=(6, 6))
    style.configure("TCombobox", font=FONT_BASE, padding=(6, 6))
    style.configure("TButton", font=FONT_BASE, padding=(8, 6))
    style.configure("TLabelframe.Label", font=FONT_HEADER)
    return style
