"""Fábricas de ``FraudCaseApp`` configuradas para pruebas unitarias."""

from __future__ import annotations

import types
from pathlib import Path

from app import FraudCaseApp
from settings import BASE_DIR
from settings import TIPO_ID_LIST, TIPO_SANCION_LIST
from tests.stubs import (ClientFrameStub, NormFrameStub, ProductFrameStub,
                         RiskFrameStub, TeamFrameStub, build_client_involvement_slot,
                         build_involvement_slot, build_populate_method,
                         build_slot_factory)
from utils.mass_import_manager import MassImportManager


class SummaryTableStub:
    """Implementación mínima de ``Treeview`` para las pruebas del resumen."""

    def get_children(self):
        return []

    def delete(self, *_args, **_kwargs):
        return None

    def insert(self, *_args, **_kwargs):
        return None


def build_import_app(monkeypatch, messagebox_spy=None):
    """Prepara una instancia ligera de ``FraudCaseApp`` para importaciones."""

    del messagebox_spy  # Sólo está para mantener la firma uniforme.
    app = FraudCaseApp.__new__(FraudCaseApp)
    app._suppress_messagebox = True
    app.logs = []
    app.mass_import_manager = MassImportManager(Path(BASE_DIR) / "logs")
    app.client_frames = []
    app.team_frames = []
    app.product_frames = []
    app._client_frames_by_id = {}
    app._team_frames_by_id = {}
    app._product_frames_by_id = {}
    app.detail_catalogs = {
        'id_cliente': {},
        'id_colaborador': {},
        'id_producto': {},
    }
    app.detail_lookup_by_id = {}
    app.client_lookup = {}
    app.team_lookup = {}
    app.product_lookup = {}
    app.summary_tables = {}
    app.summary_config = {}
    app._schedule_summary_refresh = lambda *_args, **_kwargs: None
    app._notify_taxonomy_warning = lambda *_args, **_kwargs: None
    app._notify_products_created_without_details = lambda *_args, **_kwargs: None
    app.report_calls = []
    app._autosave_job_id = None
    app._autosave_dirty = False

    def _report(self, label, ids):
        self.report_calls.append((label, list(ids)))

    app._report_missing_detail_ids = types.MethodType(_report, app)

    app.save_auto_called = False
    app.save_auto = lambda: setattr(app, 'save_auto_called', True)
    app.request_autosave = lambda: app.save_auto()

    def _notify(self, summary_sections=None):
        self.request_autosave()
        self._schedule_summary_refresh(sections=summary_sections)

    app._notify_dataset_changed = types.MethodType(_notify, app)
    app.sync_calls = []
    app.sync_main_form_after_import = lambda section, **kwargs: app.sync_calls.append(section)

    app._obtain_client_slot_for_import = types.MethodType(
        build_slot_factory(
            app.client_frames,
            ClientFrameStub,
            on_create=lambda self, frame: setattr(frame, 'id_change_callback', self._handle_client_id_change),
        ),
        app,
    )
    app._obtain_team_slot_for_import = types.MethodType(
        build_slot_factory(
            app.team_frames,
            TeamFrameStub,
            on_create=lambda self, frame: setattr(frame, 'id_change_callback', self._handle_team_id_change),
        ),
        app,
    )
    app._obtain_product_slot_for_import = types.MethodType(
        build_slot_factory(
            app.product_frames,
            ProductFrameStub,
            on_create=lambda self, frame: setattr(frame, 'id_change_callback', self._handle_product_id_change),
        ),
        app,
    )
    app._obtain_involvement_slot = types.MethodType(build_involvement_slot(), app)
    app._obtain_client_involvement_slot = types.MethodType(build_client_involvement_slot(), app)
    app._populate_client_frame_from_row = types.MethodType(
        build_populate_method('id_cliente'),
        app,
    )
    def _populate_team_stub(self, frame, row, preserve_existing=False):
        value = (row.get('id_colaborador') or "").strip()
        if not preserve_existing or not frame.id_var.get().strip():
            frame.id_var.set(value)
        mapping = {
            'nombres_var': ('nombres', 'nombre'),
            'apellidos_var': ('apellidos', 'apellido'),
            'flag_var': ('flag', 'flag_colaborador'),
            'division_var': ('division',),
            'area_var': ('area',),
            'servicio_var': ('servicio',),
            'puesto_var': ('puesto',),
            'fecha_carta_inmediatez_var': ('fecha_carta_inmediatez',),
            'fecha_carta_renuncia_var': ('fecha_carta_renuncia',),
            'nombre_agencia_var': ('nombre_agencia',),
            'codigo_agencia_var': ('codigo_agencia',),
            'tipo_falta_var': ('tipo_falta',),
            'tipo_sancion_var': ('tipo_sancion',),
        }
        for attr, keys in mapping.items():
            if not hasattr(frame, attr):
                continue
            for key in keys:
                candidate = (row.get(key) or "").strip()
                if candidate:
                    getattr(frame, attr).set(candidate)
                    break
        frame.populated_rows.append(dict(row))

    app._populate_team_frame_from_row = types.MethodType(_populate_team_stub, app)
    app._populate_product_frame_from_row = types.MethodType(
        build_populate_method('id_producto'),
        app,
    )
    app.risk_frames = []
    app.norm_frames = []

    def _add_risk(self):
        frame = RiskFrameStub()
        self.risk_frames.append(frame)
        return frame

    def _add_norm(self):
        frame = NormFrameStub()
        self.norm_frames.append(frame)
        return frame

    app.add_risk = types.MethodType(_add_risk, app)
    app.add_norm = types.MethodType(_add_norm, app)
    return app


def build_summary_app(monkeypatch, messagebox_spy=None):
    """Instancia ``FraudCaseApp`` con colecciones mínimas para el resumen."""

    del messagebox_spy
    app = FraudCaseApp.__new__(FraudCaseApp)
    app._suppress_messagebox = True
    app.logs = []
    app.client_frames = []
    app.team_frames = []
    app.product_frames = []
    app._client_frames_by_id = {}
    app._team_frames_by_id = {}
    app._product_frames_by_id = {}
    app.risk_frames = []
    app.norm_frames = []
    app.detail_catalogs = {}
    app.detail_lookup_by_id = {
        'id_producto': {
            '1234567890123': {
                'id_producto': '1234567890123',
                'id_cliente': '12345678',
                'tipo_producto': 'Crédito personal',
                'monto_investigado': '0.00',
            }
        },
        'id_colaborador': {
            'T22222': {
                'id_colaborador': 'T22222',
                'division': 'Division resumen',
                'area': 'Area resumen',
                'tipo_sancion': TIPO_SANCION_LIST[0],
            }
        },
        'id_cliente': {
            '12345678': {
                'id_cliente': '12345678',
                'tipo_id': TIPO_ID_LIST[0],
            }
        },
    }
    app.client_lookup = {}
    app.team_lookup = {}
    app.product_lookup = {}
    app.summary_tables = {}
    app.summary_config = {}
    app._schedule_summary_refresh = lambda *_args, **_kwargs: None
    app._notify_taxonomy_warning = lambda *_args, **_kwargs: None
    app._report_missing_detail_ids = lambda *_args, **_kwargs: None
    app._notify_products_created_without_details = lambda *_args, **_kwargs: None
    app._sync_product_lookup_claim_fields = lambda *_args, **_kwargs: None
    app._notify_dataset_changed = lambda *_args, **_kwargs: None
    app.save_auto = lambda: None
    app.sync_main_form_after_import = lambda *_args, **_kwargs: None

    app._obtain_client_slot_for_import = types.MethodType(
        build_slot_factory(
            app.client_frames,
            ClientFrameStub,
            on_create=lambda self, frame: setattr(frame, 'id_change_callback', self._handle_client_id_change),
        ),
        app,
    )
    app._obtain_team_slot_for_import = types.MethodType(
        build_slot_factory(
            app.team_frames,
            TeamFrameStub,
            on_create=lambda self, frame: setattr(frame, 'id_change_callback', self._handle_team_id_change),
        ),
        app,
    )
    app._obtain_product_slot_for_import = types.MethodType(
        build_slot_factory(
            app.product_frames,
            ProductFrameStub,
            on_create=lambda self, frame: setattr(frame, 'id_change_callback', self._handle_product_id_change),
        ),
        app,
    )
    app._obtain_involvement_slot = types.MethodType(build_involvement_slot(), app)
    app._obtain_client_involvement_slot = types.MethodType(build_client_involvement_slot(), app)
    app._populate_client_frame_from_row = types.MethodType(
        build_populate_method('id_cliente'),
        app,
    )
    app._populate_team_frame_from_row = types.MethodType(
        build_populate_method('id_colaborador'),
        app,
    )
    app._populate_product_frame_from_row = types.MethodType(
        build_populate_method('id_producto'),
        app,
    )

    def _identity_merge(self, frame, payload):
        return dict(payload or {})

    app._merge_client_payload_with_frame = types.MethodType(_identity_merge, app)
    app._merge_team_payload_with_frame = types.MethodType(_identity_merge, app)
    app._merge_product_payload_with_frame = types.MethodType(_identity_merge, app)

    def _add_risk(self):
        frame = RiskFrameStub()
        self.risk_frames.append(frame)
        return frame

    def _add_norm(self):
        frame = NormFrameStub()
        self.norm_frames.append(frame)
        return frame

    app.add_risk = types.MethodType(_add_risk, app)
    app.add_norm = types.MethodType(_add_norm, app)
    return app
