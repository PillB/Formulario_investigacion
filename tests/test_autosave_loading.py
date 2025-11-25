from __future__ import annotations

import json
import os
import types
from pathlib import Path

import app as app_module
import settings
from app import FraudCaseApp
from tests.test_save_and_send import _build_case_data


def _build_stub_app():
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    app._suppress_messagebox = True
    app.summary_tables = {"clientes": object()}
    app.root = None
    app.populate_calls = []
    app._display_toast = lambda *args, **kwargs: None
    app._update_window_title = lambda *args, **kwargs: None
    app._schedule_summary_refresh = lambda sections=None, data=None: setattr(app, "scheduled_data", data)
    app._flush_summary_refresh = lambda sections=None, data=None: setattr(app, "flushed_data", data)
    app._clear_case_state = lambda save_autosave=True: setattr(app, "cleared", True)
    app._get_external_drive_path = lambda: None

    def _populate(self, data):
        self.populate_calls.append(data)

    app.populate_from_data = types.MethodType(_populate, app)
    return app


def _setup_autosave_paths(tmp_path, monkeypatch):
    autosave_file = tmp_path / "autosave.json"
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)
    monkeypatch.setattr(app_module, "AUTOSAVE_FILE", autosave_file)
    monkeypatch.setattr(settings, "AUTOSAVE_FILE", autosave_file)
    return autosave_file


def test_load_autosave_uses_latest_candidate(tmp_path, monkeypatch):
    _setup_autosave_paths(tmp_path, monkeypatch)
    app = _build_stub_app()

    autosave_file = Path(app_module.AUTOSAVE_FILE)
    autosave_file.write_text(json.dumps(_build_case_data("2024-0001")), encoding="utf-8")
    os.utime(autosave_file, (1, 1))

    intermediate = tmp_path / "2024-0002_temp_20240101_120000.json"
    intermediate.write_text(json.dumps(_build_case_data("2024-0002")), encoding="utf-8")
    os.utime(intermediate, (2, 2))

    case_dir = tmp_path / "2024-0003"
    case_dir.mkdir()
    newest = case_dir / "2024-0003_temp_20240202_010101.json"
    newest.write_text(json.dumps(_build_case_data("2024-0003")), encoding="utf-8")
    os.utime(newest, (3, 3))

    app.load_autosave()

    assert app.populate_calls, "La carga de autosave debe poblar el formulario"
    loaded_dataset = app.populate_calls[-1]
    assert loaded_dataset.get("caso", {}).get("id_caso") == "2024-0003"
    assert getattr(app, "_last_autosave_source", "").endswith(newest.name)
    assert getattr(app, "flushed_data", None) is not None


def test_load_autosave_skips_invalid_and_falls_back(tmp_path, monkeypatch):
    autosave_file = _setup_autosave_paths(tmp_path, monkeypatch)
    app = _build_stub_app()

    autosave_file.write_text("{not json", encoding="utf-8")
    os.utime(autosave_file, (5, 5))

    valid_backup = tmp_path / "2024-0101_temp_20230101_000000.json"
    valid_backup.write_text(json.dumps(_build_case_data("2024-0101")), encoding="utf-8")
    os.utime(valid_backup, (4, 4))

    app.load_autosave()

    assert not getattr(app, "cleared", False)
    assert app.populate_calls, "Debe intentar cargar el respaldo válido"
    loaded_dataset = app.populate_calls[-1]
    assert loaded_dataset.get("caso", {}).get("id_caso") == "2024-0101"
    assert getattr(app, "_last_autosave_source", "").endswith(valid_backup.name)


def test_load_autosave_clears_when_all_candidates_fail(tmp_path, monkeypatch):
    autosave_file = _setup_autosave_paths(tmp_path, monkeypatch)
    app = _build_stub_app()

    autosave_file.write_text("{invalid json", encoding="utf-8")
    os.utime(autosave_file, (10, 10))

    app.load_autosave()

    assert not app.populate_calls
    assert getattr(app, "cleared", False)
