"""Verifica el helper de fecha para ``tkcalendar`` y entradas planas."""

import datetime
import types
import sys

import ui.frames.utils as utils


class DummyVariable:
    """Sustituye ``tk.StringVar`` para pruebas sin un ``Tk`` real."""

    def __init__(self, value: str | None = "") -> None:
        self._value = value or ""

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class FakeDateEntry:
    def __init__(self, _parent, *, textvariable, **_kwargs):
        self._variable = textvariable
        self._value = "2025-02-02"
        self.bindings = []
        # Simula el comportamiento de tkcalendar poblando el valor inicial.
        self._variable.set(self._value)

    def bind(self, *args, **kwargs):  # noqa: ANN001
        self.bindings.append((args, kwargs))
        return None

    def get_date(self):  # noqa: ANN001
        if not self._value:
            return None
        return datetime.date.fromisoformat(self._value)

    def get(self):  # noqa: ANN001
        return self._value

    def delete(self, *_args, **_kwargs):  # noqa: ANN001
        self._value = ""
        self._variable.set("")

    def insert(self, *_args, **kwargs):  # noqa: ANN001
        value = kwargs.get("string") if "string" in kwargs else _args[1]
        self._value = value
        self._variable.set(value)


def _inject_fake_calendar(monkeypatch):
    fake_calendar = types.SimpleNamespace(DateEntry=FakeDateEntry)
    monkeypatch.setitem(sys.modules, "tkcalendar", fake_calendar)


def test_calendar_default_is_cleared(monkeypatch):
    variable = DummyVariable("")
    _inject_fake_calendar(monkeypatch)

    widget = utils.create_date_entry(parent=object(), textvariable=variable)

    assert isinstance(widget, FakeDateEntry)
    assert variable.get() == ""
    assert widget.get() == ""


def test_initial_value_is_preserved(monkeypatch):
    variable = DummyVariable("2024-01-01")
    _inject_fake_calendar(monkeypatch)

    widget = utils.create_date_entry(parent=object(), textvariable=variable)

    assert isinstance(widget, FakeDateEntry)
    assert variable.get() == "2024-01-01"
    assert widget.get() == "2024-01-01"

