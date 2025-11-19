"""Pruebas para la exportación con ``save_and_send``."""

from __future__ import annotations

import types

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
