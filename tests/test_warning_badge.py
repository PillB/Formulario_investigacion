from types import SimpleNamespace

from ui.frames.utils import ToggleWarningBadge


class DummyVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


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


class TkStub:
    StringVar = DummyVar
    Label = StubWidget


class TtkStub:
    Frame = StubWidget
    Label = StubWidget


TK = TkStub()
TTK = TtkStub()


def test_warning_badge_toggles_and_preserves_message():
    message_var = DummyVar("Mensaje de prueba")
    badge = ToggleWarningBadge(
        StubWidget(),
        textvariable=message_var,
        initially_collapsed=True,
        tk_module=TK,
        ttk_module=TTK,
    )
    badge.pack()

    assert badge.is_collapsed is True

    badge.expand(animate=False)
    assert badge.is_collapsed is False
    assert message_var.get() == "Mensaje de prueba"

    badge.toggle(animate=False)
    assert badge.is_collapsed is True
    assert message_var.get() == "Mensaje de prueba"


def test_warning_badge_click_flow_updates_mapping_state():
    message_var = DummyVar("Mensaje crítico")
    badge = ToggleWarningBadge(
        StubWidget(),
        textvariable=message_var,
        initially_collapsed=False,
        tk_module=TK,
        ttk_module=TTK,
    )
    badge.grid()

    assert badge.winfo_ismapped() is True
    badge.collapse(animate=False)
    assert badge.is_collapsed is True

    badge.toggle(animate=False)
    assert badge.is_collapsed is False
    assert badge.winfo_ismapped() is True
