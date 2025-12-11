"""Verifica los avisos al cambiar la categoría 2 del caso."""

from datetime import datetime, timedelta

from app import FraudCaseApp
from tests.stubs import DummyVar


class _ComboStub:
    def __init__(self):
        self.values = []
        self.set_calls = []

    def __setitem__(self, key, value):
        if key != "values":
            raise KeyError(key)
        self.values = list(value)

    def set(self, value):
        self.set_calls.append(value)


def test_fraud_internal_warning_only_once_per_selection(monkeypatch, messagebox_spy):
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.cat_caso1_var = DummyVar("Riesgo de Fraude")
    app.cat_caso2_var = DummyVar("Fraude Interno")
    app.mod_caso_var = DummyVar("")
    app.case_mod_cb = _ComboStub()
    app._log_navigation_change = lambda *_args, **_kwargs: None
    app._last_fraud_warning_at = None
    app._last_case_cat2_event_value = None
    app._last_fraud_warning_selection = None
    app._last_fraud_warning_value = None

    app.on_case_cat2_change()
    assert len(messagebox_spy.warnings) == 1

    app.on_case_cat2_change()
    assert len(messagebox_spy.warnings) == 1

    app.cat_caso2_var.set("Fraude Externo")
    app.on_case_cat2_change()
    app._last_fraud_warning_at = datetime.now() - timedelta(seconds=30)

    app.cat_caso2_var.set("Fraude Interno")
    app.on_case_cat2_change()
    assert len(messagebox_spy.warnings) == 2


def test_fraud_internal_warning_respects_last_selection(monkeypatch, messagebox_spy):
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.cat_caso1_var = DummyVar("Riesgo de Fraude")
    app.cat_caso2_var = DummyVar("Fraude Interno")
    app.mod_caso_var = DummyVar("")
    app.case_mod_cb = _ComboStub()
    app._log_navigation_change = lambda *_args, **_kwargs: None
    app._last_fraud_warning_at = None
    app._last_case_cat2_event_value = None
    app._last_fraud_warning_selection = None
    app._last_fraud_warning_value = None

    app.on_case_cat2_change()
    assert len(messagebox_spy.warnings) == 1

    app._last_fraud_warning_at = None
    app._last_fraud_warning_value = None
    app.on_case_cat2_change()

    assert len(messagebox_spy.warnings) == 1
