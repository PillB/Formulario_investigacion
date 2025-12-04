from types import SimpleNamespace

import pytest

from ui.frames import clients, team
from tests import test_products_frame as tpf


class DummyVar(tpf.DummyVar):
    def trace_add(self, *_args, **_kwargs):
        return None


class FocusDummyWidget(tpf.DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.master = kwargs.get("parent") or kwargs.get("master")
        self.content = kwargs.get("content", None)

    def grid(self, *args, **kwargs):  # pragma: no cover - layout stub
        self._grid_args = (args, kwargs)
        return None

    def columnconfigure(self, *_args, **_kwargs):
        return None

    def rowconfigure(self, *_args, **_kwargs):
        return None

    def bind_all(self, sequence, callback, add=None):
        return self.bind(sequence, callback, add)


class DummyListbox(FocusDummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selection: set[int] = set()

    def selection_clear(self, start, end):
        if start == 0 and end == "end":
            self._selection.clear()

    def selection_set(self, index):
        self._selection.add(index)

    def curselection(self):
        return tuple(sorted(self._selection))

    def yview(self, *args, **kwargs):
        self._yview = (args, kwargs)
        return None


class DummyBadgeManager:
    def __init__(self, *args, **_kwargs):
        pass

    def wrap_validation(self, _key, validate_fn):
        return validate_fn

    def create_and_register(self, *args, **_kwargs):
        return None


class DummyToggleWarningBadge(FocusDummyWidget):
    def __init__(self, *args, **_kwargs):
        super().__init__(*args, **_kwargs)

    def hide(self):
        return None

    def show(self):
        return None


class DummyScrollbar(FocusDummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command = kwargs.get("command")

    def set(self, *args, **kwargs):
        self._set_args = (args, kwargs)
        return None


class DummyCollapsible(FocusDummyWidget):
    def __init__(self, parent=None, title="", open=True, on_toggle=None, **_kwargs):
        super().__init__(parent=parent)
        self.title = title
        self._is_open = open
        self._on_toggle = on_toggle
        self.header = FocusDummyWidget(parent=self)
        self.content = FocusDummyWidget(parent=self)

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


@pytest.fixture(autouse=True)
def patch_client_and_team_widgets(monkeypatch):
    class _TkStub:
        StringVar = DummyVar
        END = "end"
        Scrollbar = DummyScrollbar

        class Listbox(DummyListbox):
            pass

    class _TtkStub:
        class Treeview(FocusDummyWidget):
            def __init__(self, *args, columns=None, **kwargs):
                super().__init__(*args, **kwargs)
                self._columns = list(columns or [])
                self._items: list[str] = []
                self._values: dict[str, tuple] = {}
                self._selection: tuple[str, ...] = ()

            def heading(self, *_args, **_kwargs):
                return None

            def column(self, *_args, **_kwargs):
                return None

            def configure(self, **kwargs):
                self._config.update(kwargs)
                return None

            def yview(self, *args, **kwargs):
                self._yview = (args, kwargs)
                return None

            def xview(self, *args, **kwargs):
                self._xview = (args, kwargs)
                return None

            def tag_configure(self, *_args, **_kwargs):
                return None

            def get_children(self, *_args):
                return tuple(self._items)

            def delete(self, *items):
                for item in items:
                    if item in self._items:
                        self._items.remove(item)
                        self._values.pop(item, None)

            def insert(self, _parent, _index, iid=None, values=None, tags=None):
                iid = iid or str(len(self._items))
                self._items.append(iid)
                self._values[iid] = tuple(values or [])
                return iid

            def selection(self):
                return self._selection

            def item(self, item, option=None):
                if option == "values":
                    return self._values.get(item, ())
                return {}

            def move(self, item, _parent, index):  # pragma: no cover - sortable stub
                if item in self._items:
                    self._items.remove(item)
                    self._items.insert(index, item)

        LabelFrame = FocusDummyWidget
        Frame = FocusDummyWidget
        Label = FocusDummyWidget
        Entry = FocusDummyWidget
        Combobox = FocusDummyWidget
        Button = FocusDummyWidget
        Scrollbar = DummyScrollbar

    for module in (clients, team):
        monkeypatch.setattr(module, "tk", _TkStub())
        monkeypatch.setattr(module, "ttk", _TtkStub())
        monkeypatch.setattr(module, "CollapsibleSection", DummyCollapsible)
        monkeypatch.setattr(module, "FieldValidator", tpf.RecordingValidator)
        monkeypatch.setattr(module, "BadgeManager", DummyBadgeManager)
        monkeypatch.setattr(module, "ToggleWarningBadge", DummyToggleWarningBadge, raising=False)

    tpf.RecordingValidator.instances.clear()
    yield
    tpf.RecordingValidator.instances.clear()


def _owner_namespace():
    return SimpleNamespace(
        inline_summary_trees={},
        clients_summary_tree=None,
        team_summary_tree=None,
    )


def _build_client_frame(owner):
    return clients.ClientFrame(
        parent=FocusDummyWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        update_client_options=lambda: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
        owner=owner,
        summary_parent=FocusDummyWidget(),
        summary_refresh_callback=lambda *_args, **_kwargs: None,
    )


def _build_team_frame(owner, idx=0):
    return team.TeamMemberFrame(
        parent=FocusDummyWidget(),
        idx=idx,
        remove_callback=lambda _frame: None,
        update_team_options=lambda: None,
        team_lookup={},
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
        owner=owner,
        summary_parent=FocusDummyWidget(),
        summary_refresh_callback=lambda *_args, **_kwargs: None,
    )


def _first_focus_binding(widget):
    return next(cb for seq, cb, _add in getattr(widget, "_bindings", []) if seq == "<FocusIn>")


def test_client_summary_owner_tracks_toggle_and_focus(monkeypatch):
    owner = _owner_namespace()
    frame = _build_client_frame(owner)

    assert owner._client_summary_owner is frame

    owner._client_summary_owner = None
    frame.section._is_open = False
    frame.section.toggle(None)

    assert owner._client_summary_owner is frame

    owner._client_summary_owner = None
    focus_callback = _first_focus_binding(frame.id_entry)
    focus_callback(SimpleNamespace(widget=frame.id_entry))

    assert owner._client_summary_owner is frame


def test_team_summary_owner_follows_focus(monkeypatch):
    owner = _owner_namespace()
    team_a = _build_team_frame(owner, idx=0)
    assert owner._team_summary_owner is team_a

    team_b = _build_team_frame(owner, idx=1)
    assert owner._team_summary_owner is team_b

    focus_callback = _first_focus_binding(team_b.id_entry)
    owner._team_summary_owner = team_a
    focus_callback(SimpleNamespace(widget=team_b.id_entry))

    assert owner._team_summary_owner is team_b

    owner._team_summary_owner = None
    team_b.section._is_open = False
    team_b.section.toggle(None)

    assert owner._team_summary_owner is team_b
