"""Validations for the client frame contact fields."""

import pytest

from ui.frames import clients


class DummyVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def trace_add(self, *_args, **_kwargs):
        return "trace"

    def trace_remove(self, *_args, **_kwargs):
        return None


class DummyWidget:
    def __init__(self, *args, **kwargs):
        self.textvariable = kwargs.get("textvariable")
        self._config = {}
        self._bindings = []
        self.command = kwargs.get("command")
        if "values" in kwargs:
            self._config['values'] = kwargs["values"]

    def pack(self, *args, **kwargs):
        return None

    def bind(self, sequence, callback, add=None):
        self._bindings.append((sequence, callback, add))
        return f"bind_{len(self._bindings)}"

    def set(self, value):
        if self.textvariable is not None:
            self.textvariable.set(value)
        self._config['current_value'] = value

    def get(self):
        if self.textvariable is not None:
            return self.textvariable.get()
        return self._config.get('current_value', "")

    def destroy(self):
        return None

    def configure(self, **kwargs):
        self._config.update(kwargs)

    def __setitem__(self, key, value):
        self._config[key] = value

    def __getitem__(self, key):
        return self._config.get(key)


class DummyListbox(DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selection = set()

    def selection_clear(self, start, end):
        if start == 0 and end == "end":
            self._selection.clear()

    def selection_set(self, index):
        self._selection.add(index)

    def curselection(self):
        return tuple(sorted(self._selection))


class RecordingValidator:
    instances = []

    def __init__(self, widget, validate_callback, logs, field_name, variables=None):
        self.widget = widget
        self.validate_callback = validate_callback
        self.logs = logs
        self.field_name = field_name
        self.variables = list(variables or [])
        RecordingValidator.instances.append(self)

    def add_widget(self, _widget):
        return None

    def suppress_during(self, callback):
        return callback()

    def show_custom_error(self, _message):
        return None


@pytest.fixture(autouse=True)
def patch_client_widgets(monkeypatch):
    class _TkStub:
        StringVar = DummyVar
        END = "end"

        class Listbox(DummyListbox):
            pass

    class _TtkStub:
        LabelFrame = DummyWidget
        Frame = DummyWidget
        Label = DummyWidget
        Entry = DummyWidget
        Combobox = DummyWidget
        Button = DummyWidget

    monkeypatch.setattr(clients, "tk", _TkStub())
    monkeypatch.setattr(clients, "ttk", _TtkStub())
    RecordingValidator.instances.clear()
    monkeypatch.setattr(clients, "FieldValidator", RecordingValidator)
    yield
    RecordingValidator.instances.clear()


def _build_client_frame():
    return clients.ClientFrame(
        parent=DummyWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        update_client_options=lambda: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
    )


def _find_validator(label):
    for validator in RecordingValidator.instances:
        if label in validator.field_name:
            return validator
    return None


def test_client_contact_fields_require_inline_data():
    frame = _build_client_frame()

    phone_validator = _find_validator("Teléfonos")
    email_validator = _find_validator("Correos")

    assert phone_validator is not None
    assert email_validator is not None

    phone_error = phone_validator.validate_callback()
    assert phone_error is not None
    assert "teléfono" in phone_error.lower()
    assert phone_validator.variables and phone_validator.variables[0] is frame.telefonos_var

    email_error = email_validator.validate_callback()
    assert email_error is not None
    assert "correo" in email_error.lower()
    assert email_validator.variables and email_validator.variables[0] is frame.correos_var

    frame.telefonos_var.set("+51999888777")
    frame.correos_var.set("demo@example.com")

    assert phone_validator.validate_callback() is None
    assert email_validator.validate_callback() is None
