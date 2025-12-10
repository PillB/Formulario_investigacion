from __future__ import annotations

import threading

from utils.background_worker import (
    run_guarded_task,
    shutdown_background_workers,
)


class TimerRoot:
    """Minimal Tk-like root that executes callbacks on timers."""

    def __init__(self):
        self._timers: list[threading.Timer] = []
        self._alive = True

    def after(self, delay_ms: int, callback):
        timer = threading.Timer(delay_ms / 1000, callback)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)
        return timer

    def after_cancel(self, timer):
        timer.cancel()

    def winfo_exists(self):
        return self._alive

    def destroy(self):
        self._alive = False
        for timer in list(self._timers):
            timer.cancel()


def test_background_tasks_do_not_block_ui_callbacks():
    root = TimerRoot()
    release_gate = threading.Event()
    import_started = threading.Event()
    autosave_started = threading.Event()
    ui_tick = threading.Event()
    results: list[str] = []
    errors: list[BaseException] = []
    completion_gate = threading.Event()

    def _long_task(label: str, started_evt: threading.Event):
        started_evt.set()
        if not release_gate.wait(timeout=1.5):
            raise TimeoutError("Release gate was not opened")
        return label

    def _on_success(result):
        results.append(result)
        if len(results) == 2:
            completion_gate.set()

    def _on_error(exc: BaseException):
        errors.append(exc)
        completion_gate.set()

    futures = [
        run_guarded_task(
            lambda: _long_task("import", import_started),
            _on_success,
            _on_error,
            root,
            poll_interval_ms=5,
            category="imports",
        ),
        run_guarded_task(
            lambda: _long_task("autosave", autosave_started),
            _on_success,
            _on_error,
            root,
            poll_interval_ms=5,
            category="autosave",
        ),
    ]

    root.after(20, ui_tick.set)

    assert import_started.wait(timeout=0.5)
    assert autosave_started.wait(timeout=0.5)
    assert ui_tick.wait(timeout=0.5)
    assert not any(f.done() for f in futures)

    release_gate.set()

    assert completion_gate.wait(timeout=1.5)
    assert sorted(results) == ["autosave", "import"]
    assert errors == []

    shutdown_background_workers(cancel_futures=True)
    root.destroy()
