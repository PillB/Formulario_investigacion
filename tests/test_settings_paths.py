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


def test_ensure_external_drive_dir_creates_custom_target(tmp_path, monkeypatch):
    """La función debe crear la carpeta configurada dinámicamente."""

    external_dir = tmp_path / 'external drive'
    monkeypatch.setattr(settings, 'EXTERNAL_DRIVE_DIR', str(external_dir))
    monkeypatch.setattr(
        settings,
        'EXTERNAL_LOGS_FILE',
        str(external_dir / 'logs.csv'),
    )
    created_path = settings.ensure_external_drive_dir()
    assert created_path == external_dir
    assert external_dir.is_dir()
