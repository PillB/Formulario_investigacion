"""Componentes reutilizables de la interfaz (tooltips)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class HoverTooltip:
    """Muestra mensajes contextuales cuando el cursor pasa sobre un widget."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 300) -> None:
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow = None
        self.after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)
        widget.bind("<Destroy>", self._on_destroy)

    def _schedule(self, _event=None):
        self._cancel()
        self.after_id = self.widget.after(self.delay, self.show)

    def _cancel(self):
        if self.after_id is not None:
            try:
                self.widget.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None

    def show(self):
        if self.tipwindow or not self.text:
            return
        try:
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        except tk.TclError:
            return
        self.tipwindow = tk.Toplevel(self.widget)
        self.tipwindow.wm_overrideredirect(True)
        self.tipwindow.configure(bg="#333333")
        label = tk.Label(
            self.tipwindow,
            text=self.text,
            justify="left",
            background="#333333",
            foreground="#ffffff",
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=3,
            wraplength=280,
        )
        label.pack()
        self.tipwindow.wm_geometry(f"+{x}+{y}")

    def _hide(self, _event=None):
        self._cancel()
        if self.tipwindow is not None:
            try:
                self.tipwindow.destroy()
            except tk.TclError:
                pass
            self.tipwindow = None

    def _on_destroy(self, _event=None):
        self._hide()


class ValidationTooltip:
    """Muestra mensajes de error en rojo debajo del widget asociado."""

    def __init__(self, widget: tk.Widget) -> None:
        self.widget = widget
        self.tipwindow = None
        widget.bind("<Destroy>", self._on_destroy)

    def show(self, text: str) -> None:
        if not text:
            self.hide()
            return
        self.hide()
        try:
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        except tk.TclError:
            return
        self.tipwindow = tk.Toplevel(self.widget)
        self.tipwindow.wm_overrideredirect(True)
        self.tipwindow.configure(bg="#8B0000")
        label = tk.Label(
            self.tipwindow,
            text=text,
            justify="left",
            background="#8B0000",
            foreground="#ffffff",
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=3,
            wraplength=320,
        )
        label.pack()
        self.tipwindow.wm_geometry(f"+{x}+{y}")

    def hide(self):
        if self.tipwindow is not None:
            try:
                self.tipwindow.destroy()
            except tk.TclError:
                pass
            self.tipwindow = None

    def _on_destroy(self, _event=None):
        self.hide()


__all__ = ["HoverTooltip", "ValidationTooltip"]
