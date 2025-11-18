from datetime import datetime, timedelta

import pytest

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


class DummyClient:
    def __init__(self, client_id):
        self.tipo_id_var = DummyVar(TIPO_ID_LIST[0])
        self.id_var = DummyVar(client_id)


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
                "monto_investigado": "0",
                "tipo_moneda": TIPO_MONEDA_LIST[0],
                "monto_perdida_fraude": "0",
                "monto_falla_procesos": "0",
                "monto_contingencia": "0",
                "monto_recuperado": "0",
                "monto_pago_deuda": "0",
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
            {"id_colaborador": "", "monto_asignado": "150"},
        ],
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, _ = app.validate_data()
    assert any("monto sin colaborador" in error for error in errors)


def test_validate_data_flags_deleted_collaborator_reference():
    product_config = {
        "tipo_producto": "Crédito personal",
        "asignaciones": [
            {"id_colaborador": "T12345", "monto_asignado": "75"},
        ],
    }
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    app.team_frames = []  # Simula que el colaborador fue eliminado del formulario.
    errors, _ = app.validate_data()
    assert any("referencia un colaborador eliminado" in error for error in errors)


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
                    "monto_investigado": "100",
                    "monto_perdida_fraude": "0",
                    "monto_falla_procesos": "0",
                    "monto_contingencia": "0",
                    "monto_recuperado": "0",
                },
            },
            f"Las cuatro partidas (pérdida, falla, contingencia y recuperación) deben ser iguales al monto investigado en el producto {DEFAULT_PRODUCT_ID}",
        ),
        (
            {
                "tipo_producto": "Tarjeta de crédito",
                "producto_overrides": {
                    "monto_investigado": "50",
                    "monto_perdida_fraude": "40",
                    "monto_falla_procesos": "0",
                    "monto_contingencia": "10",
                    "monto_recuperado": "0",
                },
                "reclamos": [_complete_claim()],
            },
            f"El monto de contingencia debe ser igual al monto investigado en el producto {DEFAULT_PRODUCT_ID} porque es un crédito o tarjeta",
        ),
        (
            {
                "tipo_producto": "Crédito personal",
                "producto_overrides": {
                    "monto_investigado": "50",
                    "monto_pago_deuda": "60",
                },
            },
            f"El monto pagado de deuda excede el monto investigado en el producto {DEFAULT_PRODUCT_ID}",
        ),
        (
            {
                "tipo_producto": "Crédito personal",
                "producto_overrides": {
                    "monto_investigado": "100.123",
                    "monto_perdida_fraude": "0",
                    "monto_falla_procesos": "0",
                    "monto_contingencia": "0",
                    "monto_recuperado": "0",
                    "monto_pago_deuda": "0",
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


def test_validate_data_requires_risk_criticidad():
    app = build_headless_app("Crédito personal", risk_configs=[{"criticidad": ""}])

    errors, _ = app.validate_data()

    assert "Riesgo 1: Debe ingresar la criticidad del riesgo." in errors


def test_validate_data_rejects_unknown_risk_criticidad():
    invalid_value = "Inexistente"
    app = build_headless_app(
        "Crédito personal",
        risk_configs=[{"criticidad": invalid_value}],
    )

    errors, _ = app.validate_data()

    expected_message = f"Riesgo 1: La criticidad '{invalid_value}' no está en el catálogo CM."
    assert expected_message in errors


def test_validate_data_detects_duplicate_technical_keys():
    duplicate_assignments = [
        {"id_colaborador": "T12345", "monto_asignado": "10"},
        {"id_colaborador": "T12345", "monto_asignado": "5"},
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


def test_validate_data_requires_claim_when_losses_exist():
    product_config = {
        "tipo_producto": "Crédito personal",
        "producto_overrides": {
            "monto_investigado": "100",
            "monto_perdida_fraude": "100",
            "monto_falla_procesos": "0",
            "monto_contingencia": "0",
            "monto_recuperado": "0",
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
    app._reset_form_state = lambda confirm=False, save_autosave=False: True
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
                'monto_investigado': '100',
                'tipo_moneda': None,
                'monto_perdida_fraude': '0',
                'monto_falla_procesos': '0',
                'monto_contingencia': '0',
                'monto_recuperado': '0',
                'monto_pago_deuda': '0',
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
