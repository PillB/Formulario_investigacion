"""Frame de captura de datos generales del caso."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from settings import CANAL_LIST, PROCESO_LIST, TAXONOMIA, TIPO_INFORME_LIST
from ui.config import COL_PADX, ROW_PADY
from ui.frames.utils import (
    build_required_label,
    create_date_entry,
    ensure_grid_support,
    grid_and_configure,
)
from ui.layout import responsive_grid
from validation_badge import badge_registry
from theme_manager import ThemeManager
from validators import FieldValidator, validate_case_id, validate_required_text


ENTRY_STYLE = ThemeManager.ENTRY_STYLE
COMBOBOX_STYLE = ThemeManager.COMBOBOX_STYLE


class CaseFrame:
    """Encapsula el formulario de datos generales del caso.

    Este frame se limita a construir la interfaz y registrar las validaciones
    específicas de la sección. La lógica de negocio (autocompletado y
    callbacks) sigue viviendo en la instancia de la aplicación que se pasa
    como ``owner``.
    """

    def __init__(self, owner, parent):
        self.owner = owner
        self.frame = ttk.Frame(parent)
        grid_and_configure(self.frame, parent, padx=5, pady=5)
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self._left_fields: list[tuple[ttk.Widget, ttk.Widget]] = []
        self._right_fields: list[tuple[ttk.Widget, ttk.Widget]] = []
        self._paned = ttk.Panedwindow(self.frame, orient="horizontal")
        grid_and_configure(self._paned, self.frame)
        self._left_column = ttk.Frame(self._paned)
        self._right_column = ttk.Frame(self._paned)
        ensure_grid_support(self._left_column)
        ensure_grid_support(self._right_column)
        self.badges = badge_registry
        self._paned.add(self._left_column, weight=1)
        self._paned.add(self._right_column, weight=1)
        owner._case_inputs = {}
        self._build_header_fields(self._left_column, self._left_fields)
        self._build_taxonomy_fields(self._left_column, self._left_fields)
        self._build_investigator_block(self._right_column, self._right_fields)
        self._build_dates_block(self._right_column, self._right_fields)
        self._build_cost_center_field(self._right_column, self._right_fields)
        self.frame.bind("<Configure>", lambda _e: self._layout_columns())
        self._register_validators()

    def _layout_columns(self) -> None:
        responsive_grid(self._left_column, self._left_fields)
        responsive_grid(self._right_column, self._right_fields)

    def _make_badged_field(self, parent, key: str, widget_factory):
        container = ttk.Frame(parent)
        ensure_grid_support(container)
        if hasattr(container, "columnconfigure"):
            container.columnconfigure(0, weight=1)
        widget = widget_factory(container)
        widget.grid(row=0, column=0, padx=(0, COL_PADX // 2), pady=ROW_PADY, sticky="we")
        badge = self.badges.claim(key, container, row=0, column=1)
        return container, widget, badge

    def _build_header_fields(self, frame, collector):
        owner = self.owner
        case_id_label = build_required_label(
            frame,
            "Número de caso (AAAA-XXXX):",
            tooltip_register=owner.register_tooltip,
        )
        id_container, id_entry, _ = self._make_badged_field(
            frame,
            "case_id",
            lambda parent: ttk.Entry(
                parent, textvariable=owner.id_caso_var, width=20, style=ENTRY_STYLE
            ),
        )
        owner.register_tooltip(
            id_entry, "Formato AAAA-XXXX. Se usa para detectar duplicados."
        )

        tipo_label = build_required_label(
            frame,
            "Tipo de informe:",
            tooltip_register=owner.register_tooltip,
        )
        tipo_container, tipo_cb, _ = self._make_badged_field(
            frame,
            "case_tipo",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=owner.tipo_informe_var,
                values=TIPO_INFORME_LIST,
                state="readonly",
                width=30,
                style=COMBOBOX_STYLE,
            ),
        )
        owner.register_tooltip(tipo_cb, "Selecciona el tipo de reporte a generar.")
        tipo_cb.set('')
        owner._case_inputs.update({"id_entry": id_entry, "tipo_cb": tipo_cb})
        collector.extend(
            [
                (case_id_label, id_container),
                (tipo_label, tipo_container),
            ]
        )

    def _build_taxonomy_fields(self, frame, collector):
        owner = self.owner
        taxonomy_label = ttk.Label(frame, text="Taxonomía del caso:")
        taxonomy_container = ttk.Frame(frame)
        ensure_grid_support(taxonomy_container)
        if hasattr(taxonomy_container, "columnconfigure"):
            taxonomy_container.columnconfigure(1, weight=1)
            taxonomy_container.columnconfigure(3, weight=1)

        cat1_label = build_required_label(
            taxonomy_container,
            "Categoría nivel 1:",
            tooltip_register=owner.register_tooltip,
        )
        cat1_label.grid(
            row=0, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        cat1_container, cat1_cb, _ = self._make_badged_field(
            taxonomy_container,
            "case_cat1",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=owner.cat_caso1_var,
                values=list(TAXONOMIA.keys()),
                state="readonly",
                width=25,
                style=COMBOBOX_STYLE,
            ),
        )
        cat1_container.grid(row=0, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(cat1_cb, "Selecciona la categoría principal del caso.")
        cat1_cb.bind("<<ComboboxSelected>>", lambda _e: owner.on_case_cat1_change())
        cat1_cb.bind("<FocusOut>", lambda _e: owner.on_case_cat1_change())
        cat1_cb.set('')

        cat2_label = build_required_label(
            taxonomy_container,
            "Categoría nivel 2:",
            tooltip_register=owner.register_tooltip,
        )
        cat2_label.grid(
            row=0, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        cat2_container, case_cat2_cb, _ = self._make_badged_field(
            taxonomy_container,
            "case_cat2",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=owner.cat_caso2_var,
                values=[],
                state="readonly",
                width=25,
                style=COMBOBOX_STYLE,
            ),
        )
        cat2_container.grid(row=0, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(case_cat2_cb, "Selecciona la subcategoría del caso.")
        case_cat2_cb.bind("<<ComboboxSelected>>", lambda _e: owner.on_case_cat2_change())
        case_cat2_cb.bind("<FocusOut>", lambda _e: owner.on_case_cat2_change())
        owner.case_cat2_cb = case_cat2_cb
        case_cat2_cb.set('')

        modalidad_label = build_required_label(
            taxonomy_container,
            "Modalidad:",
            tooltip_register=owner.register_tooltip,
        )
        modalidad_label.grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        mod_container, case_mod_cb, _ = self._make_badged_field(
            taxonomy_container,
            "case_mod",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=owner.mod_caso_var,
                values=[],
                state="readonly",
                width=25,
                style=COMBOBOX_STYLE,
            ),
        )
        mod_container.grid(row=1, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(case_mod_cb, "Selecciona la modalidad específica.")
        owner.case_mod_cb = case_mod_cb
        case_mod_cb.set('')

        canal_proc_container = ttk.Frame(taxonomy_container)
        ensure_grid_support(canal_proc_container)
        canal_proc_container.grid(row=2, column=0, columnspan=4, sticky="we")
        canal_proc_container.columnconfigure(1, weight=1)
        canal_proc_container.columnconfigure(3, weight=1)
        canal_label = build_required_label(
            canal_proc_container,
            "Canal:",
            tooltip_register=owner.register_tooltip,
        )
        canal_label.grid(
            row=0, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        canal_container, canal_cb, _ = self._make_badged_field(
            canal_proc_container,
            "case_canal",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=owner.canal_caso_var,
                values=CANAL_LIST,
                state="readonly",
                width=25,
                style=COMBOBOX_STYLE,
            ),
        )
        canal_container.grid(row=0, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(canal_cb, "Canal donde se originó el evento.")
        canal_cb.set('')

        proc_label = build_required_label(
            canal_proc_container,
            "Proceso impactado:",
            tooltip_register=owner.register_tooltip,
        )
        proc_label.grid(
            row=0, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        proc_container, proc_cb, _ = self._make_badged_field(
            canal_proc_container,
            "case_proc",
            lambda parent: ttk.Combobox(
                parent,
                textvariable=owner.proceso_caso_var,
                values=PROCESO_LIST,
                state="readonly",
                width=25,
                style=COMBOBOX_STYLE,
            ),
        )
        proc_container.grid(row=0, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(proc_cb, "Proceso que sufrió la desviación.")
        proc_cb.set('')
        owner._case_inputs.update(
            {
                "cat1_cb": cat1_cb,
                "case_cat2_cb": case_cat2_cb,
                "case_mod_cb": case_mod_cb,
                "canal_cb": canal_cb,
                "proc_cb": proc_cb,
            }
        )
        collector.append((taxonomy_label, taxonomy_container))

    def _build_investigator_block(self, frame, collector):
        owner = self.owner
        investigator_label = ttk.Label(frame, text="Investigador principal:")
        investigator_container = ttk.Frame(frame)
        ensure_grid_support(investigator_container)
        investigator_container.columnconfigure(1, weight=1)
        investigator_container.columnconfigure(2, weight=1)
        ttk.Label(investigator_container, text="Matrícula:").grid(
            row=0, column=0, padx=(0, COL_PADX // 2), pady=(0, ROW_PADY // 2), sticky="e"
        )
        investigator_entry = ttk.Entry(
            investigator_container,
            textvariable=owner.investigator_id_var,
            width=16,
            style=ENTRY_STYLE,
        )
        investigator_entry.grid(
            row=0, column=1, padx=(0, COL_PADX), pady=(0, ROW_PADY // 2), sticky="we"
        )
        investigator_entry.bind("<FocusOut>", lambda _e: owner._autofill_investigator(show_errors=True))
        owner.register_tooltip(
            investigator_entry,
            "Ingresa la matrícula del investigador principal (letra + 5 dígitos) para autocompletar nombre y cargo.",
        )
        ttk.Label(investigator_container, text="Nombre y apellidos:").grid(
            row=1, column=0, padx=(0, COL_PADX // 2), pady=(0, ROW_PADY // 2), sticky="e"
        )
        investigator_name = ttk.Entry(
            investigator_container,
            textvariable=owner.investigator_nombre_var,
            state="readonly",
            style=ENTRY_STYLE,
        )
        investigator_name.grid(
            row=1, column=1, padx=(0, COL_PADX), pady=(0, ROW_PADY // 2), sticky="we"
        )
        ttk.Label(investigator_container, text="Cargo:").grid(
            row=2, column=0, padx=(0, COL_PADX // 2), pady=(0, ROW_PADY // 2), sticky="e"
        )
        investigator_role = ttk.Entry(
            investigator_container,
            textvariable=owner.investigator_cargo_var,
            state="readonly",
            style=ENTRY_STYLE,
        )
        investigator_role.grid(
            row=2, column=1, padx=(0, COL_PADX), pady=(0, ROW_PADY // 2), sticky="we"
        )
        owner.register_tooltip(
            investigator_name,
            "Nombre del investigador obtenido automáticamente desde team_details.csv.",
        )
        owner.register_tooltip(
            investigator_role, "Cargo autocompletado según la matrícula del investigador."
        )
        owner._case_inputs.update(
            {
                "investigator_entry": investigator_entry,
                "investigator_name": investigator_name,
                "investigator_role": investigator_role,
            }
        )
        collector.append((investigator_label, investigator_container))

    def _build_dates_block(self, frame, collector):
        owner = self.owner
        dates_label = ttk.Label(frame, text="Fechas del caso:")
        dates_container = ttk.Frame(frame)
        ensure_grid_support(dates_container)
        dates_container.columnconfigure(1, weight=1)
        dates_container.columnconfigure(3, weight=1)
        occurrence_label = build_required_label(
            dates_container,
            "Ocurrencia:\n(YYYY-MM-DD)",
            tooltip_register=owner.register_tooltip,
        )
        occurrence_label.grid(
            row=0,
            column=0,
            padx=(0, COL_PADX // 2),
            pady=(ROW_PADY // 2, ROW_PADY // 2),
            sticky="e",
        )
        occ_container, fecha_case_entry, _ = self._make_badged_field(
            dates_container,
            "case_fecha_oc",
            lambda parent: create_date_entry(
                parent, textvariable=owner.fecha_caso_var, width=16, style=ENTRY_STYLE
            ),
        )
        occ_container.grid(
            row=0,
            column=1,
            padx=(0, COL_PADX),
            pady=(ROW_PADY // 2, ROW_PADY // 2),
            sticky="we",
        )
        owner.register_tooltip(
            fecha_case_entry, "Fecha en que se originó el caso a nivel general."
        )
        discovery_label = build_required_label(
            dates_container,
            "Descubrimiento:\n(YYYY-MM-DD)",
            tooltip_register=owner.register_tooltip,
        )
        discovery_label.grid(
            row=0,
            column=2,
            padx=(0, COL_PADX // 2),
            pady=(ROW_PADY // 2, ROW_PADY // 2),
            sticky="e",
        )
        desc_container, fecha_desc_entry, _ = self._make_badged_field(
            dates_container,
            "case_fecha_desc",
            lambda parent: create_date_entry(
                parent,
                textvariable=owner.fecha_descubrimiento_caso_var,
                width=16,
                style=ENTRY_STYLE,
            ),
        )
        desc_container.grid(
            row=0,
            column=3,
            padx=(0, COL_PADX),
            pady=(ROW_PADY // 2, ROW_PADY // 2),
            sticky="we",
        )
        owner.register_tooltip(
            fecha_desc_entry,
            "Fecha en que se detectó el caso. Debe ser posterior a la ocurrencia y no futura.",
        )
        owner._case_inputs.update(
            {
                "fecha_case_entry": fecha_case_entry,
                "fecha_desc_entry": fecha_desc_entry,
            }
        )
        collector.append((dates_label, dates_container))

    def _build_cost_center_field(self, frame, collector):
        owner = self.owner
        cost_center_label = ttk.Label(
            frame, text="Centro de costos del caso (; separados):"
        )
        centro_costo_entry = ttk.Entry(
            frame, textvariable=owner.centro_costo_caso_var, width=35, style=ENTRY_STYLE
        )
        owner.register_tooltip(
            centro_costo_entry,
            "Ingresa centros de costos separados por punto y coma. Deben ser numéricos y de al menos 5 dígitos.",
        )
        owner._case_inputs["centro_costo_entry"] = centro_costo_entry
        collector.append((cost_center_label, centro_costo_entry))

    def _register_validators(self):
        owner = self.owner
        inputs = owner._case_inputs
        owner.validators.append(
            FieldValidator(
                inputs["id_entry"],
                self.badges.wrap_validation(
                    "case_id", lambda: validate_case_id(owner.id_caso_var.get())
                ),
                owner.logs,
                "Caso - ID",
                variables=[owner.id_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["tipo_cb"],
                self.badges.wrap_validation(
                    "case_tipo",
                    lambda: validate_required_text(
                        owner.tipo_informe_var.get(), "el tipo de informe"
                    ),
                ),
                owner.logs,
                "Caso - Tipo de informe",
                variables=[owner.tipo_informe_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["cat1_cb"],
                self.badges.wrap_validation(
                    "case_cat1",
                    lambda: validate_required_text(
                        owner.cat_caso1_var.get(), "la categoría nivel 1"
                    ),
                ),
                owner.logs,
                "Caso - Categoría 1",
                variables=[owner.cat_caso1_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["case_cat2_cb"],
                self.badges.wrap_validation(
                    "case_cat2",
                    lambda: validate_required_text(
                        owner.cat_caso2_var.get(), "la categoría nivel 2"
                    ),
                ),
                owner.logs,
                "Caso - Categoría 2",
                variables=[owner.cat_caso2_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["case_mod_cb"],
                self.badges.wrap_validation(
                    "case_mod",
                    lambda: validate_required_text(
                        owner.mod_caso_var.get(), "la modalidad del caso"
                    ),
                ),
                owner.logs,
                "Caso - Modalidad",
                variables=[owner.mod_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["canal_cb"],
                self.badges.wrap_validation(
                    "case_canal",
                    lambda: validate_required_text(
                        owner.canal_caso_var.get(), "el canal del caso"
                    ),
                ),
                owner.logs,
                "Caso - Canal",
                variables=[owner.canal_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["proc_cb"],
                self.badges.wrap_validation(
                    "case_proc",
                    lambda: validate_required_text(
                        owner.proceso_caso_var.get(), "el proceso impactado"
                    ),
                ),
                owner.logs,
                "Caso - Proceso",
                variables=[owner.proceso_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["fecha_case_entry"],
                self.badges.wrap_validation("case_fecha_oc", owner._validate_case_occurrence_date),
                owner.logs,
                "Caso - Fecha de ocurrencia",
                variables=[owner.fecha_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["fecha_desc_entry"],
                self.badges.wrap_validation(
                    "case_fecha_desc", owner._validate_case_discovery_date
                ),
                owner.logs,
                "Caso - Fecha de descubrimiento",
                variables=[owner.fecha_descubrimiento_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["centro_costo_entry"],
                lambda: owner._validate_cost_centers(text=owner.centro_costo_caso_var.get()),
                owner.logs,
                "Caso - Centro de costos",
                variables=[owner.centro_costo_caso_var],
            )
        )
