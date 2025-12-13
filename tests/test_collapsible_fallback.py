import types

import ui.frames.utils as utils


class DummyStyle:
    def element_names(self):
        return []

    def layout(self, *args, **kwargs):
        return None

    def configure(self, *args, **kwargs):
        return None

    def map(self, *args, **kwargs):
        return None


class DummyWidget:
    def __init__(self, *args, **kwargs):
        self._bindings = []

    def bind(self, sequence, callback, add=None):
        self._bindings.append((sequence, callback, add))
        return f"bind_{len(self._bindings)}"


class DummyTtk(types.SimpleNamespace):
    def __init__(self):
        super().__init__(Frame=DummyWidget, Label=DummyWidget, Style=DummyStyle)


def _patch_style(monkeypatch):
    theme = types.SimpleNamespace(current=lambda: {"name": "dummy"}, _ensure_style=lambda: DummyStyle())
    monkeypatch.setattr(utils, "ThemeManager", theme)
    monkeypatch.setattr(utils, "ttk", DummyTtk())
    monkeypatch.setattr(utils, "register_styles", lambda: None)


def test_fallback_builds_clickable_header(monkeypatch):
    _patch_style(monkeypatch)

    class CrashingSection:
        def __init__(self, *_args, **_kwargs):  # noqa: D401
            """Siempre falla para forzar el uso del fallback."""

            raise RuntimeError("boom")

    card = utils.create_collapsible_card(
        parent=DummyWidget(),
        title="Cliente 1",
        open=True,
        collapsible_cls=CrashingSection,
    )

    assert hasattr(card, "header")
    assert hasattr(card, "indicator")
    # Simula click en el encabezado y confirma que colapsa
    card.header._trigger("<Button-1>")

    assert card.is_open is False
    assert getattr(card.indicator, "_text", "") == "▸"


def test_fallback_toggle_informs_callback(monkeypatch):
    _patch_style(monkeypatch)
    toggled = []

    class CrashingSection:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    card = utils.create_collapsible_card(
        parent=DummyWidget(),
        title="Producto 1",
        open=False,
        on_toggle=lambda section: toggled.append(section.is_open),
        collapsible_cls=CrashingSection,
    )

    assert card.is_open is False

    card.header._trigger("<Button-1>")

    assert card.is_open is True
    assert toggled == [True]


def test_fallback_indicator_click_toggles(monkeypatch):
    _patch_style(monkeypatch)

    class CrashingSection:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    card = utils.create_collapsible_card(
        parent=DummyWidget(),
        title="Equipo 1",
        open=False,
        collapsible_cls=CrashingSection,
    )

    assert card.is_open is False

    card.indicator._trigger("<Button-1>")

    assert card.is_open is True
