from __future__ import annotations

import types

import pytest

from app import FraudCaseApp


class _DummyWrapper:
    def __init__(self):
        self.calls = []

    def grid(self, **_kwargs):
        self.calls.append("grid")

    def grid_remove(self):
        self.calls.append("grid_remove")


class _InlineTree:
    def __init__(self):
        self.rows = []

    def get_children(self):
        return list(range(len(self.rows)))

    def delete(self, *_args, **_kwargs):
        self.rows.clear()

    def insert(self, _parent, _index, values=None, **_kwargs):
        self.rows.append(values)


@pytest.fixture
def inline_app(monkeypatch):
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.inline_summary_trees = {}
    app.summary_tables = {}
    app._summary_dirty_sections = set()
    app._summary_pending_dataset = None
    app._clients_detail_visible = False
    app._team_detail_visible = False
    app.clients_detail_wrapper = _DummyWrapper()
    app.team_detail_wrapper = _DummyWrapper()
    app.clients_toggle_btn = types.SimpleNamespace(config=lambda **_kwargs: None)
    app.team_toggle_btn = types.SimpleNamespace(config=lambda **_kwargs: None)
    app.gather_data = lambda: {
        "clientes": [
            {
                "id_cliente": "C1",
                "tipo_id": "DNI",
                "flag": "AFECTADO",
                "telefonos": "123",
                "correos": "a@b.com",
                "direcciones": "X",
                "accionado": "Tribu",
            }
        ],
        "colaboradores": [
            {
                "id_colaborador": "T12345",
                "division": "Div",
                "area": "Area",
                "tipo_sancion": "Alerta",
            }
        ],
    }
    app._build_summary_rows = types.MethodType(FraudCaseApp._build_summary_rows, app)
    app._render_inline_rows = types.MethodType(FraudCaseApp._render_inline_rows, app)
    app._refresh_inline_section_tables = types.MethodType(FraudCaseApp._refresh_inline_section_tables, app)
    app.show_clients_detail = types.MethodType(FraudCaseApp.show_clients_detail, app)
    app.hide_clients_detail = types.MethodType(FraudCaseApp.hide_clients_detail, app)
    app.show_team_detail = types.MethodType(FraudCaseApp.show_team_detail, app)
    app.hide_team_detail = types.MethodType(FraudCaseApp.hide_team_detail, app)
    app.inline_summary_trees = {
        "clientes": _InlineTree(),
        "colaboradores": _InlineTree(),
    }
    return app


def test_clients_toggle_visibility_smoke(inline_app):
    inline_app.show_clients_detail()
    inline_app.hide_clients_detail()
    inline_app.show_clients_detail()

    assert inline_app.clients_detail_wrapper.calls == ["grid", "grid_remove", "grid"]


def test_team_toggle_visibility_smoke(inline_app):
    inline_app.show_team_detail()
    inline_app.hide_team_detail()
    inline_app.show_team_detail()

    assert inline_app.team_detail_wrapper.calls == ["grid", "grid_remove", "grid"]


def test_inline_summary_refreshes_from_dataset(inline_app):
    inline_app._refresh_inline_section_tables()

    client_rows = inline_app.inline_summary_trees["clientes"].rows
    team_rows = inline_app.inline_summary_trees["colaboradores"].rows

    assert client_rows and client_rows[0][0] == "C1"
    assert team_rows and team_rows[0][0] == "T12345"
