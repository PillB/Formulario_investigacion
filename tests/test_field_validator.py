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


EVENTS = ("<FocusOut>", "<KeyRelease>", "<<ComboboxSelected>>", "<<Paste>>", "<<Cut>>")


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


class DummyVar:
    def __init__(self, value=""):
        self._value = value
        self._callbacks = []

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        for cb in self._callbacks:
            cb("", "", "write")

    def trace_add(self, _mode, callback):
        self._callbacks.append(callback)
        return f"trace_{len(self._callbacks)}"


class DummyEvent:
    def __init__(self, widget, type_name):
        self.widget = widget
        self.type = type_name


def test_focusout_after_value_change_runs_validation_once(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    widget = DummyWidget()
    variable = DummyVar("initial")
    calls = []

    def recorder():
        calls.append(variable.get())

    validator = validators.FieldValidator(widget, recorder, [], "id_field", variables=[variable])
    variable.set("pasted value")
    assert calls == []

    focus_event = DummyEvent(widget, "FocusOut")
    validator._on_change(focus_event)

    assert calls == ["pasted value"]


def test_focusout_without_changes_skips_validation(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    widget = DummyWidget()
    variable = DummyVar("initial")
    calls = []

    validator = validators.FieldValidator(widget, lambda: calls.append("called"), [], "id_field", variables=[variable])
    focus_event = DummyEvent(widget, "FocusOut")
    validator._on_change(focus_event)

    assert calls == []


def test_modal_notification_shows_once_per_new_error(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    calls = []

    class DummyMessagebox:
        def showerror(self, title, message):
            calls.append((title, message))

    monkeypatch.setattr(validators, "messagebox", DummyMessagebox())
    widget = DummyWidget()
    validator = validators.FieldValidator(widget, lambda: "", [], "Campo")

    validator._display_error("Primer error")
    validator._display_error("Primer error")
    validator._display_error("Segundo error")

    assert calls == [
        ("Error de validación", "Campo: Primer error"),
        ("Error de validación", "Campo: Segundo error"),
    ]


def test_modal_notification_ignores_tcl_errors(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)

    class DummyTclError(Exception):
        pass

    class FailingMessagebox:
        def showerror(self, _title, _message):
            raise DummyTclError("failed")

    monkeypatch.setattr(validators, "messagebox", FailingMessagebox())
    monkeypatch.setattr(validators, "TclError", DummyTclError)

    widget = DummyWidget()
    validator = validators.FieldValidator(widget, lambda: "", [], "Campo")
    validator._display_error("Algún error")

    assert validator.last_error == "Algún error"
