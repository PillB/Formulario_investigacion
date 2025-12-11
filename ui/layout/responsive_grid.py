"""Helper to arrange label/input widgets responsively using grid."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Sequence

from ui.config import COL_PADX, ROW_PADY

WidgetPair = tuple[ttk.Widget, ttk.Widget]


def _get_width(widget: tk.Misc) -> int:
    """Return the current width for ``widget`` or its requested width."""

    try:
        width = widget.winfo_width()
    except Exception:
        width = 0

    if width <= 1:
        try:
            width = widget.winfo_reqwidth()
        except Exception:
            width = 0
    return width


def responsive_grid(parent: tk.Misc, widgets: Sequence[WidgetPair], max_width: int = 1000) -> None:
    """Arrange ``widgets`` responsively in the given ``parent``.

    Each element in ``widgets`` must be a ``(label, field)`` tuple. When the
    ``parent`` width is below ``max_width`` the tuples are stacked in a single
    column with the label on top of its corresponding field. For wider layouts
    the pairs are distributed across two columns, still keeping labels above
    their related fields for readability.
    """

    pending_attr = "_responsive_grid_pending"

    parent_width = _get_width(parent)
    if parent_width <= 1:
        scheduler = getattr(parent, "after_idle", None)
        if callable(scheduler) and not getattr(parent, pending_attr, False):
            setattr(parent, pending_attr, True)

            def _rerun():
                setattr(parent, pending_attr, False)
                responsive_grid(parent, widgets, max_width)

            try:
                scheduler(_rerun)
                return
            except Exception:
                setattr(parent, pending_attr, False)
        elif getattr(parent, pending_attr, False):
            return

    setattr(parent, pending_attr, False)

    two_column = parent_width >= max_width

    columns = 2 if two_column else 1
    for col in range(columns):
        parent.grid_columnconfigure(col, weight=1)

    for idx, (label, field) in enumerate(widgets):
        if two_column:
            base_row = (idx // 2) * 2
            column = idx % 2
        else:
            base_row = idx * 2
            column = 0

        label.grid(row=base_row, column=column, sticky="w", padx=COL_PADX, pady=(0, 2))
        field.grid(
            row=base_row + 1,
            column=column,
            sticky="ew",
            padx=COL_PADX,
            pady=(0, ROW_PADY),
        )

__all__ = ["responsive_grid"]
