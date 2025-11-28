"""Utilidades de soporte para marcos Tkinter en entornos de prueba sin grid."""
from __future__ import annotations

import math
import sys
import tkinter as tk
from tkinter import ttk
from typing import Any, Iterable, Tuple

from theme_manager import ThemeManager
from ui.config import COL_PADX, ROW_PADY
from ui.layout import CollapsibleSection, register_styles

ALERT_BADGE_ICON = "⚠️"
SUCCESS_BADGE_ICON = "✅"


def _build_collapsible_fallback(parent: Any, *, title: str, open: bool, on_toggle=None):
    """Create a minimal accordion-like container without ``CollapsibleSection``.

    The fallback mirrors the public surface used by the frames: ``content``
    frame, ``pack_content`` helper, ``toggle`` method, ``is_open`` flag and
    ``set_title`` to refresh the header text. It reuses the accordion styles
    when available so visual parity is preserved even in degraded contexts
    (headless tests or missing themed elements).
    """

    try:
        register_styles()
    except Exception:
        # En pruebas sin Tk no es crítico registrar estilos; continuar.
        pass

    header = None
    indicator = None
    title_lbl = None
    content = None
    try:
        card = ttk.Frame(parent, style="AccordionCard.TFrame")
        ensure_grid_support(card)

        header = ttk.Frame(card, style="AccordionHeader.TFrame")
        header.pack(fill="x")

        indicator = ttk.Label(
            header,
            text="▼" if open else "▸",
            style="AccordionIndicator.TLabel",
        )
        indicator.pack(side="left", padx=(6, 4))

        title_lbl = ttk.Label(
            header, text=title, style="AccordionTitle.TLabel", anchor="w"
        )
        title_lbl.pack(side="left", fill="x", expand=True, padx=(0, 6))

        content = ttk.Frame(card, style="AccordionContent.TFrame")
        ensure_grid_support(content)
        card.content = content  # type: ignore[assignment]
        if open:
            content.pack(fill="both", expand=True)

    except Exception:
        class _StubContent:
            def __init__(self):
                self.children = []

            def pack(self, *_args, **_kwargs):
                return None

            def pack_forget(self):
                return None

        class _StubCard:
            def __init__(self):
                self.content = _StubContent()
                ensure_grid_support(self)

            def pack(self, *_args, **_kwargs):
                return None

            def pack_forget(self):
                return None

        card = _StubCard()
        content = card.content

    card.is_open = bool(open)  # type: ignore[attr-defined]
    card._on_toggle = on_toggle  # type: ignore[attr-defined]

    def _set_title(new_title: str):
        try:
            if title_lbl is not None:
                title_lbl.configure(text=new_title)
            else:
                card.title = new_title  # type: ignore[attr-defined]
        except Exception:
            card.title = new_title  # type: ignore[attr-defined]

    def _pack_content(widget: Any, **pack_kwargs):
        defaults = {"fill": "both", "expand": True}
        defaults.update(pack_kwargs)
        try:
            widget.pack(**defaults)
        except Exception:
            pass
        card.is_open = True  # type: ignore[attr-defined]
        return widget

    def _toggle(_event=None):  # noqa: ANN001
        is_open = getattr(card, "is_open", True)
        if is_open:
            if hasattr(content, "pack_forget"):
                content.pack_forget()
            try:
                if indicator is not None:
                    indicator.configure(text="▸")
            except Exception:
                pass
        else:
            if hasattr(content, "pack"):
                content.pack(fill="both", expand=True)
            try:
                if indicator is not None:
                    indicator.configure(text="▼")
            except Exception:
                pass
        card.is_open = not is_open  # type: ignore[attr-defined]
        callback = getattr(card, "_on_toggle", None)
        if callable(callback):
            try:
                callback(card)
            except Exception:
                pass

    for widget in (header, title_lbl, indicator):
        if widget is not None:
            widget.bind("<Button-1>", _toggle)

    card.pack_content = _pack_content  # type: ignore[attr-defined]
    card.toggle = _toggle  # type: ignore[attr-defined]
    card.set_title = _set_title  # type: ignore[attr-defined]
    return card


def create_collapsible_card(
    parent: Any,
    *,
    title: str,
    open: bool = True,
    on_toggle=None,
    log_error=None,
    collapsible_cls=None,
):
    """Create a themed collapsible card with graceful fallback.

    When ``CollapsibleSection`` cannot be instantiated (for example in headless
    environments), this helper returns a minimal stand-in preserving the same
    public API used throughout the frames. An optional ``log_error`` callback
    receives the raised exception so callers can trace UI degradation.
    """

    collapsible = collapsible_cls or CollapsibleSection
    try:
        return collapsible(parent, title=title, open=open, on_toggle=on_toggle)
    except Exception as exc:  # pragma: no cover - solo se ejecuta en entornos degradados
        if callable(log_error):
            try:
                log_error(exc)
            except Exception:
                pass
        return _build_collapsible_fallback(
            parent, title=title, open=open, on_toggle=on_toggle
        )

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


def create_scrollable_container(
    parent: Any, *, scroll_binder: "GlobalScrollBinding | None" = None, tab_id=None
) -> Tuple[ttk.Frame, ttk.Frame]:
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

    outer._scroll_canvas = canvas  # type: ignore[attr-defined]
    outer._scroll_inner = inner  # type: ignore[attr-defined]

    if scroll_binder is not None:
        scroll_binder.register_tab_canvas(tab_id or parent, canvas, inner)
    else:
        _enable_mousewheel_scrolling(canvas, inner)

    return outer, inner


def resize_scrollable_to_content(container: Any, *, max_height: int | None = None) -> None:
    """Expande el alto del canvas para evitar desplazamiento innecesario."""

    if container is None:
        return

    canvas = getattr(container, "_scroll_canvas", None)
    inner = getattr(container, "_scroll_inner", None)
    if canvas is None or inner is None:
        return

    try:
        container.update_idletasks()
    except Exception:
        pass

    try:
        required_height = inner.winfo_reqheight()
        available_height = max_height if max_height is not None else container.winfo_height()
        if not available_height:
            parent = getattr(container, "master", None)
            try:
                available_height = parent.winfo_height() if parent else 0
            except Exception:
                available_height = 0
        target_height = required_height if not available_height else min(required_height, available_height)
        canvas.configure(height=target_height)
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.yview_moveto(0)
    except Exception:
        return


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
        steps = _normalize_mousewheel_delta(event)
        if not steps:
            return
        if _scroll_lineage(getattr(event, "widget", None), canvas, steps):
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


def _normalize_mousewheel_delta(event) -> int:  # noqa: ANN001
    delta = getattr(event, "delta", 0) or 0
    if delta == 0 and hasattr(event, "num"):
        num = getattr(event, "num", None)
        if num == 4:
            delta = 120
        elif num == 5:
            delta = -120
    if delta == 0:
        return 0
    magnitude = max(abs(delta), 120)
    steps = max(1, math.ceil(magnitude / 120))
    return -steps if delta > 0 else steps


def _iter_ancestors(widget: Any) -> Iterable[Any]:
    current = widget
    while current is not None:
        yield current
        parent_name = None
        try:
            parent_name = current.winfo_parent()
        except Exception:
            current = None
            continue
        if not parent_name:
            current = None
            continue
        try:
            current = current.nametowidget(parent_name)
        except Exception:
            current = None


def _can_scroll_widget(widget: Any, steps: int) -> bool:
    try:
        first, last = widget.yview()
    except Exception:
        return True
    if steps < 0:
        return first > 0.0
    return last < 1.0


def _scroll_lineage(widget: Any, fallback_canvas: Any, steps: int) -> bool:
    for ancestor in _iter_ancestors(widget):
        if hasattr(ancestor, "yview"):
            if _can_scroll_widget(ancestor, steps):
                try:
                    ancestor.yview_scroll(steps, "units")
                    return True
                except Exception:
                    continue
    if fallback_canvas is not None and hasattr(fallback_canvas, "yview_scroll"):
        try:
            fallback_canvas.yview_scroll(steps, "units")
            return True
        except Exception:
            return False
    return False


class GlobalScrollBinding:
    """Gestiona el enlace global de la rueda del ratón por pestaña.

    Para nuevas pestañas, registra el contenedor desplazable principal con
    ``register_tab_canvas`` y actualiza la pestaña activa desde el manejador
    ``<<NotebookTabChanged>>``. Esto evita duplicar enlaces por cada sección y
    garantiza que el desplazamiento funcione sobre cualquier hijo (botones,
    entradas, tablas) y que, al llegar al final de un scrollbar interno, la
    rueda continúe con el canvas principal de la pestaña.
    """

    def __init__(self, root: tk.Misc):
        self.root = root
        self._tab_canvases: dict[str, tk.Canvas] = {}
        self._hover_tab: str | None = None
        self._active_tab: str | None = None
        self._bound_targets: set[int] = set()
        self._is_bound = False

    def bind_to_root(self) -> None:
        if self._is_bound:
            return
        sequences = ["<MouseWheel>"]
        if sys.platform.startswith("linux"):
            sequences.extend(["<Button-4>", "<Button-5>"])
        for sequence in sequences:
            self.root.bind_all(sequence, self._handle_mousewheel, add="+")
        self._is_bound = True

    def register_tab_canvas(self, tab_id, canvas: tk.Canvas, target: ttk.Frame) -> None:
        normalized = self._normalize_tab_id(tab_id)
        if normalized is None:
            return
        self._tab_canvases[normalized] = canvas
        self._bind_hover_targets(canvas, normalized)
        self._bind_hover_targets(target, normalized)

    def activate_tab(self, tab_id) -> None:
        normalized = self._normalize_tab_id(tab_id)
        self._active_tab = normalized

    def _normalize_tab_id(self, tab_id) -> str | None:
        if tab_id is None:
            return None
        try:
            return str(tab_id)
        except Exception:
            return None

    def _bind_hover_targets(self, widget: Any, tab_id: str) -> None:
        if widget is None:
            return
        widget_id = id(widget)
        already_bound = widget_id in self._bound_targets
        if not already_bound:
            self._bound_targets.add(widget_id)
            widget.bind(
                "<Enter>", lambda _e, tid=tab_id: self._set_hover_tab(tid), add="+"
            )
            widget.bind(
                "<Leave>", lambda _e, tid=tab_id: self._clear_hover_tab(tid), add="+"
            )
        children_fn = getattr(widget, "winfo_children", None)
        if callable(children_fn):
            for child in children_fn():
                self._bind_hover_targets(child, tab_id)
        if not already_bound:
            widget.bind(
                "<Configure>",
                lambda _e, source=widget, tid=tab_id: self._bind_hover_targets(source, tid),
                add="+",
            )

    def _set_hover_tab(self, tab_id: str) -> None:
        self._hover_tab = tab_id

    def _clear_hover_tab(self, tab_id: str) -> None:
        if self._hover_tab == tab_id:
            self._hover_tab = None

    def _select_canvas(self) -> tk.Canvas | None:
        for candidate in (self._hover_tab, self._active_tab):
            if candidate and candidate in self._tab_canvases:
                canvas = self._tab_canvases[candidate]
                try:
                    exists = canvas.winfo_exists()
                except Exception:
                    return canvas
                if exists:
                    return canvas
        return None

    def _handle_mousewheel(self, event):  # noqa: ANN001
        steps = _normalize_mousewheel_delta(event)
        if not steps:
            return
        canvas = self._select_canvas()
        if canvas is None:
            return
        if _scroll_lineage(getattr(event, "widget", None), canvas, steps):
            return "break"


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
        text = success_text if is_ok else self.pending_text
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
