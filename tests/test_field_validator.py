"""Tests for FieldValidator event bindings."""

import validators


class DummyWidget:
    def __init__(self):
        self.bind_calls = []

    def bind(self, sequence, callback, add=None):
        self.bind_calls.append((sequence, callback, add))
        return f"bind_{len(self.bind_calls)}"


class DummyTooltip:
    def __init__(self, widget):
        self.widget = widget

    def show(self, _text):
        return None

    def hide(self):
        return None


EVENTS = ("<FocusOut>", "<KeyRelease>", "<<ComboboxSelected>>")


def _assert_events_have_add(bind_calls):
    for event in EVENTS:
        event_calls = [call for call in bind_calls if call[0] == event]
        assert event_calls, f"expected binding for {event}"
        assert all(call[2] == "+" for call in event_calls)


def test_field_validator_main_widget_preserves_existing_bindings(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    widget = DummyWidget()
    validators.FieldValidator(widget, lambda: None, [], "id_field")
    _assert_events_have_add(widget.bind_calls)


def test_field_validator_add_widget_uses_non_overriding_bindings(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    widget = DummyWidget()
    extra_widget = DummyWidget()
    validator = validators.FieldValidator(widget, lambda: None, [], "id_field")
    validator.add_widget(extra_widget)
    _assert_events_have_add(extra_widget.bind_calls)
