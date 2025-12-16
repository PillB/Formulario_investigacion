import types

import pytest

from app import CANAL_LIST, FraudCaseApp, PROCESO_LIST, TAXONOMIA, TIPO_INFORME_LIST


class SimpleVar:
    def __init__(self, value=""):
        self._value = value

    def set(self, value):
        self._value = value

    def get(self):
        return self._value


class TreeStub:
    def __init__(self):
        self.children = ["row1", "row2"]

    def get_children(self):
        return tuple(self.children)

    def delete(self, *items):
        if not items:
            self.children = []
            return
        targets = []
        for item in items:
            if isinstance(item, (list, tuple, set)):
                targets.extend(item)
            else:
                targets.append(item)
        if not targets:
            self.children = []
            return
        self.children = [child for child in self.children if child not in targets]

    def insert(self, *_args, **_kwargs):
        iid = _kwargs.get("iid") or f"row{len(self.children) + 1}"
        self.children.append(iid)
        return iid


@pytest.fixture
def resettable_app(monkeypatch):
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    app._suppress_messagebox = True
    app._user_has_edited = False
    app._autosave_start_guard = True
    app.client_frames = []
    app.team_frames = []
    app.product_frames = []
    app.risk_frames = []
    app.norm_frames = []
    app._summary_dirty_sections = set()
    app._summary_pending_dataset = None
    app._summary_refresh_after_id = None
    app.summary_tab = None
    app.notebook = None
    app.inline_summary_trees = {"clientes": TreeStub(), "colaboradores": TreeStub()}
    app.summary_tables = {
        key: TreeStub()
        for key in ("clientes", "colaboradores", "involucramientos", "productos", "riesgos", "reclamos", "normas")
    }
    app.summary_config = {}
    app._client_summary_owner = None
    app._team_summary_owner = None
    app._rebuild_frame_id_indexes = lambda: None
    app._reset_navigation_metrics = lambda: None
    app._reset_investigator_fields = lambda: None
    app._set_text_content = lambda *_args, **_kwargs: None
    app._analysis_text_widgets = lambda: {}
    app._reset_extended_sections = lambda: None
    app.save_auto = lambda: None
    app._update_completion_progress = lambda: None
    app._refresh_compact_views = lambda sections=None, data=None: None
    app._cancel_summary_refresh_job = lambda: None
    app._is_summary_tab_visible = lambda: True
    app._handle_validation_success_transition = lambda: None
    app._apply_treeview_theme = lambda *_args, **_kwargs: None
    app._insert_themed_row = lambda *_args, **_kwargs: None
    app._compact_views_present = lambda sections=None: False
    app._ensure_case_vars = lambda: None
    app.id_caso_var = SimpleVar()
    app.id_proceso_var = SimpleVar()
    app.tipo_informe_var = SimpleVar(TIPO_INFORME_LIST[0])
    app.cat_caso1_var = SimpleVar(list(TAXONOMIA.keys())[0])
    app.canal_caso_var = SimpleVar(CANAL_LIST[0])
    app.proceso_caso_var = SimpleVar(PROCESO_LIST[0])
    app.fecha_caso_var = SimpleVar()
    app.fecha_descubrimiento_caso_var = SimpleVar()
    app.on_case_cat1_change = lambda: None
    app.add_client = lambda: None
    app.add_team = lambda: None
    app.add_risk = lambda: None
    app.add_norm = lambda: None

    app.refresh_summary_tables = types.MethodType(FraudCaseApp.refresh_summary_tables, app)
    app._refresh_inline_section_tables = types.MethodType(FraudCaseApp._refresh_inline_section_tables, app)
    app._normalize_summary_sections = types.MethodType(FraudCaseApp._normalize_summary_sections, app)
    app._render_summary_rows = types.MethodType(FraudCaseApp._render_summary_rows, app)
    app._build_summary_dataset = lambda: None

    def _schedule(sections=None, data=None):
        app.scheduled_sections = sections
        app.scheduled_data = data
        FraudCaseApp._refresh_inline_section_tables(app, sections=sections, data=data)

    app._schedule_summary_refresh = _schedule
    return app


def test_clear_case_state_empties_all_summary_views(resettable_app):
    app = resettable_app

    app._clear_case_state(save_autosave=False)

    for tree in app.summary_tables.values():
        assert tree.get_children() == ()
    for tree in app.inline_summary_trees.values():
        assert tree.get_children() == ()
    assert app.scheduled_data == app._build_empty_summary_dataset()
