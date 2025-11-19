"""Pruebas para la exportación con ``save_and_send``."""

from __future__ import annotations

import types

import app as app_module
import settings
from app import FraudCaseApp
from tests.test_validation import build_headless_app
from settings import CANAL_LIST, PROCESO_LIST, TAXONOMIA, TIPO_INFORME_LIST


class SimpleVar:
    def __init__(self, value: str = ""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _build_dummy_frame():
    return types.SimpleNamespace(frame=types.SimpleNamespace(destroy=lambda: None))


def _build_case_data(case_id: str) -> dict:
    cat1 = next(iter(TAXONOMIA))
    cat2 = next(iter(TAXONOMIA[cat1]))
    modalidad = TAXONOMIA[cat1][cat2][0]
    return {
        'caso': {
            'id_caso': case_id,
            'tipo_informe': TIPO_INFORME_LIST[0],
            'categoria1': cat1,
            'categoria2': cat2,
            'modalidad': modalidad,
            'canal': CANAL_LIST[0],
            'proceso': PROCESO_LIST[0],
        },
        'clientes': [],
        'colaboradores': [],
        'productos': [],
        'reclamos': [],
        'involucramientos': [],
        'riesgos': [],
        'normas': [],
        'analisis': {
            'antecedentes': '',
            'modus_operandi': '',
            'hallazgos': '',
            'descargos': '',
            'conclusiones': '',
            'recomendaciones': '',
        },
    }


def _make_minimal_app():
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    app._export_base_path = None
    for attr in [
        'id_caso_var',
        'tipo_informe_var',
        'cat_caso1_var',
        'cat_caso2_var',
        'mod_caso_var',
        'canal_caso_var',
        'proceso_caso_var',
        'antecedentes_var',
        'modus_var',
        'hallazgos_var',
        'descargos_var',
        'conclusiones_var',
        'recomendaciones_var',
    ]:
        setattr(app, attr, SimpleVar())
    app.client_frames = [_build_dummy_frame()]
    app.team_frames = [_build_dummy_frame()]
    app.product_frames = [_build_dummy_frame()]
    app.risk_frames = [_build_dummy_frame()]
    app.norm_frames = [_build_dummy_frame()]
    app.next_risk_number = 1
    app._rebuild_frame_id_indexes = lambda: None
    app.save_auto = lambda *args, **kwargs: None
    app.on_case_cat1_change = lambda: None

    def _build_adder(attr_name):
        def _adder(self):
            frame = _build_dummy_frame()
            getattr(self, attr_name).append(frame)
            return frame
        return _adder

    app.add_client = types.MethodType(_build_adder('client_frames'), app)
    app.add_team = types.MethodType(_build_adder('team_frames'), app)
    app.add_risk = types.MethodType(_build_adder('risk_frames'), app)
    app.flush_autosave = types.MethodType(lambda self: None, app)
    app.flush_logs_now = types.MethodType(lambda self, reschedule=True: None, app)
    app.validate_data = types.MethodType(lambda self: ([], []), app)
    app._current_case_data = _build_case_data('test')
    app.gather_data = types.MethodType(lambda self: self._current_case_data, app)
    return app


def test_save_and_send_exports_fresh_logs(tmp_path, monkeypatch, messagebox_spy):
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()
    app = _make_minimal_app()
    app._export_base_path = export_dir

    app._current_case_data = _build_case_data('2024-0001')
    app.logs = [
        {
            'timestamp': '2024-01-01 00:00:00',
            'tipo': 'navegacion',
            'mensaje': 'primer caso',
        }
    ]
    app.save_and_send()
    first_log = export_dir / '2024-0001_logs.csv'
    assert 'primer caso' in first_log.read_text(encoding='utf-8')

    app._reset_form_state(confirm=False, save_autosave=False)
    assert app.logs == []

    app._current_case_data = _build_case_data('2024-0002')
    app.logs.append(
        {
            'timestamp': '2024-02-01 00:00:00',
            'tipo': 'navegacion',
            'mensaje': 'segundo caso',
        }
    )
    app.save_and_send()
    second_log = export_dir / '2024-0002_logs.csv'
    log_contents = second_log.read_text(encoding='utf-8')
    assert 'segundo caso' in log_contents
    assert 'primer caso' not in log_contents


def test_save_and_send_reports_catalog_errors_once(messagebox_spy):
    app = build_headless_app("Crédito personal")
    app._suppress_messagebox = False
    app.flush_autosave = lambda: None
    app.flush_logs_now = lambda reschedule=True: None
    app.logs = []

    minimal_data = {
        'caso': {'id_caso': app.id_caso_var.get()},
        'clientes': [],
        'colaboradores': [],
        'productos': [],
        'reclamos': [],
        'involucramientos': [],
    }
    app.gather_data = types.MethodType(lambda self: minimal_data, app)

    app.tipo_informe_var.set('Tipo inventado')
    app.canal_caso_var.set('Canal inventado')

    app.save_and_send()

    assert len(messagebox_spy.errors) == 1
    title, message = messagebox_spy.errors[0]
    assert title == 'Errores de validación'
    assert 'Tipo inventado' in message
    assert 'Canal inventado' in message


def test_save_and_send_mirrors_exports_to_external_drive(
    tmp_path,
    monkeypatch,
    messagebox_spy,
    external_drive_dir,
):
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()

    app = _make_minimal_app()
    app._export_base_path = export_dir
    app._current_case_data = _build_case_data('2024-9001')
    app.logs = [
        {
            'timestamp': '2024-05-01 12:00:00',
            'tipo': 'navegacion',
            'mensaje': 'mirroring',
        }
    ]
    app.save_and_send()
    case_id = '2024-9001'
    case_folder = external_drive_dir / case_id
    expected_suffixes = {
        f'{case_id}_casos.csv',
        f'{case_id}_version.json',
        f'{case_id}_informe.md',
        f'{case_id}_logs.csv',
    }
    mirrored_files = {path.name for path in case_folder.iterdir() if path.is_file()}
    assert expected_suffixes.issubset(mirrored_files)
    assert messagebox_spy.warnings == []


def test_save_and_send_warns_when_external_copy_fails(tmp_path, monkeypatch, messagebox_spy):
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()
    mirror_dir = tmp_path / 'external drive'

    def fake_ensure():
        mirror_dir.mkdir(parents=True, exist_ok=True)
        return mirror_dir

    def failing_copy(*_args, **_kwargs):
        raise OSError('disco lleno')

    monkeypatch.setattr(app_module, 'ensure_external_drive_dir', fake_ensure)
    monkeypatch.setattr(app_module.shutil, 'copy2', failing_copy)
    app = _make_minimal_app()
    app._export_base_path = export_dir
    app._current_case_data = _build_case_data('2024-9002')
    app.save_and_send()
    assert messagebox_spy.warnings
    title, message = messagebox_spy.warnings[-1]
    assert title in {'Copia pendiente', 'Copia incompleta'}
    assert '2024-9002' in message or 'archivos' in message


def test_save_temp_version_mirrors_to_external_drive(tmp_path, monkeypatch, external_drive_dir):
    app = _make_minimal_app()
    data = _build_case_data('2024-1234')
    app.gather_data = types.MethodType(lambda self: data, app)
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    app.save_temp_version(data=data)
    after_files = [path for path in tmp_path.iterdir() if path.is_file() and path not in before]
    assert len(after_files) == 1
    mirrored = external_drive_dir / after_files[0].name
    assert mirrored.is_file()


def test_flush_log_queue_writes_external_when_local_blocked(
    tmp_path,
    monkeypatch,
    external_drive_dir,
    messagebox_spy,
):
    blocked_parent = tmp_path / 'blocked'
    blocked_parent.write_text('file-instead-of-dir', encoding='utf-8')
    local_log_path = blocked_parent / 'logs.csv'
    external_log_path = external_drive_dir / 'logs.csv'
    monkeypatch.setattr(app_module, 'LOGS_FILE', str(local_log_path))
    monkeypatch.setattr(app_module, 'EXTERNAL_LOGS_FILE', str(external_log_path))

    rows = [
        {
            'timestamp': '2024-06-01 10:00:00',
            'tipo': 'navegacion',
            'mensaje': 'solo externo',
        }
    ]

    def fake_drain():
        nonlocal rows
        payload, rows = rows, []
        return payload

    monkeypatch.setattr(app_module, 'drain_log_queue', fake_drain)
    app = _make_minimal_app()
    app._flush_log_queue_to_disk()
    assert external_log_path.is_file()
    contents = external_log_path.read_text(encoding='utf-8')
    assert 'solo externo' in contents
    assert not local_log_path.exists()
    assert messagebox_spy.warnings
    warning_title, warning_message = messagebox_spy.warnings[-1]
    assert warning_title == 'Registro no guardado'
    assert str(local_log_path) in warning_message


def test_flush_log_queue_skips_local_when_disabled(
    tmp_path,
    monkeypatch,
    external_drive_dir,
    messagebox_spy,
):
    local_log_path = tmp_path / 'logs.csv'
    external_log_path = external_drive_dir / 'logs.csv'
    monkeypatch.setattr(app_module, 'LOGS_FILE', str(local_log_path))
    monkeypatch.setattr(app_module, 'EXTERNAL_LOGS_FILE', str(external_log_path))
    monkeypatch.setattr(app_module, 'STORE_LOGS_LOCALLY', False)
    monkeypatch.setattr(settings, 'STORE_LOGS_LOCALLY', False, raising=False)

    rows = [
        {
            'timestamp': '2024-06-02 11:00:00',
            'tipo': 'navegacion',
            'mensaje': 'solo externo configurable',
        }
    ]

    def fake_drain():
        nonlocal rows
        payload, rows = rows, []
        return payload

    monkeypatch.setattr(app_module, 'drain_log_queue', fake_drain)
    app = _make_minimal_app()
    app._flush_log_queue_to_disk()
    assert external_log_path.is_file()
    contents = external_log_path.read_text(encoding='utf-8')
    assert 'solo externo configurable' in contents
    assert not local_log_path.exists()
    assert messagebox_spy.warnings == []


def test_save_temp_version_writes_external_when_primary_unwritable(
    tmp_path,
    monkeypatch,
    external_drive_dir,
):
    unwritable_root = tmp_path / 'locked-root'
    unwritable_root.write_text('no es carpeta', encoding='utf-8')
    monkeypatch.setattr(app_module.os, 'getcwd', lambda: str(unwritable_root))
    app = _make_minimal_app()
    data = _build_case_data('2024-7777')
    app.gather_data = types.MethodType(lambda self: data, app)
    before = set(external_drive_dir.iterdir())
    app.save_temp_version(data=data)
    new_files = [path for path in external_drive_dir.iterdir() if path not in before]
    assert len(new_files) == 1
    mirror_contents = new_files[0].read_text(encoding='utf-8')
    assert '2024-7777' in mirror_contents
