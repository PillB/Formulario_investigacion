"""Componentes para normas transgredidas."""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import messagebox, ttk

from validators import FieldValidator, log_event, validate_date_text, validate_norm_id, validate_required_text


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

        self.frame = ttk.LabelFrame(parent, text=f"Norma {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)
        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="ID de norma:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=5)
        self.tooltip_register(id_entry, "Formato requerido: XXXX.XXX.XX.XX")
        ttk.Label(row1, text="Fecha de vigencia (YYYY-MM-DD):").pack(side="left")
        fecha_entry = ttk.Entry(row1, textvariable=self.fecha_var, width=15)
        fecha_entry.pack(side="left", padx=5)
        self.tooltip_register(fecha_entry, "Fecha de publicación o vigencia de la norma.")

        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="Descripción de la norma:").pack(side="left")
        desc_entry = ttk.Entry(row2, textvariable=self.descripcion_var, width=70)
        desc_entry.pack(side="left", padx=5)
        self.tooltip_register(desc_entry, "Detalla el artículo o sección vulnerada.")

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=2)
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
                lambda: validate_date_text(self.fecha_var.get(), "la fecha de vigencia"),
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
        if not norm_id:
            norm_id = f"{random.randint(1000, 9999)}.{random.randint(100, 999):03d}.{random.randint(10, 99):02d}.{random.randint(10, 99):02d}"
            self.id_var.set(norm_id)
            self._log_change(f"Norma {self.idx+1} sin ID: se asignó correlativo {norm_id}")
        return {
            "id_norma": norm_id,
            "descripcion": self.descripcion_var.get().strip(),
            "fecha_vigencia": self.fecha_var.get().strip(),
        }

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
