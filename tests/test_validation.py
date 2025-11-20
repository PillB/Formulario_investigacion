from datetime import datetime, timedelta

import pytest

from types import SimpleNamespace

import app as app_module
from app import FraudCaseApp
from settings import (ACCIONADO_OPTIONS, CANAL_LIST, CRITICIDAD_LIST,
                      FLAG_COLABORADOR_LIST, PROCESO_LIST, TAXONOMIA,
                      TIPO_FALTA_LIST, TIPO_ID_LIST, TIPO_INFORME_LIST,
                      TIPO_MONEDA_LIST, TIPO_SANCION_LIST)


class DummyVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def trace_add(self, _mode, _callback):
        return f"trace_{id(self)}"

    def trace_remove(self, *_args, **_kwargs):
        return None


class DummyClient:
    def __init__(self, client_id):
        self.tipo_id_var = DummyVar(TIPO_ID_LIST[0])
        self.id_var = DummyVar(client_id)

    def get_data(self):
        return {
            "tipo_id": self.tipo_id_var.get(),
            "id_cliente": self.id_var.get(),
        }


class DummyClientWithContacts(DummyClient):
    def __init__(
        self,
        client_id,
        *,
        telefonos="999888777",
        correos="demo@example.com",
        direcciones="Av. Principal 123",
        accionado="Fiscalía",
        flag="No aplica",
    ):
        super().__init__(client_id)
        self.flag_var = DummyVar(flag)
        self.telefonos_var = DummyVar(telefonos)
        self.correos_var = DummyVar(correos)
        self.direcciones_var = DummyVar(direcciones)
        self.accionado_var = DummyVar(accionado)

    def set_accionado_from_text(self, value):
        self.accionado_var.set(value.strip())


class DummyTeam:
    def __init__(
        self,
        team_id,
        division="otra division",
        area="otra area",
        nombre_agencia="",
        codigo_agencia="",
        flag=None,
        tipo_falta=None,
        tipo_sancion=None,
    ):
        flag = FLAG_COLABORADOR_LIST[0] if flag is None else flag
        tipo_falta = TIPO_FALTA_LIST[0] if tipo_falta is None else tipo_falta
        tipo_sancion = TIPO_SANCION_LIST[0] if tipo_sancion is None else tipo_sancion
        self.id_var = DummyVar(team_id)
        self.codigo_agencia_var = DummyVar(codigo_agencia)
        self.division_var = DummyVar(division)
        self.area_var = DummyVar(area)
        self.nombre_agencia_var = DummyVar(nombre_agencia)
        self.flag_var = DummyVar(flag)
        self.tipo_falta_var = DummyVar(tipo_falta)
        self.tipo_sancion_var = DummyVar(tipo_sancion)

    def get_data(self):
        return {
            "id_colaborador": self.id_var.get(),
            "division": self.division_var.get(),
            "area": self.area_var.get(),
            "nombre_agencia": self.nombre_agencia_var.get(),
            "codigo_agencia": self.codigo_agencia_var.get(),
            "flag": self.flag_var.get(),
            "tipo_falta": self.tipo_falta_var.get(),
            "tipo_sancion": self.tipo_sancion_var.get(),
        }


class _UIStubWidget:
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


def _make_recording_validator():
    class RecordingValidator:
        instances = []

        def __init__(self, widget, validate_callback, logs, field_name, variables=None):
            self.widget = widget
            self.validate_callback = validate_callback
            self.logs = logs
            self.field_name = field_name
            self.variables = list(variables or [])
            self.last_custom_error = None
            RecordingValidator.instances.append(self)

        def add_widget(self, _widget):
            return None

        def suppress_during(self, callback):
            return callback()

        def show_custom_error(self, message):
            self.last_custom_error = message
            return None

    RecordingValidator.instances = []
    return RecordingValidator


def _patch_products_module(monkeypatch):
    from ui.frames import products

    RecordingValidator = _make_recording_validator()

    class _TkStub:
        StringVar = DummyVar

    class _TtkStub:
        LabelFrame = _UIStubWidget
        Frame = _UIStubWidget
        Label = _UIStubWidget
        Entry = _UIStubWidget
        Combobox = _UIStubWidget
        Button = _UIStubWidget

    monkeypatch.setattr(products, "tk", _TkStub())
    monkeypatch.setattr(products, "ttk", _TtkStub())
    monkeypatch.setattr(products, "FieldValidator", RecordingValidator)
    return products, RecordingValidator


def _patch_risk_module(monkeypatch):
    from ui.frames import risk

    RecordingValidator = _make_recording_validator()

    class _TkStub:
        StringVar = DummyVar

    class _TtkStub:
        LabelFrame = _UIStubWidget
        Frame = _UIStubWidget
        Label = _UIStubWidget
        Entry = _UIStubWidget
        Combobox = _UIStubWidget
        Button = _UIStubWidget

    monkeypatch.setattr(risk, "tk", _TkStub())
    monkeypatch.setattr(risk, "ttk", _TtkStub())
    monkeypatch.setattr(risk, "FieldValidator", RecordingValidator)
    return risk, RecordingValidator


def _patch_team_module(monkeypatch):
    from ui.frames import team

    RecordingValidator = _make_recording_validator()

    class _TkStub:
        StringVar = DummyVar

    class _TtkStub:
        LabelFrame = _UIStubWidget
        Frame = _UIStubWidget
        Label = _UIStubWidget
        Entry = _UIStubWidget
        Combobox = _UIStubWidget
        Button = _UIStubWidget

    messagebox_stub = SimpleNamespace(
        showerror=lambda *args, **kwargs: None,
        askyesno=lambda *args, **kwargs: False,
    )

    monkeypatch.setattr(team, "tk", _TkStub())
    monkeypatch.setattr(team, "ttk", _TtkStub())
    monkeypatch.setattr(team, "messagebox", messagebox_stub)
    monkeypatch.setattr(team, "FieldValidator", RecordingValidator)
    return team, RecordingValidator


def _find_validator_instance(instances, fragment):
    for validator in instances:
        if fragment in validator.field_name:
            return validator
    return None


def _trigger_focus_out(widget):
    callbacks = [cb for seq, cb, _ in widget._bindings if seq == "<FocusOut>"]
    assert callbacks, "Expected at least one <FocusOut> binding"
    callbacks[-1](SimpleNamespace(widget=widget))


class DummyProductFrame:
    def __init__(
        self,
        tipo_producto,
        client_id,
        case_cat1,
        case_cat2,
        case_modalidad,
        producto_overrides=None,
        reclamos=None,
        asignaciones=None,
    ):
        base_product = {
            "producto": {
                "id_producto": "1234567890123",
                "id_caso": "2024-0001",
                "id_cliente": client_id,
                "categoria1": case_cat1,
                "categoria2": case_cat2,
                "modalidad": case_modalidad,
                "canal": CANAL_LIST[0],
                "proceso": PROCESO_LIST[0],
                "fecha_ocurrencia": "2023-01-01",
                "fecha_descubrimiento": "2023-01-02",
                "monto_investigado": "0.00",
                "tipo_moneda": TIPO_MONEDA_LIST[0],
                "monto_perdida_fraude": "0.00",
                "monto_falla_procesos": "0.00",
                "monto_contingencia": "0.00",
                "monto_recuperado": "0.00",
                "monto_pago_deuda": "0.00",
                "tipo_producto": tipo_producto,
            },
            "reclamos": list(reclamos or []),
            "asignaciones": list(asignaciones or []),
        }
        if producto_overrides:
            base_product["producto"].update(producto_overrides)
        self._product = base_product
        final_tipo = self._product["producto"].get("tipo_producto", tipo_producto)
        self.tipo_prod_var = DummyVar(final_tipo)
        self._product_id = self._product["producto"].get("id_producto", "")
        self.id_var = DummyVar(self._product_id)

    def get_data(self):
        return self._product


DEFAULT_PRODUCT_ID = "1234567890123"


class DummyRiskFrame:
    def __init__(
        self,
        risk_id,
        *,
        criticidad,
        lider="Líder del riesgo",
        descripcion="Descripción del riesgo",
        exposicion="0",
        planes="Plan-1",
    ):
        self._data = {
            "id_riesgo": risk_id,
            "lider": lider,
            "descripcion": descripcion,
            "criticidad": criticidad,
            "exposicion_residual": exposicion,
            "planes_accion": planes,
        }

    def get_data(self):
        return dict(self._data)


class PopulateProductFrameStub:
    def __init__(self):
        self.id_var = DummyVar()
        self.client_var = DummyVar()
        self.cat1_var = DummyVar()
        self.cat2_var = DummyVar()
        self.mod_var = DummyVar()
        self.canal_var = DummyVar("PREV_CANAL")
        self.proceso_var = DummyVar("PREV_PROCESO")
        self.fecha_oc_var = DummyVar()
        self.fecha_desc_var = DummyVar()
        self.monto_inv_var = DummyVar()
        self.moneda_var = DummyVar("PREV_MONEDA")
        self.monto_perdida_var = DummyVar()
        self.monto_falla_var = DummyVar()
        self.monto_cont_var = DummyVar()
        self.monto_rec_var = DummyVar()
        self.monto_pago_var = DummyVar()
        self.tipo_prod_var = DummyVar()
        self.claims_payload = None

    def on_cat1_change(self):
        return None

    def on_cat2_change(self):
        return None

    def set_claims_from_data(self, claims):
        self.claims_payload = claims


def build_headless_app(
    tipo_producto,
    *,
    product_configs=None,
    team_configs=None,
    risk_configs=None,
):
    app = FraudCaseApp.__new__(FraudCaseApp)
    app._suppress_messagebox = True
    case_cat1 = next(iter(TAXONOMIA))
    case_cat2 = next(iter(TAXONOMIA[case_cat1]))
    case_modalidad = TAXONOMIA[case_cat1][case_cat2][0]
    app.logs = []
    app.id_caso_var = DummyVar("2024-0001")
    app.tipo_informe_var = DummyVar(TIPO_INFORME_LIST[0])
    app.cat_caso1_var = DummyVar(case_cat1)
    app.cat_caso2_var = DummyVar(case_cat2)
    app.mod_caso_var = DummyVar(case_modalidad)
    app.canal_caso_var = DummyVar(CANAL_LIST[0])
    app.proceso_caso_var = DummyVar(PROCESO_LIST[0])
    for attr in (
        'antecedentes_var',
        'modus_var',
        'hallazgos_var',
        'descargos_var',
        'conclusiones_var',
        'recomendaciones_var',
    ):
        setattr(app, attr, DummyVar(""))
    client_id = "12345678"
    app.client_frames = [DummyClient(client_id)]
    team_definitions = team_configs or [{"team_id": "T12345"}]
    app.team_frames = [
        DummyTeam(
            config.get("team_id", "T12345"),
            division=config.get("division", "otra division"),
            area=config.get("area", "otra area"),
            nombre_agencia=config.get("nombre_agencia", ""),
            codigo_agencia=config.get("codigo_agencia", ""),
            flag=config.get("flag"),
            tipo_falta=config.get("tipo_falta"),
            tipo_sancion=config.get("tipo_sancion"),
        )
        for config in team_definitions
    ]
    product_definitions = product_configs or [
        {
            "tipo_producto": tipo_producto,
            "producto_overrides": None,
            "reclamos": None,
            "asignaciones": None,
        }
    ]
    app.product_frames = [
        DummyProductFrame(
            definition.get("tipo_producto", tipo_producto),
            definition.get("client_id", client_id),
            case_cat1,
            case_cat2,
            case_modalidad,
            producto_overrides=definition.get("producto_overrides"),
            reclamos=definition.get("reclamos"),
            asignaciones=definition.get("asignaciones"),
        )
        for definition in product_definitions
    ]
    risk_definitions = risk_configs or []
    app.risk_frames = [
        DummyRiskFrame(
            config.get("id_riesgo", f"RSK-{idx+1:06d}"),
            criticidad=config.get(
                "criticidad",
                CRITICIDAD_LIST[0],
            ),
            lider=config.get("lider", "Líder del riesgo"),
            descripcion=config.get("descripcion", "Descripción del riesgo"),
            exposicion=config.get("exposicion_residual", "0"),
            planes=config.get("planes_accion", "Plan-1"),
        )
        for idx, config in enumerate(risk_definitions)
    ]
    app.norm_frames = []
    return app


@pytest.mark.parametrize(
    "field_name,invalid_value,expected_fragment",
    [
        (
            "tipo_informe_var",
            "Tipo inventado",
            "El tipo de informe 'Tipo inventado' no está en el catálogo CM.",
        ),
        (
            "canal_caso_var",
            "Canal inventado",
            "El canal del caso 'Canal inventado' no está en el catálogo CM.",
        ),
        (
            "proceso_caso_var",
            "Proceso inventado",
            "El proceso del caso 'Proceso inventado' no está en el catálogo CM.",
        ),
    ],
)
def test_validate_data_rejects_invalid_case_catalog_values(
    field_name, invalid_value, expected_fragment
):
    app = build_headless_app("Crédito personal")
    getattr(app, field_name).set(invalid_value)

    errors, _ = app.validate_data()

    assert any(expected_fragment in error for error in errors)


def test_validate_data_rejects_unknown_case_category_level1():
    app = build_headless_app("Crédito personal")
    invalid_cat1 = "Categoría inventada"
    app.cat_caso1_var.set(invalid_cat1)

    errors, _ = app.validate_data()

    expected_fragment = f"La categoría nivel 1 '{invalid_cat1}' no está en el catálogo CM."
    assert any(expected_fragment in error for error in errors)


def test_validate_data_rejects_unknown_case_category_level2():
    app = build_headless_app("Crédito personal")
    parent_cat = app.cat_caso1_var.get()
    invalid_subcat = "Subcategoría fuera"
    app.cat_caso2_var.set(invalid_subcat)

    errors, _ = app.validate_data()

    expected_fragment = (
        f"La categoría nivel 2 '{invalid_subcat}' no está dentro de la categoría '{parent_cat}' del catálogo CM."
    )
    assert any(expected_fragment in error for error in errors)


def test_validate_data_rejects_unknown_case_modality():
    app = build_headless_app("Crédito personal")
    invalid_mod = "Modalidad inexistente"
    app.mod_caso_var.set(invalid_mod)

    errors, _ = app.validate_data()

    parent_cat1 = app.cat_caso1_var.get()
    parent_cat2 = app.cat_caso2_var.get()
    expected_fragment = (
        f"La modalidad '{invalid_mod}' no existe dentro de la categoría '{parent_cat1}'/'{parent_cat2}' del catálogo CM."
    )
    assert any(expected_fragment in error for error in errors)


def test_validate_data_accepts_catalog_product_type():
    app = build_headless_app("Crédito personal")
    errors, warnings = app.validate_data()
    assert errors == []
    assert warnings == []


def test_validate_data_rejects_products_without_taxonomy_values():
    product_config = {
        "tipo_producto": "Crédito personal",
        "producto_overrides": {
            "categoria1": "",
            "categoria2": "",
            "modalidad": "",
        },
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, _warnings = app.validate_data()
    assert any("Debe ingresar la categoría 1" in error for error in errors)
    assert any("Debe ingresar la categoría 2" in error for error in errors)
    assert any("Debe ingresar la modalidad" in error for error in errors)


def test_validate_data_accepts_products_with_explicit_taxonomy_values():
    cat1 = next(iter(TAXONOMIA))
    cat2 = next(iter(TAXONOMIA[cat1]))
    modalidad = TAXONOMIA[cat1][cat2][0]
    product_config = {
        "tipo_producto": "Crédito personal",
        "producto_overrides": {
            "categoria1": cat1,
            "categoria2": cat2,
            "modalidad": modalidad,
        },
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, warnings = app.validate_data()
    assert errors == []
    assert warnings == []


def test_validate_data_flags_unknown_product_type():
    app = build_headless_app("Producto inventado fuera de catálogo")
    errors, _warnings = app.validate_data()
    assert any("no está en el catálogo" in error for error in errors)


def test_validate_data_requires_client_tipo_id():
    app = build_headless_app("Crédito personal")
    app.client_frames[0].tipo_id_var.set("")

    errors, _warnings = app.validate_data()

    assert any("Debe ingresar el tipo de ID del cliente" in error for error in errors)


def test_validate_data_flags_duplicate_clients():
    app = build_headless_app("Crédito personal")
    duplicate_id = app.client_frames[0].id_var.get()
    app.client_frames.append(DummyClient(duplicate_id))

    errors, _ = app.validate_data()

    expected_fragment = f"El ID de cliente {duplicate_id} está duplicado"
    assert any(expected_fragment in error for error in errors)


def test_validate_data_detects_case_insensitive_client_duplicates():
    app = build_headless_app("Crédito personal")
    mixed_case_id = "ABCDEF123"
    app.client_frames[0].tipo_id_var.set("Pasaporte")
    app.client_frames[0].id_var.set(mixed_case_id)
    second_client = DummyClient(mixed_case_id.lower())
    second_client.tipo_id_var.set("Pasaporte")
    app.client_frames.append(second_client)

    errors, _ = app.validate_data()

    expected_fragment = f"El ID de cliente {mixed_case_id} está duplicado"
    assert any(expected_fragment in error for error in errors)


def test_update_frame_id_index_reverts_duplicate_ids(monkeypatch):
    app_instance = FraudCaseApp.__new__(FraudCaseApp)
    app_instance.logs = []
    app_instance._suppress_messagebox = False

    captured = {}

    def fake_showerror(title, message):
        captured["title"] = title
        captured["message"] = message

    monkeypatch.setattr(app_module.messagebox, "showerror", fake_showerror)

    original_frame = DummyClient("C0000001")
    original_frame._last_tracked_id = ""
    conflicting_frame = DummyClient("")
    conflicting_frame._last_tracked_id = ""

    index = {}
    app_instance._update_frame_id_index(index, original_frame, "", original_frame.id_var.get())
    conflicting_frame.id_var.set("C0000001")
    app_instance._update_frame_id_index(index, conflicting_frame, "", conflicting_frame.id_var.get())

    assert conflicting_frame.id_var.get() == ""
    assert conflicting_frame._last_tracked_id == ""
    assert index["C0000001"] is original_frame
    assert captured["title"] == "ID duplicado"
    assert "único" in captured["message"]


def test_validate_data_rejects_imported_clients_with_invalid_phone():
    app = build_headless_app("Crédito personal")
    invalid_client = DummyClientWithContacts(
        "12345678",
        telefonos="999-888",
        correos="demo@example.com",
        accionado=ACCIONADO_OPTIONS[0],
    )
    app.client_frames = [invalid_client]

    errors, _ = app.validate_data()

    assert any("teléfono inválido" in error for error in errors)


def test_validate_data_rejects_imported_clients_with_invalid_email():
    app = build_headless_app("Crédito personal")
    invalid_client = DummyClientWithContacts(
        "12345678",
        telefonos="999888777",
        correos="correo-invalido",
        accionado=ACCIONADO_OPTIONS[0],
    )
    app.client_frames = [invalid_client]

    errors, _ = app.validate_data()

    assert any("correo inválido" in error for error in errors)


def test_validate_data_rejects_imported_clients_with_missing_phone():
    app = build_headless_app("Crédito personal")
    invalid_client = DummyClientWithContacts(
        "12345678",
        telefonos=" ",
        correos="demo@example.com",
        accionado=ACCIONADO_OPTIONS[0],
    )
    app.client_frames = [invalid_client]

    errors, _ = app.validate_data()

    expected = "Cliente 1: Debe ingresar los teléfonos del cliente."
    assert expected in errors


def test_validate_data_rejects_imported_clients_with_missing_email():
    app = build_headless_app("Crédito personal")
    invalid_client = DummyClientWithContacts(
        "12345678",
        telefonos="999888777",
        correos="",
        accionado=ACCIONADO_OPTIONS[0],
    )
    app.client_frames = [invalid_client]

    errors, _ = app.validate_data()

    expected = "Cliente 1: Debe ingresar los correos del cliente."
    assert expected in errors


def test_validate_data_requires_accionado_for_imported_clients():
    app = build_headless_app("Crédito personal")
    invalid_client = DummyClientWithContacts(
        "12345678",
        telefonos="999888777",
        correos="demo@example.com",
        accionado="",
    )
    app.client_frames = [invalid_client]

    errors, _ = app.validate_data()

    expected = "Cliente 1: Debe seleccionar al menos una opción en Accionado."
    assert expected in errors


@pytest.mark.parametrize(
    "product_id,expect_error",
    [
        ("1234567890", None),
        ("123", "ahorro"),
    ],
)
def test_validate_data_validates_account_family_ids(product_id, expect_error):
    product_config = {
        "tipo_producto": "Cuenta de ahorro",
        "producto_overrides": {
            "tipo_producto": "Cuenta de ahorro",
            "id_producto": product_id,
        },
    }
    app = build_headless_app("Cuenta de ahorro", product_configs=[product_config])
    errors, warnings = app.validate_data()
    if expect_error:
        assert any(expect_error in error for error in errors)
    else:
        assert errors == []
        assert warnings == []


def test_validate_data_accepts_generic_alphanumeric_ids():
    product_config = {
        "tipo_producto": "Fondos mutuos",
        "producto_overrides": {
            "tipo_producto": "Fondos mutuos",
            "id_producto": "ABCD1234",
        },
    }
    app = build_headless_app("Fondos mutuos", product_configs=[product_config])
    errors, warnings = app.validate_data()
    assert errors == []
    assert warnings == []


def test_validate_data_rejects_short_generic_ids():
    product_config = {
        "tipo_producto": "Fondos mutuos",
        "producto_overrides": {
            "tipo_producto": "Fondos mutuos",
            "id_producto": "Ab1",
        },
    }
    app = build_headless_app("Fondos mutuos", product_configs=[product_config])
    errors, _ = app.validate_data()
    assert any("alfanumérico" in error for error in errors)


@pytest.mark.parametrize(
    "field,label",
    [
        ("canal", "el canal del producto"),
        ("proceso", "el proceso del producto"),
        ("tipo_moneda", "la moneda del producto"),
    ],
)
def test_validate_data_requires_product_catalog_fields(field, label):
    product_config = {
        "tipo_producto": "Crédito personal",
        "producto_overrides": {
            field: "",
        },
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, _ = app.validate_data()

    expected_message = f"Producto {DEFAULT_PRODUCT_ID}: Debe ingresar {label}."
    assert expected_message in errors


@pytest.mark.parametrize(
    "field,value,catalog_label",
    [
        ("canal", "Canal inválido", "canal"),
        ("proceso", "Proceso inválido", "proceso"),
        ("tipo_moneda", "Moneda desconocida", "tipo de moneda"),
    ],
)
def test_validate_data_rejects_unknown_product_catalog_values(field, value, catalog_label):
    product_config = {
        "tipo_producto": "Crédito personal",
        "producto_overrides": {
            field: value,
        },
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, _ = app.validate_data()

    expected_message = (
        f"Producto {DEFAULT_PRODUCT_ID}: El {catalog_label} '{value}' no está en el catálogo CM."
    )
    assert expected_message in errors


def test_validate_data_accepts_valid_product_catalog_selections():
    product_config = {
        "tipo_producto": "Crédito personal",
        "producto_overrides": {
            "canal": CANAL_LIST[-1],
            "proceso": PROCESO_LIST[-1],
            "tipo_moneda": TIPO_MONEDA_LIST[-1],
        },
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, warnings = app.validate_data()

    assert errors == []
    assert warnings == []


@pytest.mark.parametrize(
    "producto_overrides,expected_error",
    [
        (
            {"fecha_ocurrencia": "2023/01/01", "fecha_descubrimiento": "2023-01-02"},
            f"Fechas inválidas en el producto {DEFAULT_PRODUCT_ID}",
        ),
        (
            {"fecha_ocurrencia": "2023-05-05", "fecha_descubrimiento": "2023-05-05"},
            f"La fecha de ocurrencia debe ser anterior a la de descubrimiento en el producto {DEFAULT_PRODUCT_ID}",
        ),
        (
            {
                "fecha_ocurrencia": datetime.today().strftime("%Y-%m-%d"),
                "fecha_descubrimiento": (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
            },
            f"Las fechas del producto {DEFAULT_PRODUCT_ID} no pueden estar en el futuro",
        ),
    ],
)
def test_validate_data_enforces_date_rules(producto_overrides, expected_error):
    app = build_headless_app(
        "Crédito personal",
        product_configs=[{"tipo_producto": "Crédito personal", "producto_overrides": producto_overrides}],
    )
    errors, _ = app.validate_data()
    assert expected_error in errors


def _complete_claim(claim_id="C12345678"):
    return {
        "id_reclamo": claim_id,
        "nombre_analitica": "Analítica contable",
        "codigo_analitica": "4300000001",
    }


def test_validate_data_errors_when_involvement_missing_collaborator():
    product_config = {
        "tipo_producto": "Crédito personal",
        "asignaciones": [
            {"id_colaborador": "", "monto_asignado": "150.00"},
        ],
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, _ = app.validate_data()
    assert any("monto sin colaborador" in error for error in errors)


def test_validate_data_errors_when_involvement_missing_amount():
    product_config = {
        "tipo_producto": "Crédito personal",
        "asignaciones": [
            {"id_colaborador": "T12345", "monto_asignado": ""},
        ],
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, _ = app.validate_data()
    assert any("colaborador sin monto" in error for error in errors)


def test_validate_data_flags_deleted_collaborator_reference():
    product_config = {
        "tipo_producto": "Crédito personal",
        "asignaciones": [
            {"id_colaborador": "T12345", "monto_asignado": "75.00"},
        ],
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    app.team_frames = []  # Simula que el colaborador fue eliminado del formulario.
    errors, _ = app.validate_data()
    assert any("referencia un colaborador eliminado" in error for error in errors)


def test_validate_data_reports_invalid_involvement_amount():
    product_config = {
        "tipo_producto": "Crédito personal",
        "asignaciones": [
            {"id_colaborador": "T12345", "monto_asignado": "75.123"},
        ],
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])

    errors, _ = app.validate_data()

    assert any("dos decimales" in error for error in errors)


def test_validate_data_reports_involvement_amount_upper_bound():
    product_config = {
        "tipo_producto": "Crédito personal",
        "asignaciones": [
            {"id_colaborador": "T12345", "monto_asignado": "1000000000000.00"},
        ],
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])

    errors, _ = app.validate_data()

    expected_error = (
        f"Monto asignado del colaborador T12345 en el producto {DEFAULT_PRODUCT_ID} "
        "no puede tener más de 12 dígitos en la parte entera."
    )
    assert expected_error in errors


def test_validate_data_normalizes_valid_involvement_amounts():
    product_config = {
        "tipo_producto": "Crédito personal",
        "asignaciones": [
            {"id_colaborador": "T12345", "monto_asignado": "0010.50"},
            {"id_colaborador": "T54321", "monto_asignado": "75"},
        ],
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])

    errors, _ = app.validate_data()

    assert not any(
        "Monto asignado del colaborador" in error for error in errors
    )
    asignaciones = app.product_frames[0].get_data()['asignaciones']
    assert asignaciones[0]['monto_asignado'] == '10.50'
    assert asignaciones[1]['monto_asignado'] == '75.00'


def test_get_form_data_exports_normalized_involucramientos():
    product_config = {
        "tipo_producto": "Crédito personal",
        "asignaciones": [
            {"id_colaborador": "T12345", "monto_asignado": "0010.50"},
            {"id_colaborador": "T54321", "monto_asignado": "75"},
        ],
    }
    team_configs = [{"team_id": "T12345"}, {"team_id": "T54321"}]
    app = build_headless_app(
        "Crédito personal",
        product_configs=[product_config],
        team_configs=team_configs,
    )

    errors, _ = app.validate_data()
    assert errors == []

    form_data = app.gather_data()
    exported_amounts = [row['monto_asignado'] for row in form_data['involucramientos']]
    assert exported_amounts == ['10.50', '75.00']
    assert all(amount.strip() and '.' in amount for amount in exported_amounts)


@pytest.mark.parametrize(
    "config_key,label",
    [
        ("flag", "el flag del colaborador"),
        ("tipo_falta", "el tipo de falta del colaborador"),
        ("tipo_sancion", "el tipo de sanción del colaborador"),
    ],
)
def test_validate_data_requires_team_catalog_values(config_key, label):
    team_config = {"team_id": "T12345", config_key: ""}
    app = build_headless_app("Crédito personal", team_configs=[team_config])

    errors, _ = app.validate_data()

    if config_key == "flag":
        expected = "Colaborador 1: Debe ingresar el flag del colaborador."
    else:
        expected = f"Colaborador 1: Debe seleccionar {label}."
    assert expected in errors


@pytest.mark.parametrize(
    "config_key,label",
    [
        ("flag", "el flag del colaborador"),
        ("tipo_falta", "el tipo de falta del colaborador"),
        ("tipo_sancion", "el tipo de sanción del colaborador"),
    ],
)
def test_validate_data_rejects_unknown_team_catalog_values(config_key, label):
    invalid_value = "Valor fuera"
    team_config = {"team_id": "T12345", config_key: invalid_value}
    app = build_headless_app("Crédito personal", team_configs=[team_config])

    errors, _ = app.validate_data()

    if config_key == "flag":
        expected = (
            f"Colaborador 1: El flag del colaborador '{invalid_value}' no está en el catálogo CM."
        )
    else:
        expected = f"Colaborador 1: El {label} '{invalid_value}' no está en el catálogo CM."
    assert expected in errors


@pytest.mark.parametrize(
    "product_config,expected_error",
    [
        (
            {
                "tipo_producto": "Crédito personal",
                "producto_overrides": {
                    "monto_investigado": "100.00",
                    "monto_perdida_fraude": "0.00",
                    "monto_falla_procesos": "0.00",
                    "monto_contingencia": "0.00",
                    "monto_recuperado": "0.00",
                },
            },
            f"Las cuatro partidas (pérdida, falla, contingencia y recuperación) deben ser iguales al monto investigado en el producto {DEFAULT_PRODUCT_ID}",
        ),
        (
            {
                "tipo_producto": "Crédito personal",
                "producto_overrides": {
                    "monto_investigado": "100.00",
                    "monto_perdida_fraude": "99.99",
                    "monto_falla_procesos": "0.00",
                    "monto_contingencia": "0.00",
                    "monto_recuperado": "0.00",
                },
                "reclamos": [_complete_claim()],
            },
            f"Las cuatro partidas (pérdida, falla, contingencia y recuperación) deben ser iguales al monto investigado en el producto {DEFAULT_PRODUCT_ID}",
        ),
        (
            {
                "tipo_producto": "Tarjeta de crédito",
                "producto_overrides": {
                    "monto_investigado": "50.00",
                    "monto_perdida_fraude": "40.00",
                    "monto_falla_procesos": "0.00",
                    "monto_contingencia": "10.00",
                    "monto_recuperado": "0.00",
                },
                "reclamos": [_complete_claim()],
            },
            f"El monto de contingencia debe ser igual al monto investigado en el producto {DEFAULT_PRODUCT_ID} porque es un crédito o tarjeta",
        ),
        (
            {
                "tipo_producto": "Tarjeta de crédito",
                "producto_overrides": {
                    "monto_investigado": "50.00",
                    "monto_perdida_fraude": "0.00",
                    "monto_falla_procesos": "0.00",
                    "monto_contingencia": "49.99",
                    "monto_recuperado": "0.01",
                },
                "reclamos": [_complete_claim()],
            },
            f"El monto de contingencia debe ser igual al monto investigado en el producto {DEFAULT_PRODUCT_ID} porque es un crédito o tarjeta",
        ),
        (
            {
                "tipo_producto": "Crédito personal",
                "producto_overrides": {
                    "monto_investigado": "50.00",
                    "monto_pago_deuda": "60.00",
                },
            },
            f"El monto pagado de deuda excede el monto investigado en el producto {DEFAULT_PRODUCT_ID}",
        ),
        (
            {
                "tipo_producto": "Crédito personal",
                "producto_overrides": {
                    "monto_investigado": "100.123",
                    "monto_perdida_fraude": "0.00",
                    "monto_falla_procesos": "0.00",
                    "monto_contingencia": "0.00",
                    "monto_recuperado": "0.00",
                    "monto_pago_deuda": "0.00",
                },
            },
            f"Monto investigado del producto {DEFAULT_PRODUCT_ID} solo puede tener dos decimales como máximo.",
        ),
    ],
)
def test_validate_data_enforces_amount_rules(product_config, expected_error):
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, _ = app.validate_data()
    assert expected_error in errors


def test_validate_data_normalizes_product_amounts_without_two_decimals():
    product_config = {
        "tipo_producto": "Crédito personal",
        "producto_overrides": {
            "monto_investigado": "100",
            "monto_perdida_fraude": "0",
            "monto_falla_procesos": "0",
            "monto_contingencia": "100",
            "monto_recuperado": "0",
            "monto_pago_deuda": "0",
        },
        "reclamos": [_complete_claim()],
    }

    app = build_headless_app("Crédito personal", product_configs=[product_config])

    errors, _ = app.validate_data()

    assert errors == []
    producto = app.product_frames[0].get_data()['producto']
    assert producto['monto_investigado'] == '100.00'
    assert producto['monto_perdida_fraude'] == '0.00'
    assert producto['monto_contingencia'] == '100.00'


def test_validate_data_flags_case_level_one_cent_gap():
    product_config = {
        "tipo_producto": "Crédito personal",
        "producto_overrides": {
            "monto_investigado": "0.00",
            "monto_perdida_fraude": "0.00",
            "monto_falla_procesos": "0.00",
            "monto_contingencia": "0.00",
            "monto_recuperado": "0.01",
        },
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])

    errors, _ = app.validate_data()

    expected = "Las cuatro partidas (pérdida, falla, contingencia y recuperación) sumadas en el caso no coinciden con el total investigado."
    assert expected in errors


def test_validate_data_reports_product_and_case_gap():
    product_config = {
        "tipo_producto": "Crédito personal",
        "producto_overrides": {
            "monto_investigado": "10.00",
            "monto_perdida_fraude": "5.00",
            "monto_falla_procesos": "5.00",
            "monto_contingencia": "0.00",
            "monto_recuperado": "0.01",
            "monto_pago_deuda": "0.00",
        },
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])

    errors, _ = app.validate_data()

    product_message = (
        f"Las cuatro partidas (pérdida, falla, contingencia y recuperación) deben ser iguales al monto investigado en el producto {DEFAULT_PRODUCT_ID}"
    )
    case_message = (
        "Las cuatro partidas (pérdida, falla, contingencia y recuperación) sumadas en el caso no coinciden con el total investigado."
    )

    assert product_message in errors
    assert case_message in errors


def test_product_frame_amount_fields_normalize_missing_decimals(monkeypatch):
    products, validator_cls = _patch_products_module(monkeypatch)
    product = products.ProductFrame(
        parent=_UIStubWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        get_client_options=lambda: ["CLI1"],
        get_team_options=lambda: ["T12345"],
        logs=[],
        product_lookup={},
        tooltip_register=lambda *_args, **_kwargs: None,
        claim_lookup={},
    )

    product.monto_inv_var.set("100")
    product.monto_rec_var.set("100.5")

    inv_validator = _find_validator_instance(validator_cls.instances, "Monto investigado")
    rec_validator = _find_validator_instance(validator_cls.instances, "Monto recuperado")

    assert inv_validator is not None
    assert rec_validator is not None

    inv_error = inv_validator.validate_callback()
    assert inv_error is None
    assert product.monto_inv_var.get() == "100.00"

    rec_error = rec_validator.validate_callback()
    assert rec_error is None
    assert product.monto_rec_var.get() == "100.50"


def test_product_frame_detects_one_cent_gap(monkeypatch):
    products, _ = _patch_products_module(monkeypatch)
    product = products.ProductFrame(
        parent=_UIStubWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        get_client_options=lambda: ["CLI1"],
        get_team_options=lambda: ["T12345"],
        logs=[],
        product_lookup={},
        tooltip_register=lambda *_args, **_kwargs: None,
        claim_lookup={},
    )

    product.monto_inv_var.set("100.00")
    product.monto_perdida_var.set("99.99")
    product.monto_falla_var.set("0.00")
    product.monto_cont_var.set("0.00")
    product.monto_rec_var.set("0.00")
    product.monto_pago_var.set("0.00")

    assert product._validate_montos_consistentes('inv') is not None


def test_product_frame_requires_exact_contingencia_for_credit(monkeypatch):
    products, _ = _patch_products_module(monkeypatch)
    product = products.ProductFrame(
        parent=_UIStubWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        get_client_options=lambda: ["CLI1"],
        get_team_options=lambda: ["T12345"],
        logs=[],
        product_lookup={},
        tooltip_register=lambda *_args, **_kwargs: None,
        claim_lookup={},
    )

    product.tipo_prod_var.set("Tarjeta de crédito")
    product.monto_inv_var.set("50.00")
    product.monto_perdida_var.set("0.00")
    product.monto_falla_var.set("0.00")
    product.monto_cont_var.set("49.99")
    product.monto_rec_var.set("0.01")
    product.monto_pago_var.set("0.00")

    assert product._validate_montos_consistentes('contingencia') is not None


def test_involvement_row_normalizes_missing_decimals(monkeypatch):
    products, validator_cls = _patch_products_module(monkeypatch)

    class _ProductFrameStub:
        def __init__(self):
            self.idx = 0
            self.logs = []

        def log_change(self, *_args, **_kwargs):
            return None

        def schedule_summary_refresh(self, _section=None):
            return None

    row = products.InvolvementRow(
        parent=_UIStubWidget(),
        product_frame=_ProductFrameStub(),
        idx=0,
        team_getter=lambda: ["T12345"],
        remove_callback=lambda _row: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
    )

    row.monto_var.set("100.5")
    amount_validator = _find_validator_instance(validator_cls.instances, "Asignación 1")

    assert amount_validator is not None
    error = amount_validator.validate_callback()
    assert error is None
    assert row.monto_var.get() == "100.50"


def test_risk_frame_normalizes_missing_decimals(monkeypatch):
    risk_module, validator_cls = _patch_risk_module(monkeypatch)
    risk_frame = risk_module.RiskFrame(
        parent=_UIStubWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
    )

    risk_frame.exposicion_var.set("100")
    exposure_validator = _find_validator_instance(validator_cls.instances, "Exposición")

    assert exposure_validator is not None
    first_error = exposure_validator.validate_callback()
    assert first_error is None
    assert risk_frame.exposicion_var.get() == "100.00"

    risk_frame.exposicion_var.set("100.5")
    second_error = exposure_validator.validate_callback()
    assert second_error is None
    assert risk_frame.exposicion_var.get() == "100.50"


def test_validate_data_requires_risk_criticidad():
    app = build_headless_app("Crédito personal", risk_configs=[{"criticidad": ""}])

    errors, _ = app.validate_data()

    assert "Riesgo 1: Debe seleccionar la criticidad del riesgo." in errors


def test_validate_data_rejects_unknown_risk_criticidad():
    invalid_value = "Inexistente"
    app = build_headless_app(
        "Crédito personal",
        risk_configs=[{"criticidad": invalid_value}],
    )

    errors, _ = app.validate_data()

    expected_message = f"Riesgo 1: La criticidad '{invalid_value}' no está en el catálogo CM."
    assert expected_message in errors


def test_validate_data_accepts_allowed_risk_criticidad():
    allowed_value = CRITICIDAD_LIST[0]
    app = build_headless_app(
        "Crédito personal",
        risk_configs=[{"criticidad": allowed_value}],
    )

    errors, _ = app.validate_data()

    assert not any("Riesgo 1: Debe seleccionar la criticidad del riesgo." in err for err in errors)
    assert not any("Riesgo 1: La criticidad" in err for err in errors)


def test_validate_data_requires_norm_fecha_vigencia():
    app = build_headless_app("Crédito personal")

    class _NormFrame:
        def __init__(self):
            self._data = {
                'id_norma': '2024.001.01.01',
                'descripcion': 'Norma incompleta',
                'fecha_vigencia': '',
            }

        def get_data(self):
            return dict(self._data)

    app.norm_frames = [_NormFrame()]

    errors, _ = app.validate_data()

    assert any("Debe ingresar la fecha de vigencia" in error for error in errors)


def test_validate_data_detects_duplicate_technical_keys():
    duplicate_assignments = [
        {"id_colaborador": "T12345", "monto_asignado": "10.00"},
        {"id_colaborador": "T12345", "monto_asignado": "5.00"},
    ]
    app = build_headless_app(
        "Crédito personal",
        product_configs=[{"tipo_producto": "Crédito personal", "asignaciones": duplicate_assignments}],
    )
    errors, _ = app.validate_data()
    assert (
        f"Registro duplicado de clave técnica (producto {DEFAULT_PRODUCT_ID}, colaborador T12345)"
        in errors
    )


def test_validate_data_detects_case_insensitive_technical_keys():
    duplicate_assignments = [
        {"id_colaborador": "T12345", "monto_asignado": "10.00"},
        {"id_colaborador": "t12345", "monto_asignado": "5.00"},
    ]
    app = build_headless_app(
        "Crédito personal",
        product_configs=[{"tipo_producto": "Crédito personal", "asignaciones": duplicate_assignments}],
    )
    errors, _ = app.validate_data()
    assert (
        f"Registro duplicado de clave técnica (producto {DEFAULT_PRODUCT_ID}, colaborador T12345)"
        in errors
    )


def test_validate_data_detects_case_insensitive_product_duplicates():
    product_configs = [
        {"tipo_producto": "Fondos mutuos", "producto_overrides": {"id_producto": "ABCD1234"}},
        {"tipo_producto": "Fondos mutuos", "producto_overrides": {"id_producto": "abcd1234"}},
    ]
    app = build_headless_app("Fondos mutuos", product_configs=product_configs)

    errors, _ = app.validate_data()

    assert any("El producto ABCD1234 está duplicado en el formulario." in err for err in errors)


def test_validate_data_requires_claim_when_losses_exist():
    product_config = {
        "tipo_producto": "Crédito personal",
        "producto_overrides": {
            "monto_investigado": "100.00",
            "monto_perdida_fraude": "100.00",
            "monto_falla_procesos": "0.00",
            "monto_contingencia": "0.00",
            "monto_recuperado": "0.00",
        },
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, _ = app.validate_data()
    assert (
        f"Debe ingresar al menos un reclamo completo en el producto {DEFAULT_PRODUCT_ID} porque hay montos de pérdida, falla o contingencia"
        in errors
    )


def test_validate_data_rejects_collaborator_with_blank_flag():
    team_config = {"team_id": "T12345", "flag": ""}
    app = build_headless_app("Crédito personal", team_configs=[team_config])

    errors, _ = app.validate_data()

    assert "Colaborador 1: Debe ingresar el flag del colaborador." in errors


def test_validate_data_flags_duplicate_collaborators():
    duplicate_id = "T54321"
    team_configs = [{"team_id": duplicate_id}, {"team_id": duplicate_id}]
    app = build_headless_app("Crédito personal", team_configs=team_configs)

    errors, _ = app.validate_data()

    expected_fragment = f"El ID de colaborador {duplicate_id} está duplicado"
    assert any(expected_fragment in error for error in errors)


def test_validate_data_detects_case_insensitive_collaborator_duplicates():
    duplicate_id = "T54321"
    team_configs = [{"team_id": duplicate_id}, {"team_id": duplicate_id.lower()}]
    app = build_headless_app("Crédito personal", team_configs=team_configs)

    errors, _ = app.validate_data()

    expected_fragment = f"El ID de colaborador {duplicate_id} está duplicado"
    assert any(expected_fragment in error for error in errors)


def test_validate_data_accepts_collaborator_flag_in_catalog():
    team_config = {"team_id": "T12345", "flag": FLAG_COLABORADOR_LIST[-1]}
    app = build_headless_app("Crédito personal", team_configs=[team_config])

    errors, warnings = app.validate_data()

    assert errors == []
    assert warnings == []


def test_validate_data_requires_agency_data_for_commercial_channels():
    team_config = {
        "team_id": "T12345",
        "division": "DCA",
        "area": "Área Comercial Lima",
    }
    app = build_headless_app("Crédito personal", team_configs=[team_config])
    errors, _ = app.validate_data()
    assert (
        "El colaborador 1 debe registrar nombre y código de agencia por pertenecer a canales comerciales."
        in errors
    )


def test_validate_data_only_flags_required_agency_collaborator():
    team_configs = [
        {
            "team_id": "T11111",
            "division": "Canales de Atención",
            "area": "Área Comercial Norte",
        },
        {
            "team_id": "T22222",
            "division": "Banca Empresas",
            "area": "Área de riesgos",
        },
    ]
    app = build_headless_app("Crédito personal", team_configs=team_configs)

    errors, _ = app.validate_data()

    expected_message = (
        "El colaborador 1 debe registrar nombre y código de agencia por pertenecer a canales comerciales."
    )
    assert expected_message in errors
    assert not any(
        "Colaborador 2 debe registrar nombre y código de agencia" in error for error in errors
    )


def test_team_frame_inline_agency_validation_triggers_on_location(monkeypatch):
    team_module, RecordingValidator = _patch_team_module(monkeypatch)
    frame = team_module.TeamMemberFrame(
        parent=_UIStubWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        update_team_options=lambda: None,
        team_lookup={},
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
    )

    nombre_validator = _find_validator_instance(RecordingValidator.instances, "Nombre agencia")
    codigo_validator = _find_validator_instance(RecordingValidator.instances, "Código agencia")

    assert nombre_validator is not None
    assert codigo_validator is not None
    assert nombre_validator.validate_callback() is None
    assert codigo_validator.validate_callback() is None

    frame.division_var.set("Canales de Atención")
    frame.area_var.set("Área Comercial Lima")

    _trigger_focus_out(frame._area_entry)

    assert nombre_validator.last_custom_error == "Debe ingresar el nombre de la agencia."
    assert codigo_validator.last_custom_error == "Debe ingresar el código de agencia."


def test_team_frame_inline_agency_validation_clears_when_optional(monkeypatch):
    team_module, RecordingValidator = _patch_team_module(monkeypatch)
    frame = team_module.TeamMemberFrame(
        parent=_UIStubWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        update_team_options=lambda: None,
        team_lookup={},
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
    )

    nombre_validator = _find_validator_instance(RecordingValidator.instances, "Nombre agencia")
    codigo_validator = _find_validator_instance(RecordingValidator.instances, "Código agencia")

    frame.division_var.set("DCA")
    frame.area_var.set("Área Comercial Lima")
    frame.nombre_agencia_var.set("Agencia Lima")
    frame.codigo_agencia_var.set("123456")
    _trigger_focus_out(frame._division_entry)

    assert nombre_validator.last_custom_error is None
    assert codigo_validator.last_custom_error is None

    frame.division_var.set("Banca Empresas")
    frame.area_var.set("Área de riesgos")
    frame.nombre_agencia_var.set("")
    frame.codigo_agencia_var.set("")
    _trigger_focus_out(frame._division_entry)

    assert nombre_validator.last_custom_error is None
    assert codigo_validator.last_custom_error is None


def test_preserve_existing_client_contacts_on_partial_import():
    app = build_headless_app("Crédito personal")
    app.client_lookup = {}
    existing_client = DummyClientWithContacts(
        "12345678",
        telefonos="999111222",
        correos="cliente@correo.com",
        direcciones="Calle Falsa 123",
        accionado="Fiscalía; Penal",
    )
    app.client_frames = [existing_client]
    blank_row = {
        "id_cliente": "12345678",
        "telefonos": "",
        "correos": "",
        "direcciones": "",
        "accionado": "",
    }
    app._populate_client_frame_from_row(existing_client, blank_row, preserve_existing=True)
    assert existing_client.telefonos_var.get() == "999111222"
    assert existing_client.correos_var.get() == "cliente@correo.com"
    assert existing_client.direcciones_var.get() == "Calle Falsa 123"
    assert existing_client.accionado_var.get() == "Fiscalía; Penal"
    assert app.client_lookup["12345678"]["telefonos"] == "999111222"
    assert app.client_lookup["12345678"]["correos"] == "cliente@correo.com"
    assert app.client_lookup["12345678"]["direcciones"] == "Calle Falsa 123"
    assert app.client_lookup["12345678"]["accionado"] == "Fiscalía; Penal"
    errors, warnings = app.validate_data()
    assert errors == []
    assert warnings == []


def test_populate_from_data_keeps_product_dropdowns_blank_when_missing():
    app = FraudCaseApp.__new__(FraudCaseApp)
    product_frame = PopulateProductFrameStub()
    app.logs = []
    for attr in [
        'id_caso_var',
        'tipo_informe_var',
        'cat_caso1_var',
        'cat_caso2_var',
        'mod_caso_var',
        'canal_caso_var',
        'proceso_caso_var',
        'antecedentes_var',
        'modus_var',
        'hallazgos_var',
        'descargos_var',
        'conclusiones_var',
        'recomendaciones_var',
    ]:
        setattr(app, attr, DummyVar())
    app.client_frames = []
    app.team_frames = []
    app.product_frames = [product_frame]
    app.risk_frames = []
    app.norm_frames = []
    app._clear_case_state = lambda save_autosave=False: None
    app._schedule_summary_refresh = lambda data=None: None
    app.on_case_cat1_change = lambda: None
    app.on_case_cat2_change = lambda: None
    app.add_client = lambda: None
    app.add_team = lambda: None
    app.add_product = lambda: app.product_frames.append(PopulateProductFrameStub())
    app.add_risk = lambda: None
    app.add_norm = lambda: None

    cat1 = next(iter(TAXONOMIA))
    cat2 = next(iter(TAXONOMIA[cat1]))
    modalidad = TAXONOMIA[cat1][cat2][0]
    payload = {
        'caso': {
            'id_caso': '2024-0001',
            'tipo_informe': TIPO_INFORME_LIST[0],
            'categoria1': cat1,
            'categoria2': cat2,
            'modalidad': modalidad,
        },
        'clientes': [],
        'colaboradores': [],
        'productos': [
            {
                'id_producto': 'PRD1',
                'id_cliente': 'CLI1',
                'categoria1': cat1,
                'categoria2': cat2,
                'modalidad': modalidad,
                'canal': None,
                'proceso': '',
                'fecha_ocurrencia': '2023-01-01',
                'fecha_descubrimiento': '2023-01-02',
                'monto_investigado': '100.00',
                'tipo_moneda': None,
                'monto_perdida_fraude': '0.00',
                'monto_falla_procesos': '0.00',
                'monto_contingencia': '0.00',
                'monto_recuperado': '0.00',
                'monto_pago_deuda': '0.00',
                'tipo_producto': 'Crédito personal',
            }
        ],
        'reclamos': [],
        'involucramientos': [],
        'riesgos': [],
        'normas': [],
        'analisis': {},
    }

    app.populate_from_data(payload)

    assert product_frame.canal_var.get() == ""
    assert product_frame.proceso_var.get() == ""
    assert product_frame.moneda_var.get() == ""


def test_validate_data_normalizes_risk_exposure_after_populate():
    class _PopulateRiskFrameStub:
        def __init__(self):
            self.id_var = DummyVar("")
            self.lider_var = DummyVar("")
            self.descripcion_var = DummyVar("")
            self.criticidad_var = DummyVar("")
            self.exposicion_var = DummyVar("")
            self.planes_var = DummyVar("")

        def get_data(self):
            return {
                "id_riesgo": self.id_var.get().strip(),
                "lider": self.lider_var.get().strip(),
                "descripcion": self.descripcion_var.get().strip(),
                "criticidad": self.criticidad_var.get(),
                "exposicion_residual": self.exposicion_var.get().strip(),
                "planes_accion": self.planes_var.get().strip(),
            }

    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    case_cat1 = next(iter(TAXONOMIA))
    case_cat2 = next(iter(TAXONOMIA[case_cat1]))
    case_modalidad = TAXONOMIA[case_cat1][case_cat2][0]
    client_id = "12345678"
    for attr in [
        'id_caso_var',
        'tipo_informe_var',
        'cat_caso1_var',
        'cat_caso2_var',
        'mod_caso_var',
        'canal_caso_var',
        'proceso_caso_var',
        'antecedentes_var',
        'modus_var',
        'hallazgos_var',
        'descargos_var',
        'conclusiones_var',
        'recomendaciones_var',
    ]:
        setattr(app, attr, DummyVar(""))
    app.id_caso_var.set("2024-0001")
    app.tipo_informe_var.set(TIPO_INFORME_LIST[0])
    app.cat_caso1_var.set(case_cat1)
    app.cat_caso2_var.set(case_cat2)
    app.mod_caso_var.set(case_modalidad)
    app.canal_caso_var.set(CANAL_LIST[0])
    app.proceso_caso_var.set(PROCESO_LIST[0])
    app.client_frames = [DummyClientWithContacts(client_id)]
    app.team_frames = [DummyTeam("T12345")]
    app.product_frames = [
        DummyProductFrame(
            "Crédito personal",
            client_id,
            case_cat1,
            case_cat2,
            case_modalidad,
        )
    ]
    app.risk_frames = []
    app.norm_frames = []
    app._clear_case_state = lambda save_autosave=False: None
    app._schedule_summary_refresh = lambda data=None: None
    app.on_case_cat1_change = lambda: None
    app.on_case_cat2_change = lambda: None
    app.add_client = lambda: None
    app.add_team = lambda: None
    app.add_product = lambda: None
    app.add_norm = lambda: None
    app.add_risk = lambda: app.risk_frames.append(_PopulateRiskFrameStub())

    payload = {
        'caso': {
            'id_caso': '2024-0001',
            'tipo_informe': TIPO_INFORME_LIST[0],
            'categoria1': case_cat1,
            'categoria2': case_cat2,
            'modalidad': case_modalidad,
            'canal': CANAL_LIST[0],
            'proceso': PROCESO_LIST[0],
        },
        'clientes': [],
        'colaboradores': [],
        'productos': [],
        'reclamos': [],
        'involucramientos': [],
        'riesgos': [
            {
                'id_riesgo': 'RSK-000001',
                'lider': 'Líder',
                'descripcion': 'Descripción',
                'criticidad': CRITICIDAD_LIST[0],
                'exposicion_residual': '100',
                'planes_accion': 'Plan-1',
            }
        ],
        'normas': [],
        'analisis': {},
    }

    app.populate_from_data(payload)

    errors, warnings = app.validate_data()

    assert errors == []
    assert warnings == []
    gathered = app.gather_data()
    assert gathered['riesgos'][0]['exposicion_residual'] == '100.00'


def test_transform_summary_involucramientos_formats_amount():
    app = FraudCaseApp.__new__(FraudCaseApp)

    sanitized = app._transform_summary_clipboard_rows(
        "involucramientos",
        [["PRD-001", "T12345", "001.50"], ["PRD-002", "T54321", "10.5"]],
    )

    assert sanitized == [
        ("PRD-001", "T12345", "1.50"),
        ("PRD-002", "T54321", "10.50"),
    ]


def test_transform_summary_involucramientos_rejects_invalid_amount():
    app = FraudCaseApp.__new__(FraudCaseApp)

    with pytest.raises(ValueError) as excinfo:
        app._transform_summary_clipboard_rows(
            "involucramientos",
            [["PRD-001", "T12345", "10.123"]],
        )

    assert "dos decimales" in str(excinfo.value)


def test_ingest_summary_rows_involucramientos_updates_assignments():
    class _DummyCombo:
        def __init__(self, target_var):
            self._target_var = target_var

        def set(self, value):
            self._target_var.set(value)

    class _DummyInvolvement:
        def __init__(self, team_id=""):
            self.team_var = DummyVar(team_id)
            self.monto_var = DummyVar("")
            self.team_cb = _DummyCombo(self.team_var)

    class _ProductFrameStub:
        def __init__(self, product_id):
            self.id_var = DummyVar(product_id)
            self.involvements = []

        def add_involvement(self):
            row = _DummyInvolvement()
            self.involvements.append(row)
            return row

        def on_id_change(self, *_args, **_kwargs):
            return None

    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    app.detail_catalogs = {}
    app.detail_lookup_by_id = {}
    app._notify_products_created_without_details = lambda _ids: None
    app._report_missing_detail_ids = lambda *_args, **_kwargs: None
    product_frame = _ProductFrameStub("PRD-001")
    existing_row = _DummyInvolvement("T12345")
    existing_row.monto_var.set("")
    product_frame.involvements.append(existing_row)
    app.product_frames = [product_frame]
    app.team_frames = [DummyTeam("T12345"), DummyTeam("T54321")]
    app._obtain_product_slot_for_import = lambda: product_frame

    def _obtain_team_slot():
        slot = DummyTeam("TMP001")
        app.team_frames.append(slot)
        return slot

    app._obtain_team_slot_for_import = _obtain_team_slot
    app.save_auto = lambda: None
    notify_payload = {}

    def _notify(summary_sections=None):
        notify_payload['sections'] = summary_sections

    app._notify_dataset_changed = _notify
    sync_payload = {}

    def _sync(section_name, stay_on_summary=False):
        sync_payload["section"] = section_name
        sync_payload["stay"] = stay_on_summary

    app.sync_main_form_after_import = _sync

    rows = [
        ("PRD-001", "T12345", "100.00"),
        ("PRD-001", "T54321", "50.50"),
    ]

    processed = app.ingest_summary_rows("involucramientos", rows, stay_on_summary=True)

    assert processed == 2
    assert notify_payload == {"sections": "involucramientos"}
    assert sync_payload == {"section": "involucramientos", "stay": True}
    assert len(product_frame.involvements) == 2
    assert existing_row.monto_var.get() == "100.00"
    new_row = product_frame.involvements[-1]
    assert new_row.team_var.get() == "T54321"
    assert new_row.monto_var.get() == "50.50"


def test_ingest_summary_rows_involucramientos_requires_known_product():
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    app.detail_catalogs = {}
    app.detail_lookup_by_id = {}
    app.product_frames = []
    app.team_frames = [DummyTeam("T12345")]
    app.client_frames = []
    app._notify_dataset_changed = lambda *_args, **_kwargs: None
    app.save_auto = lambda: None
    app.sync_main_form_after_import = lambda *_args, **_kwargs: None

    rows = [("PRD-404", "T12345", "10.00")]

    with pytest.raises(ValueError) as excinfo:
        app.ingest_summary_rows("involucramientos", rows)

    assert "PRD-404" in str(excinfo.value)


def test_ingest_summary_rows_involucramientos_requires_known_collaborator():
    class _ProductFrameStub:
        def __init__(self):
            self.id_var = DummyVar("PRD-001")
            self.involvements = []

        def on_id_change(self, *_args, **_kwargs):
            return None

    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    app.detail_catalogs = {}
    app.detail_lookup_by_id = {}
    product_frame = _ProductFrameStub()
    app.product_frames = [product_frame]
    app.team_frames = []
    app.client_frames = []
    app._notify_dataset_changed = lambda *_args, **_kwargs: None
    app.save_auto = lambda: None
    app.sync_main_form_after_import = lambda *_args, **_kwargs: None

    rows = [("PRD-001", "T99999", "10.00")]

    with pytest.raises(ValueError) as excinfo:
        app.ingest_summary_rows("involucramientos", rows)

    assert "T99999" in str(excinfo.value)


def test_ingest_summary_rows_involucramientos_creates_product_from_details():
    class _ProductFrameStub:
        def __init__(self):
            self.id_var = DummyVar("")
            self.involvements = []
            self.populated_rows = []

        def on_id_change(self, *_args, **_kwargs):
            return None

    class _InvolvementRowStub:
        def __init__(self):
            self.team_var = DummyVar("")
            self.monto_var = DummyVar("")

    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    app.detail_catalogs = {}
    app.detail_lookup_by_id = {
        'id_producto': {
            'PRD-NEW': {
                'id_producto': 'PRD-NEW',
                'id_cliente': 'CLI-1',
                'tipo_producto': 'Crédito personal',
            }
        }
    }
    app.client_frames = []
    app.team_frames = [DummyTeam("T12345")]
    app.product_frames = []
    created_frames = []

    def _obtain_product_slot():
        frame = _ProductFrameStub()
        created_frames.append(frame)
        app.product_frames.append(frame)
        return frame

    app._obtain_product_slot_for_import = _obtain_product_slot

    def _merge_product_payload(frame, payload):
        frame.populated_rows.append(dict(payload))
        return dict(payload)

    app._merge_product_payload_with_frame = _merge_product_payload

    def _populate_product_frame(frame, row):
        frame.id_var.set(row.get('id_producto', ''))

    app._populate_product_frame_from_row = _populate_product_frame
    app._ensure_client_exists = lambda *_args, **_kwargs: (None, False)
    app._trigger_import_id_refresh = lambda *_args, **_kwargs: None

    def _obtain_involvement_slot(product_frame):
        row = _InvolvementRowStub()
        product_frame.involvements.append(row)
        return row

    app._obtain_involvement_slot = _obtain_involvement_slot
    autosave_called = []
    app.save_auto = lambda: autosave_called.append(True)
    sync_calls = []
    app.sync_main_form_after_import = lambda section, stay_on_summary=False: sync_calls.append((section, stay_on_summary))
    app._notify_dataset_changed = lambda *_args, **_kwargs: None

    rows = [("PRD-NEW", "T12345", "001.50")]

    processed = app.ingest_summary_rows("involucramientos", rows)

    assert processed == 1
    assert created_frames
    frame = created_frames[0]
    assert frame.id_var.get() == "PRD-NEW"
    assert frame.involvements[0].team_var.get() == "T12345"
    assert frame.involvements[0].monto_var.get() == "1.50"
    assert autosave_called
    assert sync_calls == [("involucramientos", False)]
