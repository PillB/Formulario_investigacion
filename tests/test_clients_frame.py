"""Validations for the client frame contact fields."""

import pytest

from ui.frames import clients


class DummyVar:
    def __init__(self, value=""):
        self._value = value
        self._traces = []

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        for callback in list(self._traces):
            callback()

    def trace_add(self, *_args, **_kwargs):
        if not _args:
            return "trace"
        callback = _args[1] if len(_args) > 1 else _kwargs.get("callback")
        if callback is None:
            return "trace"
        self._traces.append(callback)
        return f"trace_{len(self._traces)}"

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

    def event_generate(self, sequence):
        for bound_sequence, callback, _ in list(self._bindings):
            if bound_sequence == sequence and callable(callback):
                callback(None)

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

    def winfo_manager(self):
        return ""

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
        self.suspend_count = 0
        RecordingValidator.instances.append(self)

    def add_widget(self, _widget):
        return None

    def suspend(self):
        self.suspend_count += 1

    def resume(self):
        self.suspend_count = max(0, self.suspend_count - 1)

    def suppress_during(self, callback):
        return callback()

    def show_custom_error(self, _message):
        return None


@pytest.fixture(autouse=True)
def patch_client_widgets(monkeypatch):
    class _TkStub:
        StringVar = DummyVar
        BooleanVar = DummyVar
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
        Checkbutton = DummyWidget

    class _CollapsibleSection(DummyWidget):
        def __init__(self, parent=None, title="", open=True, on_toggle=None, **_kwargs):
            super().__init__(parent=parent)
            self.title = title
            self._is_open = open
            self._on_toggle = on_toggle
            self.header = DummyWidget()
            self.title_label = DummyWidget()
            self.indicator = DummyWidget()
            self.content = DummyWidget()
            for widget in (self.header, self.title_label, self.indicator):
                for seq in ("<ButtonRelease-1>", "<space>", "<Return>"):
                    widget.bind(seq, self.toggle)

        def pack_content(self, widget, **_kwargs):
            return widget

        @property
        def is_open(self):
            return self._is_open

        def set_title(self, title):
            self.title = title

        def toggle(self, *_args):
            self._is_open = not self._is_open
            if callable(self._on_toggle):
                self._on_toggle(self)

    monkeypatch.setattr(clients, "tk", _TkStub())
    monkeypatch.setattr(clients, "ttk", _TtkStub())
    monkeypatch.setattr(clients, "CollapsibleSection", _CollapsibleSection)
    RecordingValidator.instances.clear()
    monkeypatch.setattr(clients, "FieldValidator", RecordingValidator)
    yield
    RecordingValidator.instances.clear()


def _build_client_frame(**kwargs):
    params = dict(
        parent=DummyWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        update_client_options=lambda: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
    )
    params.update(kwargs)
    return clients.ClientFrame(**params)


def _find_validator(label):
    for validator in RecordingValidator.instances:
        if label in validator.field_name:
            return validator
    return None


def _assert_toggles_on_events(section, widget):
    for sequence in ("<ButtonRelease-1>", "<space>", "<Return>"):
        initial_state = section.is_open
        widget.event_generate(sequence)
        assert section.is_open is not initial_state
        widget.event_generate(sequence)
        assert section.is_open is initial_state


def test_client_section_handles_multiple_toggle_events():
    frame = _build_client_frame()
    section = frame.section

    assert section.is_open is False

    for widget in (section.header, section.title_label, section.indicator):
        _assert_toggles_on_events(section, widget)


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


def test_afectacion_interna_toggle_autofills_and_notifies():
    shared_flag = DummyVar(False)
    notifications = []
    callback_states = []

    frame = _build_client_frame(
        afectacion_interna_var=shared_flag,
        change_notifier=lambda message: notifications.append(message),
        afectacion_change_callback=lambda enabled: callback_states.append(enabled),
    )

    assert notifications == []
    assert callback_states == []
    assert frame.id_var.get() == ""
    assert frame.tipo_id_var.get() == ""

    shared_flag.set(True)

    assert frame.tipo_id_var.get() == "RUC"
    assert frame.id_var.get() == "20100047218"
    id_validator = _find_validator("ID")
    tipo_validator = _find_validator("Tipo de ID")
    assert id_validator is not None and id_validator.suspend_count == 0
    assert tipo_validator is not None and tipo_validator.suspend_count == 0
    other_validators = [
        v for v in RecordingValidator.instances if v not in (id_validator, tipo_validator)
    ]
    assert other_validators and all(v.suspend_count == 1 for v in other_validators)
    assert callback_states == [True]
    assert any("afectación interna" in msg.lower() for msg in notifications)

    shared_flag.set(False)

    assert frame.tipo_id_var.get() == ""
    assert frame.id_var.get() == ""
    assert callback_states[-1] is False
    assert all(v.suspend_count == 0 for v in other_validators)
