"""Utilidades de soporte para marcos Tkinter en entornos de prueba sin grid."""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk
from typing import Any, Tuple


def ensure_grid_support(widget: Any) -> None:
    """Garantiza que el widget exponga un método grid, incluso si solo soporta pack.

    Algunos stubs de pruebas no implementan ``grid``. En esos casos se expone un
    proxy que delega en ``pack`` con los argumentos de relleno disponibles para
    evitar errores durante la construcción de la interfaz.
    """
    if widget is None or hasattr(widget, "grid"):
        return

    pack_fn = getattr(widget, "pack", None)
    if not callable(pack_fn):
        return

    def _grid_proxy(self, *args, **kwargs):  # noqa: ANN001
        pack_kwargs = {k: kwargs.get(k) for k in ("padx", "pady") if kwargs.get(k) is not None}
        self.pack(**pack_kwargs)

    setattr(widget.__class__, "grid", _grid_proxy)


def create_scrollable_container(parent: Any) -> Tuple[ttk.Frame, ttk.Frame]:
    """Crea un contenedor desplazable con soporte para trackpad y mouse wheel.

    El contenedor externo incluye un ``Canvas`` con su respectiva barra de
    desplazamiento vertical.  Dentro del canvas se ubica un frame interior donde
    se pueden agregar widgets utilizando ``pack`` o ``grid``.  El desplazamiento
    se habilita tanto con la rueda del ratón como con gestos de trackpad para
    mejorar la navegación de formularios largos.
    """

    outer = ttk.Frame(parent)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(0, weight=1)

    canvas = tk.Canvas(outer, highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    inner = ttk.Frame(canvas)
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _configure_canvas(_event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _resize_inner(event):
        canvas.itemconfigure(window_id, width=event.width)

    inner.bind("<Configure>", _configure_canvas)
    canvas.bind("<Configure>", _resize_inner)

    _enable_mousewheel_scrolling(canvas, inner)

    return outer, inner


def _enable_mousewheel_scrolling(canvas: tk.Canvas, target: ttk.Frame) -> None:
    """Permite desplazar el canvas usando la rueda del ratón o trackpad."""

    is_active = {"value": False}

    def _activate(_event):
        is_active["value"] = True

    def _deactivate(_event):
        is_active["value"] = False

    def _on_mousewheel(event):  # noqa: ANN001
        if not is_active["value"]:
            return
        delta = event.delta
        if delta == 0 and hasattr(event, "num"):
            delta = 120 if event.num == 4 else -120
        if not delta:
            return
        direction = -1 if delta > 0 else 1
        magnitude = abs(delta)
        steps = direction * max(1, math.ceil(magnitude / 120))
        if steps:
            canvas.yview_scroll(steps, "units")
            return "break"

    for widget in (canvas, target):
        widget.bind("<Enter>", _activate, add="+")
        widget.bind("<Leave>", _deactivate, add="+")
    canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")
    canvas.bind_all("<Button-4>", _on_mousewheel, add="+")
    canvas.bind_all("<Button-5>", _on_mousewheel, add="+")
