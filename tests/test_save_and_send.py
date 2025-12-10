"""Pruebas para la exportación con ``save_and_send``."""

from __future__ import annotations

import csv
from contextlib import suppress
from datetime import datetime
from pathlib import Path
import types
import zipfile

import pytest

import app as app_module
import settings
from app import FraudCaseApp
from report_builder import DOCX_AVAILABLE, build_report_filename
from tests.test_validation import build_headless_app
from settings import (CANAL_LIST, PROCESO_LIST, TAXONOMIA, TIPO_INFORME_LIST,
                      TIPO_MONEDA_LIST, TIPO_PRODUCTO_LIST)


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
            'fecha_de_ocurrencia': '2024-01-01',
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
    app._docx_available = DOCX_AVAILABLE
    app._last_temp_saved_at = None
    app._last_temp_signature = None
    for attr in [
        'id_caso_var',
        'tipo_informe_var',
        'cat_caso1_var',
        'cat_caso2_var',
        'mod_caso_var',
        'canal_caso_var',
        'proceso_caso_var',
        'fecha_caso_var',
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
    prefix_first = Path(build_report_filename(TIPO_INFORME_LIST[0], '2024-0001', 'csv')).stem
    first_log = export_dir / f'{prefix_first}_logs.csv'
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
    prefix_second = Path(build_report_filename(TIPO_INFORME_LIST[0], '2024-0002', 'csv')).stem
    second_log = export_dir / f'{prefix_second}_logs.csv'
    log_contents = second_log.read_text(encoding='utf-8')
    assert 'segundo caso' in log_contents
    assert 'primer caso' not in log_contents


def test_save_and_send_updates_architecture_diagram(tmp_path, messagebox_spy):
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()
    architecture_path = tmp_path / 'architecture.mmd'
    architecture_path.write_text('legacy', encoding='utf-8')

    app = _make_minimal_app()
    app._export_base_path = export_dir
    app._architecture_diagram_path = architecture_path
    app._current_case_data = _build_case_data('2024-1111')

    app.save_and_send()

    content = architecture_path.read_text(encoding='utf-8')
    assert 'legacy' not in content
    assert 'erDiagram' in content
    for table in ['CASOS', 'CLIENTES', 'PRODUCTOS', 'ANALISIS', 'EVENTOS']:
        assert table in content
    assert 'CASOS ||--o{ PRODUCTOS' in content
    assert 'CASOS ||--o{ EVENTOS' in content
    assert 'PRODUCTOS ||--o{ EVENTOS : id_producto' in content
    assert 'CLIENTES ||--o{ EVENTOS : id_cliente' in content
    assert 'COLABORADORES ||--o{ EVENTOS : id_colaborador' in content


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
    report_prefix = Path(build_report_filename(TIPO_INFORME_LIST[0], case_id, 'csv')).stem
    md_report = build_report_filename(TIPO_INFORME_LIST[0], case_id, 'md')
    docx_report = build_report_filename(TIPO_INFORME_LIST[0], case_id, 'docx')
    expected_suffixes = {
        f'{report_prefix}_casos.csv',
        f'{report_prefix}_version.json',
        f'{report_prefix}_logs.csv',
        md_report,
    }
    if DOCX_AVAILABLE:
        expected_suffixes.add(docx_report)
    mirrored_files = {path.name for path in case_folder.iterdir() if path.is_file()}
    assert expected_suffixes.issubset(mirrored_files)
    if DOCX_AVAILABLE:
        assert messagebox_spy.warnings == []
    else:
        assert messagebox_spy.warnings


@pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx no está disponible")
def test_save_and_send_generates_word_report(tmp_path, messagebox_spy):
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()

    app = _make_minimal_app()
    app._export_base_path = export_dir
    app._current_case_data = _build_case_data('2024-9100')
    app.save_and_send()

    docx_name = build_report_filename(TIPO_INFORME_LIST[0], '2024-9100', 'docx')
    docx_path = export_dir / docx_name
    assert docx_path.is_file()
    with zipfile.ZipFile(docx_path) as bundle:
        xml_data = bundle.read('word/document.xml').decode('utf-8')
    assert '1. Antecedentes' in xml_data
    assert 'Tabla de clientes' in xml_data
    assert 'Tabla de productos combinado' in xml_data


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
    case_id = '2024-1234'
    data = _build_case_data(case_id)
    app.gather_data = types.MethodType(lambda self: data, app)
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 6, 1, 15, 30, 0)

    monkeypatch.setattr(app_module, 'datetime', FrozenDatetime)
    timestamp = FrozenDatetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{case_id}_temp_{timestamp}.json'
    base_target = Path(app_module.BASE_DIR) / filename
    case_folder = external_drive_dir / case_id
    mirror_target = case_folder / filename
    for path in (base_target, mirror_target):
        if path.exists():
            path.unlink()
    monkeypatch.chdir(tmp_path)
    before_entries = set(tmp_path.iterdir())
    try:
        app.save_temp_version(data=data)
        assert base_target.is_file()
        assert mirror_target.is_file()
        assert set(tmp_path.iterdir()) == before_entries
    finally:
        for path in (base_target, mirror_target):
            with suppress(FileNotFoundError):
                path.unlink()


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
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 6, 1, 16, 40, 0)

    monkeypatch.setattr(app_module, 'datetime', FrozenDatetime)
    app = _make_minimal_app()
    case_id = '2024-7777'
    data = _build_case_data(case_id)
    app.gather_data = types.MethodType(lambda self: data, app)
    timestamp = FrozenDatetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{case_id}_temp_{timestamp}.json'
    mirror_target = external_drive_dir / case_id / filename
    if mirror_target.exists():
        mirror_target.unlink()
    locked_root = tmp_path / 'locked-root'
    locked_root.write_text('no es carpeta', encoding='utf-8')
    monkeypatch.setattr(app_module, 'BASE_DIR', str(locked_root))
    base_target = Path(app_module.BASE_DIR) / filename
    monkeypatch.chdir(tmp_path)
    before_entries = set(tmp_path.iterdir())
    try:
        app.save_temp_version(data=data)
        assert mirror_target.is_file()
        assert set(tmp_path.iterdir()) == before_entries
        assert not base_target.exists()
        mirror_contents = mirror_target.read_text(encoding='utf-8')
        assert case_id in mirror_contents
        assert locked_root.read_text(encoding='utf-8') == 'no es carpeta'
    finally:
        with suppress(FileNotFoundError):
            mirror_target.unlink()


def test_save_and_send_normalizes_blank_optional_amounts(tmp_path, messagebox_spy):
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()

    app = _make_minimal_app()
    app._export_base_path = export_dir

    case_id = '2024-0101'
    data = _build_case_data(case_id)
    cat1 = data['caso']['categoria1']
    cat2 = data['caso']['categoria2']
    modalidad = data['caso']['modalidad']
    canal = data['caso']['canal']
    proceso = data['caso']['proceso']
    product_row = {
        'id_producto': 'PROD-001',
        'id_caso': '',
        'id_cliente': 'CL1',
        'categoria1': cat1,
        'categoria2': cat2,
        'modalidad': modalidad,
        'canal': canal,
        'proceso': proceso,
        'fecha_ocurrencia': '2024-01-01',
        'fecha_descubrimiento': '2024-01-02',
        'monto_investigado': '10.00',
        'tipo_moneda': TIPO_MONEDA_LIST[0],
        'monto_perdida_fraude': '',
        'monto_falla_procesos': '',
        'monto_contingencia': '',
        'monto_recuperado': '',
        'monto_pago_deuda': '',
        'tipo_producto': TIPO_PRODUCTO_LIST[0],
    }
    data['productos'] = [product_row]
    app._current_case_data = data

    app.save_and_send()

    report_prefix = Path(build_report_filename(TIPO_INFORME_LIST[0], case_id, 'csv')).stem
    productos_csv = export_dir / f'{report_prefix}_productos.csv'
    with productos_csv.open('r', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))

    assert rows, 'Expected a product row in the export'
    exported_row = rows[0]
    optional_fields = [
        'monto_perdida_fraude',
        'monto_falla_procesos',
        'monto_contingencia',
        'monto_recuperado',
        'monto_pago_deuda',
    ]
    for field in optional_fields:
        assert exported_row[field] == '0.00'


def test_save_and_send_sanitizes_csv_fields(tmp_path, messagebox_spy):
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()

    app = _make_minimal_app()
    app._export_base_path = export_dir

    case_id = '2024-0112'
    data = _build_case_data(case_id)
    data['clientes'] = [
        {
            'id_cliente': '=CLI-001',
            'id_caso': '',
            'nombres': 'Alice\r\nExample',
            'apellidos': 'Bell\x07Name',
            'tipo_id': 'DNI',
            'flag': '-flag',
            'telefonos': '+123',
            'correos': 'a@example.com',
            'direcciones': 'Street\nLine2',
            'accionado': '@attack',
        }
    ]
    app._current_case_data = data

    app.save_and_send()

    report_prefix = Path(build_report_filename(TIPO_INFORME_LIST[0], case_id, 'csv')).stem
    clientes_csv = export_dir / f'{report_prefix}_clientes.csv'
    with clientes_csv.open('r', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))

    assert rows, 'Expected a client row in the export'
    exported_row = rows[0]
    assert exported_row['id_cliente'].startswith("'=")
    assert exported_row['accionado'].startswith("'@")
    assert exported_row['telefonos'].startswith("'+")
    assert exported_row['flag'].startswith("'-")
    assert exported_row['nombres'] == 'Alice\nExample'
    assert '\r' not in exported_row['nombres']
    assert all(ch.isprintable() for ch in exported_row['apellidos'])
