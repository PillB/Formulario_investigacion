"""Componentes para la captura de riesgos."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from settings import CRITICIDAD_LIST
from validators import (FieldValidator, log_event, should_autofill_field,
                        validate_money_bounds, validate_risk_id)
from ui.frames.utils import ensure_grid_support
from ui.config import COL_PADX, ROW_PADY


class RiskFrame:
    """Representa un riesgo identificado en la sección de riesgos."""

    def __init__(
        self,
        parent,
        idx,
        remove_callback,
        logs,
        tooltip_register,
        change_notifier=None,
        default_risk_id: str | None = None,
    ):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self._last_exposicion_decimal = None
        self.risk_lookup = {}
        self._last_missing_lookup_id = None
        self.change_notifier = change_notifier

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

        self.frame = ttk.LabelFrame(parent, text=f"Riesgo {self.idx+1}")
        self.frame.pack(fill="x", padx=COL_PADX, pady=(ROW_PADY // 2, ROW_PADY))
        ensure_grid_support(self.frame)
        if hasattr(self.frame, "columnconfigure"):
            self.frame.columnconfigure(1, weight=1)

        action_row = ttk.Frame(self.frame)
        ensure_grid_support(action_row)
        action_row.grid(row=0, column=0, columnspan=3, padx=COL_PADX, pady=ROW_PADY, sticky="e")
        if hasattr(action_row, "columnconfigure"):
            action_row.columnconfigure(0, weight=1)
        remove_btn = ttk.Button(action_row, text="Eliminar riesgo", command=self.remove)
        remove_btn.grid(row=0, column=1, sticky="e")
        self.tooltip_register(remove_btn, "Quita este riesgo del caso.")

        ttk.Label(self.frame, text="ID riesgo:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        id_entry = ttk.Entry(self.frame, textvariable=self.id_var, width=15)
        id_entry.grid(row=1, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=1, column=2, padx=COL_PADX, pady=ROW_PADY)
        self.tooltip_register(id_entry, "Usa el formato RSK-000000.")
        self._bind_identifier_triggers(id_entry)

        ttk.Label(self.frame, text="Líder:").grid(
            row=2, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        lider_entry = ttk.Entry(self.frame, textvariable=self.lider_var, width=20)
        lider_entry.grid(row=2, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=2, column=2, padx=COL_PADX, pady=ROW_PADY)
        self.tooltip_register(lider_entry, "Responsable del seguimiento del riesgo.")

        ttk.Label(self.frame, text="Criticidad:").grid(
            row=3, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        crit_cb = ttk.Combobox(
            self.frame,
            textvariable=self.criticidad_var,
            values=CRITICIDAD_LIST,
            state="readonly",
            width=12,
        )
        crit_cb.grid(row=3, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=3, column=2, padx=COL_PADX, pady=ROW_PADY)
        crit_cb.set('')
        self.tooltip_register(crit_cb, "Nivel de severidad del riesgo.")

        ttk.Label(self.frame, text="Descripción del riesgo:").grid(
            row=4, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        desc_entry = ttk.Entry(self.frame, textvariable=self.descripcion_var, width=60)
        desc_entry.grid(row=4, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=4, column=2, padx=COL_PADX, pady=ROW_PADY)
        self.tooltip_register(desc_entry, "Describe el riesgo de forma clara.")

        ttk.Label(self.frame, text="Exposición residual (US$):").grid(
            row=5, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        expos_entry = ttk.Entry(self.frame, textvariable=self.exposicion_var, width=15)
        expos_entry.grid(row=5, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=5, column=2, padx=COL_PADX, pady=ROW_PADY)
        self.tooltip_register(expos_entry, "Monto estimado en dólares.")

        ttk.Label(self.frame, text="Planes de acción (IDs separados por ;):").grid(
            row=6, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        planes_entry = ttk.Entry(self.frame, textvariable=self.planes_var, width=40)
        planes_entry.grid(row=6, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=6, column=2, padx=COL_PADX, pady=ROW_PADY)
        self.tooltip_register(planes_entry, "Lista de planes registrados en OTRS o Aranda.")

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
            message, _normalized_text = self._normalize_exposure_amount()
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

        self.validators.append(
            FieldValidator(
                crit_cb,
                self._validate_criticidad,
                self.logs,
                f"Riesgo {self.idx+1} - Criticidad",
                variables=[self.criticidad_var],
            )
        )

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
            self.frame.destroy()
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


__all__ = ["RiskFrame"]
