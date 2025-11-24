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

    def bind_all(self, event, func, add=None):  # noqa: ARG002
        self.bound_all[event] = func

    def yview_scroll(self, steps, unit):
        self.scroll_calls.append((steps, unit))


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
