import pytest

from tests.test_clients_frame import DummyVar, DummyWidget, RecordingValidator
from ui.frames import risk


@pytest.fixture(autouse=True)
def patch_risk_widgets(monkeypatch):
    class _TkStub:
        StringVar = DummyVar
        BooleanVar = DummyVar
        Toplevel = DummyWidget

    class _TtkStub:
        LabelFrame = DummyWidget
        Frame = DummyWidget
        Label = DummyWidget
        Entry = DummyWidget
        Button = DummyWidget
        Checkbutton = DummyWidget
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

            def column(self, column, anchor=None, width=None, minwidth=None, stretch=None):
                self._config.setdefault("columns_cfg", {})[column] = {
                    "anchor": anchor,
                    "width": width,
                    "minwidth": minwidth,
                    "stretch": stretch,
                }

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
            self.indicator = DummyWidget()
            self.content = DummyWidget()
            for widget in (self.header, self.title_label, self.indicator):
                for seq in ("<ButtonRelease-1>", "<space>", "<Return>"):
                    widget.bind(seq, self.toggle)

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


def _find_validator(label):
    for validator in RecordingValidator.instances:
        if label in validator.field_name:
            return validator
    return None


def _assert_toggle_bindings(section):
    for widget in (section.header, section.title_label, section.indicator):
        for sequence in ("<ButtonRelease-1>", "<space>", "<Return>"):
            initial_state = section.is_open
            widget.event_generate(sequence)
            assert section.is_open is not initial_state
            widget.event_generate(sequence)
            assert section.is_open is initial_state


def test_risk_frame_section_starts_collapsed_and_toggles():
    frame = _build_risk_frame()

    assert frame.section.is_open is False

    _assert_toggle_bindings(frame.section)


def test_risk_frame_starts_with_empty_id():
    frame = _build_risk_frame()

    assert frame.id_var.get() == ""


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


def test_set_lookup_does_not_populate_shared_tree_with_catalog_data():
    frame = _build_risk_frame()
    header_tree = risk.RiskFrame.build_header_tree(DummyWidget())
    frame.attach_header_tree(header_tree)

    frame.set_lookup({"RSK-999999": {"descripcion": "Catálogo"}})

    assert header_tree.get_children() == tuple()


def test_risk_frame_skips_catalog_lookup_in_new_mode():
    frame = _build_risk_frame()
    frame.risk_lookup = {"RSK-000010": {"descripcion": "Catálogo"}}
    frame.new_risk_var.set(True)
    frame.id_var.set("RSK-000010")

    refresh_calls = []
    frame._schedule_refresh = lambda: refresh_calls.append("refresh")

    frame.on_id_change()

    assert frame.descripcion_var.get() == ""
    assert refresh_calls == ["refresh"]


def test_toggle_back_to_catalog_uses_lookup(monkeypatch):
    frame = _build_risk_frame()
    frame.risk_lookup = {"LIBRE-01": {"descripcion": "Desde catálogo"}}
    frame.new_risk_var.set(True)
    frame.id_var.set("LIBRE-01")
    frame.on_id_change()

    assert frame.descripcion_var.get() == ""

    frame.new_risk_var.set(False)
    frame._on_mode_toggle()

    assert frame.is_catalog_mode()
    assert frame.descripcion_var.get() == "Desde catálogo"


def test_tree_selection_forces_catalog_mode():
    frame = _build_risk_frame()
    header_tree = risk.RiskFrame.build_header_tree(DummyWidget())
    frame.attach_header_tree(header_tree)
    iid = header_tree.insert("", "end", values=("RSK-123456", "", "", "", ""))
    header_tree.selection_set(iid)
    frame.new_risk_var.set(True)

    frame._on_tree_select()

    assert frame.is_catalog_mode()
    assert frame.id_var.get() == "RSK-123456"


def test_new_risk_mode_allows_minimal_fields():
    frame = _build_risk_frame()
    frame.new_risk_var.set(True)

    id_validator = _find_validator("ID")
    lider_validator = _find_validator("Líder")
    criticidad_validator = _find_validator("Criticidad")
    expos_validator = _find_validator("Exposición")
    desc_validator = _find_validator("Descripción")
    planes_validator = _find_validator("Planes")

    assert id_validator is not None
    assert desc_validator is not None
    assert id_validator.validate_callback() is not None

    frame.id_var.set("LIBRE-0001")
    frame.descripcion_var.set("Riesgo libre")

    assert id_validator.validate_callback() is None
    assert desc_validator.validate_callback() is None
    assert lider_validator.validate_callback() is None
    assert criticidad_validator.validate_callback() is None
    assert expos_validator.validate_callback() is None
    assert planes_validator.validate_callback() is None


def test_catalog_mode_requires_previous_omitted_fields():
    frame = _build_risk_frame()
    frame.new_risk_var.set(True)
    frame.id_var.set("LIBRE-0002")
    frame.descripcion_var.set("Descripción libre")

    lider_validator = _find_validator("Líder")
    criticidad_validator = _find_validator("Criticidad")
    planes_validator = _find_validator("Planes")

    assert lider_validator.validate_callback() is None
    assert criticidad_validator.validate_callback() is None
    assert planes_validator.validate_callback() is None

    frame.new_risk_var.set(False)
    frame._on_mode_toggle()

    assert lider_validator.validate_callback() is not None
    assert criticidad_validator.validate_callback() is not None
    assert planes_validator.validate_callback() is not None


def test_catalog_mode_enforces_risk_id_pattern():
    frame = _build_risk_frame()
    id_validator = _find_validator("ID")

    frame.id_var.set("LIBRE-01")

    assert "RSK" in (id_validator.validate_callback() or "")


def test_new_risk_mode_accepts_free_id_format():
    frame = _build_risk_frame()
    id_validator = _find_validator("ID")

    frame.new_risk_var.set(True)
    frame.id_var.set("LIBRE-ABC-01")
    frame.update_risk_validation_state()

    assert id_validator.validate_callback() is None


def test_update_risk_validation_state_toggles_catalog_validators(monkeypatch):
    frame = _build_risk_frame()
    frame.new_risk_var.set(True)
    frame.update_risk_validation_state()

    suspended = [
        _find_validator("Líder"),
        _find_validator("Criticidad"),
        _find_validator("Exposición"),
        _find_validator("Planes"),
    ]

    assert all(v.suspend_count == 1 for v in suspended)
    assert all(
        frame.badges._registry[key]._state == "neutral"
        for key in ("riesgo_lider", "riesgo_criticidad", "riesgo_exposicion", "riesgo_planes")
    )

    frame.new_risk_var.set(False)
    frame.update_risk_validation_state()

    assert all(v.suspend_count == 0 for v in suspended)


def test_build_risk_suggestions_excludes_used_and_ranks():
    lookup = {
        "RSK-1": {"descripcion": "Fraude digital", "proceso": "Fraude", "modalidad": "Tarjeta"},
        "RSK-2": {"descripcion": "Operación manual", "proceso": "Operación"},
        "RSK-3": {"descripcion": "Fraude en canales físicos", "proceso": "Fraude", "canal": "Agencia"},
    }

    suggestions = risk.build_risk_suggestions(
        lookup,
        context={"proceso": "Fraude", "modalidad": "Tarjeta", "canal": "Digital"},
        excluded_ids={"RSK-2"},
    )

    ids = [s["id_riesgo"] for s in suggestions]
    assert "RSK-2" not in ids
    assert ids[0] == "RSK-1"


def test_offer_catalog_modal_uses_factory_and_backfills(monkeypatch):
    frame = _build_risk_frame()
    frame.risk_lookup = {"RSK-000777": {"descripcion": "Catálogo", "lider": "Lead"}}
    captured = {}

    def fake_factory(parent, suggestions, on_select, trigger=""):
        captured["suggestions"] = suggestions
        captured["trigger"] = trigger
        on_select("RSK-000777")
        return "modal"

    frame.modal_factory = fake_factory
    frame.offer_catalog_modal(trigger="add_risk")

    assert captured["trigger"] == "add_risk"
    assert captured["suggestions"][0]["id_riesgo"] == "RSK-000777"
    assert frame.id_var.get() == "RSK-000777"
    assert frame.descripcion_var.get() == "Catálogo"


def test_mode_toggle_invokes_modal_in_catalog_mode():
    frame = _build_risk_frame()
    calls = []
    frame.offer_catalog_modal = lambda trigger="": calls.append(trigger)

    frame._on_mode_toggle()

    assert calls == ["mode_toggle"]
