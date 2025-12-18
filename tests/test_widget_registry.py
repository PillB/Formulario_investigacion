import types

import app as app_module
from utils.widget_registry import WidgetIdRegistry
from validators import FieldValidator


class DummyWidget:
    def __init__(self, text: str | None = None):
        self.master = None
        self._text = text
        self._bindings = {}

    def bind(self, name, callback=None, add=None):
        self._bindings[name] = callback

    def get(self):
        return ""

    def winfo_class(self):
        return "Entry"

    def winfo_name(self):
        return "auto"

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
