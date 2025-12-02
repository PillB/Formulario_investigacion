import pytest

from tests.test_clients_frame import DummyVar, DummyWidget, RecordingValidator
from ui.frames import risk


@pytest.fixture(autouse=True)
def patch_risk_widgets(monkeypatch):
    class _TkStub:
        StringVar = DummyVar

    class _TtkStub:
        LabelFrame = DummyWidget
        Frame = DummyWidget
        Label = DummyWidget
        Entry = DummyWidget
        Button = DummyWidget
        Combobox = DummyWidget
        Scrollbar = DummyWidget

        class Treeview(DummyWidget):
            def __init__(self, *args, columns=(), show=None, height=None, **kwargs):
                super().__init__(*args, **kwargs)
                self._columns = list(columns)
                self._items = {}
                self._order = []
                self._selection = []

            def heading(self, column, text=None, command=None):
                self._config.setdefault("headings", {})[column] = {"text": text, "command": command}

            def column(self, column, anchor=None, width=None):
                self._config.setdefault("columns_cfg", {})[column] = {"anchor": anchor, "width": width}

            def insert(self, parent, index, iid=None, values=None, tags=None):
                iid = str(iid) if iid is not None else str(len(self._order))
                self._items[iid] = {"values": tuple(values or ()), "tags": tuple(tags or ())}
                self._order.append(iid)
                return iid

            def get_children(self, _item=""):
                return tuple(self._order)

            def delete(self, item):
                targets = item if isinstance(item, (list, tuple)) else [item]
                for target in list(targets):
                    if target in self._items:
                        self._order = [i for i in self._order if i != target]
                        self._items.pop(target, None)

            def item(self, iid, option=None):
                data = self._items.get(iid, {})
                if option:
                    return data.get(option)
                return data

            def move(self, item, parent, index):
                self._order = [i for i in self._order if i != item]
                self._order.insert(index, item)

            def selection(self):
                return tuple(self._selection)

            def selection_set(self, items):
                self._selection = list(items if isinstance(items, (list, tuple)) else [items])

            def tag_configure(self, tagname, **_kwargs):
                self._config.setdefault("tags", {})[tagname] = _kwargs

            def configure(self, **kwargs):
                super().configure(**kwargs)

            def yview(self, *args, **_kwargs):
                return args

            def __getitem__(self, key):
                if key == "columns":
                    return tuple(self._columns)
                return super().__getitem__(key)

    class _CollapsibleSection(DummyWidget):
        def __init__(self, parent=None, title="", open=True, on_toggle=None, **_kwargs):
            super().__init__(parent=parent)
            self.title = title
            self._is_open = open
            self._on_toggle = on_toggle
            self.header = DummyWidget()
            self.title_label = DummyWidget()
            self.content = DummyWidget()

        def pack_content(self, widget, **_kwargs):
            return widget

        @property
        def is_open(self):
            return self._is_open

        def set_title(self, title):
            self.title = title

        def toggle(self, *_args):
            self._is_open = not self._is_open
            if callable(self._on_toggle):
                self._on_toggle(self)

    monkeypatch.setattr(risk, "tk", _TkStub())
    monkeypatch.setattr(risk, "ttk", _TtkStub())
    monkeypatch.setattr(risk, "CollapsibleSection", _CollapsibleSection)
    RecordingValidator.instances.clear()
    monkeypatch.setattr(risk, "FieldValidator", RecordingValidator)
    yield
    RecordingValidator.instances.clear()


def _build_risk_frame():
    return risk.RiskFrame(
        parent=DummyWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
        change_notifier=None,
    )


def test_risk_frame_autofills_from_lookup():
    frame = _build_risk_frame()
    frame.set_lookup(
        {
            "RSK-000001": {
                "lider": "Owner",
                "descripcion": "Desde catálogo",
                "criticidad": "Alto",
                "exposicion_residual": "1200",
                "planes_accion": "Plan A",
            }
        }
    )

    frame.id_var.set("RSK-000001")
    frame.on_id_change(from_focus=True)

    assert frame.lider_var.get() == "Owner"
    assert frame.descripcion_var.get() == "Desde catálogo"
    assert frame.criticidad_var.get() == "Alto"
    assert frame.exposicion_var.get() == "1200"
    assert frame.planes_var.get() == "Plan A"


def test_risk_frame_preserves_manual_fields(monkeypatch):
    frame = _build_risk_frame()
    frame.set_lookup(
        {
            "RSK-000002": {
                "lider": "Catálogo",
                "descripcion": "Desc",
                "criticidad": "Moderado",
            }
        }
    )
    frame.id_var.set("RSK-000002")
    frame.lider_var.set("Manual")

    frame.on_id_change(preserve_existing=True)

    assert frame.lider_var.get() == "Manual"
    assert frame.descripcion_var.get() == "Desc"


def test_risk_frame_shows_message_only_on_explicit_lookup(monkeypatch):
    frame = _build_risk_frame()
    captured = []
    monkeypatch.setattr(risk.messagebox, "showerror", lambda *args: captured.append(args))

    frame.id_var.set("RSK-999999")
    frame.on_id_change(from_focus=True)
    assert captured == []

    frame.set_lookup({"RSK-000003": {"descripcion": "X"}})
    frame.id_var.set("RSK-999999")
    frame.on_id_change(from_focus=True)
    assert captured == []

    frame.on_id_change(from_focus=True, explicit_lookup=True)
    assert captured and "Riesgo no encontrado" in captured[0][0]
