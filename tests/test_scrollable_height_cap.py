import tkinter as tk

import pytest

from app import FraudCaseApp


@pytest.fixture
def app_instance(monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter requiere una pantalla para esta prueba")
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)
    app = FraudCaseApp(root)
    app._suppress_messagebox = True
    try:
        yield app
    finally:
        root.destroy()


def test_compute_scrollable_max_height_uses_generous_multiplier(app_instance, monkeypatch):
    monkeypatch.setattr(app_instance.root, "winfo_height", lambda: 640)
    monkeypatch.setattr(app_instance.root, "winfo_reqheight", lambda: 0)

    max_height = app_instance._compute_scrollable_max_height(app_instance.clients_scrollable)

    assert max_height >= 640 * app_instance.SCROLLABLE_HEIGHT_MULTIPLIER


def test_refresh_scrollable_reuses_height_cap(app_instance, monkeypatch):
    scrollable = app_instance.clients_scrollable
    monkeypatch.setattr(app_instance.root, "winfo_height", lambda: 500)
    monkeypatch.setattr(app_instance.root, "winfo_reqheight", lambda: 0)
    monkeypatch.setattr(app_instance.root, "after_idle", lambda func: func())

    recorded = []

    def _capture_refresh(
        container, *, max_height=None, adjust_height=False, debounce_ms=50
    ):  # noqa: ANN001
        recorded.append((max_height, adjust_height))

    monkeypatch.setattr("app.resize_scrollable_to_content", _capture_refresh)

    app_instance._refresh_scrollable(scrollable)
    app_instance._refresh_scrollable(scrollable)

    assert len(recorded) == 2
    expected_height = 500 * app_instance.SCROLLABLE_HEIGHT_MULTIPLIER
    assert recorded[0] == recorded[1] == (expected_height, True)

