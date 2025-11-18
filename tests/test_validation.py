from datetime import datetime, timedelta

import pytest

from app import FraudCaseApp
from settings import (CANAL_LIST, PROCESO_LIST, TAXONOMIA, TIPO_ID_LIST,
                      TIPO_INFORME_LIST, TIPO_MONEDA_LIST)


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


class DummyTeam:
    def __init__(
        self,
        team_id,
        division="otra division",
        area="otra area",
        nombre_agencia="",
        codigo_agencia="",
        tipo_sancion="No aplica",
    ):
        self.id_var = DummyVar(team_id)
        self.codigo_agencia_var = DummyVar(codigo_agencia)
        self.division_var = DummyVar(division)
        self.area_var = DummyVar(area)
        self.nombre_agencia_var = DummyVar(nombre_agencia)
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


def build_headless_app(
    tipo_producto,
    *,
    product_configs=None,
    team_configs=None,
):
    app = FraudCaseApp.__new__(FraudCaseApp)
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
            tipo_sancion=config.get("tipo_sancion", "No aplica"),
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
    app.risk_frames = []
    app.norm_frames = []
    return app


def test_validate_data_accepts_catalog_product_type():
    app = build_headless_app("Crédito personal")
    errors, warnings = app.validate_data()
    assert errors == []
    assert warnings == []


def test_validate_data_flags_unknown_product_type():
    app = build_headless_app("Producto inventado fuera de catálogo")
    errors, _warnings = app.validate_data()
    assert any("no está en el catálogo" in error for error in errors)


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
    ],
)
def test_validate_data_enforces_amount_rules(product_config, expected_error):
    app = build_headless_app("Crédito personal", product_configs=[product_config])
    errors, _ = app.validate_data()
    assert expected_error in errors


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
