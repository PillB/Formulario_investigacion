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
    def __init__(self, team_id):
        self.id_var = DummyVar(team_id)
        self.codigo_agencia_var = DummyVar("")
        self.division_var = DummyVar("otra division")
        self.area_var = DummyVar("otra area")
        self.nombre_agencia_var = DummyVar("")
        self.tipo_sancion_var = DummyVar("No aplica")


class DummyProductFrame:
    def __init__(self, tipo_producto, client_id, case_cat1, case_cat2, case_modalidad):
        self._product_id = "1234567890123"
        self.tipo_prod_var = DummyVar(tipo_producto)
        self.id_var = DummyVar(self._product_id)
        self._product = {
            "producto": {
                "id_producto": self._product_id,
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
            "reclamos": [],
            "asignaciones": [],
        }

    def get_data(self):
        return self._product


def build_headless_app(tipo_producto):
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
    app.team_frames = [DummyTeam("T12345")]
    app.product_frames = [
        DummyProductFrame(tipo_producto, client_id, case_cat1, case_cat2, case_modalidad)
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
