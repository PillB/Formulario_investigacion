import csv
import json
import types
from datetime import datetime
from pathlib import Path

import pytest

import app as app_module
import settings
from app import FraudCaseApp
from report_builder import CaseData
from utils.historical_consolidator import append_historical_records


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):  # pragma: no cover - firma compatible
        return cls(2024, 1, 1, 12, 0, 0)


def _build_case_payload(case_id: str) -> CaseData:
    return CaseData.from_mapping(
        {
            "caso": {
                "id_caso": case_id,
                "tipo_informe": "Inicial",
                "categoria1": "Cat1",
                "categoria2": "Cat2",
                "modalidad": "Modalidad",
                "canal": "Canal",
                "proceso": "Proceso",
                "fecha_de_ocurrencia": "2024-01-10",
                "fecha_de_descubrimiento": "2024-01-11",
                "matricula_investigador": "TM-1234",
                "investigador_nombre": "Lead",
                "investigador_cargo": "Cargo",
            },
            "clientes": [
                {
                    "id_cliente": "CL-1",
                    "nombres": "Ana",
                    "apellidos": "Gómez",
                    "tipo_id": "DNI",
                    "flag": "Involucrado",
                    "telefonos": "999",
                    "correos": "ana@example.com",
                    "direcciones": "Calle 1",
                    "accionado": "",
                }
            ],
            "colaboradores": [],
            "productos": [
                {
                    "id_producto": "P-1",
                    "id_cliente": "CL-1",
                    "categoria1": "Cat1",
                    "categoria2": "Cat2",
                    "modalidad": "Modalidad",
                    "canal": "Canal",
                    "proceso": "Proceso",
                    "fecha_ocurrencia": "2024-01-10",
                    "fecha_descubrimiento": "2024-01-11",
                    "tipo_producto": "Tarjeta",
                    "tipo_moneda": "PEN",
                    "monto_investigado": "100.00",
                    "monto_perdida_fraude": "10.00",
                    "monto_falla_procesos": "0.00",
                    "monto_contingencia": "20.00",
                    "monto_recuperado": "5.00",
                    "monto_pago_deuda": "0.00",
                }
            ],
            "reclamos": [],
            "involucramientos": [],
            "riesgos": [],
            "normas": [],
            "analisis": {},
            "encabezado": {},
            "operaciones": [],
            "anexos": [],
            "firmas": [],
            "recomendaciones_categorias": {},
        }
    )


def _build_consolidation_app(tmp_path: Path, external_dir: Path | None) -> FraudCaseApp:
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    app.pending_consolidation_flag = False
    app._suppress_messagebox = True
    app._docx_available = False
    app._pending_manifest_path = tmp_path / "pending_consolidation.txt"
    app._normalize_analysis_texts = types.MethodType(lambda self, payload: payload or {}, app)
    app._build_export_definitions = types.MethodType(lambda self, data: [], app)
    app._update_architecture_diagram = types.MethodType(lambda self, defs: None, app)
    app._normalize_identifier = FraudCaseApp._normalize_identifier
    app._get_external_drive_path = types.MethodType(lambda self: external_dir, app)
    app._get_pending_manifest_path = types.MethodType(lambda self: app._pending_manifest_path, app)
    return app


def test_append_historical_records_creates_and_appends(tmp_path):
    header = ["id_cliente", "id_caso"]
    rows = [{"id_cliente": "=CL1", "id_caso": "2024-0001"}]
    timestamp = datetime(2024, 1, 1, 12, 0, 0)

    first_path = append_historical_records(
        "clientes", rows, header, tmp_path, "2024-0001", timestamp=timestamp
    )
    second_rows = [{"id_cliente": "CL2"}]
    second_path = append_historical_records(
        "clientes", second_rows, header, tmp_path, "2024-0001", timestamp=timestamp
    )

    assert first_path == second_path == tmp_path / "h_clientes.csv"
    contents = (tmp_path / "h_clientes.csv").read_text(encoding="utf-8").splitlines()
    assert contents[0].split(",") == ["id_cliente", "id_caso", "case_id", "fecactualizacion"]

    data_lines = contents[1:]
    assert len(data_lines) == 2
    first_columns = data_lines[0].split(",")
    assert first_columns[0] == "'=CL1"
    assert first_columns[2] == "2024-0001"
    assert first_columns[3] == "2024-01-01T12:00:00"

    second_columns = data_lines[1].split(",")
    assert second_columns[0] == "CL2"
    assert second_columns[1] == "'-"
    assert second_columns[2] == "2024-0001"
    assert second_columns[3] == "2024-01-01T12:00:00"


def test_perform_save_exports_records_history_and_manifest(tmp_path, monkeypatch):
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    manifest_path = tmp_path / "pending_consolidation.txt"
    case_id = "2024-7777"
    data = _build_case_payload(case_id)
    app = _build_consolidation_app(tmp_path, external_dir=None)
    app._pending_manifest_path = manifest_path
    monkeypatch.setattr(app_module, "datetime", FrozenDatetime)

    app._perform_save_exports(data, export_dir, case_id)
    data.clientes.append({"id_cliente": "CL-2", "nombres": "Bea"})
    app._perform_save_exports(data, export_dir, case_id)

    history_path = export_dir / "h_clientes.csv"
    assert history_path.exists()
    rows = list(csv.DictReader(history_path.open(newline="", encoding="utf-8")))
    assert len(rows) >= 2
    assert all(row["case_id"] == case_id for row in rows)
    assert {row["id_cliente"] for row in rows} >= {"CL-1", "CL-2"}
    assert all(row["fecactualizacion"] == FrozenDatetime.now().isoformat() for row in rows[-2:])

    assert manifest_path.exists()
    manifest_lines = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            manifest_lines.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    assert len(manifest_lines) == 2
    assert all(entry.get("case_id") == case_id for entry in manifest_lines)
    assert all("h_clientes.csv" in entry.get("history_files", []) for entry in manifest_lines)


def test_startup_retry_replays_pending_manifest_once(tmp_path, monkeypatch):
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    external_dir = tmp_path / "external drive"
    manifest_path = tmp_path / "pending_consolidation.txt"
    case_id = "2024-8888"
    monkeypatch.setattr(app_module, "PENDING_CONSOLIDATION_FILE", manifest_path)
    monkeypatch.setattr(settings, "PENDING_CONSOLIDATION_FILE", manifest_path)
    monkeypatch.setattr(app_module, "datetime", FrozenDatetime)

    initial_app = _build_consolidation_app(tmp_path, external_dir=None)
    initial_app._pending_manifest_path = manifest_path
    data = _build_case_payload(case_id)
    initial_app._perform_save_exports(data, export_dir, case_id)
    manifest_path.write_text(manifest_path.read_text(encoding="utf-8") + "\n" + "{bad json", encoding="utf-8")

    external_dir.mkdir(parents=True, exist_ok=True)
    retry_app = _build_consolidation_app(tmp_path, external_dir=external_dir)
    retry_app._pending_manifest_path = manifest_path
    retry_app._external_drive_path = external_dir
    retry_app.logs = []

    retry_app._process_pending_consolidations()
    retry_app._process_pending_consolidations()

    history_path = external_dir / case_id / "h_clientes.csv"
    assert history_path.exists()
    rows = list(csv.DictReader(history_path.open(newline="", encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["case_id"] == case_id
    assert rows[0]["fecactualizacion"] == FrozenDatetime.now().isoformat()
    assert not manifest_path.exists()


def test_manifest_write_failure_sets_pending_flag(tmp_path, monkeypatch):
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    manifest_path = tmp_path / "blocked" / "pending_consolidation.txt"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    app = _build_consolidation_app(tmp_path, external_dir=None)
    app._pending_manifest_path = manifest_path
    data = _build_case_payload("2024-9999")

    original_open = Path.open

    def guarded_open(self, *args, **kwargs):
        if self == manifest_path:
            raise OSError("read-only")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    app._perform_save_exports(data, export_dir, "2024-9999")

    history_path = export_dir / "h_clientes.csv"
    assert history_path.exists()
    assert app.pending_consolidation_flag
    assert not manifest_path.exists()
