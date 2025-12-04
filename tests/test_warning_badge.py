from types import SimpleNamespace

from ui.frames.utils import BadgeManager, ToggleWarningBadge, format_warning_preview


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
    assert badge._display_var.get() == ""
    assert badge._text_label.winfo_manager() == ""
    assert message_var.get() == "Mensaje de prueba"

    badge.toggle(animate=False)
    assert badge.is_collapsed is True
    assert badge._display_var.get() == format_warning_preview(message_var.get())


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


def test_warning_badge_compacts_text_when_collapsed():
    long_message = "ABCDEFGHIJKLMNO12345678901234567890"
    message_var = DummyVar(long_message)
    badge = ToggleWarningBadge(
        StubWidget(),
        textvariable=message_var,
        initially_collapsed=True,
        tk_module=TK,
        ttk_module=TTK,
    )
    badge.pack()

    preview = badge._display_var.get()
    preview_lines = preview.splitlines()

    assert badge.is_collapsed is True
    assert len(preview_lines) <= 2
    assert all(len(line) <= 15 for line in preview_lines)
    assert preview_lines[-1].endswith("...")

    badge.expand(animate=False)
    assert badge._display_var.get() == long_message


def test_badge_manager_uses_compact_warning_preview():
    class CaptureBadge:
        def __init__(self):
            self.text = None
            self.style = None

        def configure(self, **kwargs):  # noqa: D401, ANN001
            """Capture the configured attributes for assertions."""

            self.text = kwargs.get("text", self.text)
            self.style = kwargs.get("style", self.style)

    badge = CaptureBadge()
    manager = BadgeManager()
    manager.set_badge_state(badge, False, "ABCDEFGHIJKLMNO123456789012345")

    assert badge.text is not None
    lines = badge.text.splitlines()
    assert len(lines) <= 2
    assert all(len(line) <= 15 for line in lines)
