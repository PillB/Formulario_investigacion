from types import SimpleNamespace

from ui.frames import utils


class _Bindable:
    def __init__(self):
        self.bound = {}
        self.children = []

    def bind(self, event, func, add=None):  # noqa: ARG002
        self.bound[event] = func

    def winfo_children(self):
        return list(self.children)


class _CanvasStub(_Bindable):
    def __init__(self):
        super().__init__()
        self.bound_all = {}
        self.scroll_calls = []

    def winfo_parent(self):
        return ""

    def bind_all(self, event, func, add=None):  # noqa: ARG002
        self.bound_all[event] = func

    def yview_scroll(self, steps, unit):
        self.scroll_calls.append((steps, unit))


class _ScrollableWidget(_Bindable):
    def __init__(self, *, yview=(0.0, 1.0), parent=None):
        super().__init__()
        self._yview = yview
        self._parent = parent
        self.scroll_calls = []

    def yview(self):
        return self._yview

    def yview_scroll(self, steps, unit):
        self.scroll_calls.append((steps, unit))

    def winfo_parent(self):
        return self._parent or ""

    def nametowidget(self, name):  # noqa: ANN001
        return self._parent if name == self._parent else self


class _ComboboxStub(_Bindable):
    def __init__(self, parent=None):
        super().__init__()
        self._parent = parent
        self.values = ["uno", "dos", "tres"]
        self.selection_index = 1

    def winfo_parent(self):
        return self._parent or ""

    def nametowidget(self, name):  # noqa: ANN001
        return self._parent if name == self._parent else self

    def set(self, value):  # noqa: ANN001
        if value in self.values:
            self.selection_index = self.values.index(value)

    def get(self):  # noqa: ANN001
        return self.values[self.selection_index]

    def apply_default_cycle(self, handler_result):
        if handler_result != "break":
            self.selection_index = (self.selection_index + 1) % len(self.values)


def test_mousewheel_uses_minimum_step_for_small_delta():
    canvas = _CanvasStub()
    target = _Bindable()

    utils._enable_mousewheel_scrolling(canvas, target)

    enter_handler = canvas.bound["<Enter>"]
    enter_handler(SimpleNamespace())

    handler = canvas.bound["<MouseWheel>"]
    handler(SimpleNamespace(delta=1))

    assert canvas.scroll_calls == [(-1, "units")]


def test_mousewheel_binds_child_widgets_for_scroll():
    canvas = _CanvasStub()
    target = _Bindable()
    child = _Bindable()
    target.children.append(child)

    utils._enable_mousewheel_scrolling(canvas, target)

    child.bound["<Enter>"](SimpleNamespace())
    child.bound["<MouseWheel>"](SimpleNamespace(delta=-240))

    assert canvas.scroll_calls == [(2, "units")]


def test_global_binder_scrolls_parent_canvas_on_boundary():
    root = _CanvasStub()
    binder = utils.GlobalScrollBinding(root)
    canvas = _CanvasStub()
    target = _Bindable()

    binder.register_tab_canvas("tab1", canvas, target)
    binder.activate_tab("tab1")
    binder.bind_to_root()

    handler = root.bound_all["<MouseWheel>"]
    boundary_widget = _ScrollableWidget()
    handler(SimpleNamespace(widget=boundary_widget, delta=-240))

    assert canvas.scroll_calls == [(2, "units")]


def test_combobox_scroll_forwarding_blocks_option_cycle(monkeypatch):
    canvas = _CanvasStub()
    target = _Bindable()
    combobox = _ComboboxStub(parent=target)
    target.children.append(combobox)

    monkeypatch.setattr(utils.ttk, "Combobox", _ComboboxStub)

    utils._enable_mousewheel_scrolling(canvas, target)

    combobox.bound["<Enter>"](SimpleNamespace())
    handler = combobox.bound["<MouseWheel>"]
    previous_value = combobox.get()
    result = handler(SimpleNamespace(widget=combobox, delta=-120))
    combobox.apply_default_cycle(result)

    assert canvas.scroll_calls == [(1, "units")]
    assert combobox.get() == previous_value


def test_global_binder_comboboxes_forward_scroll(monkeypatch):
    root = _CanvasStub()
    canvas = _CanvasStub()
    target = _Bindable()
    combobox = _ComboboxStub(parent=target)
    target.children.append(combobox)

    monkeypatch.setattr(utils.ttk, "Combobox", _ComboboxStub)

    binder = utils.GlobalScrollBinding(root)
    binder.register_tab_canvas("tab-combo", canvas, target)

    combobox.bound["<Enter>"](SimpleNamespace())
    handler = combobox.bound["<MouseWheel>"]
    initial_value = combobox.get()
    result = handler(SimpleNamespace(widget=combobox, delta=-240))
    combobox.apply_default_cycle(result)

    assert canvas.scroll_calls == [(2, "units")]
    assert combobox.get() == initial_value


def test_scrollable_container_wires_scrollbar_and_mousewheel(monkeypatch):
    class FrameStub(_Bindable):
        def __init__(self, parent=None):
            super().__init__()
            self.parent = parent
            self.grid_calls = []
            self.column_configure = []
            self.row_configure = []

        def columnconfigure(self, index, weight):  # noqa: D401, ANN001
            """Capture column weight configuration."""
            self.column_configure.append((index, weight))

        def rowconfigure(self, index, weight):  # noqa: D401, ANN001
            """Capture row weight configuration."""
            self.row_configure.append((index, weight))

        def grid(self, *args, **kwargs):  # noqa: ANN001
            self.grid_calls.append((args, kwargs))

        def winfo_parent(self):
            return ""

        def winfo_manager(self):
            return "grid"

    class CanvasStub(FrameStub):
        def __init__(self, parent=None, **_kwargs):
            super().__init__(parent)
            self.configure_calls = []
            self.create_window_calls = []
            self.item_configure_calls = []
            self.scroll_calls = []

        def configure(self, **kwargs):  # noqa: D401, ANN001
            """Capture configuration calls."""
            self.configure_calls.append(kwargs)

        def create_window(self, coords, window=None, anchor=None):  # noqa: ANN001
            self.create_window_calls.append((coords, window, anchor))
            return "win-1"

        def bbox(self, _tag):  # noqa: D401, ANN001
            """Return a fixed bounding box for scrollregion."""
            return (0, 0, 100, 200)

        def itemconfigure(self, item_id, **kwargs):  # noqa: ANN001
            self.item_configure_calls.append((item_id, kwargs))

        def yview(self, *args, **kwargs):  # noqa: ANN001, D401
            """Stub yview query."""
            return (args, kwargs)

        def yview_scroll(self, steps, unit):
            self.scroll_calls.append((steps, unit))

    created_scrollbars = []

    class ScrollbarStub:
        def __init__(self, parent=None, orient=None, command=None):  # noqa: ANN001
            self.parent = parent
            self.orient = orient
            self.command = command
            self.grid_calls = []
            created_scrollbars.append(self)

        def grid(self, *args, **kwargs):  # noqa: ANN001
            self.grid_calls.append((args, kwargs))

        def set(self, *args, **kwargs):  # noqa: ANN001, D401
            """Stub scroll command setter."""
            return (args, kwargs)

    monkeypatch.setattr(utils.tk, "Canvas", CanvasStub)
    monkeypatch.setattr(utils.ttk, "Frame", FrameStub)
    monkeypatch.setattr(utils.ttk, "Scrollbar", ScrollbarStub)

    outer, inner = utils.create_scrollable_container(parent=FrameStub())

    assert outer._scroll_canvas is not None  # type: ignore[attr-defined]
    assert outer._scroll_inner is inner  # type: ignore[attr-defined]
    assert outer.column_configure and outer.row_configure
    assert outer._scroll_canvas.configure_calls[-1]["yscrollcommand"]  # type: ignore[index]

    # The scrollbar should have been gridded with vertical orientation
    assert created_scrollbars
    assert created_scrollbars[-1].grid_calls
    assert created_scrollbars[-1].orient == "vertical"

    enter = inner.bound["<Enter>"]
    wheel = inner.bound["<MouseWheel>"]
    enter(SimpleNamespace())
    wheel(SimpleNamespace(delta=-120, widget=inner))

    assert outer._scroll_canvas.scroll_calls == [(1, "units")]  # type: ignore[attr-defined]


def test_resize_scrollable_avoids_canvas_height_changes(monkeypatch):
    class FrameStub(_Bindable):
        def __init__(self, parent=None):
            super().__init__()
            self.master = parent
            self.grid_calls = []
            self.column_configure = []
            self.row_configure = []
            self._height = 0
            self._reqheight = 220

        def columnconfigure(self, index, weight):  # noqa: ANN001
            self.column_configure.append((index, weight))

        def rowconfigure(self, index, weight):  # noqa: ANN001
            self.row_configure.append((index, weight))

        def grid(self, *args, **kwargs):  # noqa: ANN001
            self.grid_calls.append((args, kwargs))

        def winfo_parent(self):
            return ""

        def winfo_manager(self):
            return "grid"

        def winfo_height(self):
            return self._height

        def winfo_reqheight(self):
            return self._reqheight

        def after(self, _delay, func=None):  # noqa: ANN001
            if callable(func):
                func()
            return "job-after"

        def after_cancel(self, _job):  # noqa: ANN001
            return None

        def after_idle(self, func=None):  # noqa: ANN001
            if callable(func):
                func()
            return "job-idle"

    class CanvasStub(FrameStub):
        def __init__(self, parent=None, **_kwargs):  # noqa: ANN001
            super().__init__(parent)
            self.configure_calls = []
            self.create_window_calls = []
            self.item_configure_calls = []
            self.scroll_calls = []
            self._bbox_height = 200

        def configure(self, **kwargs):  # noqa: ANN001
            self.configure_calls.append(kwargs)
            if "height" in kwargs:
                self._height = kwargs["height"]

        def create_window(self, coords, window=None, anchor=None):  # noqa: ANN001
            self.create_window_calls.append((coords, window, anchor))
            return "win-1"

        def bbox(self, _tag):  # noqa: ANN001
            return (0, 0, 100, self._bbox_height)

        def itemconfigure(self, item_id, **kwargs):  # noqa: ANN001
            self.item_configure_calls.append((item_id, kwargs))

        def yview(self, *args, **kwargs):  # noqa: ANN001
            return (args, kwargs)

        def yview_scroll(self, steps, unit):
            self.scroll_calls.append((steps, unit))

    class ScrollbarStub:
        def __init__(self, parent=None, orient=None, command=None):  # noqa: ANN001
            self.parent = parent
            self.orient = orient
            self.command = command
            self.grid_calls = []

        def grid(self, *args, **kwargs):  # noqa: ANN001
            self.grid_calls.append((args, kwargs))

        def set(self, *args, **kwargs):  # noqa: ANN001, D401
            """Stub scroll command setter."""
            return (args, kwargs)

    monkeypatch.setattr(utils.tk, "Canvas", CanvasStub)
    monkeypatch.setattr(utils.ttk, "Frame", FrameStub)
    monkeypatch.setattr(utils.ttk, "Scrollbar", ScrollbarStub)

    outer, inner = utils.create_scrollable_container(parent=FrameStub())
    canvas = outer._scroll_canvas  # type: ignore[attr-defined]

    inner._reqheight = 260
    canvas._bbox_height = 260
    utils.resize_scrollable_to_content(outer)

    inner._reqheight = 320
    canvas._bbox_height = 320
    configure_handler = inner.bound["<Configure>"]
    for _ in range(3):
        configure_handler(SimpleNamespace(width=480))
        utils.resize_scrollable_to_content(outer)

    height_configs = [call for call in canvas.configure_calls if "height" in call]
    assert not height_configs
