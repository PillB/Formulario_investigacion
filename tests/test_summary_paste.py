"""Headless tests for summary clipboard ingestion."""

import pytest

import app as fraud_app


class DummyVar:
    def __init__(self, value=""):
        self._value = value

    def set(self, value):
        self._value = value

    def get(self):
        return self._value


class ClientFrameStub:
    def __init__(self):
        self.id_var = DummyVar()
        self.tipo_id_var = DummyVar()
        self.flag_var = DummyVar()
        self.telefonos_var = DummyVar()
        self.correos_var = DummyVar()
        self.direcciones_var = DummyVar()
        self.accionado_var = DummyVar()

    def set_data(self, row):
        self.id_var.set((row.get("id_cliente") or "").strip())
        self.tipo_id_var.set((row.get("tipo_id") or "").strip())
        self.flag_var.set((row.get("flag") or "").strip())
        self.telefonos_var.set((row.get("telefonos") or "").strip())
        self.correos_var.set((row.get("correos") or "").strip())
        self.direcciones_var.set((row.get("direcciones") or "").strip())
        self.accionado_var.set((row.get("accionado") or "").strip())


class TeamFrameStub:
    def __init__(self):
        self.id_var = DummyVar()
        self.division_var = DummyVar()
        self.area_var = DummyVar()
        self.tipo_sancion_var = DummyVar()

    def set_data(self, row):
        self.id_var.set((row.get("id_colaborador") or "").strip())
        self.division_var.set((row.get("division") or "").strip())
        self.area_var.set((row.get("area") or "").strip())
        self.tipo_sancion_var.set((row.get("tipo_sancion") or "").strip() or "No aplica")


class ProductFrameStub:
    def __init__(self):
        self.id_var = DummyVar()
        self.client_var = DummyVar()
        self.tipo_prod_var = DummyVar()
        self.monto_inv_var = DummyVar()

    def set_data(self, row):
        self.id_var.set((row.get("id_producto") or "").strip())
        self.client_var.set((row.get("id_cliente") or "").strip())
        self.tipo_prod_var.set((row.get("tipo_producto") or "").strip())
        self.monto_inv_var.set((row.get("monto_investigado") or "").strip())


class RiskFrameStub:
    def __init__(self):
        self.id_var = DummyVar()
        self.lider_var = DummyVar()
        self.criticidad_var = DummyVar()
        self.exposicion_var = DummyVar()


class NormFrameStub:
    def __init__(self):
        self.id_var = DummyVar()
        self.descripcion_var = DummyVar()
        self.fecha_var = DummyVar()


class SummaryPasteAppStub(fraud_app.FraudCaseApp):
    def __init__(self):  # type: ignore[super-init-not-called]
        self.logs = []
        self.client_frames = []
        self.team_frames = []
        self.product_frames = []
        self.risk_frames = []
        self.norm_frames = []
        self._client_frames_by_id = {}
        self._team_frames_by_id = {}
        self._product_frames_by_id = {}
        self.detail_catalogs = {}
        self.client_lookup = {}
        self.team_lookup = {}
        self.product_lookup = {}
        self.summary_tables = {}
        self.summary_config = {}
        self.next_risk_number = 1

    def _hydrate_row_from_details(self, row, id_column, alias_headers):
        hydrated = dict(row or {})
        identifier = (hydrated.get(id_column) or "").strip()
        hydrated[id_column] = identifier
        return hydrated, False

    def _obtain_client_slot_for_import(self):
        frame = ClientFrameStub()
        self.client_frames.append(frame)
        return frame

    def _obtain_team_slot_for_import(self):
        frame = TeamFrameStub()
        self.team_frames.append(frame)
        return frame

    def _obtain_product_slot_for_import(self):
        frame = ProductFrameStub()
        self.product_frames.append(frame)
        return frame

    def _merge_client_payload_with_frame(self, frame, payload):
        return dict(payload)

    def _merge_team_payload_with_frame(self, frame, payload):
        return dict(payload)

    def _merge_product_payload_with_frame(self, frame, payload):
        return dict(payload)

    def _populate_client_frame_from_row(self, frame, row, preserve_existing=False):
        frame.set_data(row)

    def _populate_team_frame_from_row(self, frame, row):
        frame.set_data(row)

    def _populate_product_frame_from_row(self, frame, row):
        frame.set_data(row)

    def _trigger_import_id_refresh(self, frame, identifier, **_kwargs):
        normalized = (identifier or "").strip()
        if not normalized:
            return
        if isinstance(frame, ClientFrameStub):
            self._client_frames_by_id[normalized] = frame
        elif isinstance(frame, TeamFrameStub):
            self._team_frames_by_id[normalized] = frame
        elif isinstance(frame, ProductFrameStub):
            self._product_frames_by_id[normalized] = frame

    def _report_missing_detail_ids(self, *_args, **_kwargs):  # pragma: no cover - not needed
        return None

    def _notify_dataset_changed(self, *args, **kwargs):  # pragma: no cover
        return None

    def sync_main_form_after_import(self, *args, **kwargs):  # pragma: no cover
        return None

    def _notify_products_created_without_details(self, *_args, **_kwargs):  # pragma: no cover
        return None

    def _sync_product_lookup_claim_fields(self, *_args, **_kwargs):  # pragma: no cover
        return None

    def _ensure_client_exists(self, client_id, row_data=None):
        client_id = (client_id or "").strip()
        if not client_id:
            return None, False
        frame = self._find_client_frame(client_id)
        created = False
        if not frame:
            frame = self._obtain_client_slot_for_import()
            created = True
        payload = dict(row_data or {})
        payload["id_cliente"] = client_id
        has_extra_data = any(
            (value or "").strip() for key, value in payload.items() if key != "id_cliente"
        )
        if has_extra_data or not frame.id_var.get().strip():
            frame.set_data(payload)
        else:
            frame.id_var.set(client_id)
        self._trigger_import_id_refresh(frame, client_id)
        return frame, created

    def add_risk(self):
        frame = RiskFrameStub()
        self.risk_frames.append(frame)
        return frame

    def add_norm(self):
        frame = NormFrameStub()
        self.norm_frames.append(frame)
        return frame


@pytest.fixture
def summary_app():
    return SummaryPasteAppStub()


def test_valid_summary_rows_create_frames(summary_app):
    client_rows = summary_app._transform_clipboard_clients(
        [["12345678", "DNI", "Involucrado", "+51987654321", "user@example.com", "Calle 123", "Banco"]]
    )
    team_rows = summary_app._transform_clipboard_colaboradores(
        [["T12345", "Operaciones", "Área 1", "Amonestación"]]
    )
    product_rows = summary_app._transform_clipboard_productos(
        [["1234567890123", "12345678", "credito personal", "1000.50"]]
    )
    risk_rows = summary_app._transform_clipboard_riesgos(
        [["rsk-000010", "Líder", "Alto", "2500.00"]]
    )
    norm_rows = summary_app._transform_clipboard_normas(
        [["2024.001.01.01", "Norma de Prueba", "2024-05-01"]]
    )

    assert summary_app.ingest_summary_rows("clientes", client_rows) == 1
    assert summary_app.ingest_summary_rows("colaboradores", team_rows) == 1
    assert summary_app.ingest_summary_rows("productos", product_rows) == 1
    assert summary_app.ingest_summary_rows("riesgos", risk_rows) == 1
    assert summary_app.ingest_summary_rows("normas", norm_rows) == 1

    client_frame = summary_app.client_frames[0]
    assert client_frame.id_var.get() == "12345678"
    assert client_frame.tipo_id_var.get() == "DNI"
    assert client_frame.flag_var.get() == "Involucrado"
    assert client_frame.telefonos_var.get() == "+51987654321"

    team_frame = summary_app.team_frames[0]
    assert team_frame.id_var.get() == "T12345"
    assert team_frame.tipo_sancion_var.get() == "Amonestación"

    product_frame = summary_app.product_frames[0]
    assert product_frame.id_var.get() == "1234567890123"
    assert product_frame.client_var.get() == "12345678"
    assert product_frame.tipo_prod_var.get() == "Crédito personal"
    assert product_frame.monto_inv_var.get() == "1000.50"

    risk_frame = summary_app.risk_frames[0]
    assert risk_frame.id_var.get() == "RSK-000010"
    assert risk_frame.criticidad_var.get() == "Alto"
    assert risk_frame.exposicion_var.get() == "2500.00"

    norm_frame = summary_app.norm_frames[0]
    assert norm_frame.id_var.get() == "2024.001.01.01"
    assert norm_frame.descripcion_var.get() == "Norma de Prueba"
    assert norm_frame.fecha_var.get() == "2024-05-01"


def test_invalid_catalog_and_amount_errors(summary_app):
    with pytest.raises(ValueError) as exc_info:
        summary_app._transform_clipboard_productos(
            [["1234567890123", "12345678", "tipo inexistente", "100.00"]]
        )
    assert "tipo de producto 'tipo inexistente'" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        summary_app._transform_clipboard_riesgos(
            [["RSK-000001", "Líder", "Bajo", "monto"]]
        )
    assert "la exposición residual debe ser un número válido" in str(exc_info.value)


def test_duplicate_risk_and_norm_paste_logs_warning(monkeypatch, summary_app):
    existing_risk = summary_app.add_risk()
    existing_risk.id_var.set("RSK-000999")
    existing_norm = summary_app.add_norm()
    existing_norm.id_var.set("2024.999.99.99")

    warnings = []

    def fake_warning(title, message):
        warnings.append((title, message))

    monkeypatch.setattr(fraud_app.messagebox, "showwarning", fake_warning)

    risk_rows = summary_app._transform_clipboard_riesgos(
        [["RSK-000999", "Líder", "Bajo", "0.00"]]
    )
    norm_rows = summary_app._transform_clipboard_normas(
        [["2024.999.99.99", "Norma duplicada", "2024-01-01"]]
    )

    assert summary_app.ingest_summary_rows("riesgos", risk_rows) == 0
    assert summary_app.ingest_summary_rows("normas", norm_rows) == 0
    assert len(summary_app.risk_frames) == 1
    assert len(summary_app.norm_frames) == 1
    assert any("Riesgo duplicado" in log["mensaje"] for log in summary_app.logs)
    assert any("Norma duplicada" in log["mensaje"] for log in summary_app.logs)
    assert warnings == [
        ("Riesgos duplicados", "Se ignoraron los siguientes riesgos ya existentes:\nRSK-000999"),
        ("Normas duplicadas", "Se ignoraron las siguientes normas ya existentes:\n2024.999.99.99"),
    ]
