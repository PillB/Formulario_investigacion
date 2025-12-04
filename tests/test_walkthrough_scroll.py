from __future__ import annotations

import types

from app import FraudCaseApp


class _RootStub:
    def __init__(self):
        self.idle_calls = 0

    def update_idletasks(self):  # noqa: D401
        """Simulate Tk idle refreshes."""

        self.idle_calls += 1


class _FrameStub:
    def __init__(self, *, parent=None, height=0, y=0, name=""):
        self._parent = parent
        self._parent_name = name or ""
        self._height = height
        self._y = y
        self.master = parent
        self.children: list[_FrameStub] = []
        if parent is not None:
            parent.children.append(self)

    def winfo_height(self):
        return self._height

    def winfo_y(self):
        return self._y

    def winfo_rooty(self):
        base = self._parent.winfo_rooty() if self._parent else 0
        return base + self._y

    def winfo_parent(self):
        return self._parent_name

    def nametowidget(self, name):  # noqa: ANN001
        return self._parent if name == self._parent_name else self

    def winfo_children(self):
        return list(self.children)

    def winfo_exists(self):
        return True


class _CanvasStub(_FrameStub):
    def __init__(self, *, inner_height, view_height, view=(0.0, 0.2), allow_scroll=True):
        super().__init__(parent=None, height=view_height, name="")
        self._view = view
        self._inner_height = inner_height
        self.allow_scroll = allow_scroll
        self.moveto_calls: list[float] = []

    def yview(self):
        return self._view

    def yview_moveto(self, fraction):  # noqa: ANN001
        self.moveto_calls.append(fraction)
        if self.allow_scroll:
            span = self._height / max(self._inner_height, 1)
            end = min(1.0, fraction + span)
            self._view = (fraction, end)

    def winfo_parent(self):
        return ""

    def nametowidget(self, name):  # noqa: ANN001
        return self


def _build_app_with_root():
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.root = _RootStub()
    return app


def test_scroll_with_canvas_reports_only_successful_scrolls():
    app = _build_app_with_root()
    canvas = _CanvasStub(inner_height=1000, view_height=200)
    inner = _FrameStub(height=1000, name="inner")
    widget_below = _FrameStub(parent=inner, height=50, y=400, name="inner")

    scrolled = app._scroll_with_canvas(canvas, inner, widget_below)

    assert scrolled is True
    assert canvas.moveto_calls, "Debe moverse cuando el widget está fuera de vista"

    widget_visible = _FrameStub(parent=inner, height=30, y=50, name="inner")
    canvas._view = (0.0, 0.2)
    canvas.moveto_calls.clear()

    visible_scroll = app._scroll_with_canvas(canvas, inner, widget_visible)

    assert visible_scroll is False
    assert not canvas.moveto_calls, "No debe desplazarse cuando el widget ya es visible"


def test_walkthrough_fallback_runs_when_canvas_scroll_fails(monkeypatch):
    app = _build_app_with_root()
    inner = _FrameStub(height=1200, name="inner")
    canvas = _CanvasStub(inner_height=1200, view_height=300, allow_scroll=False)
    target = _FrameStub(parent=inner, height=60, y=700, name="inner")

    app._scroll_with_see = types.MethodType(lambda self, widget: False, app)
    app._find_scrollable_canvas = types.MethodType(lambda self, widget: (canvas, inner), app)
    app._get_widget_geometry = types.MethodType(lambda self, widget: (0, 0, 0, 0), app)

    def _center_with_fallback(self, widget):  # noqa: ANN001
        center_target = widget.winfo_y() + (widget.winfo_height() / 2) - (canvas.winfo_height() / 2)
        max_scroll = max(inner.winfo_height() - canvas.winfo_height(), 1)
        fraction = min(max(center_target / max_scroll, 0.0), 1.0)
        canvas.allow_scroll = True
        canvas.yview_moveto(fraction)
        return True

    app._scroll_to_widget = types.MethodType(_center_with_fallback, app)

    app._ensure_walkthrough_anchor_visible(target)

    assert canvas.moveto_calls[-1] > 0.0, "El fallback debe recentrar el widget cuando el canvas no desplaza"
