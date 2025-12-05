"""Componentes para normas transgredidas."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from validators import (
    FieldValidator,
    log_event,
    should_autofill_field,
    validate_date_text,
    validate_norm_id,
    validate_required_text,
)
from ui.frames.utils import (
    create_date_entry,
    create_collapsible_card,
    ensure_grid_support,
    grid_section,
)
from ui.config import COL_PADX, ROW_PADY
from ui.layout import CollapsibleSection
from validation_badge import badge_registry


class NormFrame:
    """Representa una norma transgredida en la sección de normas."""

    HEADER_COLUMNS = (
        ("id_norma", "ID"),
        ("fecha_vigencia", "Fecha"),
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
        header_tree=None,
    ):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self.change_notifier = change_notifier
        self.header_tree = None
        self._shared_tree_refresher = None
        self._summary_refresher = None
        self._refresh_after_id = None

        self.id_var = tk.StringVar()
        self.descripcion_var = tk.StringVar()
        self.fecha_var = tk.StringVar()
        self.norm_lookup = {}
        self._last_missing_lookup_id = None

        self.section = create_collapsible_card(
            parent,
            title="",
            on_toggle=lambda _section: self._sync_section_title(),
            log_error=lambda exc: log_event(
                "validacion",
                f"No se pudo crear acordeón para norma {idx+1}: {exc}",
                self.logs,
            ),
            collapsible_cls=CollapsibleSection,
        )
        self._sync_section_title()
        self._place_section()

        self.frame = ttk.LabelFrame(self.section.content, text="")
        self.section.pack_content(self.frame, fill="x", expand=True)
        ensure_grid_support(self.frame)
        self.badges = badge_registry
        if hasattr(self.frame, "columnconfigure"):
            self.frame.columnconfigure(1, weight=1)
            self.frame.columnconfigure(3, weight=1)

        action_row = ttk.Frame(self.frame)
        ensure_grid_support(action_row)
        action_row.grid(row=0, column=0, columnspan=4, padx=COL_PADX, pady=ROW_PADY, sticky="ew")
        if hasattr(action_row, "columnconfigure"):
            action_row.columnconfigure(0, weight=1)
            action_row.columnconfigure(1, weight=0)
        remove_btn = ttk.Button(action_row, text="Eliminar norma", command=self.remove)
        remove_btn.grid(row=0, column=1, sticky="e")
        self.tooltip_register(remove_btn, "Quita esta norma del caso.")

        ttk.Label(self.frame, text="ID de norma:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        id_entry = self._make_badged_field(
            self.frame,
            "norm_id",
            lambda parent: ttk.Entry(parent, textvariable=self.id_var, width=20),
            row=1,
            column=1,
        )
        self.tooltip_register(id_entry, "Formato requerido: XXXX.XXX.XX.XX")
        self._bind_identifier_triggers(id_entry)

        ttk.Label(self.frame, text="Fecha de vigencia:\n(YYYY-MM-DD)").grid(
            row=1,
            column=2,
            padx=COL_PADX,
            pady=(ROW_PADY // 2, ROW_PADY // 2),
            sticky="e",
        )
        fecha_entry = self._make_badged_field(
            self.frame,
            "norm_fecha",
            lambda parent: create_date_entry(parent, textvariable=self.fecha_var, width=15),
            row=1,
            column=3,
        )
        self.fecha_entry = fecha_entry
        self.tooltip_register(fecha_entry, "Fecha de publicación o vigencia de la norma.")

        ttk.Label(self.frame, text="Descripción de la norma:").grid(
            row=2, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        desc_entry = self._make_badged_field(
            self.frame,
            "norm_desc",
            lambda parent: ttk.Entry(parent, textvariable=self.descripcion_var, width=70),
            row=2,
            column=1,
            columnspan=3,
        )
        self.tooltip_register(desc_entry, "Detalla el artículo o sección vulnerada.")

        self.validators.append(
            FieldValidator(
                id_entry,
                self.badges.wrap_validation(
                    "norm_id", lambda: validate_norm_id(self.id_var.get())
                ),
                self.logs,
                f"Norma {self.idx+1} - ID",
                variables=[self.id_var],
            )
        )
        self.validators.append(
            FieldValidator(
                fecha_entry,
                self.badges.wrap_validation(
                    "norm_fecha",
                    lambda: validate_date_text(
                        self.fecha_var.get(),
                        "la fecha de vigencia",
                        allow_blank=False,
                        enforce_max_today=True,
                    ),
                ),
                self.logs,
                f"Norma {self.idx+1} - Fecha",
                variables=[self.fecha_var],
            )
        )
        self.validators.append(
            FieldValidator(
                desc_entry,
                self.badges.wrap_validation(
                    "norm_desc",
                    lambda: validate_required_text(
                        self.descripcion_var.get(), "la descripción de la norma"
                    ),
                ),
                self.logs,
                f"Norma {self.idx+1} - Descripción",
                variables=[self.descripcion_var],
            )
        )

        self._register_title_traces()
        self._sync_section_title()
        self.attach_header_tree(header_tree)
        self._register_header_tree_focus(id_entry, fecha_entry, desc_entry)
        self._register_refresh_traces()

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
                self.frame.configure(text=f"Norma {self.idx+1}")
            except Exception:
                pass

    @staticmethod
    def build_header_tree(parent, xscrollcommand=None):
        header_tree = ttk.Treeview(
            parent,
            columns=[c[0] for c in NormFrame.HEADER_COLUMNS],
            show="headings",
            height=4,
        )

        column_widths = {
            "id_norma": 200,
            "fecha_vigencia": 160,
            "descripcion": 380,
        }

        for col_id, text in NormFrame.HEADER_COLUMNS:
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
        self.badges.claim(key, container, row=0, column=1)
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

    def _build_section_title(self) -> str:
        base_title = f"Norma {self.idx+1}"
        if getattr(self, "section", None) and not self.section.is_open:
            norm_id = self.id_var.get().strip()
            descripcion = self.descripcion_var.get().strip()
            details = [value for value in (norm_id, descripcion) if value]
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
        norm_id = self.id_var.get().strip()
        descripcion = self.descripcion_var.get().strip()
        fecha = self.fecha_var.get().strip()
        if not (norm_id or descripcion or fecha):
            return None
        return {
            "id_norma": norm_id,
            "descripcion": descripcion,
            "fecha_vigencia": fecha,
        }

    def set_lookup(self, lookup):
        self.norm_lookup = lookup or {}
        self._last_missing_lookup_id = None
        self.on_id_change(preserve_existing=True, silent=True)

    def on_id_change(
        self, from_focus=False, preserve_existing=False, silent=False, explicit_lookup=False
    ):
        norm_id = self.id_var.get().strip()
        if not norm_id:
            self._last_missing_lookup_id = None
            return
        data = self.norm_lookup.get(norm_id)
        if not data:
            if (
                explicit_lookup
                and from_focus
                and not silent
                and self.norm_lookup
                and self._last_missing_lookup_id != norm_id
            ):
                messagebox.showerror(
                    "Norma no encontrada",
                    (
                        f"El ID {norm_id} no existe en los catálogos de detalle. "
                        "Verifica el código o actualiza norm_details.csv."
                    ),
                )
                self._last_missing_lookup_id = norm_id
            else:
                self._last_missing_lookup_id = None
            return

        def set_if_present(var, key):
            value = data.get(key)
            if value in (None, ""):
                return
            text_value = str(value).strip()
            if text_value and should_autofill_field(var.get(), preserve_existing):
                var.set(text_value)

        set_if_present(self.descripcion_var, "descripcion")
        set_if_present(self.fecha_var, "fecha_vigencia")
        self._last_missing_lookup_id = None
        if not silent:
            self._log_change(f"Norma {self.idx+1}: autopoblada desde catálogo")
        self._schedule_refresh()

    def set_refresh_callbacks(self, shared_tree_refresher=None, summary_refresher=None):
        self._shared_tree_refresher = shared_tree_refresher
        self._summary_refresher = summary_refresher

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
        self.on_id_change(from_focus=True, explicit_lookup=True)

    def _first_selected_item(self):
        selection = self.header_tree.selection() if self.header_tree else []
        return selection[0] if selection else None

    def clear_values(self):
        """Vacía los datos manteniendo visibles las entradas."""

        def _reset():
            for var in (self.id_var, self.fecha_var, self.descripcion_var):
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

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar la norma {self.idx+1}?"):
            self._log_change(f"Se eliminó norma {self.idx+1}")
            self.section.destroy()
            self.remove_callback(self)

    def _log_change(self, message: str):
        if callable(self.change_notifier):
            self.change_notifier(message)
        else:
            log_event("navegacion", message, self.logs)

    def update_title(self, idx: int) -> None:
        self.idx = idx
        title = f"Norma {self.idx+1}"
        self.section.title_label.configure(text=title)
        self.frame.configure(text=title)

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

    def _register_refresh_traces(self):
        for var in (self.id_var, self.descripcion_var, self.fecha_var):
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


__all__ = ["NormFrame"]
