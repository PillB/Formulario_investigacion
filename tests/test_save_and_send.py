"""Pruebas para la exportación con ``save_and_send``."""

from __future__ import annotations

import types
import zipfile
from xml.sax.saxutils import escape

import app as app_module
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


class _SimpleDocxDocument:
    """Implementación mínima de ``Document`` para entornos sin python-docx."""

    _CONTENT_TYPES = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
        "<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
        "<Default Extension='xml' ContentType='application/xml'/>"
        "<Override PartName='/word/document.xml' "
        "ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/>"
        "</Types>"
    )
    _RELS = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
        "<Relationship Id='rId1' "
        "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' "
        "Target='word/document.xml'/>"
        "</Relationships>"
    )

    def __init__(self):
        self.blocks: list[tuple[str, str]] = []

    def add_paragraph(self, text: str = ""):
        self.blocks.append(('p', text or ''))
        return types.SimpleNamespace(text=text)

    def add_heading(self, text: str = "", level: int = 1):
        self.blocks.append((f'h{level}', text or ''))
        return types.SimpleNamespace(text=text)

    def save(self, path):
        xml_blocks = []
        for kind, text in self.blocks:
            if not text:
                xml_blocks.append("<w:p/>")
                continue
            escaped = escape(text)
            if kind.startswith('h'):
                level = kind[1:]
                xml_blocks.append(
                    "<w:p><w:pPr><w:pStyle w:val='Heading{}'/></w:pPr><w:r><w:t>{}</w:t></w:r></w:p>".format(
                        level, escaped
                    )
                )
            else:
                xml_blocks.append(f"<w:p><w:r><w:t>{escaped}</w:t></w:r></w:p>")
        body = ''.join(xml_blocks) + '<w:sectPr/>'
        document_xml = (
            "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
            "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
            f"<w:body>{body}</w:body></w:document>"
        )
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('[Content_Types].xml', self._CONTENT_TYPES)
            zf.writestr('_rels/.rels', self._RELS)
            zf.writestr('word/document.xml', document_xml)


def _enable_fake_docx(monkeypatch):
    monkeypatch.setattr(app_module, 'Document', _SimpleDocxDocument)


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
    _enable_fake_docx(monkeypatch)
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()
    monkeypatch.setattr(app_module.filedialog, 'askdirectory', lambda **kwargs: str(export_dir))
    app = _make_minimal_app()

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


def test_save_and_send_reports_catalog_errors_once(monkeypatch, messagebox_spy):
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

    monkeypatch.setattr(app_module.filedialog, 'askdirectory', lambda **kwargs: '')

    app.save_and_send()

    assert len(messagebox_spy.errors) == 1
    title, message = messagebox_spy.errors[0]
    assert title == 'Errores de validación'
    assert 'Tipo inventado' in message
    assert 'Canal inventado' in message


def test_save_and_send_mirrors_exports_to_external_drive(tmp_path, monkeypatch, messagebox_spy):
    _enable_fake_docx(monkeypatch)
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()
    mirror_dir = tmp_path / 'external drive'

    def fake_ensure():
        mirror_dir.mkdir(parents=True, exist_ok=True)
        return mirror_dir

    monkeypatch.setattr(app_module, 'ensure_external_drive_dir', fake_ensure)
    monkeypatch.setattr(app_module.filedialog, 'askdirectory', lambda **kwargs: str(export_dir))
    app = _make_minimal_app()
    app._current_case_data = _build_case_data('2024-9001')
    app.save_and_send()
    case_folder = mirror_dir / '2024-9001'
    assert (case_folder / '2024-9001_casos.csv').is_file()
    assert (case_folder / '2024-9001_informe.md').is_file()
    assert messagebox_spy.warnings == []


def test_save_and_send_warns_when_external_copy_fails(tmp_path, monkeypatch, messagebox_spy):
    _enable_fake_docx(monkeypatch)
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
    monkeypatch.setattr(app_module.filedialog, 'askdirectory', lambda **kwargs: str(export_dir))
    app = _make_minimal_app()
    app._current_case_data = _build_case_data('2024-9002')
    app.save_and_send()
    assert messagebox_spy.warnings
    title, message = messagebox_spy.warnings[-1]
    assert title in {'Copia pendiente', 'Copia incompleta'}
    assert '2024-9002' in message or 'archivos' in message


def test_save_temp_version_mirrors_to_external_drive(tmp_path, monkeypatch):
    mirror_dir = tmp_path / 'external drive'

    def fake_ensure():
        mirror_dir.mkdir(parents=True, exist_ok=True)
        return mirror_dir

    monkeypatch.setattr(app_module, 'ensure_external_drive_dir', fake_ensure)
    app = _make_minimal_app()
    data = _build_case_data('2024-1234')
    app.gather_data = types.MethodType(lambda self: data, app)
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    app.save_temp_version(data=data)
    after_files = [path for path in tmp_path.iterdir() if path.is_file() and path not in before]
    assert len(after_files) == 1
    mirrored = mirror_dir / after_files[0].name
    assert mirrored.is_file()


def _read_document_xml(path):
    with zipfile.ZipFile(path) as zf:
        return zf.read('word/document.xml').decode('utf-8')


def test_save_and_send_generates_docx_and_mirrors_when_library_available(
    tmp_path, monkeypatch, messagebox_spy
):
    _enable_fake_docx(monkeypatch)
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()
    mirror_dir = tmp_path / 'external drive'

    def fake_ensure():
        mirror_dir.mkdir(parents=True, exist_ok=True)
        return mirror_dir

    monkeypatch.setattr(app_module, 'ensure_external_drive_dir', fake_ensure)
    monkeypatch.setattr(app_module.filedialog, 'askdirectory', lambda **kwargs: str(export_dir))
    app = _make_minimal_app()
    app._current_case_data = _build_case_data('2024-7777')
    app.save_and_send()

    doc_path = export_dir / '2024-7777_informe.docx'
    assert doc_path.is_file()
    xml = _read_document_xml(doc_path)
    assert 'Informe' in xml
    assert 'Tabla de clientes' in xml

    case_folder = mirror_dir / '2024-7777'
    assert (case_folder / '2024-7777_informe.docx').is_file()
    assert any('Datos guardados' in title for title, _ in messagebox_spy.infos)


def test_save_and_send_reports_missing_docx_dependency(tmp_path, monkeypatch, messagebox_spy):
    monkeypatch.setattr(app_module, 'Document', None)
    export_dir = tmp_path / 'exports'
    export_dir.mkdir()
    monkeypatch.setattr(app_module.filedialog, 'askdirectory', lambda **kwargs: str(export_dir))
    app = _make_minimal_app()
    app._current_case_data = _build_case_data('2024-0003')
    app.save_and_send()
    assert messagebox_spy.errors
    assert any('python-docx' in message for _, message in messagebox_spy.errors)
    assert any('python-docx' in log['mensaje'] for log in app.logs)
