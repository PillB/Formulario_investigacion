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


def test_display_error_uses_modal_notification(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    widget = DummyWidget()
    captured = []
    monkeypatch.setattr(validators.FieldValidator, "notification_handler", lambda *args: captured.append(args))
    monkeypatch.setattr(validators.FieldValidator, "notification_title", "Dato inválido")
    monkeypatch.setattr(validators.FieldValidator, "notifications_enabled", True)

    validator = validators.FieldValidator(widget, lambda: None, [], "Campo X")
    validator._validation_armed = True

    validator._display_error("Primer error")
    validator._display_error("Primer error")
    validator._display_error("Segundo error")
    validator._display_error(None)

    assert captured == [
        ("Dato inválido", "Campo X: Primer error"),
        ("Dato inválido", "Campo X: Segundo error"),
    ]


def test_modal_notification_ignores_tcl_error(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    widget = DummyWidget()

    def failing_notifier(_title, _message):
        raise validators.TclError("no display")

    monkeypatch.setattr(validators.FieldValidator, "notification_handler", failing_notifier)
    monkeypatch.setattr(validators.FieldValidator, "notifications_enabled", True)

    validator = validators.FieldValidator(widget, lambda: None, [], "Campo Y")
    validator._validation_armed = True

    validator._display_error("Error")

    assert validator.last_error == "Error"


def test_show_custom_error_does_not_trigger_modal_by_default(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    widget = DummyWidget()
    captured = []
    monkeypatch.setattr(validators.FieldValidator, "notification_handler", lambda *args: captured.append(args))
    validator = validators.FieldValidator(widget, lambda: None, [], "Campo Z")

    validator.show_custom_error("Error")

    assert captured == []
    assert validator.last_error == "Error"


def test_show_custom_error_can_opt_in_to_modal(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    widget = DummyWidget()
    captured = []
    monkeypatch.setattr(validators.FieldValidator, "notification_handler", lambda *args: captured.append(args))
    monkeypatch.setattr(validators.FieldValidator, "notification_title", "Dato inválido")
    validator = validators.FieldValidator(widget, lambda: None, [], "Campo modal")

    validator.show_custom_error("Modal", notify=True)

    assert captured == [("Dato inválido", "Campo modal: Modal")]


def test_modal_triggers_after_inline_only_error(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    widget = DummyWidget()
    captured = []
    monkeypatch.setattr(validators.FieldValidator, "notification_handler", lambda *args: captured.append(args))
    validator = validators.FieldValidator(widget, lambda: None, [], "Campo inline")
    validator._validation_armed = True

    validator.show_custom_error("Solo tooltip")
    validator._display_error("Solo tooltip")

    assert captured == [("Dato inválido", "Campo inline: Solo tooltip")]


def test_modal_can_repeat_after_error_cleared(monkeypatch):
    monkeypatch.setattr(validators, "ValidationTooltip", DummyTooltip)
    widget = DummyWidget()
    captured = []
    monkeypatch.setattr(validators.FieldValidator, "notification_handler", lambda *args: captured.append(args))
    validator = validators.FieldValidator(widget, lambda: None, [], "Campo repetido")
    validator._validation_armed = True

    validator._display_error("Error")
    validator._display_error(None)
    validator._display_error("Error")

    assert captured == [
        ("Dato inválido", "Campo repetido: Error"),
        ("Dato inválido", "Campo repetido: Error"),
    ]
