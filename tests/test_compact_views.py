import app as app_module
from ui.frames import clients as clients_module
from ui.frames import team as team_module


class DummyVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def trace_add(self, *_args, **_kwargs):
        return None

    def trace_remove(self, *_args, **_kwargs):
        return None


class DummyWidget:
    def __init__(self, *args, **kwargs):
        self.children = []
        self._bindings = []
        self._config = {}

    def pack(self, *args, **kwargs):
        return None

    def pack_forget(self):
        return None

    def destroy(self):
        return None

    def grid(self, *args, **kwargs):
        return None

    def grid_remove(self, *args, **kwargs):
        return None

    def columnconfigure(self, *_args, **_kwargs):
        return None

    def bind(self, sequence, callback, add=None):
        self._bindings.append((sequence, callback, add))
        return f"bind_{len(self._bindings)}"

    def state(self, *_args, **_kwargs):
        return None

    def config(self, **kwargs):
        self._config.update(kwargs)

    def configure(self, **kwargs):
        self._config.update(kwargs)

    def set(self, value):
        self._config["current_value"] = value

    def get(self):
        return self._config.get("current_value", "")

    def focus_set(self):
        return None


class DummyListbox(DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selection = []

    def selection_clear(self, *_args, **_kwargs):
        self._selection.clear()

    def selection_set(self, index):
        self._selection.append(index)

    def curselection(self):
        return tuple(self._selection)

    def yview(self, *args, **kwargs):
        return None


class DummyTreeview(DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rows = {}
        self._columns = kwargs.get("columns", [])

    def heading(self, *_args, **_kwargs):
        return None

    def column(self, *_args, **_kwargs):
        return None

    def insert(self, _parent, _index, values=None, **_kwargs):
        item_id = f"row{len(self._rows)}"
        self._rows[item_id] = values or ()
        return item_id

    def delete(self, *items):
        if not items:
            self._rows.clear()
            return
        for item in items:
            self._rows.pop(item, None)

    def get_children(self):
        return list(self._rows.keys())

    def item(self, item_id, option=None):
        if option == "values":
            return self._rows.get(item_id, ())
        return {}

    def yview(self, *args, **kwargs):
        return None


class DummyScrollbar(DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command = kwargs.get("command")

    def set(self, *_args, **_kwargs):
        return None


def _build_light_app(monkeypatch):
    class _TkStub:
        StringVar = DummyVar
        END = "end"
        Listbox = DummyListbox
        TclError = Exception
        Label = DummyWidget

    class _TtkStub:
        Frame = DummyWidget
        LabelFrame = DummyWidget
        Label = DummyWidget
        Entry = DummyWidget
        Combobox = DummyWidget
        Button = DummyWidget
        Treeview = DummyTreeview
        Scrollbar = DummyScrollbar

    monkeypatch.setattr(app_module, "tk", _TkStub())
    monkeypatch.setattr(app_module, "ttk", _TtkStub())
    monkeypatch.setattr(clients_module, "tk", _TkStub())
    monkeypatch.setattr(clients_module, "ttk", _TtkStub())
    monkeypatch.setattr(team_module, "tk", _TkStub())
    monkeypatch.setattr(team_module, "ttk", _TtkStub())

    app = app_module.FraudCaseApp.__new__(app_module.FraudCaseApp)
    app.root = DummyWidget()
    app.logs = []
    app.client_frames = []
    app.team_frames = []
    app.product_frames = []
    app.risk_frames = []
    app.norm_frames = []
    app._client_frames_by_id = {}
    app._team_frames_by_id = {}
    app._product_frames_by_id = {}
    app.client_lookup = {}
    app.team_lookup = {}
    app.product_lookup = {}
    app.autofill_service = None
    app.fecha_caso_var = DummyVar()
    app.summary_tables = {"clientes": None, "colaboradores": None}
    app.summary_config = {}
    app._summary_refresh_after_id = None
    app._summary_dirty_sections = set()
    app._summary_pending_dataset = None
    app.register_tooltip = lambda *_args, **_kwargs: None
    app._log_navigation_change = lambda *_args, **_kwargs: None
    app.update_client_options_global = lambda: None
    app.update_team_options_global = lambda: None
    app._handle_client_id_change = lambda *_args, **_kwargs: None
    app._handle_team_id_change = lambda *_args, **_kwargs: None
    app._prepare_external_drive = lambda: None
    app._schedule_log_flush = lambda *_, **__: None
    app._is_summary_tab_visible = lambda: False
    app._cancel_summary_refresh_job = lambda: None
    app.gather_data = lambda: {"clientes": [], "colaboradores": []}
    return app, app.root


def test_clients_compact_toggle(monkeypatch):
    app, root = _build_light_app(monkeypatch)
    container = DummyWidget()
    container.pack()
    app.build_clients_tab(container)

    assert app._clients_detail_visible is False

    app._show_clients_detail()
    app._hide_clients_detail()
    app._show_clients_detail()

    root.destroy()


def test_compact_tables_render(monkeypatch):
    app, root = _build_light_app(monkeypatch)
    container = DummyWidget()
    container.pack()
    app.build_clients_tab(container)
    app.build_team_tab(container)

    dataset = {
        "clientes": [
            {
                "id_cliente": "12345678",
                "tipo_id": "DNI",
                "flag": "Afectado",
                "telefonos": "999999999",
                "correos": "a@b.com",
            }
        ],
        "colaboradores": [
            {
                "id_colaborador": "T12345",
                "division": "División QA",
                "area": "Área 1",
                "tipo_sancion": "Ninguna",
            }
        ],
    }

    app._refresh_compact_views(sections={"clientes", "colaboradores"}, data=dataset)

    client_rows = app.clients_compact_table.get_children()
    assert len(client_rows) == 1
    client_values = app.clients_compact_table.item(client_rows[0], "values")
    assert client_values[0] == "12345678"

    team_rows = app.team_compact_table.get_children()
    assert len(team_rows) == 1
    team_values = app.team_compact_table.item(team_rows[0], "values")
    assert team_values[0] == "T12345"

    root.destroy()
