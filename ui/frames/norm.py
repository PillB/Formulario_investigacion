"""Componentes para normas transgredidas."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from theme_manager import ThemeManager
from validators import (
    FieldValidator,
    log_event,
    should_autofill_field,
    validate_date_text,
    validate_norm_id,
    validate_required_text,
)
from ui.frames.utils import (
    build_two_column_form,
    compute_badge_minsize,
    create_date_entry,
    create_collapsible_card,
    ensure_grid_support,
    grid_labeled_widget,
    grid_section,
    record_import_issue,
)
from ui.config import COL_PADX, ROW_PADY
from ui.layout import CollapsibleSection
from validation_badge import badge_registry


class NormFrame:
    """Representa una norma transgredida en la sección de normas."""

    HEADER_COLUMNS = (
        ("id_norma", "ID"),
        ("acapite_inciso", "Acápite/Inciso"),
        ("fecha_vigencia", "Fecha"),
        ("descripcion", "Descripción"),
        ("detalle_norma", "Detalle de Norma"),
    )

    def __init__(
        self,
        parent,
        idx,
        remove_callback,
        logs,
        tooltip_register,
        owner=None,
        change_notifier=None,
        header_tree=None,
    ):
        self.parent = parent
        self.owner = owner
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
        self.case_id_var = tk.StringVar()
        self.descripcion_var = tk.StringVar()
        self.fecha_var = tk.StringVar()
        self.acapite_var = tk.StringVar()
        self.detalle_var = tk.StringVar()
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
            open=False,
        )
        self._sync_section_title()
        self._place_section()

        content_frame = ttk.Frame(self.section.content)
        self.section.pack_content(content_frame, fill="both", expand=True)
        ensure_grid_support(content_frame)
        if hasattr(content_frame, "columnconfigure"):
            try:
                content_frame.columnconfigure(0, weight=1)
            except Exception:
                pass
        if hasattr(content_frame, "rowconfigure"):
            try:
                content_frame.rowconfigure(0, weight=1)
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
        try:
            self.frame.rowconfigure(5, weight=1)
        except Exception:
            pass

        action_row = ttk.Frame(self.frame)
        ensure_grid_support(action_row)
        if hasattr(action_row, "columnconfigure"):
            action_row.columnconfigure(0, weight=1)
            action_row.columnconfigure(1, weight=0)
        remove_btn = ttk.Button(action_row, text="Eliminar norma", command=self.remove)
        remove_btn.grid(row=0, column=1, sticky="e")
        grid_labeled_widget(
            self.frame,
            row=0,
            label_widget=ttk.Frame(self.frame),
            field_widget=action_row,
            label_sticky="nsew",
        )
        self.tooltip_register(remove_btn, "Quita esta norma del caso.")

        id_label = ttk.Label(self.frame, text="ID de norma:")
        id_container, id_entry = self._make_badged_field(
            self.frame,
            "norm_id",
            lambda parent: ttk.Entry(parent, textvariable=self.id_var, width=20),
            row=1,
            column=1,
            autogrid=False,
        )
        grid_labeled_widget(
            self.frame,
            row=1,
            label_widget=id_label,
            field_widget=id_container,
        )
        self.tooltip_register(id_entry, "Formato requerido: XXXX.XXX.XX.XX")
        self._bind_identifier_triggers(id_entry)

        fecha_label = ttk.Label(self.frame, text="Fecha de vigencia:\n(YYYY-MM-DD)")
        fecha_container, fecha_entry = self._make_badged_field(
            self.frame,
            "norm_fecha",
            lambda parent: create_date_entry(parent, textvariable=self.fecha_var, width=15),
            row=2,
            column=1,
            autogrid=False,
        )
        grid_labeled_widget(
            self.frame,
            row=2,
            label_widget=fecha_label,
            field_widget=fecha_container,
        )
        self.fecha_entry = fecha_entry
        self.tooltip_register(fecha_entry, "Fecha de publicación o vigencia de la norma.")

        desc_label = ttk.Label(self.frame, text="Descripción de la norma:")
        desc_container, desc_entry = self._make_badged_field(
            self.frame,
            "norm_desc",
            lambda parent: ttk.Entry(parent, textvariable=self.descripcion_var, width=70),
            row=3,
            column=1,
            autogrid=False,
        )
        grid_labeled_widget(
            self.frame,
            row=3,
            label_widget=desc_label,
            field_widget=desc_container,
        )
        self.tooltip_register(desc_entry, "Detalla el artículo o sección vulnerada.")

        acapite_label = ttk.Label(self.frame, text="Acápite/Inciso:")
        acapite_container, acapite_entry = self._make_badged_field(
            self.frame,
            "norm_acapite",
            lambda parent: ttk.Entry(parent, textvariable=self.acapite_var, width=30),
            row=4,
            column=1,
            autogrid=False,
        )
        grid_labeled_widget(
            self.frame,
            row=4,
            label_widget=acapite_label,
            field_widget=acapite_container,
        )
        self.tooltip_register(acapite_entry, "Referencia del acápite o inciso aplicable.")

        detalle_label = ttk.Label(self.frame, text="Detalle de Norma:")
        detalle_container = ttk.Frame(self.frame)
        ensure_grid_support(detalle_container)
        if hasattr(detalle_container, "columnconfigure"):
            detalle_container.columnconfigure(0, weight=1)
        if hasattr(detalle_container, "rowconfigure"):
            detalle_container.rowconfigure(0, weight=1)
        detalle_text = scrolledtext.ScrolledText(detalle_container, height=4, wrap=tk.WORD)
        detalle_text.grid(row=0, column=0, padx=(0, COL_PADX // 2), pady=ROW_PADY, sticky="nsew")
        if hasattr(detalle_text, "winfo_children"):
            ThemeManager.apply_to_widget_tree(detalle_text)
        self.badges.claim("norm_detalle", detalle_container, row=0, column=1)
        grid_labeled_widget(
            self.frame,
            row=5,
            label_widget=detalle_label,
            field_widget=detalle_container,
            label_sticky="ne",
            field_sticky="nsew",
        )
        self.detalle_text = detalle_text
        self.tooltip_register(detalle_text, "Amplía la explicación de la transgresión.")

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
        self.validators.append(
            FieldValidator(
                acapite_entry,
                self.badges.wrap_validation(
                    "norm_acapite",
                    lambda: validate_required_text(
                        self.acapite_var.get(), "el acápite o inciso de la norma"
                    ),
                ),
                self.logs,
                f"Norma {self.idx+1} - Acápite/Inciso",
                variables=[self.acapite_var],
            )
        )
        detalle_validator = FieldValidator(
            detalle_text,
            self.badges.wrap_validation(
                "norm_detalle",
                lambda: validate_required_text(
                    self.detalle_var.get() or self._get_detalle_text(),
                    "el detalle de la norma",
                ),
            ),
            self.logs,
            f"Norma {self.idx+1} - Detalle",
            variables=[self.detalle_var],
        )
        detalle_validator.add_widget(detalle_text)
        self.validators.append(detalle_validator)

        self._register_title_traces()
        self._sync_section_title()
        self.attach_header_tree(header_tree)
        self._register_header_tree_focus(id_entry, fecha_entry, desc_entry, acapite_entry, detalle_text)
        self._bind_detalle_text_events(detalle_text)
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
            "acapite_inciso": 200,
            "fecha_vigencia": 160,
            "descripcion": 320,
            "detalle_norma": 360,
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
        for var in (self.id_var, self.descripcion_var, self.acapite_var, self.detalle_var):
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
            acapite = self.acapite_var.get().strip()
            detalle = self._shorten_preview(self._get_detalle_text())
            details = [value for value in (norm_id, acapite, descripcion, detalle) if value]
            if details:
                base_title = f"{base_title} – {' | '.join(details)}"
        return base_title

    @staticmethod
    def _shorten_preview(text: str, max_length: int = 60) -> str:
        if not text:
            return ""
        clean = " ".join(text.split())
        if len(clean) <= max_length:
            return clean
        return clean[: max_length - 1].rstrip() + "…"

    def _sync_section_title(self, *_args):
        if not getattr(self, "section", None):
            return
        set_title = getattr(self.section, "set_title", None)
        if callable(set_title):
            self.section.set_title(self._build_section_title())

    def _get_detalle_text(self) -> str:
        widget = getattr(self, "detalle_text", None)
        if widget is not None:
            try:
                return widget.get("1.0", "end-1c").strip()
            except Exception:
                pass
        try:
            return self.detalle_var.get().strip()
        except Exception:
            return ""

    def _set_detalle_text(self, value: str) -> None:
        text = (value or "").strip()
        self.detalle_var.set(text)
        widget = getattr(self, "detalle_text", None)
        if widget is None:
            return
        try:
            widget.delete("1.0", "end")
            if text:
                widget.insert("1.0", text)
            widget.edit_modified(False)
        except Exception:
            return

    def _bind_detalle_text_events(self, widget) -> None:
        if widget is None:
            return

        def _sync_from_text(_event=None):
            self.detalle_var.set(self._get_detalle_text())
            self._sync_section_title()
            self._schedule_refresh()
            try:
                widget.edit_modified(False)
            except Exception:
                pass

        for sequence in ("<<Modified>>", "<KeyRelease>", "<<Paste>>", "<<Cut>>", "<FocusOut>"):
            try:
                widget.bind(sequence, _sync_from_text, add="+")
            except Exception:
                continue
        try:
            widget.edit_modified(False)
        except Exception:
            pass

    def get_data(self):
        norm_id = self.id_var.get().strip()
        descripcion = self.descripcion_var.get().strip()
        fecha = self.fecha_var.get().strip()
        acapite = self.acapite_var.get().strip()
        detalle = self._get_detalle_text()
        if not (norm_id or descripcion or fecha or acapite or detalle):
            return None
        return {
            "id_norma": norm_id,
            "id_caso": self.case_id_var.get().strip(),
            "descripcion": descripcion,
            "fecha_vigencia": fecha,
            "acapite_inciso": acapite,
            "detalle_norma": detalle,
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
                issue_registered = record_import_issue(
                    self.owner,
                    "ID de norma no encontrado en catálogo de detalle",
                    identifier=norm_id,
                    detail=(
                        "El ID no existe en los catálogos de detalle. "
                        "Verifica el código o actualiza norm_details.csv."
                    ),
                    source="normas",
                )
                if not issue_registered:
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
        set_if_present(self.acapite_var, "acapite_inciso")
        detalle_valor = data.get("detalle_norma") or data.get("detalle")
        if detalle_valor:
            text_value = str(detalle_valor).strip()
            if text_value and should_autofill_field(self._get_detalle_text(), preserve_existing):
                self._set_detalle_text(text_value)
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
            for var in (
                self.id_var,
                self.fecha_var,
                self.descripcion_var,
                self.acapite_var,
                self.detalle_var,
            ):
                var.set("")
            self._set_detalle_text("")

        if self.validators:
            for validator in self.validators:
                suspend = getattr(validator, "suspend", None)
                if callable(suspend):
                    suspend()
            try:
                _reset()
            finally:
                for validator in self.validators:
                    resume = getattr(validator, "resume", None)
                    if callable(resume):
                        resume()
        else:
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
        for var in (self.id_var, self.descripcion_var, self.fecha_var, self.acapite_var, self.detalle_var):
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
