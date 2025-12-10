"""Background task utilities for Tkinter apps."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock
from typing import Callable, Optional

import tkinter as tk

TaskFunc = Callable[[], object]
Callback = Optional[Callable[[object], None]]
ErrorCallback = Optional[Callable[[BaseException], None]]

_EXECUTOR_CONFIG: dict[str, int] = {
    "default": 4,
    "imports": 2,
    "autosave": 2,
    "persistence": 2,
    "reports": 2,
}

_executors: dict[str, ThreadPoolExecutor] = {}
_executor_lock = Lock()


def _get_executor(category: str | None) -> ThreadPoolExecutor:
    name = category or "default"
    with _executor_lock:
        executor = _executors.get(name)
        if executor is None or getattr(executor, "_shutdown", False):
            max_workers = _EXECUTOR_CONFIG.get(name, _EXECUTOR_CONFIG["default"])
            executor = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix=f"background-{name}",
            )
            _executors[name] = executor
    return executor


def shutdown_background_workers(*, wait: bool = False, cancel_futures: bool = False) -> None:
    """Detiene todos los ejecutores activos y libera recursos."""

    with _executor_lock:
        executors = list(_executors.items())
        _executors.clear()
    for _name, executor in executors:
        executor.shutdown(wait=wait, cancel_futures=cancel_futures)


def run_guarded_task(
    task_func: TaskFunc,
    on_success: Callback,
    on_error: ErrorCallback,
    root: tk.Misc,
    *,
    poll_interval_ms: int = 50,
    category: str | None = None,
) -> Future:
    """Execute ``task_func`` in a background thread and marshal callbacks.

    The background future is polled with ``root.after`` to keep the UI
    responsive and guarantee that ``on_success``/``on_error`` are always
    invoked in the Tk main loop thread. The task is dispatched to an
    executor selected by ``category`` to avoid contention between long-
    running operations (por ejemplo, importaciones vs. autosaves).
    """

    executor = _get_executor(category)
    future = executor.submit(task_func)

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
