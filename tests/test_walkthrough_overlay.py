from __future__ import annotations

import types

from app import FraudCaseApp


class _RootStub:
    def update_idletasks(self):
        return None


class _OverlayStub:
    def __init__(self):
        self.lift_calls = 0
        self.attribute_calls: list[tuple[str, bool]] = []
        self.withdraw_calls = 0
        self.deiconify_calls = 0
        self.after_idle_callbacks: list[object] = []

    def winfo_exists(self):
        return True

    def attributes(self, flag, value):  # noqa: ANN001
        self.attribute_calls.append((flag, value))

    def lift(self):
        self.lift_calls += 1

    def withdraw(self):
        self.withdraw_calls += 1

    def deiconify(self):
        self.deiconify_calls += 1

    def after_idle(self, callback):  # noqa: ANN001
        self.after_idle_callbacks.append(callback)


class _WidgetStub:
    def __init__(self):
        self.configure_calls: list[dict[str, object]] = []

    def configure(self, **kwargs):  # noqa: ANN001
        self.configure_calls.append(kwargs)


class _AnchorStub:
    def update_idletasks(self):
        return None


def test_walkthrough_overlay_reasserts_topmost_on_each_step():
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.root = _RootStub()

    overlay = _OverlayStub()
    anchor = _AnchorStub()
    app._walkthrough_overlay = overlay
    app._walkthrough_headline = _WidgetStub()
    app._walkthrough_title_label = _WidgetStub()
    app._walkthrough_body_label = _WidgetStub()
    app._walkthrough_next_btn = _WidgetStub()
    app._walkthrough_step_index = 0
    app._walkthrough_steps = [
        {
            "anchor_getter": lambda: anchor,
            "headline": "Headline",
            "title": "Title",
            "message": "Body",
        }
    ]

    app._ensure_walkthrough_anchor_visible = types.MethodType(
        lambda self, anchor_widget: (0, 0, 100, 100), app
    )
    app._position_walkthrough = types.MethodType(
        lambda self, anchor_widget, geometry=None: None, app
    )

    app._show_walkthrough_step()
    app._show_walkthrough_step()

    assert overlay.lift_calls == 2
    assert overlay.attribute_calls == [("-topmost", True), ("-topmost", True)]
    assert overlay.withdraw_calls == 2
    assert overlay.deiconify_calls == 2
