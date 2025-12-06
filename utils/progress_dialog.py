from __future__ import annotations

from queue import SimpleQueue
from typing import Callable, Optional

import tkinter as tk
from tkinter import ttk


class ProgressDialog:
    """Muestra el avance de una tarea en segundo plano sin bloquear la UI."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        *,
        on_cancel: Optional[Callable[[], None]] = None,
        poll_interval_ms: int = 50,
    ) -> None:
        self.parent = parent
        self._on_cancel = on_cancel
        self._poll_interval_ms = poll_interval_ms
        self._queue: SimpleQueue[tuple[int, int]] | None = None
        self._future = None
        self._job_id: str | None = None
        self._cancelled = False

        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.transient(parent)
        self.top.grab_set()  # Modal pero no bloquea el hilo principal.
        self.top.protocol("WM_DELETE_WINDOW", self._handle_cancel)

        self._progress_var = tk.DoubleVar(value=0.0)
        self._label_var = tk.StringVar(value="Procesando 0 de 0 (0 %)")

        ttk.Label(self.top, text=title).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
        self._progress_bar = ttk.Progressbar(
            self.top,
            maximum=100,
            variable=self._progress_var,
            mode="determinate",
            length=360,
        )
        self._progress_bar.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        ttk.Label(self.top, textvariable=self._label_var).grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")

        self._cancel_button = ttk.Button(self.top, text="Cancelar", command=self._handle_cancel)
        self._cancel_button.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="e")
        self.top.columnconfigure(0, weight=1)

    def track_future(self, future, queue: SimpleQueue[tuple[int, int]]):
        self._future = future
        self._queue = queue
        self._schedule_poll()

    def _handle_cancel(self):
        if self._cancelled:
            return
        self._cancelled = True
        try:
            self._cancel_button.state(["disabled"])
        except tk.TclError:
            pass
        if self._on_cancel:
            try:
                self._on_cancel()
            except Exception:
                pass

    def _schedule_poll(self):
        if not self.parent or not getattr(self.parent, "after", None):
            return
        self._job_id = self.parent.after(self._poll_interval_ms, self._poll)

    def _poll(self):
        if not self.top or not self._queue:
            return
        while True:
            try:
                current, total = self._queue.get_nowait()
            except Exception:
                break
            self._update_values(current, total)
        if self._future is not None and getattr(self._future, "done", lambda: True)():
            self.close()
            return
        self._schedule_poll()

    def _update_values(self, current: int, total: int):
        total = max(total, 0)
        percent = 0.0
        if total > 0:
            percent = max(0.0, min(100.0, (current / total) * 100))
        try:
            self._progress_var.set(percent)
            self._label_var.set(f"Procesando {current} de {total} ({percent:.1f} %)")
        except tk.TclError:
            pass

    def close(self):
        if self._job_id and getattr(self.parent, "after_cancel", None):
            try:
                self.parent.after_cancel(self._job_id)
            except tk.TclError:
                pass
            self._job_id = None
        try:
            self.top.grab_release()
        except tk.TclError:
            pass
        try:
            self.top.destroy()
        except tk.TclError:
            pass
