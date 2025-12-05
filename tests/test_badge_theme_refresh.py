"""Tests ensuring validation badges stay in sync with theme changes."""

from types import SimpleNamespace

import theme_manager
from theme_manager import ThemeManager
from validation_badge import ValidationBadge


class ParentStub:
    def __init__(self):
        self._grid_calls = []

    def grid(self, *args, **kwargs):  # noqa: ANN001
        self._grid_calls.append((args, kwargs))


class LabelStub:
    def __init__(self, *args, textvariable=None, **kwargs):  # noqa: ANN001
        self.textvariable = textvariable
        self._bindings = []
        self._config = {}

    def grid(self, *args, **kwargs):  # noqa: ANN001
        return None

    def bind(self, *args, **kwargs):  # noqa: ANN001
        self._bindings.append(SimpleNamespace(args=args, kwargs=kwargs))
        return None

    def configure(self, **kwargs):  # noqa: ANN001
        self._config.update(kwargs)

    def winfo_exists(self):
        return True

    def winfo_children(self):
        return []


class StyleStub:
    def __init__(self, *args, **kwargs):
        self._config = {}

    def lookup(self, *_args, **_kwargs):
        return ""

    def configure(self, *_args, **_kwargs):
        return None


class TkStub:
    StringVar = lambda self=None: SimpleNamespace(get=lambda: "", set=lambda value: None)  # type: ignore[assignment]


class TtkStub:
    Label = LabelStub
    Style = StyleStub


def test_reapply_all_badges_refreshes_registered_badges(monkeypatch):
    parent = ParentStub()
    badge = ValidationBadge(parent, tk_module=TkStub(), ttk_module=TtkStub())

    calls: list[str] = []
    monkeypatch.setattr(badge, "reapply_style", lambda: calls.append("reapplied"))

    theme_manager.reapply_all_badges()

    assert calls == ["reapplied"]


def test_notebook_binds_badge_refresh(monkeypatch):
    bound_events: list[str] = []

    class NotebookStub:
        def configure(self, **kwargs):  # noqa: ANN001
            self.config = kwargs

        def bind(self, *args, **kwargs):  # noqa: ANN001
            bound_events.append(args[0])
            return None

        def winfo_children(self):
            return []

    monkeypatch.setattr(theme_manager.ttk, "Notebook", NotebookStub)
    notebook = NotebookStub()

    ThemeManager._apply_widget_attributes(notebook, ThemeManager.current())

    assert "<<NotebookTabChanged>>" in bound_events


def test_refresh_all_widgets_triggers_badge_reapplication(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(theme_manager, "reapply_all_badges", lambda: calls.append("refresh"))
    monkeypatch.setattr(ThemeManager, "_ensure_style", lambda: None)
    monkeypatch.setattr(ThemeManager, "_refresh_content_widgets", lambda: None)
    monkeypatch.setattr(ThemeManager, "_apply_widget_tree", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ThemeManager, "_iter_theme_windows", lambda: [])
    monkeypatch.setattr(ThemeManager, "_tracked_menus", set())
    ThemeManager._root = object()

    ThemeManager.refresh_all_widgets()

    assert calls == ["refresh"]
