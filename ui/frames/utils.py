"""Utilidades de soporte para marcos Tkinter en entornos de prueba sin grid."""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk
from typing import Any, Tuple

from theme_manager import ThemeManager
from ui.config import COL_PADX, ROW_PADY

ALERT_BADGE_ICON = "⚠️"
SUCCESS_BADGE_ICON = "✅"

def ensure_grid_support(widget: Any) -> None:
    """Garantiza que el widget exponga un método grid incluso en stubs de prueba.

    Cuando se usan dobles de prueba que solo implementan ``pack`` se expone un
    proxy de ``grid`` que persiste los argumentos recibidos y, si existe un
    método ``grid_configure``, lo invoca de forma segura. De esta manera se
    evita mezclar gestores de geometría en un mismo contenedor (``grid`` vs
    ``pack``), un problema habitual de Tkinter que puede provocar errores en
    tiempo de ejecución.
    """
    if widget is None or hasattr(widget, "grid"):
        return

    def _grid_proxy(self, *args, **kwargs):  # noqa: ANN001
        manager_fn = getattr(self, "winfo_manager", None)
        if callable(manager_fn):
            manager = manager_fn()
            if manager and manager != "grid":
                raise RuntimeError(
                    "El proxy de grid detectó un gestor incompatible: "
                    f"{manager!r}. Evita mezclar 'pack' y 'grid' en el mismo contenedor."
                )

        self._grid_last_args = args
        self._grid_last_kwargs = {k: v for k, v in kwargs.items() if v is not None}

        grid_configure = getattr(self, "grid_configure", None)
        if callable(grid_configure):
            try:
                return grid_configure(*args, **kwargs)
            except Exception:
                return None

        return None

    setattr(widget.__class__, "grid", _grid_proxy)


def build_required_label(
    parent: Any,
    text: str,
    tooltip_register=None,
    tooltip_message: str | None = None,
):
    """Return a label with a red asterisk for required fields.

    The helper keeps layout untouched by returning a compact frame that can be
    used anywhere a label would normally be gridded or packed. It reuses
    ``ThemeManager`` styles so the asterisk and background adapt to the active
    palette without duplicating style definitions.
    """

    try:
        container = ttk.Frame(parent, style="TFrame")
        label = ttk.Label(
            container, text=text, style=ThemeManager.REQUIRED_LABEL_STYLE
        )
        label.pack(side="left", fill="y")
        ttk.Label(
            container,
            text=" *",
            style=ThemeManager.REQUIRED_ASTERISK_STYLE,
        ).pack(side="left", fill="y")
    except Exception:
        class _StubLabel:
            def pack(self, *_args, **_kwargs):  # noqa: D401, ANN001
                """Stub pack method for headless tests."""

        class _StubContainer:
            def __init__(self):
                self._children = []

            def pack(self, *_args, **_kwargs):
                return None

            def winfo_children(self):
                return list(self._children)

        container = _StubContainer()
        ensure_grid_support(container)
        container._children.extend([_StubLabel(), _StubLabel()])

    if callable(tooltip_register):
        tooltip_register(
            container,
            tooltip_message
            or "Campo obligatorio según Design document CM.pdf",
        )

    return container


def create_scrollable_container(parent: Any) -> Tuple[ttk.Frame, ttk.Frame]:
    """Crea un contenedor desplazable con soporte para trackpad y mouse wheel.

    El contenedor externo incluye un ``Canvas`` con su respectiva barra de
    desplazamiento vertical.  Dentro del canvas se ubica un frame interior donde
    se pueden agregar widgets utilizando ``pack`` o ``grid``.  El desplazamiento
    se habilita tanto con la rueda del ratón como con gestos de trackpad para
    mejorar la navegación de formularios largos.
    """

    outer = ttk.Frame(parent)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(0, weight=1)

    canvas = tk.Canvas(outer, highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    inner = ttk.Frame(canvas)
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _configure_canvas(_event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _resize_inner(event):
        canvas.itemconfigure(window_id, width=event.width)

    inner.bind("<Configure>", _configure_canvas)
    canvas.bind("<Configure>", _resize_inner)

    _enable_mousewheel_scrolling(canvas, inner)

    return outer, inner


def _enable_mousewheel_scrolling(canvas: tk.Canvas, target: ttk.Frame) -> None:
    """Permite desplazar el canvas usando la rueda del ratón o trackpad.

    Además de enlazar los eventos con el propio canvas y el frame interno,
    se registran los widgets hijos (como ``ttk.Treeview``) para que el
    desplazamiento funcione sin importar el widget que tenga el foco del ratón.
    """

    is_active = {"value": False}
    bound_widgets: set[int] = set()

    def _activate(_event):
        is_active["value"] = True

    def _deactivate(_event):
        is_active["value"] = False

    def _on_mousewheel(event):  # noqa: ANN001
        if not is_active["value"]:
            return
        delta = event.delta
        if delta == 0 and hasattr(event, "num"):
            delta = 120 if event.num == 4 else -120
        if not delta:
            return
        direction = -1 if delta > 0 else 1
        magnitude = abs(delta)
        steps = direction * max(1, math.ceil(magnitude / 120))
        if steps:
            canvas.yview_scroll(steps, "units")
            return "break"

    def _bind_widget(widget):
        if widget is None:
            return
        widget_id = id(widget)
        if widget_id in bound_widgets:
            return
        bound_widgets.add(widget_id)
        widget.bind("<Enter>", _activate, add="+")
        widget.bind("<Leave>", _deactivate, add="+")
        widget.bind("<MouseWheel>", _on_mousewheel, add="+")
        widget.bind("<Button-4>", _on_mousewheel, add="+")
        widget.bind("<Button-5>", _on_mousewheel, add="+")
        children_fn = getattr(widget, "winfo_children", None)
        if callable(children_fn):
            for child in children_fn():
                _bind_widget(child)

    def _sync_children(_event=None):  # noqa: ANN001
        _bind_widget(target)

    _bind_widget(canvas)
    _bind_widget(target)
    target.bind("<Configure>", _sync_children, add="+")


class BadgeManager:
    """Crea y administra indicadores de validación por campo."""

    def __init__(
        self,
        *,
        parent=None,
        pending_text: str = ALERT_BADGE_ICON,
        success_text: str = SUCCESS_BADGE_ICON,
    ) -> None:
        self.parent = parent
        self.pending_text = pending_text
        self.success_text = success_text
        self._badge_styles: dict[str, str] = {}
        self._registry: dict[str, dict[str, object]] = {}
        self._updaters: dict[str, callable] = {}
        self._configure_badge_styles()

    def _configure_badge_styles(self) -> None:
        style = None
        try:
            style = ThemeManager.build_style(self.parent)
        except Exception:
            if hasattr(ttk, "Style"):
                try:
                    style = ttk.Style(master=self.parent)
                except Exception:
                    style = None
        if not style or not hasattr(style, "configure"):
            self._badge_styles = {"success": "TLabel", "warning": "TLabel"}
            return
        palette = ThemeManager.current()
        success_style = "SuccessBadge.TLabel"
        warning_style = "WarningBadge.TLabel"
        style.configure(
            success_style,
            background=palette.get("accent", "#2e7d32"),
            foreground=palette.get("select_foreground", "#ffffff"),
            padding=(6, 2),
            borderwidth=1,
            relief="solid",
            font=("TkDefaultFont", 9, "bold"),
        )
        style.configure(
            warning_style,
            background="#f0ad4e",
            foreground=palette.get("foreground", "#000000"),
            padding=(6, 2),
            borderwidth=1,
            relief="solid",
            font=("TkDefaultFont", 9, "bold"),
        )
        self._badge_styles = {"success": success_style, "warning": warning_style}

    def create_badge(self, parent, *, row: int, column: int, text: str | None = None):
        styles = self._badge_styles or {"warning": "TLabel"}
        try:
            badge = ttk.Label(
                parent,
                text=text or self.pending_text,
                style=styles.get("warning", "TLabel"),
                anchor="w",
            )
            badge.grid(row=row, column=column, padx=COL_PADX, pady=ROW_PADY, sticky="w")
        except Exception:
            class _StubBadge:
                def __init__(self, initial_text):
                    self._text = initial_text

                def config(self, **kwargs):  # noqa: D401, ANN001
                    """Guarda el texto configurado para pruebas sin Tk."""
                    self._text = kwargs.get("text", self._text)

                def configure(self, **kwargs):  # noqa: D401, ANN001
                    """Alias de config para compatibilidad."""
                    return self.config(**kwargs)

            badge = _StubBadge(text or self.pending_text)
            ensure_grid_support(badge)
            badge.grid(row=row, column=column, padx=COL_PADX, pady=ROW_PADY, sticky="w")
        return badge

    def register_badge(
        self,
        key: str,
        badge,
        *,
        pending_text: str | None = None,
        success_text: str | None = None,
    ) -> None:
        self._registry[key] = {
            "badge": badge,
            "pending": pending_text or self.pending_text,
            "success": success_text or self.success_text,
        }

    def create_and_register(
        self,
        key: str,
        parent,
        *,
        row: int,
        column: int,
        pending_text: str | None = None,
        success_text: str | None = None,
    ):
        badge = self.create_badge(
            parent,
            row=row,
            column=column,
            text=pending_text or self.pending_text,
        )
        self.register_badge(key, badge, pending_text=pending_text, success_text=success_text)
        return badge

    def set_badge_state(
        self,
        badge,
        is_ok: bool,
        message: str | None,
        *,
        success_text: str | None = None,
    ) -> None:
        if badge is None:
            return
        styles = self._badge_styles or {"success": "TLabel", "warning": "TLabel"}
        style_name = styles["success"] if is_ok else styles["warning"]
        text = success_text if is_ok else (message or self.pending_text)
        try:
            badge.configure(text=text, style=style_name)
        except Exception:
            if hasattr(badge, "config"):
                try:
                    badge.config(text=text)
                except Exception:
                    return

    def update_badge(
        self,
        key: str,
        is_ok: bool,
        message: str | None,
        *,
        success_text: str | None = None,
        pending_text: str | None = None,
    ) -> None:
        config = self._registry.get(key)
        if not config:
            return
        success_label = success_text or config.get("success", self.success_text)
        pending_label = pending_text or config.get("pending", self.pending_text)
        badge = config.get("badge")
        self.set_badge_state(badge, is_ok, message or pending_label, success_text=success_label)

    def wrap_validation(
        self,
        key: str,
        validate_fn,
        *,
        success_text: str | None = None,
        pending_text: str | None = None,
    ):
        def _wrapped():
            message = validate_fn()
            self.update_badge(
                key,
                message is None,
                message,
                success_text=success_text,
                pending_text=pending_text,
            )
            return message

        self._updaters[key] = _wrapped
        return _wrapped

    def refresh(self) -> None:
        for updater in self._updaters.values():
            updater()
