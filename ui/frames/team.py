"""Componentes de interfaz para colaboradores y asignaciones."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from models import TeamHierarchyCatalog
from models.static_team_catalog import AGENCY_CATALOG, build_team_catalog_rows
from settings import FLAG_COLABORADOR_LIST, TIPO_FALTA_LIST, TIPO_SANCION_LIST
from validators import (FieldValidator, log_event, normalize_team_member_identifier,
                        normalize_without_accents, should_autofill_field,
                        validate_agency_code, validate_date_text, validate_required_text,
                        validate_team_member_id)
from ui.frames.utils import (
    BadgeManager,
    SectionToggleMixin,
    ToggleWarningBadge,
    build_summary_tree,
    compose_section_title,
    build_grid_container,
    create_collapsible_card,
    create_date_entry,
    ensure_grid_support,
    generate_section_id,
    grid_section,
)
from theme_manager import ThemeManager
from ui.config import COL_PADX, ROW_PADY
from ui.layout import CollapsibleSection


class TeamMemberFrame(SectionToggleMixin):
    """Representa un colaborador y su interfaz en la sección de colaboradores."""

    ENTITY_LABEL = "colaborador"
    MIN_TEXT_ENTRY_WIDTH = 11

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
        team_catalog: TeamHierarchyCatalog | None = None,
    ):
        SectionToggleMixin.__init__(self)
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
        self._focus_widgets: set[object] = set()
        self._focus_binding_target = None
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
        self.team_catalog = team_catalog or TeamHierarchyCatalog(build_team_catalog_rows())
        self._selection_error_cache: set[str] = set()
        self._area_option_map: dict[str, str] = {}
        self._service_option_map: dict[str, str] = {}
        self._agency_lookup: dict[str, tuple[str, str]] = self._build_agency_lookup()
        self._agency_sync_in_progress = False
        self.section_id = generate_section_id("colaborador")

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
        self._division_combo = None
        self._area_combo = None
        self._servicio_combo = None
        self._puesto_combo = None
        self._agencia_nombre_combo = None
        self._agencia_codigo_combo = None

        self.section = self._create_section(parent)
        self.register_section_toggle(
            self.section_id,
            section=self.section,
            header=getattr(self.section, "header", None),
            content=getattr(self.section, "content", None),
            indicator=getattr(self.section, "indicator", None),
            collapsed=not getattr(self.section, "is_open", True),
        )
        self.section_title_var = getattr(self.section, "title_var", tk.StringVar())
        self._sync_section_title()
        self._register_title_traces()
        self._place_section()
        self._install_focus_binding()
        if summary_parent is not None and owner is not None and not getattr(owner, "team_summary_tree", None):
            self.summary_tree = self._build_summary(summary_parent)
            owner.team_summary_tree = self.summary_tree
            owner.inline_summary_trees["colaboradores"] = self.summary_tree
            owner._team_summary_owner = self
        else:
            self.summary_tree = getattr(owner, "team_summary_tree", None)
        self._set_as_summary_target()
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
            lambda parent: ttk.Entry(
                parent, textvariable=self.id_var, width=self._entry_width(20)
            ),
            row=0,
            column=1,
            columnspan=2,
        )
        self.id_entry = id_entry
        self._bind_identifier_triggers(id_entry)
        self.tooltip_register(id_entry, "Coloca el código único del colaborador investigado.")
        self._register_focusable_widgets(id_entry)

        ttk.Label(self.frame, text="Nombres:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        nombres_entry = self._make_badged_field(
            self.frame,
            "team_nombres",
            lambda parent: ttk.Entry(
                parent, textvariable=self.nombres_var, width=self._entry_width(25)
            ),
            row=1,
            column=1,
            columnspan=2,
        )
        self._bind_dirty_tracking(nombres_entry, "nombres")
        self.tooltip_register(nombres_entry, "Ingresa los nombres del colaborador.")
        self._register_focusable_widgets(nombres_entry)

        ttk.Label(self.frame, text="Apellidos:").grid(
            row=2, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        apellidos_entry = self._make_badged_field(
            self.frame,
            "team_apellidos",
            lambda parent: ttk.Entry(
                parent, textvariable=self.apellidos_var, width=self._entry_width(25)
            ),
            row=2,
            column=1,
            columnspan=2,
        )
        self._bind_dirty_tracking(apellidos_entry, "apellidos")
        self.tooltip_register(apellidos_entry, "Ingresa los apellidos del colaborador.")
        self._register_focusable_widgets(apellidos_entry)

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
        self._register_focusable_widgets(flag_cb)

        self._fallback_label = ToggleWarningBadge(
            self.frame,
            textvariable=self._fallback_message_var,
            tk_module=tk,
            ttk_module=ttk,
        )

        ttk.Label(self.frame, text="División:").grid(
            row=4, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        div_cb = self._make_badged_field(
            self.frame,
            "team_division",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.division_var,
                width=self._entry_width(20),
            ),
            row=4,
            column=1,
            columnspan=2,
        )
        self._division_combo = div_cb
        self._bind_dirty_tracking(div_cb, "division")
        self.tooltip_register(div_cb, "Ingresa la división o gerencia del colaborador.")
        for sequence in ("<FocusOut>", "<<ComboboxSelected>>", "<KeyRelease>"):
            div_cb.bind(sequence, lambda _e=None: self._on_division_change(), add="+")
        self._register_focusable_widgets(div_cb)

        ttk.Label(self.frame, text="Área:").grid(
            row=5, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        area_cb = self._make_badged_field(
            self.frame,
            "team_area",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.area_var,
                width=self._entry_width(20),
            ),
            row=5,
            column=1,
            columnspan=2,
        )
        self._area_combo = area_cb
        self._bind_dirty_tracking(area_cb, "area")
        self.tooltip_register(area_cb, "Detalla el área específica.")
        for sequence in ("<FocusOut>", "<<ComboboxSelected>>", "<KeyRelease>"):
            area_cb.bind(sequence, lambda _e=None: self._on_area_change(), add="+")

        ttk.Label(self.frame, text="Servicio:").grid(
            row=6, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        serv_cb = self._make_badged_field(
            self.frame,
            "team_servicio",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.servicio_var,
                width=self._entry_width(20),
            ),
            row=6,
            column=1,
            columnspan=2,
        )
        self._servicio_combo = serv_cb
        self._bind_dirty_tracking(serv_cb, "servicio")
        self.tooltip_register(serv_cb, "Describe el servicio o célula.")
        for sequence in ("<FocusOut>", "<<ComboboxSelected>>", "<KeyRelease>"):
            serv_cb.bind(sequence, lambda _e=None: self._on_service_change(), add="+")

        ttk.Label(self.frame, text="Puesto:").grid(
            row=7, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        puesto_cb = self._make_badged_field(
            self.frame,
            "team_puesto",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.puesto_var,
                width=self._entry_width(20),
            ),
            row=7,
            column=1,
            columnspan=2,
        )
        self._puesto_combo = puesto_cb
        self._bind_dirty_tracking(puesto_cb, "puesto")
        self.tooltip_register(puesto_cb, "Define el cargo actual del colaborador.")
        for sequence in ("<FocusOut>", "<<ComboboxSelected>>", "<KeyRelease>"):
            puesto_cb.bind(sequence, lambda _e=None: self._on_puesto_change(), add="+")

        ttk.Label(self.frame, text="Fecha carta inmediatez:\n(YYYY-MM-DD)").grid(
            row=8,
            column=0,
            padx=COL_PADX,
            pady=(ROW_PADY // 2, ROW_PADY // 2),
            sticky="e",
        )
        fecha_inm_entry = self._make_badged_field(
            self.frame,
            "team_fecha_inm",
            lambda parent: create_date_entry(
                parent,
                textvariable=self.fecha_carta_inmediatez_var,
                width=self._entry_width(20),
            ),
            row=8,
            column=1,
            columnspan=2,
        )
        self.fecha_inm_entry = fecha_inm_entry
        self._bind_dirty_tracking(fecha_inm_entry, "fecha_carta_inmediatez")
        self._bind_date_validation(fecha_inm_entry, self.fecha_carta_inmediatez_var, "la fecha de carta de inmediatez")
        self.tooltip_register(
            fecha_inm_entry,
            "Registrar en formato YYYY-MM-DD. Puede quedar vacío si no aplica.",
        )

        ttk.Label(self.frame, text="Fecha carta renuncia:\n(YYYY-MM-DD)").grid(
            row=9,
            column=0,
            padx=COL_PADX,
            pady=(ROW_PADY // 2, ROW_PADY // 2),
            sticky="e",
        )
        fecha_ren_entry = self._make_badged_field(
            self.frame,
            "team_fecha_ren",
            lambda parent: create_date_entry(
                parent,
                textvariable=self.fecha_carta_renuncia_var,
                width=self._entry_width(20),
            ),
            row=9,
            column=1,
            columnspan=2,
        )
        self.fecha_ren_entry = fecha_ren_entry
        self._bind_dirty_tracking(fecha_ren_entry, "fecha_carta_renuncia")
        self._bind_date_validation(fecha_ren_entry, self.fecha_carta_renuncia_var, "la fecha de carta de renuncia")
        self.tooltip_register(
            fecha_ren_entry,
            "Registrar en formato YYYY-MM-DD. Puede quedar vacío si no aplica.",
        )

        ttk.Label(self.frame, text="Nombre agencia:").grid(
            row=10, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        nombre_ag_cb = self._make_badged_field(
            self.frame,
            "team_agencia_nombre",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.nombre_agencia_var,
                width=self._entry_width(25),
            ),
            row=10,
            column=1,
            columnspan=2,
        )
        self._agencia_nombre_combo = nombre_ag_cb
        self._bind_dirty_tracking(nombre_ag_cb, "nombre_agencia")
        self.tooltip_register(nombre_ag_cb, "Especifica la agencia u oficina de trabajo.")
        for sequence in ("<FocusOut>", "<<ComboboxSelected>>", "<KeyRelease>"):
            nombre_ag_cb.bind(sequence, lambda _e=None: self._on_agency_name_change(), add="+")

        ttk.Label(self.frame, text="Código agencia:").grid(
            row=11, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        cod_ag_cb = self._make_badged_field(
            self.frame,
            "team_agencia_codigo",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=self.codigo_agencia_var,
                width=self._entry_width(10),
            ),
            row=11,
            column=1,
            columnspan=2,
        )
        self._agencia_codigo_combo = cod_ag_cb
        self._bind_dirty_tracking(cod_ag_cb, "codigo_agencia")
        self.tooltip_register(cod_ag_cb, "Código interno de la agencia (solo números).")
        for sequence in ("<FocusOut>", "<<ComboboxSelected>>", "<KeyRelease>"):
            cod_ag_cb.bind(sequence, lambda _e=None: self._on_agency_code_change(), add="+")
        self._division_entry = div_cb
        self._area_entry = area_cb
        self._apply_team_catalog_state(preserve_values=True, silent=True)

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
        self._fallback_label.hide()

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
                nombres_entry,
                self.badges.wrap_validation(
                    "team_nombres",
                    lambda: validate_required_text(
                        self.nombres_var.get(), "los nombres del colaborador"
                    ),
                ),
                self.logs,
                f"Colaborador {self.idx+1} - Nombres",
                variables=[self.nombres_var],
            )
        )
        self.validators.append(
            FieldValidator(
                apellidos_entry,
                self.badges.wrap_validation(
                    "team_apellidos",
                    lambda: validate_required_text(
                        self.apellidos_var.get(), "los apellidos del colaborador"
                    ),
                ),
                self.logs,
                f"Colaborador {self.idx+1} - Apellidos",
                variables=[self.apellidos_var],
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
        location_validations = [
            (div_cb, self.division_var, "división", "team_division", "division"),
            (area_cb, self.area_var, "área", "team_area", "area"),
            (serv_cb, self.servicio_var, "servicio", "team_servicio", "servicio"),
            (puesto_cb, self.puesto_var, "puesto", "team_puesto", "puesto"),
        ]
        for widget, variable, label, badge_key, level in location_validations:
            self.validators.append(
                FieldValidator(
                    widget,
                    self.badges.wrap_validation(
                        badge_key, lambda lvl=level: self._validate_location_field(lvl)
                    ),
                    self.logs,
                    f"Colaborador {self.idx+1} - {label.capitalize()}",
                    variables=[variable],
                )
            )

        nombre_validator = FieldValidator(
            nombre_ag_cb,
            self.badges.wrap_validation(
                "team_agencia_nombre", lambda: self._validate_agency_fields("nombre")
            ),
            self.logs,
            f"Colaborador {self.idx+1} - Nombre agencia",
            variables=[self.nombre_agencia_var],
        )
        codigo_validator = FieldValidator(
            cod_ag_cb,
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

    def _entry_width(self, width: int) -> int:
        """Garantiza un ancho mínimo para los campos de texto."""

        return max(width, self.MIN_TEXT_ENTRY_WIDTH)

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
        return create_collapsible_card(
            parent,
            title="",
            identifier=self.section_id,
            logs=self.logs,
            on_toggle=self._handle_toggle,
            log_error=lambda exc: log_event(
                "validacion",
                f"No se pudo crear sección colapsable para colaborador {self.idx+1}: {exc}",
                self.logs,
            ),
            collapsible_cls=CollapsibleSection,
        )

    def _place_section(self):
        grid_section(self.section, self.parent, row=self.idx, padx=COL_PADX, pady=ROW_PADY)
        if hasattr(self.parent, "columnconfigure"):
            try:
                self.parent.columnconfigure(0, weight=1)
            except Exception:
                pass

    def update_position(self, new_index: int | None = None):
        if new_index is not None:
            self.idx = new_index
        try:
            self.section.grid_configure(row=self.idx, padx=COL_PADX, pady=ROW_PADY, sticky="nsew")
        except Exception:
            self._place_section()

    def refresh_indexed_state(self):
        self._sync_section_title()
        if getattr(self, "frame", None):
            try:
                self.frame.config(text=f"Colaborador {self.idx+1}")
            except Exception:
                pass

    def _register_title_traces(self):
        for var in (self.id_var, self.puesto_var, self.area_var):
            var.trace_add("write", self._on_identity_field_change)

    def _build_section_title(self) -> str:
        details = (
            self.id_var.get().strip(),
            self.puesto_var.get().strip(),
            self.area_var.get().strip(),
        )
        return compose_section_title(
            self.section,
            f"Colaborador {self.idx+1}",
            details,
            max_details=2,
        )

    def _sync_section_title(self, *_args):
        if not getattr(self, "section", None):
            return
        title = self._build_section_title()
        try:
            self.section_title_var.set(title)
        except Exception:
            pass
        self.section.set_title(title)

    def _on_identity_field_change(self, *_args):
        self._sync_section_title()

    def _handle_toggle(self, _section=None):
        self._sync_section_title()
        self._set_as_summary_target()

    def _install_focus_binding(self):
        container = getattr(self.section, "content", None) or getattr(self, "section", None)
        if not container:
            return
        bind_all = getattr(container, "bind_all", None)
        if callable(bind_all):
            try:
                bind_all("<FocusIn>", self._handle_focus_in, add="+")
                self._focus_binding_target = ("all", container)
                return
            except Exception:
                self._focus_binding_target = None
        binder = getattr(container, "bind", None)
        if callable(binder):
            try:
                binder("<FocusIn>", self._handle_focus_in, add="+")
                self._focus_binding_target = ("local", container)
            except Exception:
                self._focus_binding_target = None

    def _register_focusable_widgets(self, *widgets):
        for widget in widgets:
            if widget is None:
                continue
            self._focus_widgets.add(widget)
            binder = getattr(widget, "bind", None)
            if callable(binder):
                try:
                    binder("<FocusIn>", lambda _e, frame=self: frame._set_as_summary_target(), add="+")
                except Exception:
                    continue

    def _widget_belongs_to_team(self, widget) -> bool:
        if widget is None:
            return False
        if widget in self._focus_widgets:
            return True
        containers = [
            getattr(self, "frame", None),
            getattr(self, "section", None),
            getattr(getattr(self, "section", None), "content", None),
        ]
        return widget in containers

    def _handle_focus_in(self, event):
        widget = getattr(event, "widget", None)
        if widget is None or self._widget_belongs_to_team(widget):
            self._set_as_summary_target()

    def _set_as_summary_target(self):
        owner = getattr(self, "owner", None)
        if not owner:
            return self
        try:
            owner._team_summary_owner = self
        except Exception:
            pass
        return self

    def _bind_identifier_triggers(self, widget) -> None:
        widget.bind("<FocusIn>", lambda _e: self._set_as_summary_target(), add="+")
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

    def _normalize_catalog_key(self, value: str) -> str:
        return normalize_without_accents((value or "").strip()).lower()

    def _build_agency_lookup(self) -> dict[str, tuple[str, str]]:
        lookup: dict[str, tuple[str, str]] = {}

        def _remember(name: str, code: str) -> None:
            normalized_name = self._normalize_catalog_key(name)
            normalized_code = (code or "").strip()
            if normalized_name and normalized_name not in lookup:
                lookup[normalized_name] = (name, normalized_code)
            if normalized_code and normalized_code not in lookup:
                lookup[normalized_code] = (name, normalized_code)

        for agency_name, agency_code in (AGENCY_CATALOG or {}).items():
            _remember(agency_name, agency_code)

        if self.team_catalog:
            divisions = set()
            for _, label in self.team_catalog.list_hierarchy_divisions():
                if label:
                    divisions.add(label)
            for label in self.team_catalog.list_divisions():
                if label:
                    divisions.add(label)

            for division in divisions:
                areas = set()
                for _, label in self.team_catalog.list_hierarchy_areas(division):
                    if label:
                        areas.add(label)
                for label in self.team_catalog.list_areas(division):
                    if label:
                        areas.add(label)

                for area in areas:
                    for name in self.team_catalog.list_agency_names(division, area):
                        match = self.team_catalog.match_agency_by_name(division, area, name) or {}
                        _remember(name, match.get("codigo") or "")
                    for code in self.team_catalog.list_agency_codes(division, area):
                        match = self.team_catalog.match_agency_by_code(division, area, code) or {}
                        _remember(match.get("nombre") or "", match.get("codigo") or code)

        return lookup

    def _set_combobox_state(self, widget, values, *, enabled: bool = True, allow_free_text: bool = False) -> None:
        if widget is None:
            return
        try:
            widget["values"] = values
        except Exception:
            try:
                widget.configure(values=values)
            except Exception:
                pass
        if not enabled:
            target_state = "disabled"
        elif self.team_catalog.has_data and not allow_free_text:
            target_state = "readonly"
        else:
            target_state = "normal"
        state_method = getattr(widget, "state", None)
        if callable(state_method):
            try:
                state_method([target_state])
                return
            except Exception:
                pass
        try:
            widget.configure(state=target_state)
        except Exception:
            pass

    def _reset_selection_error_cache(self) -> None:
        self._selection_error_cache.clear()

    def _notify_catalog_error(self, message: str) -> None:
        if not message or message in self._selection_error_cache:
            return
        self._selection_error_cache.add(message)
        try:
            messagebox.showerror("Catálogo de colaboradores", message)
        except tk.TclError:
            log_event("validacion", message, self.logs)

    def _apply_team_catalog_state(self, *, preserve_values: bool = True, silent: bool = False) -> None:
        self._update_division_options()
        self._update_area_options(preserve_value=preserve_values, silent=silent)
        self._update_service_options(preserve_value=preserve_values, silent=silent)
        self._update_puesto_options(preserve_value=preserve_values, silent=silent)
        self._update_agency_options(preserve_value=preserve_values, silent=silent)

    def _update_division_options(self) -> None:
        division_pairs = []
        if self.team_catalog:
            division_pairs = self.team_catalog.list_hierarchy_divisions()
            if not division_pairs:
                values = self.team_catalog.list_divisions()
                division_pairs = [(value, value) for value in values]
        values = [label for _, label in division_pairs]
        self._set_combobox_state(
            self._division_combo,
            values,
            enabled=True,
            allow_free_text=not self.team_catalog.has_data and not bool(values),
        )

    def _has_valid_division(self) -> bool:
        division = self.division_var.get().strip()
        if not division:
            return False
        if not self.team_catalog.has_data:
            return True
        return bool(
            self.team_catalog.contains_division(division)
            or self.team_catalog.hierarchy_contains_division(division)
        )

    def _has_valid_area(self) -> bool:
        if not self._has_valid_division():
            return False
        area = self.area_var.get().strip()
        if not area:
            return False
        if not self.team_catalog.has_data:
            return True
        available_areas = self.team_catalog.list_hierarchy_areas(self.division_var.get())
        if not available_areas:
            return True
        return bool(
            self.team_catalog.hierarchy_contains_area(self.division_var.get(), area)
        )

    def _has_valid_service(self) -> bool:
        if not self._has_valid_area():
            return False
        servicio = self.servicio_var.get().strip()
        if not servicio:
            return False
        if not self.team_catalog.has_data:
            return True
        available_services = self.team_catalog.list_hierarchy_services(
            self.division_var.get(), self.area_var.get()
        )
        if not available_services:
            return True
        return bool(
            self.team_catalog.hierarchy_contains_service(
                self.division_var.get(), self.area_var.get(), servicio
            )
        )

    def _update_area_options(self, *, preserve_value: bool = False, silent: bool = False) -> None:
        if not self._has_valid_division():
            if not preserve_value:
                self.area_var.set("")
            self.servicio_var.set("")
            self.puesto_var.set("")
            self._set_combobox_state(self._area_combo, [], enabled=False)
            self._set_combobox_state(self._servicio_combo, [], enabled=False)
            self._set_combobox_state(self._puesto_combo, [], enabled=False)
            self._update_agency_options(preserve_value=preserve_value, silent=silent)
            return
        area_pairs = []
        if self.team_catalog:
            area_pairs = self.team_catalog.list_hierarchy_areas(self.division_var.get())
        area_labels = [label for _, label in area_pairs]
        self._area_option_map = {label: key for key, label in area_pairs}
        allow_free_text = not bool(area_labels)
        self._set_combobox_state(
            self._area_combo,
            area_labels,
            enabled=True,
            allow_free_text=allow_free_text,
        )
        previous_area = self.area_var.get().strip()
        if (
            previous_area
            and area_labels
            and self.team_catalog.has_data
            and previous_area not in self._area_option_map
        ):
            if not silent:
                self._notify_catalog_error(
                    "El área seleccionada no pertenece a la división dentro del catálogo CM."
                )
            self.area_var.set("")
            previous_area = ""
        if previous_area in self._area_option_map:
            self.area_var.set(previous_area)
            self._area_combo.set(previous_area)
        elif area_labels:
            self.area_var.set("")
            self._area_combo.set("")
        if not self.area_var.get().strip():
            self.servicio_var.set("")
            self.puesto_var.set("")
            self._set_combobox_state(self._servicio_combo, [], enabled=False)
            self._set_combobox_state(self._puesto_combo, [], enabled=False)
            self._update_agency_options(preserve_value=False, silent=silent)
            return
        self._update_service_options(preserve_value=preserve_value, silent=silent)
        self._update_agency_options(preserve_value=preserve_value, silent=silent)

    def _update_service_options(self, *, preserve_value: bool = False, silent: bool = False) -> None:
        if not self._has_valid_area():
            self.servicio_var.set("")
            self.puesto_var.set("")
            self._set_combobox_state(self._servicio_combo, [], enabled=False)
            self._set_combobox_state(self._puesto_combo, [], enabled=False)
            return
        service_pairs = []
        if self.team_catalog:
            service_pairs = self.team_catalog.list_hierarchy_services(
                self.division_var.get(), self.area_var.get()
            )
            if not service_pairs:
                service_pairs = self.team_catalog.list_services(
                    self.division_var.get(), self.area_var.get()
                )
                service_pairs = [(value, value) for value in service_pairs]
        service_labels = [label for _, label in service_pairs]
        self._service_option_map = {label: key for key, label in service_pairs}
        allow_free_text = not bool(service_labels)
        self._set_combobox_state(
            self._servicio_combo,
            service_labels,
            enabled=True,
            allow_free_text=allow_free_text,
        )
        previous_service = self.servicio_var.get().strip()
        if (
            previous_service
            and service_labels
            and self.team_catalog.has_data
            and previous_service not in self._service_option_map
        ):
            if not silent:
                self._notify_catalog_error(
                    "El servicio seleccionado no existe para la división y área en el catálogo CM."
                )
            self.servicio_var.set("")
            previous_service = ""
        if previous_service in self._service_option_map:
            self.servicio_var.set(previous_service)
            self._servicio_combo.set(previous_service)
        elif service_labels:
            self.servicio_var.set("")
            self._servicio_combo.set("")
        if not self.servicio_var.get().strip():
            self.puesto_var.set("")
            self._set_combobox_state(self._puesto_combo, [], enabled=False)
            return
        self._update_puesto_options(preserve_value=preserve_value, silent=silent)

    def _update_puesto_options(self, *, preserve_value: bool = False, silent: bool = False) -> None:
        if not self._has_valid_service():
            self.puesto_var.set("")
            self._set_combobox_state(self._puesto_combo, [], enabled=False)
            return
        puestos = []
        if self.team_catalog:
            puestos = self.team_catalog.list_hierarchy_roles(
                self.division_var.get(), self.area_var.get(), self.servicio_var.get()
            )
            if not puestos:
                puestos = self.team_catalog.list_roles(
                    self.division_var.get(), self.area_var.get(), self.servicio_var.get()
                )
                puestos = [(value, value) for value in puestos]
        puesto_labels = [label for _, label in puestos]
        allow_free_text = not bool(puesto_labels)
        self._set_combobox_state(
            self._puesto_combo,
            puesto_labels,
            enabled=True,
            allow_free_text=allow_free_text,
        )
        previous_puesto = self.puesto_var.get().strip()
        valid_positions = {label for label in puesto_labels}
        if (
            previous_puesto
            and puesto_labels
            and self.team_catalog.has_data
            and previous_puesto not in valid_positions
        ):
            if not silent:
                self._notify_catalog_error(
                    "El puesto seleccionado no pertenece al servicio registrado en el catálogo CM."
                )
            self.puesto_var.set("")
            previous_puesto = ""
        if previous_puesto in valid_positions:
            self.puesto_var.set(previous_puesto)
            self._puesto_combo.set(previous_puesto)
        elif puesto_labels:
            self.puesto_var.set("")
            self._puesto_combo.set("")

    def _update_agency_options(self, *, preserve_value: bool = False, silent: bool = False) -> None:
        names = sorted({pair[0] for pair in self._agency_lookup.values()}, key=str.casefold)
        codes = sorted({pair[1] for pair in self._agency_lookup.values() if pair[1]})
        if not preserve_value:
            self.nombre_agencia_var.set("")
            self.codigo_agencia_var.set("")
        self._set_combobox_state(
            self._agencia_nombre_combo,
            names,
            enabled=True,
            allow_free_text=True,
        )
        self._set_combobox_state(
            self._agencia_codigo_combo,
            codes,
            enabled=True,
            allow_free_text=True,
        )

    def _refresh_location_options(self, *, preserve_values: bool = False, silent: bool = False) -> None:
        self._apply_team_catalog_state(preserve_values=preserve_values, silent=silent)

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
        try:
            self._fallback_label.hide()
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
        try:
            self._fallback_label.set_message(message or "", expand=False)
            self._fallback_label.show()
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

    def _set_location_values(
        self,
        *,
        division: str | None = None,
        area: str | None = None,
        servicio: str | None = None,
        puesto: str | None = None,
        silent: bool = False,
    ) -> None:
        if division is not None:
            self.division_var.set(division)
        self._update_division_options()
        if area is not None:
            self.area_var.set(area)
        self._update_area_options(preserve_value=True, silent=silent)
        if servicio is not None:
            self.servicio_var.set(servicio)
        self._update_service_options(preserve_value=True, silent=silent)
        if puesto is not None:
            self.puesto_var.set(puesto)
        self._update_puesto_options(preserve_value=True, silent=silent)
        if not silent:
            self._handle_location_change()

    def _set_agency_values(
        self, nombre: str | None = None, codigo: str | None = None, *, silent: bool = False
    ) -> None:
        if nombre is not None:
            self.nombre_agencia_var.set(nombre)
        if codigo is not None:
            self.codigo_agencia_var.set(codigo)
        self._update_agency_options(preserve_value=True, silent=silent)
        if not silent:
            self._handle_location_change()

    def _on_division_change(self, *, silent: bool = False) -> None:
        self._reset_selection_error_cache()
        if silent:
            self._refresh_location_options(preserve_values=True, silent=True)
            return
        self._refresh_location_options(preserve_values=True)
        self._handle_location_change()
        self._log_change(f"Colaborador {self.idx+1}: modificó división")

    def _on_area_change(self, *, silent: bool = False) -> None:
        self._reset_selection_error_cache()
        if silent:
            self._refresh_location_options(preserve_values=True, silent=True)
            return
        if not self.division_var.get().strip():
            self.area_var.set("")
            self.servicio_var.set("")
            self.puesto_var.set("")
            self._notify_catalog_error("Selecciona la división antes de elegir un área.")
            self._refresh_location_options(preserve_values=False)
            return
        self._refresh_location_options(preserve_values=True)
        self._handle_location_change()
        self._log_change(f"Colaborador {self.idx+1}: modificó área")

    def _on_service_change(self, *, silent: bool = False) -> None:
        self._reset_selection_error_cache()
        if silent:
            self._refresh_location_options(preserve_values=True, silent=True)
            return
        if not self.area_var.get().strip():
            self.servicio_var.set("")
            self._notify_catalog_error("Selecciona el área antes de elegir un servicio.")
            self._refresh_location_options(preserve_values=False)
            return
        self._refresh_location_options(preserve_values=True)
        self._handle_location_change()
        self._log_change(f"Colaborador {self.idx+1}: modificó servicio")

    def _on_puesto_change(self, *, silent: bool = False) -> None:
        self._reset_selection_error_cache()
        if silent:
            self._update_puesto_options(preserve_value=True, silent=True)
            return
        if not self.servicio_var.get().strip():
            self.puesto_var.set("")
            self._notify_catalog_error("Selecciona el servicio antes de elegir un puesto.")
            self._update_puesto_options(preserve_value=False, silent=True)
            return
        self._update_puesto_options(preserve_value=True)
        self._handle_location_change()
        self._log_change(f"Colaborador {self.idx+1}: modificó puesto")

    def _on_agency_name_change(self, *, silent: bool = False) -> None:
        self._reset_selection_error_cache()
        if silent:
            self._update_agency_options(preserve_value=True, silent=True)
            return
        self._update_agency_options(preserve_value=True)
        self._sync_agency_pair(source="nombre")
        self._handle_location_change()
        self._log_change(f"Colaborador {self.idx+1}: modificó agencia")

    def _on_agency_code_change(self, *, silent: bool = False) -> None:
        self._reset_selection_error_cache()
        if silent:
            self._update_agency_options(preserve_value=True, silent=True)
            return
        self._update_agency_options(preserve_value=True)
        self._sync_agency_pair(source="codigo")
        self._handle_location_change()
        self._log_change(f"Colaborador {self.idx+1}: modificó código de agencia")

    def _sync_agency_pair(self, *, source: str) -> None:
        if self._agency_sync_in_progress:
            return

        if source == "nombre":
            incoming_value = self.nombre_agencia_var.get().strip()
            lookup_key = self._normalize_catalog_key(incoming_value)
        else:
            incoming_value = self.codigo_agencia_var.get().strip()
            lookup_key = incoming_value

        if not lookup_key:
            return

        match = self._agency_lookup.get(lookup_key)
        if not match:
            return

        target_name, target_code = match
        self._agency_sync_in_progress = True
        try:
            if source == "nombre" and target_code and self.codigo_agencia_var.get().strip() != target_code:
                self.codigo_agencia_var.set(target_code)
            elif source == "codigo" and target_name:
                current_name_norm = self._normalize_catalog_key(self.nombre_agencia_var.get())
                if current_name_norm != self._normalize_catalog_key(target_name):
                    self.nombre_agencia_var.set(target_name)
        finally:
            self._agency_sync_in_progress = False

    def _apply_autofill_result(self, result) -> None:
        location_kwargs = {k: v for k, v in result.applied.items() if k in {"division", "area", "servicio", "puesto"}}
        if location_kwargs:
            self._set_location_values(
                division=location_kwargs.get("division"),
                area=location_kwargs.get("area"),
                servicio=location_kwargs.get("servicio"),
                puesto=location_kwargs.get("puesto"),
                silent=True,
            )
        if "nombre_agencia" in result.applied or "codigo_agencia" in result.applied:
            self._set_agency_values(
                nombre=result.applied.get("nombre_agencia"),
                codigo=result.applied.get("codigo_agencia"),
                silent=True,
            )
        for key, var in {
            "nombres": self.nombres_var,
            "apellidos": self.apellidos_var,
            "fecha_carta_inmediatez": self.fecha_carta_inmediatez_var,
            "fecha_carta_renuncia": self.fecha_carta_renuncia_var,
        }.items():
            if key in result.applied:
                var.set(result.applied[key])

    def set_lookup(self, lookup):
        self.team_lookup = lookup or {}
        self._last_missing_lookup_id = None

    def set_team_catalog(self, catalog: TeamHierarchyCatalog | None) -> None:
        self.team_catalog = catalog or TeamHierarchyCatalog(build_team_catalog_rows())
        self._agency_lookup = self._build_agency_lookup()
        self._apply_team_catalog_state(preserve_values=True, silent=True)

    def _requires_agency_details(self) -> bool:
        division_norm = normalize_without_accents(self.division_var.get()).lower()
        area_norm = normalize_without_accents(self.area_var.get()).lower()
        return (
            ('dca' in division_norm or 'canales de atencion' in division_norm)
            and ('area comercial' in area_norm)
        )

    def _validate_agency_fields(self, field: str) -> str | None:
        requires_agency = self._requires_agency_details()
        agency_name = self.nombre_agencia_var.get().strip()
        agency_code = self.codigo_agencia_var.get().strip()
        code_lookup = self._agency_lookup.get(agency_code.strip()) if agency_code else None
        name_lookup = self._agency_lookup.get(self._normalize_catalog_key(agency_name)) if agency_name else None
        if field == "nombre":
            if not requires_agency and not agency_name:
                return None
            if requires_agency and not agency_name:
                return "Debe ingresar el nombre de la agencia."
            if self.team_catalog.has_data and agency_name:
                if name_lookup and agency_code:
                    expected_code = name_lookup[1]
                    if expected_code and expected_code != agency_code:
                        return "El código de agencia no coincide con el catálogo CM."
                elif code_lookup and code_lookup[0]:
                    if self._normalize_catalog_key(code_lookup[0]) != self._normalize_catalog_key(agency_name):
                        return "El nombre de agencia no coincide con el catálogo CM."
            return None
        if field == "codigo":
            code_error = validate_agency_code(
                agency_code,
                allow_blank=not requires_agency,
            )
            if code_error:
                return code_error
            if not agency_code:
                return None
            if self.team_catalog.has_data:
                if code_lookup and agency_name:
                    expected_name = code_lookup[0]
                    if expected_name and self._normalize_catalog_key(agency_name) != self._normalize_catalog_key(expected_name):
                        return "El nombre de agencia no coincide con el catálogo CM."
                elif name_lookup:
                    expected_code = name_lookup[1]
                    if expected_code and expected_code != agency_code:
                        return "El código de agencia no coincide con el catálogo CM."
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
                    def choose_value(var, key):
                        value = data.get(key, "").strip()
                        if self._dirty_fields.get(key):
                            return None
                        if value and should_autofill_field(var.get(), preserve_existing):
                            return value
                        return None

                    location_payload = {
                        key: choose_value(var, key)
                        for key, var in (
                            ("division", self.division_var),
                            ("area", self.area_var),
                            ("servicio", self.servicio_var),
                            ("puesto", self.puesto_var),
                        )
                    }
                    agency_name = choose_value(self.nombre_agencia_var, "nombre_agencia")
                    agency_code = choose_value(self.codigo_agencia_var, "codigo_agencia")

                    for key, var in (
                        ("nombres", self.nombres_var),
                        ("apellidos", self.apellidos_var),
                        ("fecha_carta_inmediatez", self.fecha_carta_inmediatez_var),
                        ("fecha_carta_renuncia", self.fecha_carta_renuncia_var),
                    ):
                        chosen = choose_value(var, key)
                        if chosen:
                            var.set(chosen)

                    self._set_location_values(
                        division=location_payload.get("division"),
                        area=location_payload.get("area"),
                        servicio=location_payload.get("servicio"),
                        puesto=location_payload.get("puesto"),
                        silent=True,
                    )
                    if agency_name or agency_code:
                        self._set_agency_values(
                            nombre=agency_name,
                            codigo=agency_code,
                            silent=True,
                        )
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
        columns = (
            ("id", "ID", 150),
            ("nombres", "Nombres", 150),
            ("apellidos", "Apellidos", 150),
            ("division", "División", 140),
            ("area", "Área", 140),
            ("servicio", "Servicio", 140),
            ("puesto", "Puesto", 140),
            ("tipo_sancion", "Tipo sanción", 140),
            ("fecha_carta_inmediatez", "Carta inmediatez", 150),
            ("fecha_carta_renuncia", "Carta renuncia", 150),
        )
        return build_summary_tree(
            container,
            columns,
            sort_callback=self._sort_summary,
            select_callback=self._on_summary_select,
            double_click_callback=self._on_summary_double_click,
        )

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

    def _validate_location_field(self, level: str) -> str | None:
        def _in_hierarchy(pairs: list[tuple[str, str]], value: str) -> bool:
            normalized = self._normalize_catalog_key(value)
            for key, label in pairs:
                if normalized in {self._normalize_catalog_key(key), self._normalize_catalog_key(label)}:
                    return True
            return False

        division = self.division_var.get().strip()
        area = self.area_var.get().strip()
        servicio = self.servicio_var.get().strip()
        puesto = self.puesto_var.get().strip()
        has_catalog = self.team_catalog.has_data

        if level == "division":
            if not division:
                return "Debe seleccionar la división del colaborador."
            if not has_catalog:
                return None
            if self.team_catalog.contains_division(division) or self.team_catalog.hierarchy_contains_division(division):
                return None
            return f"La división '{division}' no está en el catálogo CM de team_details."

        if level == "area":
            if not area:
                return "Debe seleccionar el área del colaborador."
            if not division:
                return "Selecciona la división antes de validar el área."
            if not has_catalog:
                return None
            if self.team_catalog.contains_area(division, area):
                return None
            area_pairs = self.team_catalog.list_hierarchy_areas(division)
            if _in_hierarchy(area_pairs, area):
                return None
            return f"El área '{area}' no pertenece a la división seleccionada en el catálogo CM."

        if level == "servicio":
            if not servicio:
                return "Debe seleccionar el servicio del colaborador."
            if not area or not division:
                return "Completa división y área antes de validar el servicio."
            if not has_catalog:
                return None
            if self.team_catalog.contains_service(division, area, servicio):
                return None
            service_pairs = self.team_catalog.list_hierarchy_services(division, area)
            if _in_hierarchy(service_pairs, servicio):
                return None
            return (
                f"El servicio '{servicio}' no existe para la división y área seleccionadas en el catálogo CM."
            )

        if level == "puesto":
            if not puesto:
                return "Debe seleccionar el puesto del colaborador."
            if not servicio or not area or not division:
                return "Completa división, área y servicio antes de validar el puesto."
            if not has_catalog:
                return None
            if self.team_catalog.contains_role(division, area, servicio, puesto):
                return None
            puesto_pairs = self.team_catalog.list_hierarchy_roles(division, area, servicio)
            if _in_hierarchy(puesto_pairs, puesto):
                return None
            return (
                f"El puesto '{puesto}' no pertenece al servicio seleccionado en el catálogo CM."
            )
        return None

    def _validate_catalog_selection(self, value: str, label: str, catalog) -> str | None:
        text = (value or "").strip()
        if not text:
            return f"Debe seleccionar {label}."
        normalized_catalog = {self._normalize_catalog_key(item) for item in catalog}
        if self._normalize_catalog_key(text) not in normalized_catalog:
            return f"El {label} '{text}' no está en el catálogo CM."
        return None


__all__ = ["TeamMemberFrame"]
