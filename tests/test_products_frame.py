"""UI-level tests for ProductFrame validators."""

from decimal import Decimal

import pytest

from ui.frames import products
from models.analitica_catalog import get_analitica_codes, get_analitica_names


class DummyVar:
    def __init__(self, value=""):
        self._value = value
        self._traces = []

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        for callback in list(self._traces):
            if callable(callback):
                callback(None, None, None)

    def trace_add(self, _mode, callback):
        self._traces.append(callback)
        return f"trace_{len(self._traces)}"


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

    def focus_set(self):
        self._config['focused'] = True

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
def patch_tk_components(monkeypatch):
    class _DummyBadge:
        def grid(self, *args, **kwargs):
            return None

    class _DummyBadgeRegistry:
        def __init__(self):
            self.claimed_keys = []

        def claim(self, key, *_args, **_kwargs):
            self.claimed_keys.append(key)
            return _DummyBadge()

        def wrap_validation(self, key, validate_fn):
            self.claimed_keys.append(key)
            return validate_fn

        def refresh(self):
            return None

        def update_badge(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(products.tk, "StringVar", DummyVar)
    monkeypatch.setattr(products.ttk, "LabelFrame", DummyWidget)
    monkeypatch.setattr(products.ttk, "Frame", DummyWidget)
    monkeypatch.setattr(products.ttk, "Label", DummyWidget)
    monkeypatch.setattr(products.ttk, "Entry", DummyWidget)
    monkeypatch.setattr(products.ttk, "Combobox", DummyWidget)
    monkeypatch.setattr(products.ttk, "Button", DummyWidget)
    monkeypatch.setattr(products, "ValidationBadgeRegistry", _DummyBadgeRegistry)
    monkeypatch.setattr(products, "badge_registry", _DummyBadgeRegistry())
    monkeypatch.setattr(products.tk, "BooleanVar", DummyVar)
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
        claim_lookup={},
        initialize_rows=False,
    )


def _assert_toggle_bindings(section):
    for widget in (section.header, section.title_label, section.indicator):
        for sequence in ("<ButtonRelease-1>", "<space>", "<Return>"):
            initial_state = section.is_open
            widget.event_generate(sequence)
            assert section.is_open is not initial_state
            widget.event_generate(sequence)
            assert section.is_open is initial_state


def test_product_section_starts_collapsed_and_retains_title(monkeypatch):
    class _CollapsibleSection(DummyWidget):
        def __init__(self, parent=None, title="", open=True, on_toggle=None, **_kwargs):
            super().__init__(parent=parent)
            self.is_open = open
            self._on_toggle = on_toggle
            self.header = DummyWidget()
            self.title_label = DummyWidget()
            self.indicator = DummyWidget()
            self.indicator.configure(text="▼" if open else "▸")
            self.content = DummyWidget()
            for widget in (self.header, self.title_label, self.indicator):
                for seq in ("<ButtonRelease-1>", "<space>", "<Return>"):
                    widget.bind(seq, self.toggle)

        def pack_content(self, widget, **_kwargs):
            return widget

        def set_title(self, title):
            self.title_label.configure(text=title)

        def toggle(self, *_args):
            self.is_open = not self.is_open
            if callable(self._on_toggle):
                self._on_toggle(self)

    monkeypatch.setattr(products, "CollapsibleSection", _CollapsibleSection)
    product = _build_product_frame()

    assert product.section.is_open is False
    assert product.section.title_label["text"] == "Producto 1"
    assert product.section.indicator["text"] == "▸"

    _assert_toggle_bindings(product.section)


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

    product.monto_perdida_var.set("-10.00")
    error = perdida_validator.validate_callback()
    assert error is not None
    assert "fraude" in error.lower()
    assert "no puede ser negativo" in error.lower()
    assert perdida_validator.variables and perdida_validator.variables[0] is product.monto_perdida_var

    product.monto_falla_var.set("-5.00")
    error = falla_validator.validate_callback()
    assert error is not None
    assert "falla" in error.lower()
    assert "no puede ser negativo" in error.lower()
    assert falla_validator.variables and falla_validator.variables[0] is product.monto_falla_var


def test_contingency_and_recovered_fields_have_inline_validation():
    product = _build_product_frame()
    contingencia_validator = _find_validator("Monto contingencia")
    recuperado_validator = _find_validator("Monto recuperado")
    assert contingencia_validator is not None
    assert recuperado_validator is not None

    product.monto_cont_var.set("abc")
    error = contingencia_validator.validate_callback()
    assert error is not None
    assert "contingencia" in error.lower()
    assert "número" in error.lower()
    assert contingencia_validator.variables and contingencia_validator.variables[0] is product.monto_cont_var

    product.monto_rec_var.set("-1.00")
    error = recuperado_validator.validate_callback()
    assert error is not None
    assert "recuperado" in error.lower()
    assert "no puede ser negativo" in error.lower()
    assert recuperado_validator.variables and recuperado_validator.variables[0] is product.monto_rec_var


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


def test_optional_amount_field_normalizes_blank_value():
    product = _build_product_frame()
    product.monto_perdida_var.set("")

    message, decimal_value = product._validate_amount_field(
        product.monto_perdida_var,
        "Monto pérdida de fraude",
        True,
    )

    assert message is None
    assert decimal_value is None


def test_involvement_validator_requires_amount_when_collaborator_selected():
    product = _build_product_frame()
    row = product.add_involvement()
    row.team_var.set("T12345")
    row.monto_var.set("")

    validator = _find_validator("Asignación 1 colaborador")
    assert validator is not None

    error = validator.validate_callback()
    assert error is not None
    assert "monto" in error.lower()


def test_claim_row_autofills_from_lookup(monkeypatch):
    product = _build_product_frame()
    product.set_claim_lookup(
        {
            "C00000001": {
                "nombre_analitica": "Analítica catálogo",
                "codigo_analitica": "4300000001",
            }
        }
    )
    row = product.add_claim()
    row.id_var.set("C00000001")
    row.on_id_change(from_focus=True)

    assert row.name_var.get() == "Analítica catálogo"
    assert row.code_var.get() == "4300000001"


def test_claim_row_preserves_manual_fields_when_requested():
    product = _build_product_frame()
    product.set_claim_lookup(
        {
            "C00000002": {
                "nombre_analitica": "Del catálogo",
                "codigo_analitica": "4300000002",
            }
        }
    )
    row = product.add_claim()
    row.id_var.set("C00000002")
    row.name_var.set("Manual")
    row.code_var.set("")

    row.on_id_change(preserve_existing=True)

    assert row.name_var.get() == "Manual"
    assert row.code_var.get() == "4300000002"


def test_claim_row_catalog_lists_are_populated():
    product = _build_product_frame()
    row = product.add_claim()

    assert list(row.code_entry["values"]) == get_analitica_codes()
    assert list(row.name_entry["values"]) == get_analitica_names()


def test_claim_row_catalog_selection_syncs_fields():
    product = _build_product_frame()
    row = product.add_claim()
    codes = get_analitica_codes()
    names = get_analitica_names()

    row.code_var.set(codes[0])
    row._on_analitica_code_change(from_focus=True)
    assert row.name_var.get() == names[0]

    row.name_var.set(names[1])
    row._on_analitica_name_change(from_focus=True)
    assert row.code_var.get() == codes[1]


def test_claim_row_validation_rejects_unknown_catalog_entries():
    product = _build_product_frame()
    row = product.add_claim()

    row.code_var.set("4300999999")

    assert row._validate_claim_code() is not None


def test_duplicate_key_tuple_does_not_use_team_options_without_assignments():
    product = _build_product_frame()
    product.add_involvement()
    product.add_involvement()

    key_tuple = product._compose_duplicate_key_tuple()

    parts = key_tuple.strip("()\n").split(", ")
    assert len(parts) == 6
    assert parts[3] == "-"
    assert "T12345" not in key_tuple


def test_duplicate_key_tuple_uses_assigned_involvement_collaborator():
    product = _build_product_frame()
    row = product.add_involvement()
    row.team_var.set("T99999")

    key_tuple = product._compose_duplicate_key_tuple()

    assert "T99999" in key_tuple
    assert "T12345" not in key_tuple


def test_claim_row_shows_message_for_unknown_id(monkeypatch):
    product = _build_product_frame()
    product.set_claim_lookup({})
    row = product.add_claim()
    row.id_var.set("C00009999")

    captured = []
    monkeypatch.setattr(products.messagebox, "showerror", lambda *args: captured.append(args))

    row.on_id_change(from_focus=True)

    assert captured == []

    product.set_claim_lookup({"OTHER": {"nombre_analitica": "X"}})
    row.on_id_change(from_focus=True)
    assert captured and "Reclamo no encontrado" in captured[0][0]


def test_contingency_must_match_investigated_for_credit_types():
    product = _build_product_frame()
    product.tipo_prod_var.set("Tarjeta de crédito")
    product.monto_inv_var.set("100.00")
    product.monto_cont_var.set("50.00")

    validator = _find_validator("Consistencia de montos (Monto contingencia)")
    assert validator is not None

    error = validator.validate_callback()

    assert error is not None
    assert "contingencia" in error.lower()
    assert "monto investigado" in error.lower()


def test_claims_required_when_positive_losses_from_user_actions(monkeypatch):
    product = _build_product_frame()
    captured = []
    monkeypatch.setattr(products.messagebox, "showerror", lambda *args: captured.append(args))

    product.monto_perdida_var.set("10.00")
    product._handle_claim_requirement_change(source_is_user=True)

    assert product.claim_fields_required is True
    assert captured and "al menos un reclamo completo" in captured[0][1]


def test_payload_loaded_claim_requirement_enforced_with_partial_claim():
    product = _build_product_frame()
    product.set_claims_from_data([{"id_reclamo": "C00001234"}])

    product.monto_falla_var.set("5.00")
    product._handle_claim_requirement_change()

    errors = product.claim_requirement_errors()

    assert any("C00001234" in err for err in errors)
    assert any("al menos un reclamo completo" in err for err in errors)


def test_infidencia_modalities_bypass_product_validations():
    product = _build_product_frame()
    monto_validator = _find_validator("Monto investigado")

    assert product.cat2_var._traces
    assert product.mod_var._traces

    product.id_var.set("")
    product.tipo_prod_var.set("")
    product.monto_inv_var.set("abc")

    assert product.id_validator.validate_callback() is not None
    assert monto_validator.validate_callback() is not None

    product.cat2_var.set("Fraude Interno")
    product.mod_var.set("violación de secreto bancario")
    product._handle_infidencia_state_change()

    assert product._infidencia_active is True
    assert product.id_validator.validate_callback() is None
    assert monto_validator.validate_callback() is None
    message, is_valid = product._validate_montos_consistentes()
    assert message is None
    assert is_valid is True

    product.mod_var.set("Otra modalidad")
    assert product._infidencia_active is False
    assert product.id_validator.validate_callback() is not None
    assert monto_validator.validate_callback() is not None


def test_afectacion_interna_bypasses_core_product_validations():
    product = _build_product_frame()
    internal_flag = products.tk.BooleanVar(value=False)

    product.id_var.set("")
    product.tipo_prod_var.set("")
    product.monto_inv_var.set("abc")

    assert product.id_validator.validate_callback() is not None
    assert product.monto_inv_validator.validate_callback() is not None

    product.set_afectacion_interna(internal_flag)
    internal_flag.set(True)

    assert product._is_internal_mode_active() is True
    assert product.id_validator.validate_callback() is None
    assert product.monto_inv_validator.validate_callback() is None

    internal_flag.set(False)
    product.client_var.set(product.INTERNAL_CLIENT_ID)

    assert product._is_internal_mode_active() is True
    assert product.client_validator.validate_callback() is None
