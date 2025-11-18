"""Componentes para la captura de riesgos."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from settings import CRITICIDAD_LIST
from validators import FieldValidator, log_event, validate_money_bounds, validate_risk_id


class RiskFrame:
    """Representa un riesgo identificado en la sección de riesgos."""

    def __init__(self, parent, idx, remove_callback, logs, tooltip_register):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self._last_exposicion_decimal = None

        self.id_var = tk.StringVar(value=f"RSK-{idx+1:06d}")
        self.lider_var = tk.StringVar()
        self.descripcion_var = tk.StringVar()
        self.criticidad_var = tk.StringVar()
        self.exposicion_var = tk.StringVar()
        self.planes_var = tk.StringVar()

        self.frame = ttk.LabelFrame(parent, text=f"Riesgo {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)

        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="ID riesgo:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=15)
        id_entry.pack(side="left", padx=5)
        self.tooltip_register(id_entry, "Usa el formato RSK-000000.")
        ttk.Label(row1, text="Líder:").pack(side="left")
        lider_entry = ttk.Entry(row1, textvariable=self.lider_var, width=20)
        lider_entry.pack(side="left", padx=5)
        self.tooltip_register(lider_entry, "Responsable del seguimiento del riesgo.")
        ttk.Label(row1, text="Criticidad:").pack(side="left")
        crit_cb = ttk.Combobox(row1, textvariable=self.criticidad_var, values=CRITICIDAD_LIST, state="readonly", width=12)
        crit_cb.pack(side="left", padx=5)
        crit_cb.set('')
        self.tooltip_register(crit_cb, "Nivel de severidad del riesgo.")

        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="Descripción del riesgo:").pack(side="left")
        desc_entry = ttk.Entry(row2, textvariable=self.descripcion_var, width=60)
        desc_entry.pack(side="left", padx=5)
        self.tooltip_register(desc_entry, "Describe el riesgo de forma clara.")

        row3 = ttk.Frame(self.frame)
        row3.pack(fill="x", pady=1)
        ttk.Label(row3, text="Exposición residual (US$):").pack(side="left")
        expos_entry = ttk.Entry(row3, textvariable=self.exposicion_var, width=15)
        expos_entry.pack(side="left", padx=5)
        self.tooltip_register(expos_entry, "Monto estimado en dólares.")
        ttk.Label(row3, text="Planes de acción (IDs separados por ;):").pack(side="left")
        planes_entry = ttk.Entry(row3, textvariable=self.planes_var, width=40)
        planes_entry.pack(side="left", padx=5)
        self.tooltip_register(planes_entry, "Lista de planes registrados en OTRS o Aranda.")

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=2)
        remove_btn = ttk.Button(btn_frame, text="Eliminar riesgo", command=self.remove)
        remove_btn.pack(side="right")
        self.tooltip_register(remove_btn, "Quita este riesgo del caso.")

        self.validators.append(
            FieldValidator(
                id_entry,
                self._validate_risk_id,
                self.logs,
                f"Riesgo {self.idx+1} - ID",
                variables=[self.id_var],
            )
        )

        def _validate_exposure_amount():
            message, decimal_value = validate_money_bounds(
                self.exposicion_var.get(),
                "la exposición residual",
                allow_blank=True,
            )
            self._last_exposicion_decimal = decimal_value
            return message

        self.validators.append(
            FieldValidator(
                expos_entry,
                _validate_exposure_amount,
                self.logs,
                f"Riesgo {self.idx+1} - Exposición",
                variables=[self.exposicion_var],
            )
        )

    def get_data(self):
        return {
            "id_riesgo": self.id_var.get().strip(),
            "lider": self.lider_var.get().strip(),
            "descripcion": self.descripcion_var.get().strip(),
            "criticidad": self.criticidad_var.get(),
            "exposicion_residual": self.exposicion_var.get().strip(),
            "planes_accion": self.planes_var.get().strip(),
        }

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el riesgo {self.idx+1}?"):
            log_event("navegacion", f"Se eliminó riesgo {self.idx+1}", self.logs)
            self.frame.destroy()
            self.remove_callback(self)

    def _validate_risk_id(self):
        return validate_risk_id(self.id_var.get())


__all__ = ["RiskFrame"]
