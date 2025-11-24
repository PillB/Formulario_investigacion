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
    """Permite desplazar el canvas usando la rueda del ratón o trackpad.

    Además de enlazar los eventos con el propio canvas y el frame interno,
    se registran los widgets hijos (como ``ttk.Treeview``) para que el
    desplazamiento funcione sin importar el widget que tenga el foco del ratón.
    """

    is_active = {"value": False}
    bound_widgets: set[int] = set()

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

    def _bind_widget(widget):
        if widget is None:
            return
        widget_id = id(widget)
        if widget_id in bound_widgets:
            return
        bound_widgets.add(widget_id)
        widget.bind("<Enter>", _activate, add="+")
        widget.bind("<Leave>", _deactivate, add="+")
        widget.bind("<MouseWheel>", _on_mousewheel, add="+")
        widget.bind("<Button-4>", _on_mousewheel, add="+")
        widget.bind("<Button-5>", _on_mousewheel, add="+")
        children_fn = getattr(widget, "winfo_children", None)
        if callable(children_fn):
            for child in children_fn():
                _bind_widget(child)

    def _sync_children(_event=None):  # noqa: ANN001
        _bind_widget(target)

    _bind_widget(canvas)
    _bind_widget(target)
    target.bind("<Configure>", _sync_children, add="+")
