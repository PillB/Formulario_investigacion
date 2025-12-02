import pytest

from ui.frames import norm
from tests.test_clients_frame import DummyVar, DummyWidget, RecordingValidator
from ui.frames import norm


@pytest.fixture(autouse=True)
def patch_norm_widgets(monkeypatch):
    class _TkStub:
        StringVar = DummyVar

    class _TtkStub:
        LabelFrame = DummyWidget
        Frame = DummyWidget
        Label = DummyWidget
        Entry = DummyWidget
        Button = DummyWidget
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

    monkeypatch.setattr(norm, "tk", _TkStub())
    monkeypatch.setattr(norm, "ttk", _TtkStub())
    monkeypatch.setattr(norm, "CollapsibleSection", _CollapsibleSection)
    RecordingValidator.instances.clear()
    monkeypatch.setattr(norm, "FieldValidator", RecordingValidator)
    yield
    RecordingValidator.instances.clear()


def _build_norm_frame():
    return norm.NormFrame(
        parent=DummyWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
        change_notifier=None,
    )


def _find_validator(label_fragment):
    for validator in RecordingValidator.instances:
        if label_fragment in validator.field_name:
            return validator
    return None


def test_norm_frame_fecha_validator_requires_value():
    frame = _build_norm_frame()

    fecha_validator = _find_validator("Fecha")
    assert fecha_validator is not None

    frame.fecha_var.set("")
    error = fecha_validator.validate_callback()
    assert error is not None
    assert "fecha de vigencia" in error.lower()

    frame.fecha_var.set("2023-01-01")
    assert fecha_validator.validate_callback() is None


def test_norm_frame_autofills_from_lookup(monkeypatch):
    frame = _build_norm_frame()
    frame.set_lookup({"123": {"descripcion": "Desde catálogo", "fecha_vigencia": "2024-03-01"}})

    frame.id_var.set("123")
    frame.on_id_change(from_focus=True)

    assert frame.descripcion_var.get() == "Desde catálogo"
    assert frame.fecha_var.get() == "2024-03-01"


def test_norm_frame_preserves_manual_fields_with_preserve_flag():
    frame = _build_norm_frame()
    frame.set_lookup({"321": {"descripcion": "Catálogo", "fecha_vigencia": "2024-05-05"}})
    frame.descripcion_var.set("Manual")
    frame.id_var.set("321")

    frame.on_id_change(preserve_existing=True)

    assert frame.descripcion_var.get() == "Manual"
    assert frame.fecha_var.get() == "2024-05-05"


def test_norm_frame_shows_message_only_on_explicit_lookup(monkeypatch):
    frame = _build_norm_frame()
    captured = []
    monkeypatch.setattr(norm.messagebox, "showerror", lambda *args: captured.append(args))

    frame.id_var.set("999")
    frame.on_id_change(from_focus=True)
    assert captured == []

    frame.set_lookup({"111": {"descripcion": "x"}})
    frame.id_var.set("999")
    frame.on_id_change(from_focus=True)
    assert captured == []

    frame.on_id_change(from_focus=True, explicit_lookup=True)
    assert captured and "Norma no encontrada" in captured[0][0]
