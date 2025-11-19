"""Componentes de interfaz para colaboradores y asignaciones."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from settings import FLAG_COLABORADOR_LIST, TIPO_FALTA_LIST, TIPO_SANCION_LIST
from validators import (FieldValidator, log_event, should_autofill_field,
                        validate_agency_code, validate_required_text,
                        validate_team_member_id)


class TeamMemberFrame:
    """Representa un colaborador y su interfaz en la sección de colaboradores."""

    ENTITY_LABEL = "colaborador"

    def __init__(
        self,
        parent,
        idx,
        remove_callback,
        update_team_options,
        team_lookup,
        logs,
        tooltip_register,
        summary_refresh_callback=None,
        change_notifier=None,
        id_change_callback=None,
    ):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.update_team_options = update_team_options
        self.team_lookup = team_lookup
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self._last_missing_lookup_id = None
        self.schedule_summary_refresh = summary_refresh_callback or (lambda _sections=None: None)
        self.change_notifier = change_notifier
        self.id_change_callback = id_change_callback
        self._last_tracked_id = ''

        self.id_var = tk.StringVar()
        self.flag_var = tk.StringVar()
        self.division_var = tk.StringVar()
        self.area_var = tk.StringVar()
        self.servicio_var = tk.StringVar()
        self.puesto_var = tk.StringVar()
        self.nombre_agencia_var = tk.StringVar()
        self.codigo_agencia_var = tk.StringVar()
        self.tipo_falta_var = tk.StringVar()
        self.tipo_sancion_var = tk.StringVar()

        self.frame = ttk.LabelFrame(parent, text=f"Colaborador {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)

        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="ID del colaborador:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=5)
        id_entry.bind("<FocusOut>", lambda e: self.on_id_change(from_focus=True))
        id_entry.bind("<KeyRelease>", lambda e: self.on_id_change())
        self.tooltip_register(id_entry, "Coloca el código único del colaborador investigado.")
        ttk.Label(row1, text="Flag:").pack(side="left")
        flag_cb = ttk.Combobox(
            row1,
            textvariable=self.flag_var,
            values=FLAG_COLABORADOR_LIST,
            state="readonly",
            width=20,
        )
        flag_cb.pack(side="left", padx=5)
        flag_cb.set('')
        self.tooltip_register(flag_cb, "Define el rol del colaborador en el caso.")
        flag_cb.bind("<FocusOut>", lambda e: self._log_change(f"Colaborador {self.idx+1}: modificó flag"))

        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="División:").pack(side="left")
        div_entry = ttk.Entry(row2, textvariable=self.division_var, width=20)
        div_entry.pack(side="left", padx=5)
        self.tooltip_register(div_entry, "Ingresa la división o gerencia del colaborador.")
        ttk.Label(row2, text="Área:").pack(side="left")
        area_entry = ttk.Entry(row2, textvariable=self.area_var, width=20)
        area_entry.pack(side="left", padx=5)
        self.tooltip_register(area_entry, "Detalla el área específica.")
        ttk.Label(row2, text="Servicio:").pack(side="left")
        serv_entry = ttk.Entry(row2, textvariable=self.servicio_var, width=20)
        serv_entry.pack(side="left", padx=5)
        self.tooltip_register(serv_entry, "Describe el servicio o célula.")
        ttk.Label(row2, text="Puesto:").pack(side="left")
        puesto_entry = ttk.Entry(row2, textvariable=self.puesto_var, width=20)
        puesto_entry.pack(side="left", padx=5)
        self.tooltip_register(puesto_entry, "Define el cargo actual del colaborador.")

        row3 = ttk.Frame(self.frame)
        row3.pack(fill="x", pady=1)
        ttk.Label(row3, text="Nombre agencia:").pack(side="left")
        nombre_ag_entry = ttk.Entry(row3, textvariable=self.nombre_agencia_var, width=25)
        nombre_ag_entry.pack(side="left", padx=5)
        self.tooltip_register(nombre_ag_entry, "Especifica la agencia u oficina de trabajo.")
        ttk.Label(row3, text="Cdigo agencia:").pack(side="left")
        cod_ag_entry = ttk.Entry(row3, textvariable=self.codigo_agencia_var, width=10)
        cod_ag_entry.pack(side="left", padx=5)
        self.tooltip_register(cod_ag_entry, "Código interno de la agencia (solo números).")

        row4 = ttk.Frame(self.frame)
        row4.pack(fill="x", pady=1)
        ttk.Label(row4, text="Tipo de falta:").pack(side="left")
        falta_cb = ttk.Combobox(
            row4,
            textvariable=self.tipo_falta_var,
            values=TIPO_FALTA_LIST,
            state="readonly",
            width=20,
        )
        falta_cb.pack(side="left", padx=5)
        falta_cb.set('')
        self.tooltip_register(falta_cb, "Selecciona la falta disciplinaria tipificada.")
        ttk.Label(row4, text="Tipo de sanción:").pack(side="left")
        sanc_cb = ttk.Combobox(
            row4,
            textvariable=self.tipo_sancion_var,
            values=TIPO_SANCION_LIST,
            state="readonly",
            width=20,
        )
        sanc_cb.pack(side="left", padx=5)
        sanc_cb.set('')
        self.tooltip_register(sanc_cb, "Describe la sanción propuesta o aplicada.")

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=2)
        remove_btn = ttk.Button(btn_frame, text="Eliminar colaborador", command=self.remove)
        remove_btn.pack(side="right")
        self.tooltip_register(remove_btn, "Quita al colaborador y sus datos del caso.")

        self.validators.append(
            FieldValidator(
                id_entry,
                lambda: validate_team_member_id(self.id_var.get()),
                self.logs,
                f"Colaborador {self.idx+1} - ID",
                variables=[self.id_var],
            )
        )
        self.validators.append(
            FieldValidator(
                flag_cb,
                lambda: validate_required_text(self.flag_var.get(), "el flag del colaborador"),
                self.logs,
                f"Colaborador {self.idx+1} - Flag",
                variables=[self.flag_var],
            )
        )
        self.validators.append(
            FieldValidator(
                cod_ag_entry,
                lambda: validate_agency_code(self.codigo_agencia_var.get(), allow_blank=True),
                self.logs,
                f"Colaborador {self.idx+1} - Código agencia",
                variables=[self.codigo_agencia_var],
            )
        )
        catalog_validations = [
            (
                flag_cb,
                self.flag_var,
                FLAG_COLABORADOR_LIST,
                "el flag del colaborador",
            ),
            (
                falta_cb,
                self.tipo_falta_var,
                TIPO_FALTA_LIST,
                "el tipo de falta del colaborador",
            ),
            (
                sanc_cb,
                self.tipo_sancion_var,
                TIPO_SANCION_LIST,
                "el tipo de sanción del colaborador",
            ),
        ]
        for widget, variable, catalog, label in catalog_validations:
            self.validators.append(
                FieldValidator(
                    widget,
                    lambda v=variable, c=catalog, l=label: self._validate_catalog_selection(v.get(), l, c),
                    self.logs,
                    f"Colaborador {self.idx+1} - {label.capitalize()}",
                    variables=[variable],
                )
            )

    def set_lookup(self, lookup):
        self.team_lookup = lookup or {}
        self._last_missing_lookup_id = None

    def on_id_change(self, from_focus=False, preserve_existing=False, silent=False):
        cid = self.id_var.get().strip()
        self._notify_id_change(cid)
        if cid:
            data = self.team_lookup.get(cid)
            if data:
                def set_if_present(var, key):
                    value = data.get(key, "").strip()
                    if value and should_autofill_field(var.get(), preserve_existing):
                        var.set(value)

                set_if_present(self.division_var, "division")
                set_if_present(self.area_var, "area")
                set_if_present(self.servicio_var, "servicio")
                set_if_present(self.puesto_var, "puesto")
                set_if_present(self.nombre_agencia_var, "nombre_agencia")
                set_if_present(self.codigo_agencia_var, "codigo_agencia")
                self._last_missing_lookup_id = None
                self._log_change(f"Autopoblado colaborador {self.idx+1} desde team_details.csv")
            elif from_focus and not silent and self.team_lookup:
                log_event("validacion", f"ID de colaborador {cid} no encontrado en team_details.csv", self.logs)
                if self._last_missing_lookup_id != cid:
                    messagebox.showerror(
                        "Colaborador no encontrado",
                        (
                            f"El ID {cid} no existe en el catálogo team_details.csv. "
                            "Verifica el código o actualiza el archivo maestro."
                        ),
                    )
                    self._last_missing_lookup_id = cid
        else:
            self._last_missing_lookup_id = None
        self.update_team_options()
        self.schedule_summary_refresh('colaboradores')

    def _notify_id_change(self, new_id):
        if new_id == self._last_tracked_id:
            return
        previous = self._last_tracked_id
        self._last_tracked_id = new_id
        if callable(self.id_change_callback):
            self.id_change_callback(self, previous, new_id)

    def get_data(self):
        return {
            "id_colaborador": self.id_var.get().strip(),
            "id_caso": "",
            "flag": self.flag_var.get(),
            "division": self.division_var.get().strip(),
            "area": self.area_var.get().strip(),
            "servicio": self.servicio_var.get().strip(),
            "puesto": self.puesto_var.get().strip(),
            "nombre_agencia": self.nombre_agencia_var.get().strip(),
            "codigo_agencia": self.codigo_agencia_var.get().strip(),
            "tipo_falta": self.tipo_falta_var.get(),
            "tipo_sancion": self.tipo_sancion_var.get(),
        }

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el colaborador {self.idx+1}?"):
            self._log_change(f"Se eliminó colaborador {self.idx+1}")
            self.frame.destroy()
            self.remove_callback(self)

    def _log_change(self, message: str):
        if callable(self.change_notifier):
            self.change_notifier(message)
        else:
            log_event("navegacion", message, self.logs)

    @staticmethod
    def _validate_catalog_selection(value: str, label: str, catalog) -> str | None:
        text = (value or "").strip()
        if not text:
            return f"Debe seleccionar {label}."
        if text not in catalog:
            return f"El {label} '{text}' no está en el catálogo CM."
        return None


__all__ = ["TeamMemberFrame"]
