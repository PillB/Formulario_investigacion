"""Componentes para normas transgredidas."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from validators import (FieldValidator, log_event, should_autofill_field,
                        validate_date_text, validate_norm_id,
                        validate_required_text)
from ui.frames.utils import ensure_grid_support
from ui.config import COL_PADX, ROW_PADY
from ui.layout import CollapsibleSection


class NormFrame:
    """Representa una norma transgredida en la sección de normas."""

    def __init__(self, parent, idx, remove_callback, logs, tooltip_register, change_notifier=None):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self.change_notifier = change_notifier

        self.id_var = tk.StringVar()
        self.descripcion_var = tk.StringVar()
        self.fecha_var = tk.StringVar()
        self.norm_lookup = {}
        self._last_missing_lookup_id = None

        self.section = CollapsibleSection(parent, title=f"Norma {self.idx+1}")
        self.section.pack(fill="x", padx=COL_PADX, pady=(ROW_PADY // 2, ROW_PADY))
        self._build_header_table()

        self.frame = ttk.LabelFrame(self.section.content, text=f"Norma {self.idx+1}")
        self.section.pack_content(self.frame, fill="x", expand=True)
        ensure_grid_support(self.frame)
        if hasattr(self.frame, "columnconfigure"):
            self.frame.columnconfigure(1, weight=1)

        action_row = ttk.Frame(self.frame)
        ensure_grid_support(action_row)
        action_row.grid(row=0, column=0, columnspan=3, padx=COL_PADX, pady=ROW_PADY, sticky="e")
        if hasattr(action_row, "columnconfigure"):
            action_row.columnconfigure(0, weight=1)
        remove_btn = ttk.Button(action_row, text="Eliminar norma", command=self.remove)
        remove_btn.grid(row=0, column=1, sticky="e")
        self.tooltip_register(remove_btn, "Quita esta norma del caso.")

        ttk.Label(self.frame, text="ID de norma:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        id_entry = ttk.Entry(self.frame, textvariable=self.id_var, width=20)
        id_entry.grid(row=1, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=1, column=2, padx=COL_PADX, pady=ROW_PADY)
        self.tooltip_register(id_entry, "Formato requerido: XXXX.XXX.XX.XX")
        id_entry.bind("<FocusOut>", lambda _e: self.on_id_change(from_focus=True), add="+")

        ttk.Label(self.frame, text="Fecha de vigencia (YYYY-MM-DD):").grid(
            row=2, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        fecha_entry = ttk.Entry(self.frame, textvariable=self.fecha_var, width=15)
        fecha_entry.grid(row=2, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=2, column=2, padx=COL_PADX, pady=ROW_PADY)
        self.tooltip_register(fecha_entry, "Fecha de publicación o vigencia de la norma.")

        ttk.Label(self.frame, text="Descripción de la norma:").grid(
            row=3, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        desc_entry = ttk.Entry(self.frame, textvariable=self.descripcion_var, width=70)
        desc_entry.grid(row=3, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=3, column=2, padx=COL_PADX, pady=ROW_PADY)
        self.tooltip_register(desc_entry, "Detalla el artículo o sección vulnerada.")

        self.validators.append(
            FieldValidator(
                id_entry,
                lambda: validate_norm_id(self.id_var.get()),
                self.logs,
                f"Norma {self.idx+1} - ID",
                variables=[self.id_var],
            )
        )
        self.validators.append(
            FieldValidator(
                fecha_entry,
                lambda: validate_date_text(
                    self.fecha_var.get(),
                    "la fecha de vigencia",
                    allow_blank=False,
                    enforce_max_today=True,
                ),
                self.logs,
                f"Norma {self.idx+1} - Fecha",
                variables=[self.fecha_var],
            )
        )
        self.validators.append(
            FieldValidator(
                desc_entry,
                lambda: validate_required_text(self.descripcion_var.get(), "la descripción de la norma"),
                self.logs,
                f"Norma {self.idx+1} - Descripción",
                variables=[self.descripcion_var],
            )
        )

    def _build_header_table(self):
        container = ttk.Frame(self.section.content)
        self.section.pack_content(container, fill="x", expand=False)
        ensure_grid_support(container)
        if hasattr(container, "columnconfigure"):
            container.columnconfigure(0, weight=1)

        columns = (("id_norma", "ID"), ("fecha_vigencia", "Fecha"), ("descripcion", "Descripción"))
        self.header_tree = ttk.Treeview(
            container, columns=[c[0] for c in columns], show="headings", height=4
        )
        self.header_tree.grid(row=0, column=0, sticky="nsew", padx=COL_PADX, pady=(ROW_PADY, ROW_PADY // 2))
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.header_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=(ROW_PADY, ROW_PADY // 2))
        self.header_tree.configure(yscrollcommand=scrollbar.set)

        for col_id, text in columns:
            self.header_tree.heading(col_id, text=text, command=lambda c=col_id: self._sort_treeview(c))
            self.header_tree.column(col_id, anchor="w", width=140)

        self.header_tree.tag_configure("even", background="#f7f7f7")
        self.header_tree.tag_configure("odd", background="#ffffff")
        self.header_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.header_tree.bind("<Double-1>", self._on_tree_double_click)
        self._tree_sort_state = {}

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
        self._populate_header_tree()
        self.on_id_change(preserve_existing=True, silent=True)

    def on_id_change(self, from_focus=False, preserve_existing=False, silent=False):
        norm_id = self.id_var.get().strip()
        if not norm_id:
            self._last_missing_lookup_id = None
            return
        data = self.norm_lookup.get(norm_id)
        if not data:
            if from_focus and not silent and self.norm_lookup and self._last_missing_lookup_id != norm_id:
                messagebox.showerror(
                    "Norma no encontrada",
                    (
                        f"El ID {norm_id} no existe en los catálogos de detalle. "
                        "Verifica el código o actualiza norm_details.csv."
                    ),
                )
                self._last_missing_lookup_id = norm_id
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

    def _populate_header_tree(self):
        if not hasattr(self, "header_tree"):
            return

        for child in self.header_tree.get_children(""):
            self.header_tree.delete(child)

        for row_index, (norm_id, data) in enumerate(sorted(self.norm_lookup.items())):
            values = (
                str(norm_id),
                str(data.get("fecha_vigencia", "")),
                str(data.get("descripcion", "")),
            )
            tag = "even" if row_index % 2 == 0 else "odd"
            self.header_tree.insert("", "end", iid=str(norm_id), values=values, tags=(tag,))

    def _sort_treeview(self, column):
        if not hasattr(self, "header_tree"):
            return

        reverse = self._tree_sort_state.get(column, False)
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
        selection = self.header_tree.selection()
        return selection[0] if selection else None

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


__all__ = ["NormFrame"]
