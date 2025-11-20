from types import SimpleNamespace

from tests.stubs import DummyVar
from ui.frames.clients import ClientFrame
from ui.frames.products import ClaimRow, ProductFrame
from ui.frames.risk import RiskFrame


class _ComboStub:
    def __init__(self):
        self.values = []
        self.current = ""

    def __getitem__(self, key):
        if key == "values":
            return list(self.values)
        raise KeyError(key)

    def __setitem__(self, key, value):
        if key == "values":
            self.values = list(value)
            return None
        raise KeyError(key)

    def set(self, value):
        self.current = value


def test_client_autofill_respects_preserve_existing_flag():
    logs: list[str] = []
    frame = ClientFrame.__new__(ClientFrame)
    frame.idx = 0
    frame.logs = logs
    frame.client_lookup = {
        "CLI-1": {
            "tipo_id": "DNI",
            "flag": "Afectado",
            "telefonos": "999111222",
            "correos": "auto@example.com",
            "direcciones": "Calle 123",
            "accionado": "Fiscalía",
        }
    }
    frame.tipo_id_var = DummyVar("Manual tipo")
    frame.id_var = DummyVar("CLI-1")
    frame.flag_var = DummyVar("Manual flag")
    frame.telefonos_var = DummyVar("")
    frame.correos_var = DummyVar("")
    frame.direcciones_var = DummyVar("")
    frame.accionado_var = DummyVar("")
    frame._last_missing_lookup_id = None
    frame._last_tracked_id = ""
    frame.id_change_callback = None
    frame.update_client_options = lambda: None
    frame.schedule_summary_refresh = lambda *_args, **_kwargs: None
    frame._log_change = lambda *_args, **_kwargs: logs.append("log")
    frame.set_accionado_from_text = lambda value: frame.accionado_var.set(value.strip())
    frame._notify_id_change = lambda: None

    frame.on_id_change(preserve_existing=True)

    assert frame.tipo_id_var.get() == "Manual tipo"
    assert frame.flag_var.get() == "Manual flag"
    assert frame.telefonos_var.get() == "999111222"
    assert frame.correos_var.get() == "auto@example.com"
    assert frame.direcciones_var.get() == "Calle 123"
    assert frame.accionado_var.get() == "Fiscalía"


def test_product_autofill_preserves_dirty_amounts():
    logs: list[str] = []
    frame = ProductFrame.__new__(ProductFrame)
    frame.idx = 0
    frame.product_lookup = {
        "P-1": {
            "id_producto": "P-1",
            "monto_investigado": "250.00",
            "tipo_producto": "Crédito personal",
        }
    }
    frame.claims = []
    frame.id_var = DummyVar("P-1")
    frame.client_var = DummyVar("")
    frame.client_cb = _ComboStub()
    frame.cat1_var = DummyVar("")
    frame.cat2_var = DummyVar("")
    frame.mod_var = DummyVar("")
    frame.canal_var = DummyVar("")
    frame.proceso_var = DummyVar("")
    frame.tipo_prod_var = DummyVar("Manual tipo")
    frame.fecha_oc_var = DummyVar("")
    frame.fecha_desc_var = DummyVar("")
    frame.monto_inv_var = DummyVar("150.00")
    frame.moneda_var = DummyVar("")
    frame.monto_perdida_var = DummyVar("")
    frame.monto_falla_var = DummyVar("")
    frame.monto_cont_var = DummyVar("")
    frame.monto_rec_var = DummyVar("")
    frame.monto_pago_var = DummyVar("")
    frame._last_missing_lookup_id = None
    frame._last_tracked_id = ""
    frame.log_change = lambda *_args, **_kwargs: logs.append("product")
    frame.schedule_summary_refresh = lambda *_args, **_kwargs: None
    frame.on_cat1_change = lambda: None
    frame.on_cat2_change = lambda: None
    frame.extract_claims_from_payload = lambda payload: []
    frame.claims_have_content = lambda: False
    frame.set_claims_from_payload = lambda *_args, **_kwargs: logs.append("claims")
    frame._notify_id_change = lambda *_args, **_kwargs: None

    frame.on_id_change(preserve_existing=True)

    assert frame.monto_inv_var.get() == "150.00"
    assert frame.tipo_prod_var.get() == "Manual tipo"


def test_claim_autofill_skips_dirty_fields(monkeypatch):
    logs: list[str] = []

    product_stub = SimpleNamespace(
        claim_lookup={
            "C00000010": {
                "id_reclamo": "C00000010",
                "nombre_analitica": "Auto analítica",
                "codigo_analitica": "4300000010",
            }
        },
        idx=0,
        log_change=lambda *_args, **_kwargs: logs.append("claim_log"),
        persist_lookup_snapshot=lambda: logs.append("persist"),
    )
    row = ClaimRow.__new__(ClaimRow)
    row.product_frame = product_stub
    row.id_var = DummyVar("C00000010")
    row.name_var = DummyVar("Manual nombre")
    row.code_var = DummyVar("")
    row._last_missing_lookup_id = None

    row.on_id_change(preserve_existing=True)

    assert row.name_var.get() == "Manual nombre"
    assert row.code_var.get() == "4300000010"
    assert "persist" in logs


def test_risk_autofill_preserves_manual_entries():
    logs: list[str] = []
    frame = RiskFrame.__new__(RiskFrame)
    frame.idx = 0
    frame.risk_lookup = {
        "RSK-000123": {
            "id_riesgo": "RSK-000123",
            "lider": "Auto líder",
            "descripcion": "Auto descripción",
            "criticidad": "Alta",
            "exposicion_residual": "100.00",
            "planes_accion": "Auto plan",
        }
    }
    frame.id_var = DummyVar("RSK-000123")
    frame.lider_var = DummyVar("Manual líder")
    frame.descripcion_var = DummyVar("")
    frame.criticidad_var = DummyVar("Manual")
    frame.exposicion_var = DummyVar("")
    frame.planes_var = DummyVar("")
    frame._last_missing_lookup_id = None
    frame.change_notifier = lambda message: logs.append(message)
    frame.logs = []

    frame.on_id_change(preserve_existing=True)

    assert frame.lider_var.get() == "Manual líder"
    assert frame.descripcion_var.get() == "Auto descripción"
    assert frame.criticidad_var.get() == "Manual"
    assert frame.exposicion_var.get() == "100.00"
    assert frame.planes_var.get() == "Auto plan"
