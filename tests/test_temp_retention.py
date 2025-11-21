"""Pruebas de retención y compactación de autosaves temporales."""

import os
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import app as app_module
import settings
from report_builder import CaseData
from tests.test_save_and_send import _build_case_data, _make_minimal_app


def test_temp_autosave_debounce_respects_critical_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)
    monkeypatch.setattr(app_module, "TEMP_AUTOSAVE_DEBOUNCE_SECONDS", 3600)
    monkeypatch.setattr(settings, "TEMP_AUTOSAVE_DEBOUNCE_SECONDS", 3600)
    monkeypatch.setattr(app_module, "ensure_external_drive_dir", lambda: None)
    app = _make_minimal_app()
    app._external_drive_path = None

    data = CaseData.from_mapping(_build_case_data("2024-0001"))
    app.save_temp_version(data=data)
    first_files = list(tmp_path.glob("*_temp_*.json"))
    assert len(first_files) == 1

    app.save_temp_version(data=data)
    assert len(list(tmp_path.glob("*_temp_*.json"))) == 1

    data.caso["tipo_informe"] = "Interno"
    app.save_temp_version(data=data)
    assert len(list(tmp_path.glob("*_temp_*.json"))) == 2


def test_trim_temp_versions_applies_retention_and_archives(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)
    monkeypatch.setattr(app_module, "TEMP_AUTOSAVE_MAX_PER_CASE", 2)
    monkeypatch.setattr(settings, "TEMP_AUTOSAVE_MAX_PER_CASE", 2)
    monkeypatch.setattr(app_module, "TEMP_AUTOSAVE_MAX_AGE_DAYS", 1)
    monkeypatch.setattr(settings, "TEMP_AUTOSAVE_MAX_AGE_DAYS", 1)
    monkeypatch.setattr(app_module, "TEMP_AUTOSAVE_COMPRESS_OLD", True)
    monkeypatch.setattr(settings, "TEMP_AUTOSAVE_COMPRESS_OLD", True)
    monkeypatch.setattr(app_module, "ensure_external_drive_dir", lambda: None)
    app = _make_minimal_app()
    app._external_drive_path = None

    case_id = "2024-7777"
    now = datetime.now()
    stale = []
    sequence = 0

    def _write_temp(offset_days: int) -> Path:
        nonlocal sequence
        ts_time = now - timedelta(days=offset_days, seconds=sequence)
        sequence += 1
        ts = ts_time.strftime("%Y%m%d_%H%M%S")
        path = tmp_path / f"{case_id}_temp_{ts}.json"
        path.write_text("{}", encoding="utf-8")
        mtime = ts_time.timestamp()
        os.utime(path, (mtime, mtime))
        return path

    recent_one = _write_temp(0)
    recent_two = _write_temp(0)
    stale.extend([_write_temp(2), _write_temp(3)])

    app._trim_temp_versions(case_id)

    remaining = list(tmp_path.glob(f"{case_id}_temp_*.json"))
    assert len(remaining) == 2
    for file_path in remaining:
        assert file_path in {recent_one, recent_two}

    archive_path = tmp_path / f"{case_id}_temp_archive.zip"
    assert archive_path.exists()
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
    for pruned in stale:
        assert pruned.name in names

