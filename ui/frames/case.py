"""Frame de captura de datos generales del caso."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from settings import CANAL_LIST, PROCESO_LIST, TAXONOMIA, TIPO_INFORME_LIST
from ui.config import COL_PADX, ROW_PADY
from ui.frames.utils import ensure_grid_support
from validators import FieldValidator, validate_case_id, validate_required_text


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
        self.frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.frame.columnconfigure(0, weight=0)
        self.frame.columnconfigure(1, weight=1)
        owner._case_inputs = {}
        self._build_header_fields()
        self._build_taxonomy_fields()
        self._build_investigator_block()
        self._build_dates_block()
        self._build_cost_center_field()
        self._register_validators()

    def _build_header_fields(self):
        owner = self.owner
        frame = self.frame
        ttk.Label(frame, text="Número de caso (AAAA-XXXX):").grid(
            row=0, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        id_entry = ttk.Entry(frame, textvariable=owner.id_caso_var, width=20)
        id_entry.grid(row=0, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        id_entry.bind(
            "<FocusOut>", lambda _e: owner._log_navigation_change("Modificó número de caso")
        )
        owner.register_tooltip(
            id_entry, "Formato AAAA-XXXX. Se usa para detectar duplicados."
        )

        ttk.Label(frame, text="Tipo de informe:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        tipo_cb = ttk.Combobox(
            frame,
            textvariable=owner.tipo_informe_var,
            values=TIPO_INFORME_LIST,
            state="readonly",
            width=30,
        )
        tipo_cb.grid(row=1, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(tipo_cb, "Selecciona el tipo de reporte a generar.")
        tipo_cb.set('')
        owner._case_inputs.update({"id_entry": id_entry, "tipo_cb": tipo_cb})

    def _build_taxonomy_fields(self):
        owner = self.owner
        frame = self.frame
        taxonomy_container = ttk.Frame(frame)
        ensure_grid_support(taxonomy_container)
        taxonomy_container.grid(row=2, column=0, columnspan=2, sticky="we")
        if hasattr(taxonomy_container, "columnconfigure"):
            taxonomy_container.columnconfigure(1, weight=1)
            taxonomy_container.columnconfigure(3, weight=1)

        ttk.Label(taxonomy_container, text="Categoría nivel 1:").grid(
            row=0, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        cat1_cb = ttk.Combobox(
            taxonomy_container,
            textvariable=owner.cat_caso1_var,
            values=list(TAXONOMIA.keys()),
            state="readonly",
            width=25,
        )
        cat1_cb.grid(row=0, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(cat1_cb, "Selecciona la categoría principal del caso.")
        cat1_cb.bind("<<ComboboxSelected>>", lambda _e: owner.on_case_cat1_change())
        cat1_cb.bind("<FocusOut>", lambda _e: owner.on_case_cat1_change())
        cat1_cb.set('')

        ttk.Label(taxonomy_container, text="Categoría nivel 2:").grid(
            row=0, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        case_cat2_cb = ttk.Combobox(
            taxonomy_container,
            textvariable=owner.cat_caso2_var,
            values=[],
            state="readonly",
            width=25,
        )
        case_cat2_cb.grid(row=0, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(case_cat2_cb, "Selecciona la subcategoría del caso.")
        case_cat2_cb.bind("<<ComboboxSelected>>", lambda _e: owner.on_case_cat2_change())
        case_cat2_cb.bind("<FocusOut>", lambda _e: owner.on_case_cat2_change())
        owner.case_cat2_cb = case_cat2_cb
        case_cat2_cb.set('')

        ttk.Label(taxonomy_container, text="Modalidad:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        case_mod_cb = ttk.Combobox(
            taxonomy_container,
            textvariable=owner.mod_caso_var,
            values=[],
            state="readonly",
            width=25,
        )
        case_mod_cb.grid(row=1, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(case_mod_cb, "Selecciona la modalidad específica.")
        owner.case_mod_cb = case_mod_cb
        case_mod_cb.set('')

        canal_proc_container = ttk.Frame(frame)
        ensure_grid_support(canal_proc_container)
        canal_proc_container.grid(row=3, column=0, columnspan=2, sticky="we")
        canal_proc_container.columnconfigure(1, weight=1)
        canal_proc_container.columnconfigure(3, weight=1)
        ttk.Label(canal_proc_container, text="Canal:").grid(
            row=0, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        canal_cb = ttk.Combobox(
            canal_proc_container,
            textvariable=owner.canal_caso_var,
            values=CANAL_LIST,
            state="readonly",
            width=25,
        )
        canal_cb.grid(row=0, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(canal_cb, "Canal donde se originó el evento.")
        canal_cb.set('')

        ttk.Label(canal_proc_container, text="Proceso impactado:").grid(
            row=0, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        proc_cb = ttk.Combobox(
            canal_proc_container,
            textvariable=owner.proceso_caso_var,
            values=PROCESO_LIST,
            state="readonly",
            width=25,
        )
        proc_cb.grid(row=0, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
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

    def _build_investigator_block(self):
        owner = self.owner
        frame = self.frame
        ttk.Label(frame, text="Investigador principal:").grid(
            row=4, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="ne"
        )
        investigator_container = ttk.Frame(frame)
        ensure_grid_support(investigator_container)
        investigator_container.grid(row=4, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        investigator_container.columnconfigure(1, weight=1)
        investigator_container.columnconfigure(2, weight=1)
        ttk.Label(investigator_container, text="Matrícula:").grid(
            row=0, column=0, padx=(0, COL_PADX // 2), pady=(0, ROW_PADY // 2), sticky="e"
        )
        investigator_entry = ttk.Entry(
            investigator_container, textvariable=owner.investigator_id_var, width=16
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
            investigator_container, textvariable=owner.investigator_nombre_var, state="readonly"
        )
        investigator_name.grid(
            row=1, column=1, padx=(0, COL_PADX), pady=(0, ROW_PADY // 2), sticky="we"
        )
        ttk.Label(investigator_container, text="Cargo:").grid(
            row=2, column=0, padx=(0, COL_PADX // 2), pady=(0, ROW_PADY // 2), sticky="e"
        )
        investigator_role = ttk.Entry(
            investigator_container, textvariable=owner.investigator_cargo_var, state="readonly"
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

    def _build_dates_block(self):
        owner = self.owner
        frame = self.frame
        ttk.Label(frame, text="Fechas del caso:").grid(
            row=5, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        dates_container = ttk.Frame(frame)
        ensure_grid_support(dates_container)
        dates_container.grid(row=5, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        dates_container.columnconfigure(1, weight=1)
        dates_container.columnconfigure(3, weight=1)
        ttk.Label(dates_container, text="Ocurrencia (YYYY-MM-DD):").grid(
            row=0, column=0, padx=(0, COL_PADX // 2), pady=(0, ROW_PADY // 2), sticky="e"
        )
        fecha_case_entry = ttk.Entry(dates_container, textvariable=owner.fecha_caso_var, width=16)
        fecha_case_entry.grid(
            row=0, column=1, padx=(0, COL_PADX), pady=(0, ROW_PADY // 2), sticky="we"
        )
        owner.register_tooltip(
            fecha_case_entry, "Fecha en que se originó el caso a nivel general."
        )
        ttk.Label(dates_container, text="Descubrimiento (YYYY-MM-DD):").grid(
            row=0, column=2, padx=(0, COL_PADX // 2), pady=(0, ROW_PADY // 2), sticky="e"
        )
        fecha_desc_entry = ttk.Entry(
            dates_container, textvariable=owner.fecha_descubrimiento_caso_var, width=16
        )
        fecha_desc_entry.grid(
            row=0, column=3, padx=(0, COL_PADX), pady=(0, ROW_PADY // 2), sticky="we"
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

    def _build_cost_center_field(self):
        owner = self.owner
        frame = self.frame
        ttk.Label(frame, text="Centro de costos del caso (; separados):").grid(
            row=6, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        centro_costo_entry = ttk.Entry(
            frame, textvariable=owner.centro_costo_caso_var, width=35
        )
        centro_costo_entry.grid(row=6, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        owner.register_tooltip(
            centro_costo_entry,
            "Ingresa centros de costos separados por punto y coma. Deben ser numéricos y de al menos 5 dígitos.",
        )
        owner._case_inputs["centro_costo_entry"] = centro_costo_entry

    def _register_validators(self):
        owner = self.owner
        inputs = owner._case_inputs
        owner.validators.append(
            FieldValidator(
                inputs["id_entry"],
                lambda: validate_case_id(owner.id_caso_var.get()),
                owner.logs,
                "Caso - ID",
                variables=[owner.id_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["tipo_cb"],
                lambda: validate_required_text(owner.tipo_informe_var.get(), "el tipo de informe"),
                owner.logs,
                "Caso - Tipo de informe",
                variables=[owner.tipo_informe_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["cat1_cb"],
                lambda: validate_required_text(owner.cat_caso1_var.get(), "la categoría nivel 1"),
                owner.logs,
                "Caso - Categoría 1",
                variables=[owner.cat_caso1_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["case_cat2_cb"],
                lambda: validate_required_text(owner.cat_caso2_var.get(), "la categoría nivel 2"),
                owner.logs,
                "Caso - Categoría 2",
                variables=[owner.cat_caso2_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["case_mod_cb"],
                lambda: validate_required_text(owner.mod_caso_var.get(), "la modalidad del caso"),
                owner.logs,
                "Caso - Modalidad",
                variables=[owner.mod_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["canal_cb"],
                lambda: validate_required_text(owner.canal_caso_var.get(), "el canal del caso"),
                owner.logs,
                "Caso - Canal",
                variables=[owner.canal_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["proc_cb"],
                lambda: validate_required_text(owner.proceso_caso_var.get(), "el proceso impactado"),
                owner.logs,
                "Caso - Proceso",
                variables=[owner.proceso_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["fecha_case_entry"],
                owner._validate_case_occurrence_date,
                owner.logs,
                "Caso - Fecha de ocurrencia",
                variables=[owner.fecha_caso_var],
            )
        )
        owner.validators.append(
            FieldValidator(
                inputs["fecha_desc_entry"],
                owner._validate_case_discovery_date,
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
