from types import SimpleNamespace

from ui.layout import accordion


def test_collapsible_refresh_schedules_lazy_scrollable_resize(monkeypatch):
    refresh_calls = []

    def _resolver():
        def _refresher(widget):
            refresh_calls.append(widget)

        return _refresher

    monkeypatch.setattr(
        accordion.CollapsibleSection, "_resolve_scrollable_refresh", staticmethod(_resolver)
    )

    section = object.__new__(accordion.CollapsibleSection)
    section.content = SimpleNamespace(
        pack=lambda **_kwargs: None, pack_forget=lambda: None
    )
    scheduled = []
    section.after_idle = lambda fn: scheduled.append(fn) or (fn() if callable(fn) else None)
    section._is_open = False

    section._show_content()
    section._hide_content()

    assert refresh_calls == [section, section]
    assert len(scheduled) >= 2


def test_collapsible_refresh_is_optional_on_toggle(monkeypatch):
    monkeypatch.setattr(
        accordion.CollapsibleSection, "_resolve_scrollable_refresh", staticmethod(lambda: None)
    )

    toggled_states = []

    section = object.__new__(accordion.CollapsibleSection)
    section.content = SimpleNamespace(pack=lambda **_kwargs: None, pack_forget=lambda: None)
    section.indicator = SimpleNamespace(configure=lambda **_kwargs: None)
    section.after_idle = lambda *_args, **_kwargs: None
    section._is_open = False
    section._on_toggle = lambda cs: toggled_states.append(cs.is_open)

    section.toggle()

    assert toggled_states == [True]
