"""Tests for the unified validation badge component."""

from types import SimpleNamespace

from validation_badge import (
    NEUTRAL_ICON,
    SUCCESS_ICON,
    WARNING_ICON,
    ValidationBadge,
    ValidationBadgeGroup,
    build_message_preview,
)


class DummyVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def trace_add(self, *_args):
        return None


class StubWidget:
    def __init__(self, *args, textvariable=None, **kwargs):
        self.textvariable = textvariable
        self._mapped = False
        self._bindings = []
        self._config = {}

    def grid(self, *args, **kwargs):
        self._mapped = True
        return None

    def pack(self, *args, **kwargs):
        self._mapped = True
        return None

    def grid_remove(self, *args, **kwargs):
        self._mapped = False
        return None

    def pack_forget(self, *args, **kwargs):
        self._mapped = False
        return None

    def winfo_ismapped(self):
        return self._mapped

    def winfo_manager(self):
        return "grid" if self._mapped else ""

    def bind(self, *args, **kwargs):
        self._bindings.append(SimpleNamespace(args=args, kwargs=kwargs))
        return None

    def configure(self, **kwargs):
        self._config.update(kwargs)

    def update_idletasks(self):
        return None

    def winfo_reqwidth(self):
        return 160

    def winfo_exists(self):
        return True


class DummyStyle:
    def __init__(self, *args, **kwargs):
        self._config = {}

    def lookup(self, style, option):
        return self._config.get((style, option), "")

    def configure(self, style, **kwargs):
        for key, value in kwargs.items():
            self._config[(style, key)] = value


class TkStub:
    StringVar = DummyVar


class TtkStub:
    Frame = StubWidget
    Label = StubWidget
    Style = DummyStyle


TK = TkStub()
TTK = TtkStub()


def test_validation_badge_cycles_through_states():
    message_var = DummyVar("Completa la fecha de ocurrencia para continuar")
    badge = ValidationBadge(
        StubWidget(),
        textvariable=message_var,
        default_state="warning",
        tk_module=TK,
        ttk_module=TTK,
    )
    badge.pack()

    preview = badge._text_var.get()
    assert preview == build_message_preview(message_var.get())

    badge._cycle_display()
    assert badge._text_var.get() == message_var.get()

    badge._cycle_display()
    assert badge._text_var.get() == WARNING_ICON

    badge._cycle_display()
    assert badge._text_var.get() == build_message_preview(message_var.get())


def test_validation_badge_group_updates_states():
    group = ValidationBadgeGroup(
        pending_text=NEUTRAL_ICON, success_text=SUCCESS_ICON, tk_module=TK, ttk_module=TTK
    )
    badge = group.create_and_register("sample", StubWidget(), row=0, column=0)

    group.update_badge("sample", False, "Dato pendiente")
    assert badge._text_var.get() == build_message_preview("Dato pendiente")

    group.update_badge("sample", True, None)
    assert badge._text_var.get() == SUCCESS_ICON

    group.update_badge("sample", False, None)
    assert badge._text_var.get() == NEUTRAL_ICON


def test_validation_badge_hide_and_show_preserves_mapping():
    badge = ValidationBadge(StubWidget(), default_state="warning", tk_module=TK, ttk_module=TTK)
    badge.grid()

    assert badge.winfo_ismapped() is True
    badge.hide()
    assert badge.winfo_ismapped() is False

    badge.show()
    assert badge.winfo_ismapped() is True
