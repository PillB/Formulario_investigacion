import types

import app as app_module
from utils.widget_registry import WidgetIdRegistry
from validators import FieldValidator


class DummyWidget:
    def __init__(self, text: str | None = None, root_coords: tuple[int, int] = (0, 0)):
        self.master = None
        self._text = text
        self._bindings = {}
        self._root_coords = root_coords

    def bind(self, name, callback=None, add=None):
        self._bindings[name] = callback

    def get(self):
        return ""

    def winfo_class(self):
        return "Entry"

    def winfo_name(self):
        return "auto"

    def winfo_rootx(self):
        return self._root_coords[0]

    def winfo_rooty(self):
        return self._root_coords[1]

    def cget(self, key):
        if key == "text":
            return self._text
        raise KeyError(key)


def test_field_validator_registers_logical_id(monkeypatch):
    app = app_module.FraudCaseApp.__new__(app_module.FraudCaseApp)
    app._widget_registry = WidgetIdRegistry()
    app._tab_widgets = {}
    app._slugify_identifier = app_module.FraudCaseApp._slugify_identifier.__get__(app)
    app._is_descendant_of = app_module.FraudCaseApp._is_descendant_of.__get__(app)
    monkeypatch.setattr(
        FieldValidator,
        "widget_registry_consumer",
        app_module.FraudCaseApp._register_field_widget.__get__(app),
    )

    widget = DummyWidget("Campo")
    FieldValidator(widget, lambda: None, [], "Caso - ID")

    resolved = app._widget_registry.resolve(widget)
    assert resolved is not None
    assert resolved.startswith("field.") or resolved.startswith("tab.")


def test_navigation_event_prefers_registered_id(monkeypatch):
    app = app_module.FraudCaseApp.__new__(app_module.FraudCaseApp)
    app.logs = []
    app._widget_registry = WidgetIdRegistry()
    app._tab_widgets = {}
    app._slugify_identifier = app_module.FraudCaseApp._slugify_identifier.__get__(app)
    app._describe_widget = app_module.FraudCaseApp._describe_widget.__get__(app)
    app._resolve_widget_id = app_module.FraudCaseApp._resolve_widget_id.__get__(app)
    captured_metrics: list[str] = []
    app._accumulate_navigation_metrics = lambda widget_id, coords: captured_metrics.append(
        widget_id
    )

    widget = DummyWidget()
    logical_id = app._widget_registry.register(widget, "tab.caso.field.case_id")

    captured_logs: list[str | None] = []

    def capture(event_type, message, logs, widget_id=None, **kwargs):
        captured_logs.append(widget_id)
        logs.append({"widget_id": widget_id})

    monkeypatch.setattr(app_module, "log_event", capture)

    app.root = types.SimpleNamespace(focus_get=lambda: widget)
    event = types.SimpleNamespace(widget=widget, x_root=5, y_root=10)

    app._handle_global_navigation_event(event, "focus_in")

    assert logical_id in captured_logs
    assert logical_id in captured_metrics


def test_navigation_event_uses_widget_root_coords_when_missing(monkeypatch):
    app = app_module.FraudCaseApp.__new__(app_module.FraudCaseApp)
    app.logs = []
    app._widget_registry = WidgetIdRegistry()
    app._tab_widgets = {}
    app._slugify_identifier = app_module.FraudCaseApp._slugify_identifier.__get__(app)
    app._describe_widget = app_module.FraudCaseApp._describe_widget.__get__(app)
    app._resolve_widget_id = app_module.FraudCaseApp._resolve_widget_id.__get__(app)
    app._safe_update_idletasks = lambda: setattr(app, "_idle_called", True)

    widget = DummyWidget(root_coords=(120, 340))
    logical_id = app._widget_registry.register(widget, "tab.caso.field.case_id")

    captured_coords: list[str | None] = []
    captured_metrics: list[tuple | None] = []

    def capture(event_type, message, logs, widget_id=None, coords=None, **kwargs):
        captured_coords.append(coords)
        logs.append({"widget_id": widget_id, "coords": coords})

    def accumulate(widget_id, coords):
        captured_metrics.append(coords)

    monkeypatch.setattr(app_module, "log_event", capture)
    app._accumulate_navigation_metrics = accumulate

    app.root = types.SimpleNamespace(focus_get=lambda: widget)
    event = types.SimpleNamespace(widget=widget, x_root=None, y_root=None)

    app._handle_global_navigation_event(event, "focus_in")

    assert app._idle_called is True
    assert captured_coords[-1] == "120.0,340.0"
    assert captured_metrics[-1] == (120.0, 340.0)
    assert captured_coords[-1] is not None
    assert captured_metrics[-1] is not None
