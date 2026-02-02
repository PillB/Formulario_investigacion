from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import app as app_module
import json
from app import FraudCaseApp
from utils.persistence_manager import CURRENT_SCHEMA_VERSION
from tests.stubs import DummyVar, InvolvementRowStub, RichTextWidgetStub


class _PopulateClientFrame:
    def __init__(self):
        self.tipo_id_var = DummyVar()
        self.id_var = DummyVar()
        self.flag_var = DummyVar()
        self.telefonos_var = DummyVar()
        self.correos_var = DummyVar()
        self.direcciones_var = DummyVar()
        self.accionado_var = DummyVar()

    def set_accionado_from_text(self, value: str):
        self.accionado_var.set(value.strip())


class _ComboStub:
    def __init__(self):
        self.values: list[str] = []
        self.current = ""

    def __setitem__(self, key, value):
        if key == "values":
            self.values = list(value)
            return None
        raise KeyError(key)

    def set(self, value):
        self.current = value


class _PopulateTeamFrame:
    def __init__(self):
        self.id_var = DummyVar()
        self.flag_var = DummyVar()
        self.nombres_var = DummyVar()
        self.apellidos_var = DummyVar()
        self.division_var = DummyVar()
        self.area_var = DummyVar()
        self.servicio_var = DummyVar()
        self.puesto_var = DummyVar()
        self.fecha_carta_inmediatez_var = DummyVar()
        self.fecha_carta_renuncia_var = DummyVar()
        self.motivo_cese_var = DummyVar()
        self.nombre_agencia_var = DummyVar()
        self.codigo_agencia_var = DummyVar()
        self.tipo_falta_var = DummyVar()
        self.tipo_sancion_var = DummyVar()


class _PopulateProductFrame:
    def __init__(self):
        self.id_var = DummyVar()
        self.client_var = DummyVar()
        self.cat1_var = DummyVar()
        self.cat2_var = DummyVar()
        self.mod_var = DummyVar()
        self.canal_var = DummyVar()
        self.proceso_var = DummyVar()
        self.fecha_oc_var = DummyVar()
        self.fecha_desc_var = DummyVar()
        self.monto_inv_var = DummyVar()
        self.moneda_var = DummyVar()
        self.monto_perdida_var = DummyVar()
        self.monto_falla_var = DummyVar()
        self.monto_cont_var = DummyVar()
        self.monto_rec_var = DummyVar()
        self.monto_pago_var = DummyVar()
        self.tipo_prod_var = DummyVar()
        self.claims_payload = None
        self.involvements: list[InvolvementRowStub] = []
        self.client_involvements: list[InvolvementRowStub] = []
        self.refresh_amounts_called = False

    def on_cat1_change(self):
        return None

    def on_cat2_change(self):
        return None

    def set_claims_from_data(self, claims):
        self.claims_payload = list(claims)

    def clear_involvements(self):
        self.involvements.clear()

    def add_involvement(self):
        row = InvolvementRowStub()
        self.involvements.append(row)
        return row

    def add_client_involvement(self):
        row = InvolvementRowStub()
        self.client_involvements.append(row)
        return row

    def _refresh_amount_validation_after_programmatic_update(self):
        self.refresh_amounts_called = True


class _LoadingAppFactory:
    def __init__(self):
        self.app = FraudCaseApp.__new__(FraudCaseApp)
        self.app.logs = []
        self.app._suppress_messagebox = True
        self.app._rich_text_images = defaultdict(list)
        self.app._rich_text_image_sources = {}
        self.app._encabezado_vars = {}
        self.app._operation_vars = {}
        self.app._anexo_vars = {}
        self.app._firmas_vars = {}
        self.app._encabezado_data = {}
        self.app._operaciones_data = []
        self.app._anexos_data = []
        self.app._firmas_data = []
        self.app._recomendaciones_categorias = {}
        self.app.summary_tables = {}
        self.app.root = None
        self.app.client_frames = []
        self.app.team_frames = []
        self.app.product_frames = []
        self.app.risk_frames = []
        self.app.norm_frames = []
        self.app.antecedentes_text = RichTextWidgetStub()
        self.app.modus_text = RichTextWidgetStub()
        self.app.hallazgos_text = RichTextWidgetStub()
        self.app.descargos_text = RichTextWidgetStub()
        self.app.conclusiones_text = RichTextWidgetStub()
        self.app.recomendaciones_text = RichTextWidgetStub()
        self.app._refresh_shared_norm_tree = lambda: None
        self.app._sync_extended_sections_to_ui = lambda: None
        self.app._rebuild_frame_id_indexes = lambda: None
        self.app._run_duplicate_check_post_load = lambda: None
        self.app._schedule_summary_refresh = lambda **_kwargs: None
        self.app._flush_summary_refresh = lambda **_kwargs: None
        self.app._update_window_title = lambda **_kwargs: None
        self.app.case_cat2_cb = _ComboStub()
        self.app.case_mod_cb = _ComboStub()
        self.app._log_navigation_change = lambda *_args, **_kwargs: None
        self.app._last_fraud_warning_at = None

    def add_client(self):
        frame = _PopulateClientFrame()
        self.app.client_frames.append(frame)
        return frame

    def add_team(self):
        frame = _PopulateTeamFrame()
        self.app.team_frames.append(frame)
        return frame

    def add_product(self, initialize_rows=True):  # noqa: ARG002
        frame = _PopulateProductFrame()
        self.app.product_frames.append(frame)
        return frame

    def add_risk(self):
        from tests.stubs import RiskFrameStub

        frame = RiskFrameStub()
        self.app.risk_frames.append(frame)
        return frame

    def add_norm(self):
        from tests.stubs import NormFrameStub

        frame = NormFrameStub()
        self.app.norm_frames.append(frame)
        return frame

    def build(self) -> FraudCaseApp:
        self.app.add_client = self.add_client
        self.app.add_team = self.add_team
        self.app.add_product = self.add_product
        self.app.add_risk = self.add_risk
        self.app.add_norm = self.add_norm
        self.app._clear_case_state = lambda save_autosave=False: (
            self.app.client_frames.clear(),
            self.app.team_frames.clear(),
            self.app.product_frames.clear(),
            self.app.risk_frames.clear(),
            self.app.norm_frames.clear(),
        )
        return self.app


def _build_loading_app() -> FraudCaseApp:
    factory = _LoadingAppFactory()
    return factory.build()


def test_load_form_dialog_populates_from_fixture(monkeypatch, messagebox_spy):
    fixture_path = Path(__file__).parent / "fixtures" / "test-save.json"
    app = _build_loading_app()
    monkeypatch.setattr(app_module.filedialog, "askopenfilename", lambda **_: str(fixture_path))

    app.load_form_dialog()

    assert len(app.client_frames) == 2
    assert [frame.id_var.get() for frame in app.client_frames] == ["12345678", "20123456789"]
    assert app.client_frames[0].telefonos_var.get() == "+51999888777"
    assert app.client_frames[1].accionado_var.get() == "Tribu Canal Impactado"

    assert len(app.team_frames) == 2
    assert app.team_frames[0].division_var.get() == "Riesgos"
    assert app.team_frames[1].nombre_agencia_var.get() == "Agencia Trujillo Centro"

    assert len(app.product_frames) == 3
    primary_product = app.product_frames[0]
    assert primary_product.id_var.get() == "1234567890123"
    assert primary_product.canal_var.get() == "Agencias"
    assert primary_product.monto_cont_var.get() == "2000.00"
    assert primary_product.claims_payload[0]["id_reclamo"] == "C12345678"
    assert len(primary_product.involvements) == 1
    assert primary_product.involvements[0].team_var.get() == "T12345"

    third_product = app.product_frames[2]
    assert third_product.id_var.get() == "4455667788990011"
    assert third_product.involvements[0].monto_var.get() == "300.00"

    assert len(app.risk_frames) == 1
    assert app.risk_frames[0].descripcion_var.get().startswith("Riesgo de repetición")

    assert len(app.norm_frames) == 1
    assert app.norm_frames[0].id_var.get() == "2024.001.01.01"

    assert app.antecedentes_text.get() == "El caso fue reportado por monitoreo preventivo."
    assert app.recomendaciones_text.get().startswith("Fortalecer MFA")


def test_load_form_dialog_reports_invalid_json(monkeypatch, messagebox_spy, tmp_path):
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{bad", encoding="utf-8")
    app = _build_loading_app()
    app._suppress_messagebox = False
    monkeypatch.setattr(app_module.filedialog, "askopenfilename", lambda **_: str(invalid_json))

    app.load_form_dialog()

    notifications = getattr(app, "_ui_notifications", [])
    assert notifications
    level = notifications[0].get("level")
    message = notifications[0].get("message", "")
    assert level == "error"
    assert "No se pudo cargar el formulario" in message
    assert "invalid.json" in message
    assert not app.client_frames


def test_load_form_dialog_requires_dataset_section(monkeypatch, messagebox_spy, tmp_path):
    missing_dataset = tmp_path / "missing_dataset.json"
    missing_dataset.write_text(
        json.dumps({"schema_version": CURRENT_SCHEMA_VERSION, "form_state": {}}),
        encoding="utf-8",
    )
    app = _build_loading_app()
    app._suppress_messagebox = False
    monkeypatch.setattr(app_module.filedialog, "askopenfilename", lambda **_: str(missing_dataset))

    app.load_form_dialog()

    notifications = getattr(app, "_ui_notifications", [])
    assert notifications
    assert notifications[0].get("level") == "error"
    assert "dataset" in notifications[0].get("message", "").lower()
    assert not app.client_frames


def test_load_form_dialog_detects_schema_version_mismatch(monkeypatch, messagebox_spy, tmp_path):
    incompatible = tmp_path / "wrong_version.json"
    incompatible.write_text(
        json.dumps(
            {
                "schema_version": "0.5",
                "dataset": {"caso": {}},
                "form_state": {},
            }
        ),
        encoding="utf-8",
    )
    app = _build_loading_app()
    app._suppress_messagebox = False
    monkeypatch.setattr(app_module.filedialog, "askopenfilename", lambda **_: str(incompatible))

    app.load_form_dialog()

    notifications = getattr(app, "_ui_notifications", [])
    assert notifications
    assert notifications[0].get("level") == "error"
    assert "versión" in notifications[0].get("message", "").lower()
    assert not app.client_frames


def test_load_form_dialog_cancel_does_not_mutate_state(monkeypatch):
    app = _build_loading_app()
    app.id_caso_var = DummyVar("BASE")
    app.client_frames.append(_PopulateClientFrame())
    monkeypatch.setattr(app_module.filedialog, "askopenfilename", lambda **_: "")

    app.load_form_dialog()

    assert app.id_caso_var.get() == "BASE"
    assert len(app.client_frames) == 1
