from types import SimpleNamespace

import app


class DummyWidget:
    def __init__(self):
        self._bindings = {}

    def bind(self, event_name, callback, add=None):
        self._bindings.setdefault(event_name, []).append(callback)

    def trigger(self, event_name):
        for callback in self._bindings.get(event_name, []):
            callback(SimpleNamespace(type=event_name))


def test_post_edit_validator_arms_on_paste_and_validates_on_focus_out(monkeypatch):
    errors = []

    def fake_showerror(title, message):
        errors.append((title, message))

    monkeypatch.setattr(app.messagebox, "showerror", fake_showerror)

    widget = DummyWidget()
    logs = []
    validator = app.FraudCaseApp._PostEditValidator(
        widget,
        lambda: "Dato inválido",
        "Campo X",
        logs,
        suppression_flag=lambda: False,
    )

    widget.trigger("<<Paste>>")
    widget.trigger("<FocusOut>")

    assert errors == [("Dato inválido", "Dato inválido")]
    assert any(entry["mensaje"].endswith("Dato inválido") for entry in logs)


def test_post_edit_validator_handles_combobox_selection(monkeypatch):
    errors = []

    def fake_showerror(title, message):
        errors.append((title, message))

    monkeypatch.setattr(app.messagebox, "showerror", fake_showerror)

    widget = DummyWidget()
    logs = []
    validator = app.FraudCaseApp._PostEditValidator(
        widget,
        lambda: "Seleccion inválida",
        "Campo Y",
        logs,
        suppression_flag=lambda: False,
    )

    widget.trigger("<<ComboboxSelected>>")

    assert errors == [("Dato inválido", "Seleccion inválida")]
    assert any(entry["mensaje"].endswith("Seleccion inválida") for entry in logs)
    assert validator._last_error == "Seleccion inválida"


def test_post_edit_validator_requires_new_edit_to_validate_again(monkeypatch):
    errors = []
    validation_calls = []

    def fake_showerror(title, message):
        errors.append((title, message))

    def validate():
        validation_calls.append("called")
        return "Dato inválido"

    monkeypatch.setattr(app.messagebox, "showerror", fake_showerror)

    widget = DummyWidget()
    logs = []
    validator = app.FraudCaseApp._PostEditValidator(
        widget,
        validate,
        "Campo Z",
        logs,
        suppression_flag=lambda: False,
    )

    widget.trigger("<FocusOut>")
    assert not validation_calls
    assert not errors

    widget.trigger("<KeyRelease>")
    widget.trigger("<FocusOut>")
    assert validation_calls == ["called"]
    assert errors == [("Dato inválido", "Dato inválido")]

    widget.trigger("<FocusOut>")
    assert validation_calls == ["called"]
    assert errors == [("Dato inválido", "Dato inválido")]

    widget.trigger("<<Paste>>")
    widget.trigger("<FocusOut>")
    assert validation_calls == ["called", "called"]
    assert errors == [("Dato inválido", "Dato inválido"), ("Dato inválido", "Dato inválido")]


def test_post_edit_validator_logs_even_if_messagebox_fails(monkeypatch):
    def failing_showerror(*_args, **_kwargs):
        raise app.tk.TclError("boom")

    monkeypatch.setattr(app.messagebox, "showerror", failing_showerror)

    widget = DummyWidget()
    logs = []
    validator = app.FraudCaseApp._PostEditValidator(
        widget,
        lambda: "Dato inválido",
        "Campo W",
        logs,
        suppression_flag=lambda: False,
    )

    widget.trigger("<<Cut>>")
    widget.trigger("<FocusOut>")

    assert validator._last_error == "Dato inválido"
    assert any(entry["mensaje"].endswith("Dato inválido") for entry in logs)
