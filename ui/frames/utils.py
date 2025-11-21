"""Utilidades de soporte para marcos Tkinter en entornos de prueba sin grid."""
from __future__ import annotations

from typing import Any


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
