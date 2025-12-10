from __future__ import annotations

import types
import tkinter as tk

import app as app_module


def build_confetti_app(monkeypatch):
    app = app_module.FraudCaseApp.__new__(app_module.FraudCaseApp)
    app.logs = []
    app._suppress_messagebox = True
    app.root = types.SimpleNamespace(
        winfo_pointerx=lambda: 100,
        winfo_pointery=lambda: 200,
        winfo_exists=lambda: True,
    )
    app.actions_action_bar = types.SimpleNamespace(buttons={})
    app.flush_logs_now = lambda: None
    app._play_feedback_sound = lambda: None
    app._handle_session_saved = lambda data: setattr(app, "saved", data)
    app._show_success_toast = lambda *_args, **_kwargs: setattr(app, "toast", True)
    return app


def _minimal_result():
    return {
        "report_prefix": "demo",
        "data": {},
        "md_path": None,
        "docx_path": None,
        "warnings": [],
    }


def test_confetti_not_triggered_when_disabled(monkeypatch):
    app = build_confetti_app(monkeypatch)
    app._confetti_enabled = False
    calls = []

    monkeypatch.setattr(app_module, "start_confetti_burst", lambda *args, **kwargs: calls.append((args, kwargs)))

    app._handle_save_success(_minimal_result())

    assert calls == []


def test_confetti_triggered_when_enabled(monkeypatch):
    app = build_confetti_app(monkeypatch)
    app._confetti_enabled = True
    calls = []

    def fake_confetti(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(app_module, "start_confetti_burst", fake_confetti)

    app._handle_save_success(_minimal_result())

    assert len(calls) == 1
    assert calls[0][1].get("enabled") is True


def test_confetti_errors_swallowed(monkeypatch):
    app = build_confetti_app(monkeypatch)
    app._confetti_enabled = True

    def boom(*_args, **_kwargs):
        raise tk.TclError("no canvas")

    monkeypatch.setattr(app_module, "start_confetti_burst", boom)

    app._handle_save_success(_minimal_result())
