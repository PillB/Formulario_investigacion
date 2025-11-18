"""Tests relacionados con las rutas declaradas en ``settings``."""

from __future__ import annotations

from importlib import reload
from pathlib import Path

import settings


def test_team_details_file_exists_from_repo_root(monkeypatch):
    """La ruta al catálogo del equipo debe existir desde la raíz del repo."""

    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)
    reloaded_settings = reload(settings)
    team_details_path = Path(reloaded_settings.TEAM_DETAILS_FILE)
    assert team_details_path.is_file(), team_details_path


def test_autosave_defaults_to_cwd(tmp_path, monkeypatch):
    """Autosave/log files deben escribirse en el directorio de trabajo."""

    monkeypatch.delenv("FORMULARIO_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    reloaded_settings = reload(settings)
    autosave_path = Path(reloaded_settings.AUTOSAVE_FILE)
    logs_path = Path(reloaded_settings.LOGS_FILE)

    assert autosave_path.parent == tmp_path
    assert logs_path.parent == tmp_path


def test_autosave_respects_env_override(tmp_path, monkeypatch):
    """La variable de entorno debe permitir configurar la carpeta escribible."""

    custom_dir = tmp_path / "custom-output"
    monkeypatch.setenv("FORMULARIO_DATA_DIR", str(custom_dir))
    reloaded_settings = reload(settings)
    autosave_path = Path(reloaded_settings.AUTOSAVE_FILE)
    logs_path = Path(reloaded_settings.LOGS_FILE)

    assert autosave_path.parent == custom_dir
    assert logs_path.parent == custom_dir
    assert custom_dir.is_dir()
