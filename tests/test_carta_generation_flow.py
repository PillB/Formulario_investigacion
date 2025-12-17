from __future__ import annotations

import types
from datetime import datetime

import app as app_module
from app import FraudCaseApp
from tests.stubs import DummyVar


def _build_carta_app(monkeypatch, generator_payload):
    app = FraudCaseApp.__new__(FraudCaseApp)
    app._suppress_messagebox = True
    app.logs = []
    app.id_caso_var = DummyVar("2024-0001")
    app.investigator_id_var = DummyVar("T99999")
    app.investigator_nombre_var = DummyVar("Investigador")
    app.investigator_cargo_var = DummyVar("Investigador Principal")
    app._mirror_exports_to_external_drive = lambda *args, **kwargs: []
    app.flush_logs_now = lambda *args, **kwargs: None
    app._play_feedback_sound = lambda *args, **kwargs: None
    app._show_success_toast = lambda *args, **kwargs: None
    app._destroy_carta_dialog = lambda *args, **kwargs: None
    refresh_calls: list = []
    app._schedule_summary_refresh = lambda sections=None, data=None: refresh_calls.append(sections)
    app.team_frames = []
    app._team_frames_by_id = {}
    app.gather_data = types.MethodType(
        lambda self: {
            "caso": {
                "id_caso": self.id_caso_var.get(),
                "investigador": {
                    "matricula": self.investigator_id_var.get(),
                    "nombre": self.investigator_nombre_var.get(),
                },
            }
        },
        app,
    )

    class GeneratorStub:
        def __init__(self, payload):
            self.payload = payload
            self.calls: list = []

        def generate_cartas(self, data, members):
            self.calls.append((data, members))
            return self.payload

    monkeypatch.setattr(app, "_get_carta_generator", lambda: GeneratorStub(generator_payload))
    return app, refresh_calls


def test_perform_carta_generation_sets_missing_dates(monkeypatch):
    row_date = "2024-02-10"
    app, refresh_calls = _build_carta_app(
        monkeypatch,
        {"files": [], "rows": [{"matricula_team_member": "T00001", "fecha_generacion": row_date, "Numero_de_Carta": "001-2024"}]},
    )
    frame = types.SimpleNamespace(id_var=DummyVar("T00001"), fecha_carta_inmediatez_var=DummyVar(""))
    app.team_frames.append(frame)
    app._team_frames_by_id[app._normalize_identifier(frame.id_var.get())] = frame

    app._perform_carta_generation([{"id_colaborador": "t00001"}])

    assert frame.fecha_carta_inmediatez_var.get() == row_date
    assert refresh_calls and refresh_calls[-1] == "colaboradores"


def test_perform_carta_generation_respects_existing_dates(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return cls(2024, 3, 1)

    monkeypatch.setattr(app_module, "datetime", FixedDatetime)
    app, refresh_calls = _build_carta_app(
        monkeypatch,
        {"files": [], "rows": [{"matricula_team_member": "T00002", "Numero_de_Carta": "002-2024"}]},
    )
    frame_with_missing = types.SimpleNamespace(id_var=DummyVar("T00002"), fecha_carta_inmediatez_var=DummyVar(""))
    frame_with_value = types.SimpleNamespace(id_var=DummyVar("T00003"), fecha_carta_inmediatez_var=DummyVar("2024-01-05"))
    for frame in (frame_with_missing, frame_with_value):
        app.team_frames.append(frame)
        app._team_frames_by_id[app._normalize_identifier(frame.id_var.get())] = frame

    app._perform_carta_generation(
        [
            {"id_colaborador": "T00002"},
            {"id_colaborador": "T00003"},
        ]
    )

    assert frame_with_missing.fecha_carta_inmediatez_var.get() == "2024-03-01"
    assert frame_with_value.fecha_carta_inmediatez_var.get() == "2024-01-05"
    assert refresh_calls and refresh_calls[-1] == "colaboradores"
