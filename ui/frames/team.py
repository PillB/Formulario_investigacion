"""Componentes de interfaz para colaboradores y asignaciones."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from settings import FLAG_COLABORADOR_LIST, TIPO_FALTA_LIST, TIPO_SANCION_LIST
from validators import (FieldValidator, log_event, normalize_team_member_identifier,
                        normalize_without_accents, should_autofill_field,
                        validate_agency_code, validate_date_text, validate_required_text,
                        validate_team_member_id)
from ui.frames.utils import BadgeManager, ensure_grid_support
from theme_manager import ThemeManager
from ui.config import COL_PADX, ROW_PADY
from ui.layout import CollapsibleSection


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
        owner=None,
        summary_parent=None,
        summary_refresh_callback=None,
        change_notifier=None,
        id_change_callback=None,
        autofill_service=None,
        case_date_getter=None,
    ):
        self.parent = parent
        self.owner = owner
        self.idx = idx
        self.remove_callback = remove_callback
        self.update_team_options = update_team_options
        self.team_lookup = team_lookup or {}
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
        self.summary_tree = None
        self._summary_tree_sort_state: dict[str, bool] = {}

        self.id_var = tk.StringVar()
        self.nombres_var = tk.StringVar()
        self.apellidos_var = tk.StringVar()
        self.flag_var = tk.StringVar()
        self.division_var = tk.StringVar()
        self.area_var = tk.StringVar()
        self.servicio_var = tk.StringVar()
        self.puesto_var = tk.StringVar()
        self.fecha_carta_inmediatez_var = tk.StringVar()
        self.fecha_carta_renuncia_var = tk.StringVar()
        self.nombre_agencia_var = tk.StringVar()
        self.codigo_agencia_var = tk.StringVar()
        self.tipo_falta_var = tk.StringVar()
        self.tipo_sancion_var = tk.StringVar()

        self.section = self._create_section(parent)
        self._sync_section_title()
        self._register_title_traces()
        self.section.pack(fill="x", padx=COL_PADX, pady=ROW_PADY)
        if summary_parent is not None and owner is not None and not getattr(owner, "team_summary_tree", None):
            self.summary_tree = self._build_summary(summary_parent)
            owner.team_summary_tree = self.summary_tree
            owner.inline_summary_trees["colaboradores"] = self.summary_tree
            owner._team_summary_owner = self
        else:
            self.summary_tree = getattr(owner, "team_summary_tree", None)
        self.frame = ttk.LabelFrame(self.section.content, text="")
        self.section.pack_content(self.frame, fill="x", expand=True)
        ensure_grid_support(self.frame)
        self.badges = BadgeManager(parent=self.frame)
        if hasattr(self.frame, "columnconfigure"):
            self.frame.columnconfigure(0, weight=0)
            self.frame.columnconfigure(1, weight=1)
            self.frame.columnconfigure(2, weight=1)

        ttk.Label(self.frame, text="ID del colaborador:").grid(
            row=0, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        id_entry = self._make_badged_field(
            self.frame,
            "team_id",
            lambda parent: ttk.Entry(parent, textvariable=self.id_var, width=20),
            row=0,
            column=1,
            columnspan=2,
        )
        self._bind_identifier_triggers(id_entry)
        self.tooltip_register(id_entry, "Coloca el código único del colaborador investigado.")

        ttk.Label(self.frame, text="Nombres:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        nombres_entry = ttk.Entry(self.frame, textvariable=self.nombres_var, width=25)
        nombres_entry.grid(row=1, column=1, columnspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self._bind_dirty_tracking(nombres_entry, "nombres")
        self.tooltip_register(nombres_entry, "Ingresa los nombres del colaborador.")

        ttk.Label(self.frame, text="Apellidos:").grid(
            row=2, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        apellidos_entry = ttk.Entry(self.frame, textvariable=self.apellidos_var, width=25)
        apellidos_entry.grid(row=2, column=1, columnspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self._bind_dirty_tracking(apellidos_entry, "apellidos")
        self.tooltip_register(apellidos_entry, "Ingresa los apellidos del colaborador.")

        ttk.Label(self.frame, text="Flag:").grid(
            row=3, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        flag_cb = self._make_badged_field(
            self.frame,
            "team_flag",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.flag_var,
                values=FLAG_COLABORADOR_LIST,
                state="readonly",
                width=20,
            ),
            row=3,
            column=1,
            columnspan=2,
        )
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

        ttk.Label(self.frame, text="División:").grid(
            row=4, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        div_entry = ttk.Entry(self.frame, textvariable=self.division_var, width=20)
        div_entry.grid(row=4, column=1, columnspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self._bind_dirty_tracking(div_entry, "division")
        self.tooltip_register(div_entry, "Ingresa la división o gerencia del colaborador.")
        div_entry.bind("<FocusOut>", lambda _e: self._handle_location_change(), add="+")

        ttk.Label(self.frame, text="Área:").grid(
            row=5, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        area_entry = ttk.Entry(self.frame, textvariable=self.area_var, width=20)
        area_entry.grid(row=5, column=1, columnspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self._bind_dirty_tracking(area_entry, "area")
        self.tooltip_register(area_entry, "Detalla el área específica.")
        area_entry.bind("<FocusOut>", lambda _e: self._handle_location_change(), add="+")

        ttk.Label(self.frame, text="Servicio:").grid(
            row=6, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        serv_entry = ttk.Entry(self.frame, textvariable=self.servicio_var, width=20)
        serv_entry.grid(row=6, column=1, columnspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self._bind_dirty_tracking(serv_entry, "servicio")
        self.tooltip_register(serv_entry, "Describe el servicio o célula.")

        ttk.Label(self.frame, text="Puesto:").grid(
            row=7, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        puesto_entry = ttk.Entry(self.frame, textvariable=self.puesto_var, width=20)
        puesto_entry.grid(row=7, column=1, columnspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self._bind_dirty_tracking(puesto_entry, "puesto")
        self.tooltip_register(puesto_entry, "Define el cargo actual del colaborador.")

        ttk.Label(self.frame, text="Fecha carta inmediatez:").grid(
            row=8, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        fecha_inm_entry = self._make_badged_field(
            self.frame,
            "team_fecha_inm",
            lambda parent: ttk.Entry(parent, textvariable=self.fecha_carta_inmediatez_var, width=20),
            row=8,
            column=1,
            columnspan=2,
        )
        self._bind_dirty_tracking(fecha_inm_entry, "fecha_carta_inmediatez")
        self._bind_date_validation(fecha_inm_entry, self.fecha_carta_inmediatez_var, "la fecha de carta de inmediatez")
        self.tooltip_register(
            fecha_inm_entry,
            "Registrar en formato YYYY-MM-DD. Puede quedar vacío si no aplica.",
        )

        ttk.Label(self.frame, text="Fecha carta renuncia:").grid(
            row=9, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        fecha_ren_entry = self._make_badged_field(
            self.frame,
            "team_fecha_ren",
            lambda parent: ttk.Entry(parent, textvariable=self.fecha_carta_renuncia_var, width=20),
            row=9,
            column=1,
            columnspan=2,
        )
        self._bind_dirty_tracking(fecha_ren_entry, "fecha_carta_renuncia")
        self._bind_date_validation(fecha_ren_entry, self.fecha_carta_renuncia_var, "la fecha de carta de renuncia")
        self.tooltip_register(
            fecha_ren_entry,
            "Registrar en formato YYYY-MM-DD. Puede quedar vacío si no aplica.",
        )

        ttk.Label(self.frame, text="Nombre agencia:").grid(
            row=10, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        nombre_ag_entry = self._make_badged_field(
            self.frame,
            "team_agencia_nombre",
            lambda parent: ttk.Entry(parent, textvariable=self.nombre_agencia_var, width=25),
            row=10,
            column=1,
            columnspan=2,
        )
        self._bind_dirty_tracking(nombre_ag_entry, "nombre_agencia")
        self.tooltip_register(nombre_ag_entry, "Especifica la agencia u oficina de trabajo.")

        ttk.Label(self.frame, text="Código agencia:").grid(
            row=11, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        cod_ag_entry = self._make_badged_field(
            self.frame,
            "team_agencia_codigo",
            lambda parent: ttk.Entry(parent, textvariable=self.codigo_agencia_var, width=10),
            row=11,
            column=1,
            columnspan=2,
        )
        self._bind_dirty_tracking(cod_ag_entry, "codigo_agencia")
        self.tooltip_register(cod_ag_entry, "Código interno de la agencia (solo números).")
        self._division_entry = div_entry
        self._area_entry = area_entry

        ttk.Label(self.frame, text="Tipo de falta:").grid(
            row=12, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        falta_cb = self._make_badged_field(
            self.frame,
            "team_tipo_falta",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.tipo_falta_var,
                values=TIPO_FALTA_LIST,
                state="readonly",
                width=20,
            ),
            row=12,
            column=1,
            columnspan=2,
        )
        falta_cb.set('')
        self.tooltip_register(falta_cb, "Selecciona la falta disciplinaria tipificada.")

        ttk.Label(self.frame, text="Tipo de sanción:").grid(
            row=13, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        sanc_cb = self._make_badged_field(
            self.frame,
            "team_tipo_sancion",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.tipo_sancion_var,
                values=TIPO_SANCION_LIST,
                state="readonly",
                width=20,
            ),
            row=13,
            column=1,
            columnspan=2,
        )
        sanc_cb.set('')
        self.tooltip_register(sanc_cb, "Describe la sanción propuesta o aplicada.")

        self._fallback_label.grid(
            row=14,
            column=0,
            columnspan=3,
            padx=COL_PADX,
            pady=ROW_PADY,
            sticky="we",
        )

        action_row = ttk.Frame(self.frame)
        ensure_grid_support(action_row)
        action_row.grid(row=15, column=0, columnspan=3, padx=COL_PADX, pady=ROW_PADY, sticky="ew")
        if hasattr(action_row, "columnconfigure"):
            action_row.columnconfigure(0, weight=1)
            action_row.columnconfigure(1, weight=0)
        remove_btn = ttk.Button(action_row, text="Eliminar colaborador", command=self.remove)
        remove_btn.grid(row=0, column=1, sticky="e")
        self.tooltip_register(remove_btn, "Quita al colaborador y sus datos del caso.")

        self.validators.append(
            FieldValidator(
                id_entry,
                self.badges.wrap_validation(
                    "team_id", lambda: validate_team_member_id(self.id_var.get())
                ),
                self.logs,
                f"Colaborador {self.idx+1} - ID",
                variables=[self.id_var],
            )
        )
        self.validators.append(
            FieldValidator(
                flag_cb,
                self.badges.wrap_validation(
                    "team_flag",
                    lambda: validate_required_text(
                        self.flag_var.get(), "el flag del colaborador"
                    ),
                ),
                self.logs,
                f"Colaborador {self.idx+1} - Flag",
                variables=[self.flag_var],
            )
        )
        nombre_validator = FieldValidator(
            nombre_ag_entry,
            self.badges.wrap_validation(
                "team_agencia_nombre", lambda: self._validate_agency_fields("nombre")
            ),
            self.logs,
            f"Colaborador {self.idx+1} - Nombre agencia",
            variables=[self.nombre_agencia_var],
        )
        codigo_validator = FieldValidator(
            cod_ag_entry,
            self.badges.wrap_validation(
                "team_agencia_codigo", lambda: self._validate_agency_fields("codigo")
            ),
            self.logs,
            f"Colaborador {self.idx+1} - Código agencia",
            variables=[self.codigo_agencia_var],
        )
        self.validators.extend([nombre_validator, codigo_validator])
        self._agency_validators.extend([nombre_validator, codigo_validator])
        for widget, label, var, badge_key in [
            (
                fecha_inm_entry,
                "la fecha de carta de inmediatez",
                self.fecha_carta_inmediatez_var,
                "team_fecha_inm",
            ),
            (
                fecha_ren_entry,
                "la fecha de carta de renuncia",
                self.fecha_carta_renuncia_var,
                "team_fecha_ren",
            ),
        ]:
            self.validators.append(
                FieldValidator(
                    widget,
                    self.badges.wrap_validation(
                        badge_key, lambda v=var, l=label: self._validate_date_field(v, l)
                    ),
                    self.logs,
                    f"Colaborador {self.idx+1} - {label}",
                    variables=[var],
                )
            )
        catalog_validations = [
            (
                flag_cb,
                self.flag_var,
                FLAG_COLABORADOR_LIST,
                "el flag del colaborador",
                "team_flag",
            ),
            (
                falta_cb,
                self.tipo_falta_var,
                TIPO_FALTA_LIST,
                "el tipo de falta del colaborador",
                "team_tipo_falta",
            ),
            (
                sanc_cb,
                self.tipo_sancion_var,
                TIPO_SANCION_LIST,
                "el tipo de sanción del colaborador",
                "team_tipo_sancion",
            ),
        ]
        for widget, variable, catalog, label, badge_key in catalog_validations:
            self.validators.append(
                FieldValidator(
                    widget,
                    self.badges.wrap_validation(
                        badge_key,
                        lambda v=variable, c=catalog, l=label: self._validate_catalog_selection(v.get(), l, c),
                    ),
                    self.logs,
                    f"Colaborador {self.idx+1} - {label.capitalize()}",
                    variables=[variable],
                )
            )

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

    def _create_section(self, parent):
        try:
            return CollapsibleSection(
                parent, title="", on_toggle=lambda _section: self._sync_section_title()
            )
        except Exception as exc:
            log_event(
                "validacion",
                f"No se pudo crear sección colapsable para colaborador {self.idx+1}: {exc}",
                self.logs,
            )
            fallback = ttk.Frame(parent)
            ensure_grid_support(fallback)
            fallback.content = ttk.Frame(fallback)
            fallback.is_open = True  # type: ignore[attr-defined]
            fallback.set_title = lambda _title: None  # type: ignore[attr-defined]

            def _pack_content(widget, **pack_kwargs):
                defaults = {"fill": "both", "expand": True}
                defaults.update(pack_kwargs)
                widget.pack(**defaults)
                return widget

            fallback.pack_content = _pack_content  # type: ignore[attr-defined]
            return fallback

    def _register_title_traces(self):
        for var in (self.id_var, self.nombres_var, self.apellidos_var):
            var.trace_add("write", self._on_identity_field_change)

    def _build_section_title(self) -> str:
        base_title = f"Colaborador {self.idx+1}"
        if getattr(self, "section", None) and not getattr(self.section, "is_open", True):
            id_value = self.id_var.get().strip()
            name_value = " ".join(
                part.strip()
                for part in (self.nombres_var.get(), self.apellidos_var.get())
                if part.strip()
            )
            details = [value for value in (id_value, name_value) if value]
            if details:
                base_title = f"{base_title} – {' | '.join(details)}"
        return base_title

    def _sync_section_title(self, *_args):
        if not getattr(self, "section", None):
            return
        self.section.set_title(self._build_section_title())

    def _on_identity_field_change(self, *_args):
        self._sync_section_title()

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

    def _bind_date_validation(self, widget, variable: tk.StringVar, label: str) -> None:
        widget.bind(
            "<FocusOut>",
            lambda _e, v=variable, l=label: self._validate_date_field(v, l, show_alert=True),
            add="+",
        )

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
            "nombres": self.nombres_var.get(),
            "apellidos": self.apellidos_var.get(),
            "fecha_carta_inmediatez": self.fecha_carta_inmediatez_var.get(),
            "fecha_carta_renuncia": self.fecha_carta_renuncia_var.get(),
            "nombre_agencia": self.nombre_agencia_var.get(),
            "codigo_agencia": self.codigo_agencia_var.get(),
        }

    def _clear_fallback_warning(self) -> None:
        self._fallback_message_var.set("")
        exists_fn = getattr(self._fallback_label, "winfo_exists", None)
        try:
            label_exists = exists_fn() if callable(exists_fn) else True
        except tk.TclError as exc:
            log_event(
                "validacion",
                f"Error verificando existencia de etiqueta de fallback: {exc}",
                self.logs,
            )
            label_exists = False
        if not label_exists:
            log_event(
                "validacion",
                "No se pudo ocultar advertencia: la etiqueta de fallback no existe",
                self.logs,
            )
            return
        try:
            if self._fallback_label.winfo_ismapped():
                manager = getattr(self._fallback_label, "winfo_manager", lambda: "")()
                if manager == "grid" and hasattr(self._fallback_label, "grid_remove"):
                    self._fallback_label.grid_remove()
                elif manager == "pack" and hasattr(self._fallback_label, "pack_forget"):
                    self._fallback_label.pack_forget()
                elif hasattr(self._fallback_label, "pack_forget"):
                    self._fallback_label.pack_forget()
                elif hasattr(self._fallback_label, "grid_remove"):
                    self._fallback_label.grid_remove()
                else:
                    log_event(
                        "validacion",
                        "No se pudo ocultar advertencia: no hay método para desacoplar la etiqueta",
                        self.logs,
                    )
        except tk.TclError as exc:
            log_event(
                "validacion",
                f"Error al ocultar advertencia de fallback: {exc}",
                self.logs,
            )

    def _set_fallback_warning(self, message: str | None) -> None:
        if not message:
            self._clear_fallback_warning()
            return
        self._fallback_message_var.set(message)
        exists_fn = getattr(self._fallback_label, "winfo_exists", None)
        try:
            label_exists = exists_fn() if callable(exists_fn) else True
        except tk.TclError as exc:
            log_event(
                "validacion",
                f"Error verificando existencia de etiqueta de fallback: {exc}",
                self.logs,
            )
            label_exists = False
        if not label_exists:
            log_event(
                "validacion",
                "No se pudo mostrar advertencia: la etiqueta de fallback no existe",
                self.logs,
            )
            return
        try:
            if not self._fallback_label.winfo_ismapped():
                manager = getattr(self._fallback_label, "winfo_manager", lambda: "")()
                if manager == "grid" and hasattr(self._fallback_label, "grid"):
                    self._fallback_label.grid()
                elif manager == "pack" and hasattr(self._fallback_label, "pack"):
                    self._fallback_label.pack(fill="x", padx=COL_PADX, pady=(0, ROW_PADY // 2))
                elif hasattr(self._fallback_label, "pack"):
                    self._fallback_label.pack(fill="x", padx=COL_PADX, pady=(0, ROW_PADY // 2))
                elif hasattr(self._fallback_label, "grid"):
                    self._fallback_label.grid()
        except tk.TclError as exc:
            log_event(
                "validacion",
                f"Error al mostrar advertencia de fallback: {exc}",
                self.logs,
            )

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
            "nombres": self.nombres_var,
            "apellidos": self.apellidos_var,
            "fecha_carta_inmediatez": self.fecha_carta_inmediatez_var,
            "fecha_carta_renuncia": self.fecha_carta_renuncia_var,
            "nombre_agencia": self.nombre_agencia_var,
            "codigo_agencia": self.codigo_agencia_var,
        }
        for key, value in result.applied.items():
            var = field_map.get(key)
            if var is not None:
                var.set(value)

    def set_lookup(self, lookup):
        self.team_lookup = lookup or {}
        self._last_missing_lookup_id = None

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
                    set_if_present(self.nombres_var, "nombres")
                    set_if_present(self.apellidos_var, "apellidos")
                    set_if_present(self.fecha_carta_inmediatez_var, "fecha_carta_inmediatez")
                    set_if_present(self.fecha_carta_renuncia_var, "fecha_carta_renuncia")
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

    @staticmethod
    def _validate_date_field(var: tk.StringVar, label: str, show_alert: bool = False) -> str | None:
        message = validate_date_text(
            var.get(), label, allow_blank=True, enforce_max_today=True
        )
        if show_alert and message:
            try:
                messagebox.showerror("Fecha inválida", message)
            except tk.TclError:
                pass
        return message

    # ------------------------------------------------------------------
    # Resumen de colaboradores
    # ------------------------------------------------------------------
    def _build_summary(self, container):
        summary_frame = ttk.Frame(container)
        ensure_grid_support(summary_frame)
        if hasattr(summary_frame, "columnconfigure"):
            summary_frame.columnconfigure(0, weight=1)

        columns = (
            ("id", "ID"),
            ("nombres", "Nombres"),
            ("apellidos", "Apellidos"),
            ("division", "División"),
            ("area", "Área"),
            ("servicio", "Servicio"),
            ("puesto", "Puesto"),
            ("tipo_sancion", "Tipo sanción"),
            ("fecha_carta_inmediatez", "Carta inmediatez"),
            ("fecha_carta_renuncia", "Carta renuncia"),
        )
        tree = ttk.Treeview(summary_frame, columns=[col for col, _ in columns], show="headings", height=5)
        vscroll = ttk.Scrollbar(summary_frame, orient="vertical", command=tree.yview)
        hscroll = ttk.Scrollbar(summary_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=COL_PADX, pady=(ROW_PADY, ROW_PADY // 2))
        vscroll.grid(row=0, column=1, sticky="ns", pady=(ROW_PADY, ROW_PADY // 2))
        hscroll.grid(row=1, column=0, sticky="ew")

        for col_id, heading in columns:
            tree.heading(col_id, text=heading, command=lambda c=col_id: self._sort_summary(c))
            tree.column(col_id, width=150, anchor="w")

        palette = ThemeManager.current()
        if hasattr(tree, "tag_configure"):
            tree.tag_configure("even", background=palette.get("heading_background", palette.get("background")), foreground=palette.get("foreground"))
            tree.tag_configure("odd", background=palette.get("background"), foreground=palette.get("foreground"))

        tree.bind("<<TreeviewSelect>>", self._on_summary_select)
        tree.bind("<Double-1>", self._on_summary_double_click)
        summary_frame.pack(fill="both", expand=True)
        return tree

    def refresh_summary(self):
        tree = self.summary_tree or getattr(self.owner, "team_summary_tree", None)
        if not tree or not hasattr(tree, "get_children"):
            return
        try:
            existing_rows = tree.get_children()
            if existing_rows:
                tree.delete(*existing_rows)
        except Exception as exc:
            log_event("validacion", f"No se pudo limpiar el resumen de colaboradores: {exc}", self.logs)
            return
        team_frames = getattr(self.owner, "team_frames", []) if self.owner else []

        def build_unique_iid(base: str, used: set[str]) -> str:
            normalized = (base or "").strip() or "colaborador"
            candidate = normalized
            suffix = 1
            while candidate in used:
                candidate = f"{normalized}-{suffix}"
                suffix += 1
            return candidate

        seen_iids: set[str] = set()
        inserted_count = 0
        for idx, member in enumerate(team_frames):
            data = member.get_data()
            values = (
                data.get("id_colaborador", ""),
                data.get("nombres", ""),
                data.get("apellidos", ""),
                data.get("division", ""),
                data.get("area", ""),
                data.get("servicio", ""),
                data.get("puesto", ""),
                data.get("tipo_sancion", ""),
                data.get("fecha_carta_inmediatez", ""),
                data.get("fecha_carta_renuncia", ""),
            )
            base_iid = data.get("id_colaborador", f"colaborador-{idx+1}")
            iid = build_unique_iid(base_iid, seen_iids)
            tag = "even" if inserted_count % 2 == 0 else "odd"
            try:
                tree.insert("", "end", iid=iid, values=values, tags=(tag,))
                seen_iids.add(iid)
                inserted_count += 1
            except Exception as exc:
                log_event("validacion", f"IID duplicado o inválido '{iid}' para colaborador: {exc}", self.logs)
                retry_iid = build_unique_iid(base_iid, seen_iids | {iid})
                try:
                    tree.insert("", "end", iid=retry_iid, values=values, tags=(tag,))
                    seen_iids.add(retry_iid)
                    inserted_count += 1
                    log_event("validacion", f"Reintento exitoso con IID '{retry_iid}'", self.logs)
                except Exception as retry_exc:
                    log_event("validacion", f"Omitido colaborador con IID '{iid}': {retry_exc}", self.logs)
        self._apply_summary_theme(tree)
        self._on_summary_select()

    def _sort_summary(self, column):
        tree = self.summary_tree or getattr(self.owner, "team_summary_tree", None)
        if not tree or not hasattr(tree, "get_children"):
            return
        reverse = self._summary_tree_sort_state.get(column, False)
        items = list(tree.get_children(""))
        col_index = tree["columns"].index(column)
        items.sort(key=lambda item: tree.item(item, "values")[col_index], reverse=reverse)
        for idx, item in enumerate(items):
            tree.move(item, "", idx)
            tag = "even" if idx % 2 == 0 else "odd"
            tree.item(item, tags=(tag,))
        self._summary_tree_sort_state[column] = not reverse

    def _on_summary_select(self, _event=None):
        tree = self.summary_tree or getattr(self.owner, "team_summary_tree", None)
        if not tree or not hasattr(tree, "selection"):
            return
        if callable(getattr(self.owner, "_on_team_selected", None)):
            try:
                self.owner._on_team_selected()
            except Exception:
                pass

    def _on_summary_double_click(self, _event=None):
        self._on_summary_select()
        if callable(getattr(self.owner, "_edit_selected_team_member", None)):
            try:
                self.owner._edit_selected_team_member()
            except Exception:
                pass

    def _apply_summary_theme(self, tree):
        palette = ThemeManager.current()
        if hasattr(tree, "tag_configure"):
            tree.tag_configure("even", background=palette.get("heading_background", palette.get("background")), foreground=palette.get("foreground"))
            tree.tag_configure("odd", background=palette.get("background"), foreground=palette.get("foreground"))

    def get_data(self):
        normalized_id = normalize_team_member_identifier(self.id_var.get())
        if normalized_id != self.id_var.get():
            self.id_var.set(normalized_id)
        return {
            "id_colaborador": normalized_id,
            "id_caso": "",
            "flag": self.flag_var.get(),
            "nombres": self.nombres_var.get().strip(),
            "apellidos": self.apellidos_var.get().strip(),
            "division": self.division_var.get().strip(),
            "area": self.area_var.get().strip(),
            "servicio": self.servicio_var.get().strip(),
            "puesto": self.puesto_var.get().strip(),
            "fecha_carta_inmediatez": self.fecha_carta_inmediatez_var.get().strip(),
            "fecha_carta_renuncia": self.fecha_carta_renuncia_var.get().strip(),
            "nombre_agencia": self.nombre_agencia_var.get().strip(),
            "codigo_agencia": self.codigo_agencia_var.get().strip(),
            "tipo_falta": self.tipo_falta_var.get(),
            "tipo_sancion": self.tipo_sancion_var.get(),
        }

    def clear_values(self):
        """Vacía los valores sin eliminar el contenedor del colaborador."""

        def _reset():
            for var in (
                self.id_var,
                self.nombres_var,
                self.apellidos_var,
                self.flag_var,
                self.division_var,
                self.area_var,
                self.servicio_var,
                self.puesto_var,
                self.fecha_carta_inmediatez_var,
                self.fecha_carta_renuncia_var,
                self.nombre_agencia_var,
                self.codigo_agencia_var,
                self.tipo_falta_var,
                self.tipo_sancion_var,
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

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el colaborador {self.idx+1}?"):
            self._log_change(f"Se eliminó colaborador {self.idx+1}")
            self.section.destroy()
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
