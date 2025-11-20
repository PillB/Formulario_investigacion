"""Componentes de interfaz para colaboradores y asignaciones."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from settings import FLAG_COLABORADOR_LIST, TIPO_FALTA_LIST, TIPO_SANCION_LIST
from validators import (FieldValidator, log_event, normalize_team_member_identifier,
                        normalize_without_accents, should_autofill_field,
                        validate_agency_code, validate_required_text,
                        validate_team_member_id)
from ui.config import COL_PADX, ROW_PADY


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
        autofill_service=None,
        case_date_getter=None,
    ):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.update_team_options = update_team_options
        self.team_lookup = self._normalize_lookup(team_lookup)
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self._agency_validators: list[FieldValidator] = []
        self._dirty_fields: dict[str, bool] = {}
        self._last_missing_lookup_id = None
        self.schedule_summary_refresh = summary_refresh_callback or (lambda _sections=None: None)
        self.change_notifier = change_notifier
        self.id_change_callback = id_change_callback
        self._last_tracked_id = ''
        self.autofill_service = autofill_service
        self.case_date_getter = case_date_getter
        self._future_snapshot_warnings: set[str] = set()
        self._fallback_message_var = tk.StringVar(value="")

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
        self.frame.pack(fill="x", padx=COL_PADX, pady=ROW_PADY)

        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=ROW_PADY // 2)
        ttk.Label(row1, text="ID del colaborador:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=COL_PADX)
        self._bind_identifier_triggers(id_entry)
        self.tooltip_register(id_entry, "Coloca el código único del colaborador investigado.")
        ttk.Label(row1, text="Flag:").pack(side="left")
        flag_cb = ttk.Combobox(
            row1,
            textvariable=self.flag_var,
            values=FLAG_COLABORADOR_LIST,
            state="readonly",
            width=20,
        )
        flag_cb.pack(side="left", padx=COL_PADX)
        flag_cb.set('')
        self.tooltip_register(flag_cb, "Define el rol del colaborador en el caso.")
        flag_cb.bind("<FocusOut>", lambda e: self._log_change(f"Colaborador {self.idx+1}: modificó flag"))

        self._fallback_label = tk.Label(
            self.frame,
            textvariable=self._fallback_message_var,
            background="#fff3cd",
            foreground="#664d03",
            anchor="w",
            justify="left",
            wraplength=520,
            relief="groove",
            padx=6,
            pady=3,
        )

        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=ROW_PADY // 2)
        ttk.Label(row2, text="División:").pack(side="left")
        div_entry = ttk.Entry(row2, textvariable=self.division_var, width=20)
        div_entry.pack(side="left", padx=COL_PADX)
        self._bind_dirty_tracking(div_entry, "division")
        self.tooltip_register(div_entry, "Ingresa la división o gerencia del colaborador.")
        div_entry.bind("<FocusOut>", lambda _e: self._handle_location_change(), add="+")
        ttk.Label(row2, text="Área:").pack(side="left")
        area_entry = ttk.Entry(row2, textvariable=self.area_var, width=20)
        area_entry.pack(side="left", padx=COL_PADX)
        self._bind_dirty_tracking(area_entry, "area")
        self.tooltip_register(area_entry, "Detalla el área específica.")
        area_entry.bind("<FocusOut>", lambda _e: self._handle_location_change(), add="+")
        ttk.Label(row2, text="Servicio:").pack(side="left")
        serv_entry = ttk.Entry(row2, textvariable=self.servicio_var, width=20)
        serv_entry.pack(side="left", padx=COL_PADX)
        self._bind_dirty_tracking(serv_entry, "servicio")
        self.tooltip_register(serv_entry, "Describe el servicio o célula.")
        ttk.Label(row2, text="Puesto:").pack(side="left")
        puesto_entry = ttk.Entry(row2, textvariable=self.puesto_var, width=20)
        puesto_entry.pack(side="left", padx=COL_PADX)
        self._bind_dirty_tracking(puesto_entry, "puesto")
        self.tooltip_register(puesto_entry, "Define el cargo actual del colaborador.")

        row3 = ttk.Frame(self.frame)
        row3.pack(fill="x", pady=ROW_PADY // 2)
        ttk.Label(row3, text="Nombre agencia:").pack(side="left")
        nombre_ag_entry = ttk.Entry(row3, textvariable=self.nombre_agencia_var, width=25)
        nombre_ag_entry.pack(side="left", padx=COL_PADX)
        self._bind_dirty_tracking(nombre_ag_entry, "nombre_agencia")
        self.tooltip_register(nombre_ag_entry, "Especifica la agencia u oficina de trabajo.")
        ttk.Label(row3, text="Código agencia:").pack(side="left")
        cod_ag_entry = ttk.Entry(row3, textvariable=self.codigo_agencia_var, width=10)
        cod_ag_entry.pack(side="left", padx=COL_PADX)
        self._bind_dirty_tracking(cod_ag_entry, "codigo_agencia")
        self.tooltip_register(cod_ag_entry, "Código interno de la agencia (solo números).")
        self._division_entry = div_entry
        self._area_entry = area_entry

        row4 = ttk.Frame(self.frame)
        row4.pack(fill="x", pady=ROW_PADY // 2)
        ttk.Label(row4, text="Tipo de falta:").pack(side="left")
        falta_cb = ttk.Combobox(
            row4,
            textvariable=self.tipo_falta_var,
            values=TIPO_FALTA_LIST,
            state="readonly",
            width=20,
        )
        falta_cb.pack(side="left", padx=COL_PADX)
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
        sanc_cb.pack(side="left", padx=COL_PADX)
        sanc_cb.set('')
        self.tooltip_register(sanc_cb, "Describe la sanción propuesta o aplicada.")

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=ROW_PADY)
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
        nombre_validator = FieldValidator(
            nombre_ag_entry,
            lambda: self._validate_agency_fields("nombre"),
            self.logs,
            f"Colaborador {self.idx+1} - Nombre agencia",
            variables=[self.nombre_agencia_var],
        )
        codigo_validator = FieldValidator(
            cod_ag_entry,
            lambda: self._validate_agency_fields("codigo"),
            self.logs,
            f"Colaborador {self.idx+1} - Código agencia",
            variables=[self.codigo_agencia_var],
        )
        self.validators.extend([nombre_validator, codigo_validator])
        self._agency_validators.extend([nombre_validator, codigo_validator])
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

    def _bind_identifier_triggers(self, widget) -> None:
        widget.bind("<FocusOut>", lambda _e: self.on_id_change(from_focus=True), add="+")
        widget.bind("<Return>", lambda _e: self.on_id_change(from_focus=True), add="+")
        widget.bind("<KeyRelease>", lambda _e: self.on_id_change(), add="+")
        widget.bind("<<Paste>>", lambda _e: self.on_id_change(), add="+")
        widget.bind("<<ComboboxSelected>>", lambda _e: self.on_id_change(from_focus=True), add="+")

    def _bind_dirty_tracking(self, widget, field_key: str) -> None:
        widget.bind("<KeyRelease>", lambda _e: self._mark_dirty(field_key), add="+")
        widget.bind("<<Paste>>", lambda _e: self._mark_dirty(field_key), add="+")
        widget.bind("<<ComboboxSelected>>", lambda _e: self._mark_dirty(field_key), add="+")

    def _mark_dirty(self, field_key: str) -> None:
        self._clear_fallback_warning()
        if field_key:
            self._dirty_fields[field_key] = True

    def _collect_current_values(self) -> dict[str, str]:
        return {
            "division": self.division_var.get(),
            "area": self.area_var.get(),
            "servicio": self.servicio_var.get(),
            "puesto": self.puesto_var.get(),
            "nombre_agencia": self.nombre_agencia_var.get(),
            "codigo_agencia": self.codigo_agencia_var.get(),
        }

    def _clear_fallback_warning(self) -> None:
        self._fallback_message_var.set("")
        try:
            if self._fallback_label.winfo_ismapped():
                self._fallback_label.pack_forget()
        except tk.TclError:
            pass

    def _set_fallback_warning(self, message: str | None) -> None:
        if not message:
            self._clear_fallback_warning()
            return
        self._fallback_message_var.set(message)
        try:
            if not self._fallback_label.winfo_ismapped():
                self._fallback_label.pack(fill="x", padx=COL_PADX, pady=(0, ROW_PADY // 2))
        except tk.TclError:
            pass

    @staticmethod
    def _build_fallback_warning(reason: str | None) -> str | None:
        if reason == "no_past_snapshot":
            return (
                "La fecha de ocurrencia es anterior a la última actualización del colaborador; "
                "se usará el registro disponible más reciente."
            )
        if reason == "case_date_missing_or_invalid":
            return (
                "No se pudo interpretar la fecha de ocurrencia; se usará el registro más reciente "
                "disponible del colaborador."
            )
        if reason:
            return f"Se usó un registro alternativo del colaborador ({reason})."
        return None

    def _apply_autofill_result(self, result) -> None:
        field_map = {
            "division": self.division_var,
            "area": self.area_var,
            "servicio": self.servicio_var,
            "puesto": self.puesto_var,
            "nombre_agencia": self.nombre_agencia_var,
            "codigo_agencia": self.codigo_agencia_var,
        }
        for key, value in result.applied.items():
            var = field_map.get(key)
            if var is not None:
                var.set(value)

    def set_lookup(self, lookup):
        self.team_lookup = self._normalize_lookup(lookup)
        self._last_missing_lookup_id = None

    def _normalize_lookup(self, lookup):
        normalized = {}
        for key, value in (lookup or {}).items():
            normalized_key = normalize_team_member_identifier(key)
            if normalized_key:
                normalized[normalized_key] = value
        return normalized

    def _requires_agency_details(self) -> bool:
        division_norm = normalize_without_accents(self.division_var.get()).lower()
        area_norm = normalize_without_accents(self.area_var.get()).lower()
        return (
            ('dca' in division_norm or 'canales de atencion' in division_norm)
            and ('area comercial' in area_norm)
        )

    def _validate_agency_fields(self, field: str) -> str | None:
        requires_agency = self._requires_agency_details()
        if field == "nombre":
            if not requires_agency:
                return None
            return validate_required_text(
                self.nombre_agencia_var.get(),
                "el nombre de la agencia",
            )
        if field == "codigo":
            return validate_agency_code(
                self.codigo_agencia_var.get(),
                allow_blank=not requires_agency,
            )
        return None

    def _handle_location_change(self) -> None:
        if not self._agency_validators:
            return
        for validator in self._agency_validators:
            validator.show_custom_error(validator.validate_callback())

    def on_id_change(self, from_focus=False, preserve_existing=False, silent=False):
        normalized_id = normalize_team_member_identifier(self.id_var.get())
        if normalized_id != self.id_var.get():
            self.id_var.set(normalized_id)
        cid = normalized_id
        self._notify_id_change(cid)
        self._clear_fallback_warning()
        if cid:
            result = None
            if self.autofill_service:
                case_date = self.case_date_getter() if callable(self.case_date_getter) else None
                result = self.autofill_service.lookup_team_autofill(
                    cid,
                    current_values=self._collect_current_values(),
                    dirty_fields=self._dirty_fields,
                    preserve_existing=preserve_existing,
                    case_date=case_date,
                )
                if result.found:
                    if result.applied:
                        self._apply_autofill_result(result)
                        if not silent:
                            self._log_change(
                                f"Autopoblado colaborador {self.idx+1} desde team_details.csv"
                            )
                    if getattr(result, "meta", {}).get("fallback_used"):
                        warning_message = self._build_fallback_warning(
                            getattr(result, "meta", {}).get("reason")
                        )
                        self._set_fallback_warning(warning_message)
                        if result.used_future_snapshot:
                            self._warn_future_snapshot(cid, warning_message)
                    else:
                        self._clear_fallback_warning()
                    self._last_missing_lookup_id = None
            if not result or not result.found:
                data = self.team_lookup.get(cid)
                if data:
                    def set_if_present(var, key):
                        value = data.get(key, "").strip()
                        if self._dirty_fields.get(key):
                            return
                        if value and should_autofill_field(var.get(), preserve_existing):
                            var.set(value)

                    set_if_present(self.division_var, "division")
                    set_if_present(self.area_var, "area")
                    set_if_present(self.servicio_var, "servicio")
                    set_if_present(self.puesto_var, "puesto")
                    set_if_present(self.nombre_agencia_var, "nombre_agencia")
                    set_if_present(self.codigo_agencia_var, "codigo_agencia")
                    self._last_missing_lookup_id = None
                    if not silent:
                        self._log_change(
                            f"Autopoblado colaborador {self.idx+1} desde team_details.csv"
                        )
                elif from_focus and not silent and (self.team_lookup or self.autofill_service):
                    self._show_missing_catalog_error(cid)
        else:
            self._last_missing_lookup_id = None
        self.update_team_options()
        self.schedule_summary_refresh('colaboradores')

    def _show_missing_catalog_error(self, cid: str) -> None:
        log_event("validacion", f"ID de colaborador {cid} no encontrado en team_details.csv", self.logs)
        if self._last_missing_lookup_id == cid:
            return
        try:
            messagebox.showerror(
                "Colaborador no encontrado",
                (
                    f"El ID {cid} no existe en el catálogo team_details.csv. "
                    "Verifica el código o actualiza el archivo maestro."
                ),
            )
        except tk.TclError:
            pass
        self._last_missing_lookup_id = cid

    def _notify_id_change(self, new_id):
        if new_id == self._last_tracked_id:
            return
        previous = self._last_tracked_id
        self._last_tracked_id = new_id
        self._dirty_fields.clear()
        self._clear_fallback_warning()
        if callable(self.id_change_callback):
            self.id_change_callback(self, previous, new_id)

    def _warn_future_snapshot(self, cid: str, message: str | None = None) -> None:
        cid = cid or ""
        if cid in self._future_snapshot_warnings:
            return
        self._future_snapshot_warnings.add(cid)
        message = message or (
            "La fecha de ocurrencia es anterior a la última actualización del colaborador; "
            "se usará el registro disponible más reciente."
        )
        try:
            messagebox.showwarning("Colaborador con datos futuros", message)
        except tk.TclError:
            pass
        log_event("validacion", message, self.logs)

    def get_data(self):
        normalized_id = normalize_team_member_identifier(self.id_var.get())
        if normalized_id != self.id_var.get():
            self.id_var.set(normalized_id)
        return {
            "id_colaborador": normalized_id,
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
