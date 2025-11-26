"""Componentes para la captura de riesgos."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from settings import CRITICIDAD_LIST
from validators import (FieldValidator, log_event, should_autofill_field,
                        validate_money_bounds, validate_risk_id)
from ui.frames.utils import BadgeManager, ensure_grid_support
from ui.config import COL_PADX, ROW_PADY
from ui.layout import CollapsibleSection


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
    ):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self._refresh_after_id = None
        self._summary_refresher = None
        self._shared_tree_refresher = None
        self._last_exposicion_decimal = None
        self.risk_lookup = {}
        self._last_missing_lookup_id = None
        self.change_notifier = change_notifier
        self.header_tree = None

        self.id_var = tk.StringVar()
        self._auto_id_value = ""
        self._id_user_modified = False
        self._suppress_id_trace = False
        self.id_var.trace_add("write", self._on_id_var_change)
        self.assign_new_auto_id(default_risk_id or f"RSK-{idx+1:06d}")
        self.lider_var = tk.StringVar()
        self.descripcion_var = tk.StringVar()
        self.criticidad_var = tk.StringVar()
        self.exposicion_var = tk.StringVar()
        self.planes_var = tk.StringVar()
        self._register_refresh_traces()

        self.section = CollapsibleSection(
            parent, title="", on_toggle=lambda _section: self._sync_section_title()
        )
        self.section.pack(fill="x", padx=COL_PADX, pady=(ROW_PADY // 2, ROW_PADY))

        self.frame = ttk.LabelFrame(self.section.content, text=f"Riesgo {self.idx+1}")
        self.section.pack_content(self.frame, fill="x", expand=True)
        ensure_grid_support(self.frame)
        self.badges = BadgeManager(parent=self.frame)
        if hasattr(self.frame, "columnconfigure"):
            self.frame.columnconfigure(1, weight=1)
            self.frame.columnconfigure(3, weight=1)

        action_row = ttk.Frame(self.frame)
        ensure_grid_support(action_row)
        action_row.grid(row=0, column=0, columnspan=4, padx=COL_PADX, pady=ROW_PADY, sticky="ew")
        if hasattr(action_row, "columnconfigure"):
            action_row.columnconfigure(0, weight=1)
            action_row.columnconfigure(1, weight=0)
        remove_btn = ttk.Button(action_row, text="Eliminar riesgo", command=self.remove)
        remove_btn.grid(row=0, column=1, sticky="e")
        self.tooltip_register(remove_btn, "Quita este riesgo del caso.")

        ttk.Label(self.frame, text="ID riesgo:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        id_entry = self._make_badged_field(
            self.frame,
            "riesgo_id",
            lambda parent: ttk.Entry(parent, textvariable=self.id_var, width=15),
            row=1,
            column=1,
        )
        self.tooltip_register(id_entry, "Usa el formato RSK-000000.")
        self._bind_identifier_triggers(id_entry)

        ttk.Label(self.frame, text="Criticidad:").grid(
            row=1, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        crit_cb = self._make_badged_field(
            self.frame,
            "riesgo_criticidad",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.criticidad_var,
                values=CRITICIDAD_LIST,
                state="readonly",
                width=12,
            ),
            row=1,
            column=3,
        )
        crit_cb.set('')
        self.tooltip_register(crit_cb, "Nivel de severidad del riesgo.")

        ttk.Label(self.frame, text="Líder:").grid(
            row=2, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        lider_entry = ttk.Entry(self.frame, textvariable=self.lider_var, width=20)
        lider_entry.grid(row=2, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.tooltip_register(lider_entry, "Responsable del seguimiento del riesgo.")

        ttk.Label(self.frame, text="Exposición residual (US$):").grid(
            row=2, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        expos_entry = self._make_badged_field(
            self.frame,
            "riesgo_exposicion",
            lambda parent: ttk.Entry(parent, textvariable=self.exposicion_var, width=15),
            row=2,
            column=3,
        )
        self.tooltip_register(expos_entry, "Monto estimado en dólares.")

        ttk.Label(self.frame, text="Descripción del riesgo:").grid(
            row=3, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        desc_entry = ttk.Entry(self.frame, textvariable=self.descripcion_var, width=60)
        desc_entry.grid(row=3, column=1, columnspan=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.tooltip_register(desc_entry, "Describe el riesgo de forma clara.")

        ttk.Label(self.frame, text="Planes de acción (IDs separados por ;):").grid(
            row=4, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        planes_entry = ttk.Entry(self.frame, textvariable=self.planes_var, width=40)
        planes_entry.grid(row=4, column=1, columnspan=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.tooltip_register(planes_entry, "Lista de planes registrados en OTRS o Aranda.")

        self.validators.append(
            FieldValidator(
                id_entry,
                self.badges.wrap_validation("riesgo_id", self._validate_risk_id),
                self.logs,
                f"Riesgo {self.idx+1} - ID",
                variables=[self.id_var],
            )
        )

        def _validate_exposure_amount():
            message, _normalized_text = self._normalize_exposure_amount()
            return message

        self.validators.append(
            FieldValidator(
                expos_entry,
                self.badges.wrap_validation(
                    "riesgo_exposicion", _validate_exposure_amount
                ),
                self.logs,
                f"Riesgo {self.idx+1} - Exposición",
                variables=[self.exposicion_var],
            )
        )

        self.validators.append(
            FieldValidator(
                crit_cb,
                self.badges.wrap_validation(
                    "riesgo_criticidad", self._validate_criticidad
                ),
                self.logs,
                f"Riesgo {self.idx+1} - Criticidad",
                variables=[self.criticidad_var],
            )
        )

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
        self._sync_section_title()

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
    ):
        container = ttk.Frame(parent)
        ensure_grid_support(container)
        if hasattr(container, "columnconfigure"):
            container.columnconfigure(0, weight=1)

        widget = widget_factory(container)
        widget.grid(row=0, column=0, padx=(0, COL_PADX // 2), pady=ROW_PADY, sticky="we")
        self.badges.create_and_register(key, container, row=0, column=1)
        container.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            padx=COL_PADX,
            pady=ROW_PADY,
            sticky=sticky,
        )
        return widget

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
            "lider": self.lider_var.get().strip(),
            "descripcion": self.descripcion_var.get().strip(),
            "criticidad": self.criticidad_var.get(),
            "exposicion_residual": exposure_value,
            "planes_accion": self.planes_var.get().strip(),
        }

    def set_lookup(self, lookup):
        self.risk_lookup = lookup or {}
        self._last_missing_lookup_id = None
        self._populate_header_tree()
        self.on_id_change(preserve_existing=True, silent=True)

    def on_id_change(self, from_focus=False, preserve_existing=False, silent=False):
        rid = self.id_var.get().strip()
        if not rid:
            self._last_missing_lookup_id = None
            return
        data = self.risk_lookup.get(rid)
        if not data:
            if from_focus and not silent and self.risk_lookup and self._last_missing_lookup_id != rid:
                messagebox.showerror(
                    "Riesgo no encontrado",
                    (
                        f"El ID {rid} no existe en los catálogos de detalle. "
                        "Verifica el código o actualiza risk_details.csv."
                    ),
                )
                self._last_missing_lookup_id = rid
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

    def _populate_header_tree(self):
        if not self.header_tree:
            return

        for child in self.header_tree.get_children(""):
            self.header_tree.delete(child)

        for row_index, (risk_id, data) in enumerate(sorted(self.risk_lookup.items())):
            values = (
                str(risk_id),
                str(data.get("criticidad", "")),
                str(data.get("exposicion_residual", "")),
                str(data.get("lider", "")),
                str(data.get("descripcion", "")),
            )
            tag = "even" if row_index % 2 == 0 else "odd"
            self.header_tree.insert("", "end", iid=str(risk_id), values=values, tags=(tag,))

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
        self.on_id_change(preserve_existing=True, silent=True)

    def _on_tree_double_click(self, _event=None):
        item = self._first_selected_item()
        if not item:
            return
        values = self.header_tree.item(item, "values")
        if not values:
            return
        self.id_var.set(values[0])
        self.on_id_change(from_focus=True)

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

    def _validate_risk_id(self):
        return validate_risk_id(self.id_var.get())

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
        widget.bind("<Return>", lambda _e: self.on_id_change(from_focus=True), add="+")
        widget.bind("<<Paste>>", lambda _e: self.on_id_change(), add="+")
        widget.bind("<<ComboboxSelected>>", lambda _e: self.on_id_change(from_focus=True), add="+")

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


__all__ = ["RiskFrame"]
