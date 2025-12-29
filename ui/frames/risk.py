"""Componentes para la captura de riesgos."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from settings import CRITICIDAD_LIST
from validators import (
    FieldValidator,
    log_event,
    should_autofill_field,
    validate_money_bounds,
    validate_required_text,
    validate_catalog_risk_id,
    validate_risk_id,
)
from ui.frames.utils import (
    build_two_column_form,
    compute_badge_minsize,
    create_collapsible_card,
    ensure_grid_support,
    grid_labeled_widget,
    grid_section,
)
from ui.config import COL_PADX, ROW_PADY
from ui.layout import CollapsibleSection
from validation_badge import badge_registry


def _normalize_token(value: str | None) -> str:
    return (value or "").strip().lower()


def _extract_categories(source: dict) -> set[str]:
    categories: set[str] = set()
    for key in ("categoria1", "categoria2", "categorias", "categoria"):
        raw_value = source.get(key)
        if raw_value is None:
            continue
        if isinstance(raw_value, (list, tuple, set)):
            values = raw_value
        else:
            values = str(raw_value).replace("/", ",").split(",")
        for chunk in values:
            token = _normalize_token(chunk)
            if token:
                categories.add(token)
    return categories


def build_risk_suggestions(risk_lookup, *, context=None, excluded_ids=None):
    """Ordena los riesgos del catálogo según el contexto del caso."""

    context = context or {}
    excluded = {_normalize_token(rid) for rid in (excluded_ids or set()) if rid}
    normalized_context = {k: _normalize_token(v) for k, v in (context or {}).items()}
    context_categories = _extract_categories(normalized_context)
    suggestions = []

    for risk_id, payload in (risk_lookup or {}).items():
        if not risk_id:
            continue
        normalized_id = _normalize_token(risk_id)
        if normalized_id in excluded:
            continue

        data = payload or {}
        normalized_payload = {k: _normalize_token(v) for k, v in data.items() if k}
        score = 0

        for key in ("id_proceso", "proceso", "canal", "modalidad"):
            ctx = normalized_context.get(key)
            if not ctx:
                continue
            value = normalized_payload.get(key)
            if not value:
                continue
            if ctx == value:
                score += 3
            elif ctx in value:
                score += 1

        record_categories = _extract_categories(normalized_payload)
        if context_categories:
            shared = context_categories & record_categories
            if shared:
                score += 2 * len(shared)

        descripcion = normalized_payload.get("descripcion", "")
        for token in (
            normalized_context.get("proceso"),
            normalized_context.get("canal"),
            normalized_context.get("modalidad"),
        ):
            if token and token in descripcion:
                score += 1

        suggestions.append({"id_riesgo": risk_id, "data": data, "_score": score})

    suggestions.sort(key=lambda item: (-item["_score"], item["id_riesgo"]))
    return suggestions


class RiskCatalogModal:
    """Modal sencillo para seleccionar riesgos del catálogo."""

    COLUMNS = (
        ("id_riesgo", "ID"),
        ("descripcion", "Descripción"),
        ("criticidad", "Criticidad"),
        ("lider", "Líder"),
        ("exposicion_residual", "Exposición"),
    )

    def __init__(self, parent, suggestions, *, on_select, trigger=""):
        self.parent = parent
        self.on_select = on_select
        self.suggestions = list(suggestions or [])
        self.trigger = trigger
        self.search_var = tk.StringVar()

        self.window = tk.Toplevel(parent)
        try:
            self.window.transient(parent)
            self.window.grab_set()
        except Exception:
            pass
        try:
            self.window.title("Sugerencias de riesgos")
        except Exception:
            pass
        container = ttk.Frame(self.window)
        container.pack(fill="both", expand=True, padx=COL_PADX, pady=ROW_PADY)

        search_row = ttk.Frame(container)
        search_row.pack(fill="x", expand=False, pady=(0, ROW_PADY))
        search_label = ttk.Label(search_row, text="Filtrar:")
        search_label.pack(side="left")
        search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=40)
        search_entry.pack(side="left", padx=(COL_PADX // 2, 0), fill="x", expand=True)
        try:
            search_entry.focus_set()
        except Exception:
            pass
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_rows())

        self.tree = ttk.Treeview(
            container,
            columns=[c[0] for c in self.COLUMNS],
            show="headings",
            height=8,
        )
        for col_id, label in self.COLUMNS:
            self.tree.heading(col_id, text=label)
            self.tree.column(col_id, anchor="w", stretch=True)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _e: self._commit_selection())

        buttons = ttk.Frame(container)
        buttons.pack(fill="x", expand=False, pady=(ROW_PADY // 2, 0))
        select_btn = ttk.Button(buttons, text="Usar riesgo", command=self._commit_selection)
        select_btn.pack(side="right")
        close_btn = ttk.Button(buttons, text="Cerrar", command=self.window.destroy)
        close_btn.pack(side="right", padx=(0, COL_PADX // 2))

        self._refresh_rows()

    def _filtered(self):
        needle = _normalize_token(self.search_var.get())
        if not needle:
            return self.suggestions
        filtered = []
        for suggestion in self.suggestions:
            data = suggestion.get("data", {})
            haystack = " ".join(
                _normalize_token(value)
                for value in (
                    suggestion.get("id_riesgo"),
                    data.get("descripcion", ""),
                    data.get("lider", ""),
                    data.get("criticidad", ""),
                )
            )
            if needle in haystack:
                filtered.append(suggestion)
        return filtered

    def _refresh_rows(self):
        try:
            self.tree.delete(*self.tree.get_children(""))
        except Exception:
            return
        for idx, suggestion in enumerate(self._filtered()):
            data = suggestion.get("data", {})
            values = [
                suggestion.get("id_riesgo", ""),
                data.get("descripcion", ""),
                data.get("criticidad", ""),
                data.get("lider", ""),
                data.get("exposicion_residual", ""),
            ]
            tags = ("even" if idx % 2 == 0 else "odd",)
            try:
                self.tree.insert("", "end", values=values, tags=tags)
            except Exception:
                continue

    def _commit_selection(self):
        selection = None
        try:
            selected_item = self.tree.selection()
            if selected_item:
                values = self.tree.item(selected_item[0], "values")
                selection = values[0] if values else None
        except Exception:
            selection = None
        try:
            self.window.destroy()
        except Exception:
            pass
        if callable(self.on_select):
            self.on_select(selection)

class RiskFrame:
    """Representa un riesgo identificado en la sección de riesgos."""

    HEADER_COLUMNS = (
        ("id_riesgo", "ID"),
        ("criticidad", "Criticidad"),
        ("exposicion_residual", "Exposición"),
        ("lider", "Líder"),
        ("descripcion", "Descripción"),
    )

    def __init__(
        self,
        parent,
        idx,
        remove_callback,
        logs,
        tooltip_register,
        change_notifier=None,
        default_risk_id: str | None = None,
        header_tree=None,
        context_provider=None,
        existing_ids_provider=None,
        modal_factory=None,
    ):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self._catalog_validators_suspended = False
        self._validation_state_initialized = False
        self._refresh_after_id = None
        self._summary_refresher = None
        self._shared_tree_refresher = None
        self._last_exposicion_decimal = None
        self.risk_lookup = {}
        self._last_missing_lookup_id = None
        self.change_notifier = change_notifier
        self.header_tree = None
        self.context_provider = context_provider
        self.existing_ids_provider = existing_ids_provider
        self.modal_factory = modal_factory

        self.id_var = tk.StringVar()
        self.case_id_var = tk.StringVar()
        self.new_risk_var = tk.BooleanVar(value=False)
        self._auto_id_value = ""
        self._id_user_modified = False
        self._suppress_id_trace = False
        self.id_var.trace_add("write", self._on_id_var_change)
        if default_risk_id:
            self.assign_new_auto_id(default_risk_id)
        self.lider_var = tk.StringVar()
        self.descripcion_var = tk.StringVar()
        self.criticidad_var = tk.StringVar()
        self.exposicion_var = tk.StringVar()
        self.planes_var = tk.StringVar()
        self._register_refresh_traces()

        self.section = create_collapsible_card(
            parent,
            title="",
            on_toggle=lambda _section: self._sync_section_title(),
            log_error=lambda exc: log_event(
                "validacion",
                f"No se pudo crear acordeón para riesgo {idx+1}: {exc}",
                self.logs,
            ),
            collapsible_cls=CollapsibleSection,
            open=False,
        )
        self._sync_section_title()
        self._place_section()

        content_frame = ttk.Frame(self.section.content)
        self.section.pack_content(content_frame, fill="x", expand=True)
        ensure_grid_support(content_frame)
        if hasattr(content_frame, "columnconfigure"):
            try:
                content_frame.columnconfigure(0, weight=1)
            except Exception:
                pass

        self.frame = build_two_column_form(
            content_frame,
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
        )
        self.badges = badge_registry

        action_row = ttk.Frame(self.frame)
        ensure_grid_support(action_row)
        if hasattr(action_row, "columnconfigure"):
            action_row.columnconfigure(0, weight=1)
            action_row.columnconfigure(1, weight=0)
        remove_btn = ttk.Button(action_row, text="Eliminar riesgo", command=self.remove)
        remove_btn.grid(row=0, column=1, sticky="e")
        self.tooltip_register(remove_btn, "Quita este riesgo del caso.")
        grid_labeled_widget(
            self.frame,
            row=0,
            label_widget=ttk.Frame(self.frame),
            field_widget=action_row,
            label_sticky="nsew",
        )

        risk_id_label = ttk.Label(self.frame, text="ID riesgo (catálogo o nuevo):")
        id_row = ttk.Frame(self.frame)
        ensure_grid_support(id_row)
        if hasattr(id_row, "columnconfigure"):
            id_row.columnconfigure(0, weight=1)
        id_container, id_entry = self._make_badged_field(
            id_row,
            "riesgo_id",
            lambda parent: ttk.Entry(parent, textvariable=self.id_var, width=15),
            row=0,
            column=0,
            autogrid=False,
        )
        id_container.grid(row=0, column=0, padx=(0, COL_PADX // 2), pady=0, sticky="we")
        toggle_btn = ttk.Checkbutton(
            id_row,
            text="Agregar riesgo nuevo",
            variable=self.new_risk_var,
            command=self._on_mode_toggle,
        )
        toggle_btn.grid(row=0, column=1, padx=(COL_PADX // 2, 0), sticky="w")
        self.tooltip_register(
            id_entry,
            (
                "Selecciona un riesgo catalogado para autopoblar campos o marca "
                "'Agregar riesgo nuevo' para capturar un ID libre sin buscar en el catálogo."
            ),
        )
        self.tooltip_register(
            toggle_btn,
            "Activa para registrar un riesgo nuevo sin búsqueda de catálogo; desactiva para usar el catálogo.",
        )
        self._bind_identifier_triggers(id_entry)
        grid_labeled_widget(
            self.frame,
            row=1,
            label_widget=risk_id_label,
            field_widget=id_row,
        )

        crit_label = ttk.Label(self.frame, text="Criticidad:")
        crit_container, crit_cb = self._make_badged_field(
            self.frame,
            "riesgo_criticidad",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.criticidad_var,
                values=CRITICIDAD_LIST,
                state="readonly",
                width=12,
            ),
            row=2,
            column=1,
            autogrid=False,
        )
        crit_cb.set('')
        self.tooltip_register(crit_cb, "Nivel de severidad del riesgo.")
        grid_labeled_widget(
            self.frame,
            row=2,
            label_widget=crit_label,
            field_widget=crit_container,
        )

        lider_label = ttk.Label(self.frame, text="Líder:")
        lider_container, lider_entry = self._make_badged_field(
            self.frame,
            "riesgo_lider",
            lambda parent: ttk.Entry(parent, textvariable=self.lider_var, width=20),
            row=3,
            column=1,
            autogrid=False,
        )
        self.tooltip_register(lider_entry, "Responsable del seguimiento del riesgo.")
        grid_labeled_widget(
            self.frame,
            row=3,
            label_widget=lider_label,
            field_widget=lider_container,
        )

        expos_label = ttk.Label(self.frame, text="Exposición residual (US$):")
        expos_container, expos_entry = self._make_badged_field(
            self.frame,
            "riesgo_exposicion",
            lambda parent: ttk.Entry(parent, textvariable=self.exposicion_var, width=15),
            row=4,
            column=1,
            autogrid=False,
        )
        self.tooltip_register(expos_entry, "Monto estimado en dólares.")
        grid_labeled_widget(
            self.frame,
            row=4,
            label_widget=expos_label,
            field_widget=expos_container,
        )

        desc_label = ttk.Label(self.frame, text="Descripción del riesgo:")
        desc_container, desc_entry = self._make_badged_field(
            self.frame,
            "riesgo_desc",
            lambda parent: ttk.Entry(parent, textvariable=self.descripcion_var, width=60),
            row=5,
            column=1,
            autogrid=False,
        )
        self.tooltip_register(desc_entry, "Describe el riesgo de forma clara.")
        grid_labeled_widget(
            self.frame,
            row=5,
            label_widget=desc_label,
            field_widget=desc_container,
        )

        planes_label = ttk.Label(self.frame, text="Planes de acción (IDs separados por ;):")
        planes_container, planes_entry = self._make_badged_field(
            self.frame,
            "riesgo_planes",
            lambda parent: ttk.Entry(parent, textvariable=self.planes_var, width=40),
            row=6,
            column=1,
            autogrid=False,
        )
        self.tooltip_register(planes_entry, "Lista de planes registrados en OTRS o Aranda.")
        grid_labeled_widget(
            self.frame,
            row=6,
            label_widget=planes_label,
            field_widget=planes_container,
        )

        self.id_validator = FieldValidator(
            id_entry,
            self.badges.wrap_validation("riesgo_id", self._validate_risk_id),
            self.logs,
            f"Riesgo {self.idx+1} - ID",
            variables=[self.id_var],
        )
        self.validators.append(self.id_validator)

        self.lider_validator = FieldValidator(
            lider_entry,
            self.badges.wrap_validation(
                "riesgo_lider",
                lambda: self._validate_when_catalog(
                    lambda: validate_required_text(
                        self.lider_var.get(), "el líder del riesgo"
                    )
                ),
            ),
            self.logs,
            f"Riesgo {self.idx+1} - Líder",
            variables=[self.lider_var],
        )
        self.validators.append(self.lider_validator)

        def _validate_exposure_amount():
            message, _normalized_text = self._normalize_exposure_amount()
            return message

        self.expos_validator = FieldValidator(
            expos_entry,
            self.badges.wrap_validation(
                "riesgo_exposicion",
                lambda: self._validate_when_catalog(_validate_exposure_amount),
            ),
            self.logs,
            f"Riesgo {self.idx+1} - Exposición",
            variables=[self.exposicion_var],
        )
        self.validators.append(self.expos_validator)

        self.criticidad_validator = FieldValidator(
            crit_cb,
            self.badges.wrap_validation(
                "riesgo_criticidad",
                lambda: self._validate_when_catalog(self._validate_criticidad),
            ),
            self.logs,
            f"Riesgo {self.idx+1} - Criticidad",
            variables=[self.criticidad_var],
        )
        self.validators.append(self.criticidad_validator)

        self.desc_validator = FieldValidator(
            desc_entry,
            self.badges.wrap_validation(
                "riesgo_desc",
                lambda: validate_required_text(
                    self.descripcion_var.get(), "la descripción del riesgo"
                ),
            ),
            self.logs,
            f"Riesgo {self.idx+1} - Descripción",
            variables=[self.descripcion_var],
        )
        self.validators.append(self.desc_validator)

        self.planes_validator = FieldValidator(
            planes_entry,
            self.badges.wrap_validation(
                "riesgo_planes",
                lambda: self._validate_when_catalog(
                    lambda: validate_required_text(
                        self.planes_var.get(), "los planes de acción"
                    )
                ),
            ),
            self.logs,
            f"Riesgo {self.idx+1} - Planes",
            variables=[self.planes_var],
        )
        self.validators.append(self.planes_validator)

        self.attach_header_tree(header_tree)
        self._register_header_tree_focus(
            id_entry,
            lider_entry,
            crit_cb,
            desc_entry,
            expos_entry,
            planes_entry,
        )

        self._register_title_traces()
        self.new_risk_var.trace_add("write", self.update_risk_validation_state)
        self.update_risk_validation_state()
        self._sync_section_title()

    def _place_section(self):
        grid_section(
            self.section,
            self.parent,
            row=self.idx,
            padx=COL_PADX,
            pady=(ROW_PADY // 2, ROW_PADY),
        )
        if hasattr(self.parent, "columnconfigure"):
            try:
                self.parent.columnconfigure(0, weight=1)
            except Exception:
                pass

    def update_position(self, new_index: int | None = None):
        if new_index is not None:
            self.idx = new_index
        try:
            self.section.grid_configure(
                row=self.idx, padx=COL_PADX, pady=(ROW_PADY // 2, ROW_PADY), sticky="nsew"
            )
        except Exception:
            self._place_section()

    def refresh_indexed_state(self):
        self._sync_section_title()
        if getattr(self, "frame", None):
            try:
                self.frame.config(text=f"Riesgo {self.idx+1}")
            except Exception:
                pass

    @staticmethod
    def build_header_tree(parent, xscrollcommand=None):
        header_tree = ttk.Treeview(
            parent,
            columns=[c[0] for c in RiskFrame.HEADER_COLUMNS],
            show="headings",
            height=4,
        )

        column_widths = {
            "id_riesgo": 180,
            "criticidad": 140,
            "exposicion_residual": 160,
            "lider": 180,
            "descripcion": 360,
        }

        for col_id, text in RiskFrame.HEADER_COLUMNS:
            header_tree.heading(col_id, text=text)
            header_tree.column(
                col_id,
                anchor="w",
                width=column_widths.get(col_id, 140),
                minwidth=column_widths.get(col_id, 140),
                stretch=True,
            )

        if xscrollcommand:
            header_tree.configure(xscrollcommand=xscrollcommand)

        header_tree.tag_configure("even", background="#f7f7f7")
        header_tree.tag_configure("odd", background="#ffffff")
        header_tree._tree_sort_state = {}
        return header_tree

    def attach_header_tree(self, header_tree):
        self.header_tree = header_tree
        if not self.header_tree:
            return
        tree_sort_state = getattr(self.header_tree, "_tree_sort_state", {})
        setattr(self.header_tree, "_tree_sort_state", tree_sort_state)
        self._tree_sort_state = tree_sort_state
        for col_id, text in self.HEADER_COLUMNS:
            self.header_tree.heading(
                col_id, text=text, command=lambda _c=col_id: self._sort_treeview(_c)
            )
        self.header_tree.bind("<<TreeviewSelect>>", self._on_tree_select, add=False)
        self.header_tree.bind("<Double-1>", self._on_tree_double_click, add=False)

    def _make_badged_field(
        self,
        parent,
        key: str,
        widget_factory,
        *,
        row: int,
        column: int,
        columnspan: int = 1,
        sticky: str = "we",
        autogrid: bool = True,
    ):
        container = ttk.Frame(parent)
        ensure_grid_support(container)
        if hasattr(container, "columnconfigure"):
            badge_minsize = compute_badge_minsize()
            container.columnconfigure(0, weight=1)
            container.columnconfigure(1, weight=0, minsize=badge_minsize)

        widget = widget_factory(container)
        widget.grid(row=0, column=0, padx=(0, COL_PADX // 2), pady=ROW_PADY, sticky="we")
        self.badges.claim(key, container, row=0, column=1)
        if autogrid:
            container.grid(
                row=row,
                column=column,
                columnspan=columnspan,
                padx=COL_PADX,
                pady=ROW_PADY,
                sticky=sticky,
            )
        return container, widget

    def _register_title_traces(self):
        for var in (self.id_var, self.descripcion_var):
            trace_add = getattr(var, "trace_add", None)
            if callable(trace_add):
                trace_add("write", self._sync_section_title)

    def _build_section_title(self) -> str:
        base_title = f"Riesgo {self.idx+1}"
        if getattr(self, "section", None) and not self.section.is_open:
            rid = self.id_var.get().strip()
            desc = self.descripcion_var.get().strip()
            details = [value for value in (rid, desc) if value]
            if details:
                base_title = f"{base_title} – {' | '.join(details)}"
        return base_title

    def _sync_section_title(self, *_args):
        if not getattr(self, "section", None):
            return
        set_title = getattr(self.section, "set_title", None)
        if callable(set_title):
            self.section.set_title(self._build_section_title())

    def get_data(self):
        _, normalized_text = self._normalize_exposure_amount()
        exposure_value = (
            normalized_text
            if normalized_text and normalized_text.strip()
            else self.exposicion_var.get().strip()
        )
        return {
            "id_riesgo": self.id_var.get().strip(),
            "id_caso": self.case_id_var.get().strip(),
            "lider": self.lider_var.get().strip(),
            "descripcion": self.descripcion_var.get().strip(),
            "criticidad": self.criticidad_var.get(),
            "exposicion_residual": exposure_value,
            "planes_accion": self.planes_var.get().strip(),
        }

    def set_lookup(self, lookup):
        self.risk_lookup = lookup or {}
        self._last_missing_lookup_id = None
        self.on_id_change(preserve_existing=True, silent=True)

    def on_id_change(
        self, from_focus=False, preserve_existing=False, silent=False, explicit_lookup=False
    ):
        rid = self.id_var.get().strip()
        if not rid:
            self._last_missing_lookup_id = None
            self._schedule_refresh()
            return
        if not self.is_catalog_mode():
            self._last_missing_lookup_id = None
            self._schedule_refresh()
            return
        data = self.risk_lookup.get(rid)
        if not data:
            if (
                explicit_lookup
                and from_focus
                and not silent
                and self.risk_lookup
                and self._last_missing_lookup_id != rid
            ):
                messagebox.showerror(
                    "Riesgo no encontrado",
                    (
                        f"El ID {rid} no existe en los catálogos de detalle. "
                        "Verifica el código o actualiza risk_details.csv."
                    ),
                )
                self._last_missing_lookup_id = rid
            else:
                self._last_missing_lookup_id = None
            self._schedule_refresh()
            return

        def set_if_present(var, key):
            value = data.get(key)
            if value in (None, ""):
                return
            text_value = str(value).strip()
            if text_value and should_autofill_field(var.get(), preserve_existing):
                var.set(text_value)

        set_if_present(self.lider_var, "lider")
        set_if_present(self.descripcion_var, "descripcion")
        set_if_present(self.criticidad_var, "criticidad")
        set_if_present(self.exposicion_var, "exposicion_residual")
        set_if_present(self.planes_var, "planes_accion")
        self._last_missing_lookup_id = None
        if not silent:
            self._log_change(f"Riesgo {self.idx+1}: autopoblado desde catálogo")
        self._schedule_refresh()

    def _sort_treeview(self, column):
        if not self.header_tree:
            return
        reverse = self._tree_sort_state.get(column, False) if hasattr(self, "_tree_sort_state") else False
        items = list(self.header_tree.get_children(""))
        column_index = self.header_tree["columns"].index(column)
        items.sort(key=lambda item: self.header_tree.item(item, "values")[column_index], reverse=reverse)
        for new_index, item in enumerate(items):
            self.header_tree.move(item, "", new_index)
            tag = "even" if new_index % 2 == 0 else "odd"
            self.header_tree.item(item, tags=(tag,))
        self._tree_sort_state[column] = not reverse

    def _on_tree_select(self, _event=None):
        item = self._first_selected_item()
        if not item:
            return
        values = self.header_tree.item(item, "values")
        if not values:
            return
        self.id_var.set(values[0])
        self._set_catalog_mode(True)
        self.on_id_change(preserve_existing=True, silent=True)

    def _on_tree_double_click(self, _event=None):
        item = self._first_selected_item()
        if not item:
            return
        values = self.header_tree.item(item, "values")
        if not values:
            return
        self.id_var.set(values[0])
        self._set_catalog_mode(True)
        self.on_id_change(from_focus=True, explicit_lookup=True)

    def _first_selected_item(self):
        selection = self.header_tree.selection() if self.header_tree else []
        return selection[0] if selection else None

    def _normalize_exposure_amount(self):
        message, decimal_value, normalized_text = validate_money_bounds(
            self.exposicion_var.get(),
            "la exposición residual",
            allow_blank=True,
        )
        current_value = (self.exposicion_var.get() or "").strip()
        if not message and normalized_text and normalized_text != current_value:
            self.exposicion_var.set(normalized_text)
        self._last_exposicion_decimal = decimal_value
        return message, normalized_text

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el riesgo {self.idx+1}?"):
            self._log_change(f"Se eliminó riesgo {self.idx+1}")
            self.section.destroy()
            self.remove_callback(self)

    def _validate_when_catalog(self, validator):
        if self.is_catalog_mode():
            return validator()
        return None

    def _validate_risk_id(self):
        if self.is_catalog_mode():
            return self._validate_catalog_risk_id()
        return self._validate_new_risk_id()

    def _validate_catalog_risk_id(self):
        return validate_catalog_risk_id(self.id_var.get())

    def _validate_new_risk_id(self):
        return validate_risk_id(self.id_var.get())

    def update_risk_validation_state(self, *_args):
        is_new_mode = bool(self.new_risk_var.get())
        initializing = self._validation_state_initialized is False
        self._validation_state_initialized = True

        toggled_validators = [
            (self.lider_validator, "riesgo_lider"),
            (self.expos_validator, "riesgo_exposicion"),
            (self.criticidad_validator, "riesgo_criticidad"),
            (self.planes_validator, "riesgo_planes"),
        ]

        if is_new_mode:
            if not self._catalog_validators_suspended:
                for validator, _ in toggled_validators:
                    validator.suspend()
                self._catalog_validators_suspended = True
            for _, badge_key in toggled_validators:
                self.badges.update_badge(badge_key, False, None)
            return

        if self._catalog_validators_suspended:
            for validator, _ in toggled_validators:
                validator.resume()
            self._catalog_validators_suspended = False

        if initializing:
            return

        for validator, _ in toggled_validators:
            validator.validate_callback()
        self.id_validator.validate_callback()
        self.desc_validator.validate_callback()

    # ------------------------------------------------------------------
    # Catálogo y sugerencias

    def _get_case_context(self) -> dict:
        if callable(self.context_provider):
            try:
                return self.context_provider() or {}
            except Exception:
                return {}
        return {}

    def _get_existing_ids(self) -> set[str]:
        if callable(self.existing_ids_provider):
            try:
                return set(self.existing_ids_provider(self) or set())
            except Exception:
                return set()
        return set()

    def offer_catalog_modal(self, trigger: str = ""):
        """Lanza un modal de catálogo cuando hay sugerencias disponibles."""

        if not self.is_catalog_mode():
            return None

        suggestions = build_risk_suggestions(
            self.risk_lookup,
            context=self._get_case_context(),
            excluded_ids=self._get_existing_ids(),
        )
        if not suggestions:
            return None

        def _on_select(risk_id: str | None):
            if not risk_id:
                return
            self.id_var.set(risk_id)
            self._set_catalog_mode(True)
            self.on_id_change(from_focus=True, explicit_lookup=True, preserve_existing=False)

        factory = self.modal_factory or RiskCatalogModal
        try:
            parent = self.frame.winfo_toplevel()
        except Exception:
            parent = getattr(self, "frame", None)

        try:
            return factory(parent, suggestions, on_select=_on_select, trigger=trigger)
        finally:
            self._schedule_refresh()

    def _validate_criticidad(self):
        value = (self.criticidad_var.get() or "").strip()
        if not value:
            return "Debe seleccionar la criticidad del riesgo."
        if value not in CRITICIDAD_LIST:
            return f"La criticidad '{value}' no está en el catálogo CM."
        return None

    def clear_values(self):
        """Limpia los valores capturados manteniendo visibles los widgets."""

        def _reset():
            for var in (
                self.id_var,
                self.lider_var,
                self.descripcion_var,
                self.criticidad_var,
                self.exposicion_var,
                self.planes_var,
            ):
                var.set("")

        managed = False
        for validator in self.validators:
            suppress = getattr(validator, "suppress_during", None)
            if callable(suppress):
                suppress(_reset)
                managed = True
                break
        if not managed:
            _reset()

    def _log_change(self, message: str):
        if callable(self.change_notifier):
            self.change_notifier(message)
        else:
            log_event("navegacion", message, self.logs)

    # ------------------------------------------------------------------
    # Gestión del identificador

    def _on_id_var_change(self, *_):
        if self._suppress_id_trace:
            return
        current_value = self.id_var.get()
        if current_value != self._auto_id_value:
            self._id_user_modified = True

    def _bind_identifier_triggers(self, widget) -> None:
        widget.bind("<FocusOut>", lambda _e: self.on_id_change(from_focus=True), add="+")
        widget.bind("<KeyRelease>", lambda _e: self.on_id_change(), add="+")
        widget.bind(
            "<Return>",
            lambda _e: self.on_id_change(from_focus=True, explicit_lookup=True),
            add="+",
        )
        widget.bind("<<Paste>>", lambda _e: self.on_id_change(), add="+")
        widget.bind("<<ComboboxSelected>>", lambda _e: self.on_id_change(from_focus=True), add="+")

    def _on_mode_toggle(self):
        if self.is_catalog_mode():
            self.on_id_change(preserve_existing=True, silent=True)
            self.offer_catalog_modal(trigger="mode_toggle")
        else:
            self._last_missing_lookup_id = None
            self._schedule_refresh()

    def _set_catalog_mode(self, enabled: bool):
        self.new_risk_var.set(not enabled)

    def is_catalog_mode(self) -> bool:
        var = getattr(self, "new_risk_var", None)
        if var is None:
            return True
        return not var.get()

    def assign_new_auto_id(self, value: str):
        """Asigna un identificador automático sin marcarlo como editado."""

        self._auto_id_value = value
        self._suppress_id_trace = True
        self.id_var.set(value)
        self._suppress_id_trace = False
        self._id_user_modified = False

    def has_user_modified_id(self) -> bool:
        """Indica si el usuario cambió manualmente el identificador."""

        return self._id_user_modified

    def _activate_header_tree(self, *_):
        if self.header_tree:
            self.attach_header_tree(self.header_tree)

    def _register_header_tree_focus(self, *widgets):
        for widget in widgets:
            try:
                widget.bind("<FocusIn>", self._activate_header_tree, add="+")
            except Exception:
                continue
        try:
            self.section.bind("<FocusIn>", self._activate_header_tree, add="+")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Refresh management

    def set_refresh_callbacks(self, shared_tree_refresher=None, summary_refresher=None):
        self._shared_tree_refresher = shared_tree_refresher
        self._summary_refresher = summary_refresher

    def _register_refresh_traces(self):
        for var in (
            self.id_var,
            self.new_risk_var,
            self.lider_var,
            self.descripcion_var,
            self.criticidad_var,
            self.exposicion_var,
            self.planes_var,
        ):
            var.trace_add("write", lambda *_args: self._schedule_refresh())

    def _schedule_refresh(self):
        current_after_id = getattr(self, "_refresh_after_id", None)
        if current_after_id:
            try:
                self.frame.after_cancel(current_after_id)
            except Exception:
                self._refresh_after_id = None
        frame = getattr(self, "frame", None)
        if frame and hasattr(frame, "after"):
            try:
                self._refresh_after_id = frame.after(120, self._run_refresh_callbacks)
                return
            except Exception:
                self._refresh_after_id = None
        self._run_refresh_callbacks()

    def _run_refresh_callbacks(self):
        self._refresh_after_id = None
        shared_refresher = getattr(self, "_shared_tree_refresher", None)
        summary_refresher = getattr(self, "_summary_refresher", None)
        if callable(shared_refresher):
            shared_refresher()
        if callable(summary_refresher):
            summary_refresher()


__all__ = ["RiskFrame", "RiskCatalogModal", "build_risk_suggestions"]
