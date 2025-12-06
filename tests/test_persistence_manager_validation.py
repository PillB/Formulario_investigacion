import json
from pathlib import Path

from utils.persistence_manager import CURRENT_SCHEMA_VERSION, PersistenceManager


def _collect_errors(path: Path) -> list[BaseException]:
    errors: list[BaseException] = []
    manager = PersistenceManager(None)
    manager.load(path, on_error=lambda exc: errors.append(exc))
    return errors


def test_persistence_manager_reports_malformed_json(tmp_path):
    corrupted = tmp_path / "corrupted.json"
    corrupted.write_text("{bad", encoding="utf-8")

    errors = _collect_errors(corrupted)

    assert errors
    assert corrupted.name in str(errors[0])


def test_persistence_manager_requires_dataset(tmp_path):
    payload = {"schema_version": CURRENT_SCHEMA_VERSION, "form_state": {}}
    missing_dataset = tmp_path / "missing_dataset.json"
    missing_dataset.write_text(json.dumps(payload), encoding="utf-8")

    errors = _collect_errors(missing_dataset)

    assert errors
    assert "dataset" in str(errors[0]).lower()


def test_persistence_manager_detects_version_mismatch(tmp_path):
    payload = {"schema_version": "0.0", "dataset": {}, "form_state": {}}
    wrong_version = tmp_path / "wrong_version.json"
    wrong_version.write_text(json.dumps(payload), encoding="utf-8")

    errors = _collect_errors(wrong_version)

    assert errors
    assert "versión" in str(errors[0]).lower()
