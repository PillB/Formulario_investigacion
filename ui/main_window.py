"""Helpers for the main application window and navigation notebook."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from theme_manager import reapply_all_badges


def bind_notebook_refresh_handlers(root: tk.Misc, notebook: ttk.Notebook) -> None:
    """Bind refresh tasks to the main notebook tab change event.

    All tab frames are created during startup so this handler only refreshes the
    layout and badge styling without deferring widget creation to the tab change
    event.
    """

    if root is None or notebook is None:
        return

    def _on_tab_changed(event) -> None:
        if event.widget is not notebook:
            return

        # Avoid triggering a full geometry recalculation; badges already handle
        # visual refresh so we only schedule a minimal idle callback.
        try:
            root.after_idle(lambda: None)
        except tk.TclError:
            pass

        reapply_all_badges()

    notebook.bind("<<NotebookTabChanged>>", _on_tab_changed, add="+")


__all__ = ["bind_notebook_refresh_handlers"]
