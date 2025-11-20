"""Componentes para normas transgredidas."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from validators import (FieldValidator, log_event, should_autofill_field,
                        validate_date_text, validate_norm_id,
                        validate_required_text)
from ui.config import COL_PADX, ROW_PADY


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

        self.frame = ttk.LabelFrame(parent, text=f"Norma {self.idx+1}")
        self.frame.pack(fill="x", padx=COL_PADX, pady=ROW_PADY)
        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=ROW_PADY // 2)
        ttk.Label(row1, text="ID de norma:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=COL_PADX)
        self.tooltip_register(id_entry, "Formato requerido: XXXX.XXX.XX.XX")
        id_entry.bind("<FocusOut>", lambda _e: self.on_id_change(from_focus=True), add="+")
        ttk.Label(row1, text="Fecha de vigencia (YYYY-MM-DD):").pack(side="left")
        fecha_entry = ttk.Entry(row1, textvariable=self.fecha_var, width=15)
        fecha_entry.pack(side="left", padx=COL_PADX)
        self.tooltip_register(fecha_entry, "Fecha de publicación o vigencia de la norma.")

        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=ROW_PADY // 2)
        ttk.Label(row2, text="Descripción de la norma:").pack(side="left")
        desc_entry = ttk.Entry(row2, textvariable=self.descripcion_var, width=70)
        desc_entry.pack(side="left", padx=COL_PADX)
        self.tooltip_register(desc_entry, "Detalla el artículo o sección vulnerada.")

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=ROW_PADY)
        remove_btn = ttk.Button(btn_frame, text="Eliminar norma", command=self.remove)
        remove_btn.pack(side="right")
        self.tooltip_register(remove_btn, "Quita esta norma del caso.")

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
                    self.fecha_var.get(), "la fecha de vigencia", allow_blank=False
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

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar la norma {self.idx+1}?"):
            self._log_change(f"Se eliminó norma {self.idx+1}")
            self.frame.destroy()
            self.remove_callback(self)

    def _log_change(self, message: str):
        if callable(self.change_notifier):
            self.change_notifier(message)
        else:
            log_event("navegacion", message, self.logs)


__all__ = ["NormFrame"]
