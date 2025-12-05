"""Background task utilities for Tkinter apps."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, Optional

import tkinter as tk

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="background-worker")


TaskFunc = Callable[[], object]
Callback = Optional[Callable[[object], None]]
ErrorCallback = Optional[Callable[[BaseException], None]]


def run_guarded_task(
    task_func: TaskFunc,
    on_success: Callback,
    on_error: ErrorCallback,
    root: tk.Misc,
    *,
    poll_interval_ms: int = 50,
) -> Future:
    """Execute ``task_func`` in a background thread and marshal callbacks.

    The background future is polled with ``root.after`` to keep the UI
    responsive and guarantee that ``on_success``/``on_error`` are always
    invoked in the Tk main loop thread.
    """

    future = _executor.submit(task_func)

    def _dispatch_callback(callback: Callable[[object], None], value: object) -> None:
        try:
            callback(value)
        except Exception:
            # Avoid propagating exceptions into Tk's event loop
            pass

    def _poll_future() -> None:
        if not root or not getattr(root, "winfo_exists", lambda: False)():
            return
        if not future.done():
            root.after(poll_interval_ms, _poll_future)
            return
        try:
            result = future.result()
        except BaseException as exc:  # pragma: no cover - defensive
            if on_error:
                _dispatch_callback(on_error, exc)
            return
        if on_success:
            _dispatch_callback(on_success, result)

    root.after(poll_interval_ms, _poll_future)
    return future
