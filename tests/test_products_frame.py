"""UI-level tests for ProductFrame validators."""

import pytest

from ui.frames import products


class DummyVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class DummyWidget:
    def __init__(self, *args, **kwargs):
        self.textvariable = kwargs.get("textvariable")
        self._config = {}
        self._bindings = []
        self.command = kwargs.get("command")
        values = kwargs.get("values")
        if values is not None:
            self._config['values'] = values

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
def patch_tk_components(monkeypatch):
    monkeypatch.setattr(products.tk, "StringVar", DummyVar)
    monkeypatch.setattr(products.ttk, "LabelFrame", DummyWidget)
    monkeypatch.setattr(products.ttk, "Frame", DummyWidget)
    monkeypatch.setattr(products.ttk, "Label", DummyWidget)
    monkeypatch.setattr(products.ttk, "Entry", DummyWidget)
    monkeypatch.setattr(products.ttk, "Combobox", DummyWidget)
    monkeypatch.setattr(products.ttk, "Button", DummyWidget)
    RecordingValidator.instances.clear()
    monkeypatch.setattr(products, "FieldValidator", RecordingValidator)
    yield
    RecordingValidator.instances.clear()


def _build_product_frame():
    return products.ProductFrame(
        parent=DummyWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        get_client_options=lambda: ["CL1"],
        get_team_options=lambda: ["T12345"],
        logs=[],
        product_lookup={},
        tooltip_register=lambda *_args, **_kwargs: None,
    )


class _ClaimRowProductStub:
    def __init__(self):
        self.idx = 0

    def _register_lookup_sync(self, _widget):
        return None


def _find_validator(label):
    for validator in RecordingValidator.instances:
        if label in validator.field_name:
            return validator
    return None


def test_loss_fields_have_inline_validation():
    product = _build_product_frame()
    perdida_validator = _find_validator("Monto pérdida fraude")
    falla_validator = _find_validator("Monto falla procesos")
    assert perdida_validator is not None
    assert falla_validator is not None

    product.monto_perdida_var.set("-10")
    error = perdida_validator.validate_callback()
    assert error is not None
    assert "fraude" in error.lower()
    assert "no puede ser negativo" in error.lower()
    assert perdida_validator.variables and perdida_validator.variables[0] is product.monto_perdida_var

    product.monto_falla_var.set("-5")
    error = falla_validator.validate_callback()
    assert error is not None
    assert "falla" in error.lower()
    assert "no puede ser negativo" in error.lower()
    assert falla_validator.variables and falla_validator.variables[0] is product.monto_falla_var


def test_claim_row_requires_name_even_before_save():
    claim_row = products.ClaimRow(
        parent=DummyWidget(),
        product_frame=_ClaimRowProductStub(),
        idx=0,
        remove_callback=lambda _row: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
    )

    name_validator = _find_validator("Nombre analítica")
    assert name_validator is not None

    claim_row.name_var.set("")
    error = name_validator.validate_callback()
    assert error is not None
    assert "nombre" in error.lower()
    assert name_validator.variables and name_validator.variables[0] is claim_row.name_var
