"""Componentes de interfaz relacionados a productos, reclamos e involucramientos."""

from __future__ import annotations

from decimal import Decimal

import tkinter as tk
from tkinter import messagebox, ttk

from settings import (CANAL_LIST, PROCESO_LIST, TAXONOMIA, TIPO_MONEDA_LIST,
                      TIPO_PRODUCTO_LIST)
from validators import (FieldValidator, log_event, normalize_without_accents,
                        should_autofill_field, sum_investigation_components,
                        validate_codigo_analitica, validate_date_text,
                        validate_money_bounds,
                        validate_product_dates, validate_product_id,
                        validate_reclamo_id, validate_required_text)


class InvolvementRow:
    """Representa una fila de asignación de monto a un colaborador dentro de un producto."""

    def __init__(self, parent, product_frame, idx, team_getter, remove_callback, logs, tooltip_register):
        self.parent = parent
        self.product_frame = product_frame
        self.idx = idx
        self.team_getter = team_getter
        self.remove_callback = remove_callback
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self.team_validator = None

        self.team_var = tk.StringVar()
        self.monto_var = tk.StringVar()

        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", pady=1)

        ttk.Label(self.frame, text="Colaborador:").pack(side="left")
        self.team_cb = ttk.Combobox(
            self.frame,
            textvariable=self.team_var,
            values=self.team_getter(),
            state="readonly",
            width=20,
        )
        self.team_cb.pack(side="left", padx=5)
        self.team_cb.set('')
        self.team_cb.bind("<FocusOut>", lambda _e: self._handle_team_focus_out(), add="+")
        self.team_cb.bind("<<ComboboxSelected>>", lambda _e: self._handle_team_focus_out(), add="+")
        self.tooltip_register(self.team_cb, "Elige al colaborador que participa en este producto.")
        ttk.Label(self.frame, text="Monto asignado:").pack(side="left")
        monto_entry = ttk.Entry(self.frame, textvariable=self.monto_var, width=15)
        monto_entry.pack(side="left", padx=5)
        monto_entry.bind("<FocusOut>", lambda _e: self._handle_amount_focus_out(), add="+")
        self.tooltip_register(monto_entry, "Monto en soles asignado a este colaborador.")

        remove_btn = ttk.Button(self.frame, text="Eliminar", command=self.remove)
        remove_btn.pack(side="left", padx=5)
        self.tooltip_register(remove_btn, "Elimina esta asignación específica.")

        amount_validator = FieldValidator(
            monto_entry,
            self._validate_assignment_amount,
            self.logs,
            f"Producto {self.product_frame.idx+1} - Asignación {self.idx+1}",
            variables=[self.monto_var],
        )
        self.validators.append(amount_validator)

        self.team_validator = FieldValidator(
            self.team_cb,
            self._validate_team_selection,
            self.logs,
            f"Producto {self.product_frame.idx+1} - Asignación {self.idx+1} colaborador",
            variables=[self.team_var, self.monto_var],
        )
        self.team_validator.add_widget(monto_entry)
        self.validators.append(self.team_validator)

    def get_data(self):
        return {
            "id_colaborador": self.team_var.get().strip(),
            "monto_asignado": self.monto_var.get().strip(),
        }

    def update_team_options(self):
        options = self.team_getter()
        self.team_cb['values'] = options
        current_value = self.team_var.get().strip()
        if not current_value:
            return
        known_ids = {option.strip() for option in options if option and option.strip()}
        if current_value not in known_ids:
            message = (
                "El colaborador seleccionado ya no está disponible. Selecciona un nuevo colaborador."
            )
            if self.team_validator:
                self.team_validator.show_custom_error(message)
            else:
                messagebox.showerror("Colaborador eliminado", message)
            self._notify_summary_change()

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar esta asignación?"):
            self.product_frame.log_change(
                f"Se eliminó asignación de colaborador en producto {self.product_frame.idx+1}"
            )
            self.frame.destroy()
            self.remove_callback(self)

    def _handle_amount_focus_out(self):
        self.product_frame.log_change(
            f"Producto {self.product_frame.idx+1}, asignación {self.idx+1}: modificó monto"
        )
        self._notify_summary_change()

    def _handle_team_focus_out(self):
        self.product_frame.log_change(
            f"Producto {self.product_frame.idx+1}, asignación {self.idx+1}: modificó colaborador"
        )
        self._notify_summary_change()

    def _notify_summary_change(self):
        if hasattr(self.product_frame, 'schedule_summary_refresh'):
            self.product_frame.schedule_summary_refresh('involucramientos')

    def _get_known_team_ids(self):
        return {option.strip() for option in self.team_getter() if option and option.strip()}

    def _clear_if_completely_blank(self):
        if self.team_var.get().strip() or self.monto_var.get().strip():
            return

        def _clear():
            self.team_cb.set('')
            self.team_var.set('')
            self.monto_var.set('')

        if self.team_validator:
            self.team_validator.suppress_during(_clear)
        else:
            _clear()
        self._notify_summary_change()

    def _validate_team_selection(self):
        monto_text = self.monto_var.get().strip()
        team_value = self.team_var.get().strip()
        if not monto_text:
            if team_value:
                if team_value not in self._get_known_team_ids():
                    return "Debe seleccionar un colaborador válido."
                return "Debe ingresar un monto asignado para este colaborador."
            self._clear_if_completely_blank()
            return None
        if not team_value:
            return "Debe seleccionar un colaborador para este monto asignado."
        if team_value not in self._get_known_team_ids():
            return "Debe seleccionar un colaborador válido."
        return None

    def _validate_assignment_amount(self):
        message, _decimal_value, normalized_text = validate_money_bounds(
            self.monto_var.get(),
            "el monto asignado",
            allow_blank=True,
        )
        if not message and normalized_text != (self.monto_var.get() or "").strip():
            self.monto_var.set(normalized_text)
        return message


class ClaimRow:
    """Fila dinámica que captura los reclamos asociados a un producto."""

    def __init__(self, parent, product_frame, idx, remove_callback, logs, tooltip_register):
        self.parent = parent
        self.product_frame = product_frame
        self.idx = idx
        self.remove_callback = remove_callback
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []

        self.id_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.code_var = tk.StringVar()

        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", pady=1)

        ttk.Label(self.frame, text="ID reclamo:").pack(side="left")
        id_entry = ttk.Entry(self.frame, textvariable=self.id_var, width=15)
        id_entry.pack(side="left", padx=5)
        self.tooltip_register(id_entry, "Número del reclamo (C + 8 dígitos).")

        ttk.Label(self.frame, text="Analítica nombre:").pack(side="left")
        name_entry = ttk.Entry(self.frame, textvariable=self.name_var, width=20)
        name_entry.pack(side="left", padx=5)
        self.tooltip_register(name_entry, "Nombre descriptivo de la analítica.")

        ttk.Label(self.frame, text="Código:").pack(side="left")
        code_entry = ttk.Entry(self.frame, textvariable=self.code_var, width=12)
        code_entry.pack(side="left", padx=5)
        self.tooltip_register(code_entry, "Código numérico de 10 dígitos.")

        remove_btn = ttk.Button(self.frame, text="Eliminar", command=self.remove)
        remove_btn.pack(side="left", padx=5)
        self.tooltip_register(remove_btn, "Elimina este reclamo del producto.")

        self.product_frame._register_lookup_sync(id_entry)
        self.product_frame._register_lookup_sync(name_entry)
        self.product_frame._register_lookup_sync(code_entry)

        self.validators.append(
            FieldValidator(
                id_entry,
                lambda: validate_reclamo_id(self.id_var.get()),
                self.logs,
                f"Producto {self.product_frame.idx+1} - Reclamo {self.idx+1} ID",
                variables=[self.id_var],
            )
        )
        self.validators.append(
            FieldValidator(
                name_entry,
                lambda: validate_required_text(
                    self.name_var.get(), "el nombre de la analítica"
                ),
                self.logs,
                f"Producto {self.product_frame.idx+1} - Reclamo {self.idx+1} Nombre analítica",
                variables=[self.name_var],
            )
        )

        self.validators.append(
            FieldValidator(
                code_entry,
                lambda: validate_codigo_analitica(self.code_var.get()),
                self.logs,
                f"Producto {self.product_frame.idx+1} - Reclamo {self.idx+1} Código",
                variables=[self.code_var],
            )
        )

    def get_data(self):
        return {
            "id_reclamo": self.id_var.get().strip(),
            "nombre_analitica": self.name_var.get().strip(),
            "codigo_analitica": self.code_var.get().strip(),
        }

    def set_data(self, data):
        self.id_var.set((data.get("id_reclamo") or "").strip())
        self.name_var.set((data.get("nombre_analitica") or "").strip())
        self.code_var.set((data.get("codigo_analitica") or "").strip())

    def is_empty(self):
        snapshot = self.get_data()
        return not any(snapshot.values())

    def remove(self):
        if messagebox.askyesno("Confirmar", "¿Desea eliminar este reclamo?"):
            self.product_frame.log_change(
                f"Se eliminó reclamo del producto {self.product_frame.idx+1}"
            )
            self.frame.destroy()
            self.remove_callback(self)


PRODUCT_MONEY_SPECS = (
    ("monto_investigado", "monto_inv_var", "Monto investigado", False, "inv"),
    ("monto_perdida_fraude", "monto_perdida_var", "Monto pérdida de fraude", True, "perdida"),
    ("monto_falla_procesos", "monto_falla_var", "Monto falla en procesos", True, "falla"),
    ("monto_contingencia", "monto_cont_var", "Monto contingencia", True, "contingencia"),
    ("monto_recuperado", "monto_rec_var", "Monto recuperado", True, "recuperado"),
    ("monto_pago_deuda", "monto_pago_var", "Monto pago de deuda", True, "pago"),
)


class ProductFrame:
    """Representa un producto y su interfaz en la sección de productos."""

    ENTITY_LABEL = "producto"

    def __init__(
        self,
        parent,
        idx,
        remove_callback,
        get_client_options,
        get_team_options,
        logs,
        product_lookup,
        tooltip_register,
        summary_refresh_callback=None,
        change_notifier=None,
        id_change_callback=None,
    ):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.get_client_options = get_client_options
        self.get_team_options = get_team_options
        self.logs = logs
        self.product_lookup = product_lookup or {}
        self.tooltip_register = tooltip_register
        self.validators = []
        self.client_validator = None
        self.involvements = []
        self.claims = []
        self._last_missing_lookup_id = None
        self.schedule_summary_refresh = summary_refresh_callback or (lambda _sections=None: None)
        self.change_notifier = change_notifier
        self.id_change_callback = id_change_callback
        self._last_tracked_id = ''

        self.id_var = tk.StringVar()
        self.client_var = tk.StringVar()
        taxonomy_keys = list(TAXONOMIA.keys())
        default_cat1 = taxonomy_keys[0] if taxonomy_keys else ""
        first_subcats = list(TAXONOMIA.get(default_cat1, {}).keys()) or ['']
        first_modalities = TAXONOMIA.get(default_cat1, {}).get(first_subcats[0], []) or ['']
        self.cat1_var = tk.StringVar()
        self.cat2_var = tk.StringVar()
        self.mod_var = tk.StringVar()
        self.canal_var = tk.StringVar()
        self.proceso_var = tk.StringVar()
        self.fecha_oc_var = tk.StringVar()
        self.fecha_desc_var = tk.StringVar()
        self.monto_inv_var = tk.StringVar()
        self.moneda_var = tk.StringVar()
        self.monto_perdida_var = tk.StringVar()
        self.monto_falla_var = tk.StringVar()
        self.monto_cont_var = tk.StringVar()
        self.monto_rec_var = tk.StringVar()
        self.monto_pago_var = tk.StringVar()
        self.tipo_prod_var = tk.StringVar()

        self.frame = ttk.LabelFrame(parent, text=f"Producto {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)

        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="ID del producto:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=5)
        id_entry.bind("<FocusOut>", lambda e: self.on_id_change(from_focus=True))
        id_entry.bind("<KeyRelease>", lambda e: self.on_id_change())
        self.tooltip_register(id_entry, "Código único del producto investigado.")
        ttk.Label(row1, text="Cliente:").pack(side="left")
        self.client_cb = ttk.Combobox(
            row1,
            textvariable=self.client_var,
            values=self.get_client_options(),
            state="readonly",
            width=20,
        )
        self.client_cb.pack(side="left", padx=5)
        self.client_cb.set('')
        self.client_cb.bind(
            "<FocusOut>",
            lambda e: self.log_change(f"Producto {self.idx+1}: seleccionó cliente"),
        )
        self.tooltip_register(self.client_cb, "Selecciona al cliente dueño del producto.")

        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="Categoría 1:").pack(side="left")
        cat1_cb = ttk.Combobox(row2, textvariable=self.cat1_var, values=list(TAXONOMIA.keys()), state="readonly", width=20)
        cat1_cb.pack(side="left", padx=5)
        cat1_cb.set('')
        cat1_cb.bind("<FocusOut>", lambda e: self.on_cat1_change())
        cat1_cb.bind("<<ComboboxSelected>>", lambda e: self.on_cat1_change())
        self.tooltip_register(cat1_cb, "Define la categoría principal del riesgo de producto.")
        ttk.Label(row2, text="Categoría 2:").pack(side="left")
        self.cat2_cb = ttk.Combobox(row2, textvariable=self.cat2_var, values=first_subcats, state="readonly", width=20)
        self.cat2_cb.pack(side="left", padx=5)
        self.cat2_cb.set('')
        self.cat2_cb.bind("<FocusOut>", lambda e: self.on_cat2_change())
        self.cat2_cb.bind("<<ComboboxSelected>>", lambda e: self.on_cat2_change())
        self.tooltip_register(self.cat2_cb, "Selecciona la subcategoría específica.")
        ttk.Label(row2, text="Modalidad:").pack(side="left")
        self.mod_cb = ttk.Combobox(row2, textvariable=self.mod_var, values=first_modalities, state="readonly", width=25)
        self.mod_cb.pack(side="left", padx=5)
        self.mod_cb.set('')
        self.tooltip_register(self.mod_cb, "Indica la modalidad concreta del fraude.")

        row3 = ttk.Frame(self.frame)
        row3.pack(fill="x", pady=1)
        ttk.Label(row3, text="Canal:").pack(side="left")
        canal_cb = ttk.Combobox(row3, textvariable=self.canal_var, values=CANAL_LIST, state="readonly", width=20)
        canal_cb.pack(side="left", padx=5)
        canal_cb.set('')
        self.tooltip_register(canal_cb, "Canal por donde ocurrió el evento.")
        ttk.Label(row3, text="Proceso:").pack(side="left")
        proc_cb = ttk.Combobox(row3, textvariable=self.proceso_var, values=PROCESO_LIST, state="readonly", width=25)
        proc_cb.pack(side="left", padx=5)
        proc_cb.set('')
        self.tooltip_register(proc_cb, "Proceso impactado por el incidente.")
        ttk.Label(row3, text="Tipo de producto:").pack(side="left")
        tipo_prod_cb = ttk.Combobox(
            row3,
            textvariable=self.tipo_prod_var,
            values=TIPO_PRODUCTO_LIST,
            state="readonly",
            width=25,
        )
        tipo_prod_cb.pack(side="left", padx=5)
        tipo_prod_cb.set('')
        self.tooltip_register(tipo_prod_cb, "Clasificación comercial del producto.")

        row4 = ttk.Frame(self.frame)
        row4.pack(fill="x", pady=1)
        ttk.Label(row4, text="Fecha de ocurrencia (YYYY-MM-DD):").pack(side="left")
        focc_entry = ttk.Entry(row4, textvariable=self.fecha_oc_var, width=15)
        focc_entry.pack(side="left", padx=5)
        self.tooltip_register(focc_entry, "Fecha exacta del evento.")
        ttk.Label(row4, text="Fecha de descubrimiento (YYYY-MM-DD):").pack(side="left")
        fdesc_entry = ttk.Entry(row4, textvariable=self.fecha_desc_var, width=15)
        fdesc_entry.pack(side="left", padx=5)
        self.tooltip_register(fdesc_entry, "Fecha en la que se detectó el evento.")

        row5 = ttk.Frame(self.frame)
        row5.pack(fill="x", pady=1)
        ttk.Label(row5, text="Monto investigado:").pack(side="left")
        inv_entry = ttk.Entry(row5, textvariable=self.monto_inv_var, width=15)
        inv_entry.pack(side="left", padx=5)
        self.tooltip_register(inv_entry, "Monto total bajo investigación.")
        ttk.Label(row5, text="Moneda:").pack(side="left")
        moneda_cb = ttk.Combobox(row5, textvariable=self.moneda_var, values=TIPO_MONEDA_LIST, state="readonly", width=12)
        moneda_cb.pack(side="left", padx=5)
        moneda_cb.set('')
        self.tooltip_register(moneda_cb, "Tipo de moneda principal del caso.")

        row6 = ttk.Frame(self.frame)
        row6.pack(fill="x", pady=1)
        ttk.Label(row6, text="Monto pérdida fraude:").pack(side="left")
        perdida_entry = ttk.Entry(row6, textvariable=self.monto_perdida_var, width=12)
        perdida_entry.pack(side="left", padx=5)
        self.tooltip_register(perdida_entry, "Monto directo perdido por fraude.")
        ttk.Label(row6, text="Monto falla procesos:").pack(side="left")
        falla_entry = ttk.Entry(row6, textvariable=self.monto_falla_var, width=12)
        falla_entry.pack(side="left", padx=5)
        self.tooltip_register(falla_entry, "Monto asociado a fallas de proceso.")
        ttk.Label(row6, text="Monto contingencia:").pack(side="left")
        cont_entry = ttk.Entry(row6, textvariable=self.monto_cont_var, width=12)
        cont_entry.pack(side="left", padx=5)
        self.tooltip_register(cont_entry, "Monto reservado por contingencias.")
        ttk.Label(row6, text="Monto recuperado:").pack(side="left")
        rec_entry = ttk.Entry(row6, textvariable=self.monto_rec_var, width=12)
        rec_entry.pack(side="left", padx=5)
        self.tooltip_register(rec_entry, "Monto efectivamente recuperado.")
        ttk.Label(row6, text="Monto pago deuda:").pack(side="left")
        pago_entry = ttk.Entry(row6, textvariable=self.monto_pago_var, width=12)
        pago_entry.pack(side="left", padx=5)
        self.tooltip_register(pago_entry, "Pago realizado por deuda vinculada.")

        self.claims_frame = ttk.LabelFrame(self.frame, text="Reclamos asociados")
        self.claims_frame.pack(fill="x", padx=5, pady=5)
        claim_add_btn = ttk.Button(self.claims_frame, text="Añadir reclamo", command=self.add_claim)
        claim_add_btn.pack(anchor="e", padx=5, pady=2)
        self.tooltip_register(claim_add_btn, "Agrega un reclamo adicional al producto.")

        self.invol_frame = ttk.LabelFrame(self.frame, text="Involucramiento de colaboradores")
        self.invol_frame.pack(fill="x", padx=5, pady=5)
        inv_add_btn = ttk.Button(self.invol_frame, text="Añadir involucrado", command=self.add_involvement)
        inv_add_btn.pack(anchor="e", padx=5, pady=2)
        self.tooltip_register(inv_add_btn, "Registra un colaborador asociado a este producto.")

        self.validators.append(
            FieldValidator(
                id_entry,
                lambda: validate_product_id(self.tipo_prod_var.get(), self.id_var.get()),
                self.logs,
                f"Producto {self.idx+1} - ID",
                variables=[self.id_var, self.tipo_prod_var],
            )
        )
        self.client_validator = FieldValidator(
            self.client_cb,
            lambda: validate_required_text(self.client_var.get(), "el cliente del producto"),
            self.logs,
            f"Producto {self.idx+1} - Cliente",
            variables=[self.client_var],
        )
        self._register_product_catalog_validators(
            canal_cb,
            proc_cb,
            moneda_cb,
        )

        self.validators.extend(
            [
                FieldValidator(
                    cat1_cb,
                    lambda: validate_required_text(self.cat1_var.get(), "la categoría 1"),
                    self.logs,
                    f"Producto {self.idx+1} - Categoría 1",
                    variables=[self.cat1_var],
                ),
                FieldValidator(
                    self.cat2_cb,
                    lambda: validate_required_text(self.cat2_var.get(), "la categoría 2"),
                    self.logs,
                    f"Producto {self.idx+1} - Categoría 2",
                    variables=[self.cat2_var],
                ),
                FieldValidator(
                    self.mod_cb,
                    lambda: validate_required_text(self.mod_var.get(), "la modalidad"),
                    self.logs,
                    f"Producto {self.idx+1} - Modalidad",
                    variables=[self.mod_var],
                ),
                FieldValidator(
                    tipo_prod_cb,
                    lambda: validate_required_text(self.tipo_prod_var.get(), "el tipo de producto"),
                    self.logs,
                    f"Producto {self.idx+1} - Tipo de producto",
                    variables=[self.tipo_prod_var],
                ),
                FieldValidator(
                    focc_entry,
                    lambda: validate_date_text(self.fecha_oc_var.get(), "la fecha de ocurrencia", allow_blank=False),
                    self.logs,
                    f"Producto {self.idx+1} - Fecha ocurrencia",
                    variables=[self.fecha_oc_var],
                ),
                FieldValidator(
                    fdesc_entry,
                    self._validate_fecha_descubrimiento,
                    self.logs,
                    f"Producto {self.idx+1} - Fecha descubrimiento",
                    variables=[self.fecha_desc_var, self.fecha_oc_var],
                ),
                FieldValidator(
                    inv_entry,
                    self._build_amount_validator(self.monto_inv_var, "el monto investigado", False),
                    self.logs,
                    f"Producto {self.idx+1} - Monto investigado",
                    variables=[self.monto_inv_var],
                ),
                FieldValidator(
                    perdida_entry,
                    self._build_amount_validator(self.monto_perdida_var, "el monto pérdida de fraude", True),
                    self.logs,
                    f"Producto {self.idx+1} - Monto pérdida fraude",
                    variables=[self.monto_perdida_var],
                ),
                FieldValidator(
                    falla_entry,
                    self._build_amount_validator(self.monto_falla_var, "el monto falla de procesos", True),
                    self.logs,
                    f"Producto {self.idx+1} - Monto falla procesos",
                    variables=[self.monto_falla_var],
                ),
                FieldValidator(
                    cont_entry,
                    self._build_amount_validator(self.monto_cont_var, "el monto contingencia", True),
                    self.logs,
                    f"Producto {self.idx+1} - Monto contingencia",
                    variables=[self.monto_cont_var],
                ),
                FieldValidator(
                    rec_entry,
                    self._build_amount_validator(self.monto_rec_var, "el monto recuperado", True),
                    self.logs,
                    f"Producto {self.idx+1} - Monto recuperado",
                    variables=[self.monto_rec_var],
                ),
                FieldValidator(
                    pago_entry,
                    self._build_amount_validator(self.monto_pago_var, "el monto pago de deuda", True),
                    self.logs,
                    f"Producto {self.idx+1} - Pago de deuda",
                    variables=[self.monto_pago_var],
                ),
            ]
        )

        amount_vars = [
            self.monto_inv_var,
            self.monto_perdida_var,
            self.monto_falla_var,
            self.monto_cont_var,
            self.monto_rec_var,
            self.monto_pago_var,
        ]
        shared_amount_vars = amount_vars + [self.tipo_prod_var]
        self._create_amount_consistency_validators(
            shared_amount_vars,
            {
                'inv': (inv_entry, "Monto investigado"),
                'recuperado': (rec_entry, "Monto recuperado"),
                'pago': (pago_entry, "Monto pago de deuda"),
                'contingencia': (cont_entry, "Monto contingencia"),
            },
        )

    def on_cat1_change(self):
        cat1 = self.cat1_var.get()
        subcats = list(TAXONOMIA.get(cat1, {}).keys()) or [""]
        previous_cat2 = self.cat2_var.get()
        self.cat2_cb['values'] = subcats

        if previous_cat2 in subcats:
            self.cat2_var.set(previous_cat2)
            self.cat2_cb.set(previous_cat2)
        else:
            self.cat2_var.set('')
            self.cat2_cb.set('')

        # Always refresh modalidades to keep them aligned with the selected categorías
        self.on_cat2_change()
        self.log_change(f"Producto {self.idx+1}: cambió categoría 1")

    def on_cat2_change(self):
        cat1 = self.cat1_var.get()
        cat2 = self.cat2_var.get()
        modalities = TAXONOMIA.get(cat1, {}).get(cat2, []) or ['']
        self.mod_cb['values'] = modalities
        self.mod_var.set('')
        self.mod_cb.set('')
        self.log_change(f"Producto {self.idx+1}: cambió categoría 2")

    def add_claim(self):
        idx = len(self.claims)
        row = ClaimRow(self.claims_frame, self, idx, self.remove_claim, self.logs, self.tooltip_register)
        self.claims.append(row)
        self.schedule_summary_refresh('reclamos')
        self.persist_lookup_snapshot()
        return row

    def remove_claim(self, row):
        if row in self.claims:
            self.claims.remove(row)
        if not self.claims:
            self.add_claim()
        self.schedule_summary_refresh('reclamos')
        self.persist_lookup_snapshot()

    def clear_claims(self):
        for claim in self.claims:
            claim.frame.destroy()
        self.claims.clear()

    def set_claims_from_data(self, claims):
        self.clear_claims()
        added = False
        for claim_data in claims or []:
            if not isinstance(claim_data, dict):
                continue
            row = self.add_claim()
            row.set_data(claim_data)
            added = True
        if not added:
            self.add_claim()
        self.schedule_summary_refresh('reclamos')
        self.persist_lookup_snapshot()

    def _create_amount_consistency_validators(self, variables, widget_map):
        for key, (widget, label) in widget_map.items():
            validator = FieldValidator(
                widget,
                lambda key=key: self._validate_montos_consistentes(key),
                self.logs,
                f"Producto {self.idx+1} - Consistencia de montos ({label})",
                variables=variables,
            )
            self.validators.append(validator)

    def _register_product_catalog_validators(self, canal_cb, proc_cb, moneda_cb):
        catalog_specs = [
            (
                canal_cb,
                self.canal_var,
                "el canal del producto",
                CANAL_LIST,
                "canales",
                "Canal",
            ),
            (
                proc_cb,
                self.proceso_var,
                "el proceso del producto",
                PROCESO_LIST,
                "procesos",
                "Proceso",
            ),
            (
                moneda_cb,
                self.moneda_var,
                "la moneda del producto",
                TIPO_MONEDA_LIST,
                "tipos de moneda",
                "Moneda",
            ),
        ]

        for widget, variable, label, catalog, catalog_label, log_suffix in catalog_specs:
            self.validators.append(
                FieldValidator(
                    widget,
                    lambda var=variable, label=label, catalog=catalog, catalog_label=catalog_label: self._validate_catalog_selection(
                        var.get(),
                        label,
                        catalog,
                        catalog_label,
                    ),
                    self.logs,
                    f"Producto {self.idx+1} - {log_suffix}",
                    variables=[variable],
                )
            )

    def obtain_claim_slot(self):
        empty = next((claim for claim in self.claims if claim.is_empty()), None)
        if empty:
            return empty
        return self.add_claim()

    def find_claim_by_id(self, claim_id):
        claim_id = (claim_id or '').strip()
        if not claim_id:
            return None
        for claim in self.claims:
            if claim.id_var.get().strip() == claim_id:
                return claim
        return None

    def claims_have_content(self):
        return any(not claim.is_empty() for claim in self.claims)

    def _normalize_claim_dict(self, payload):
        return {
            'id_reclamo': (payload.get('id_reclamo') or '').strip(),
            'nombre_analitica': (payload.get('nombre_analitica') or '').strip(),
            'codigo_analitica': (payload.get('codigo_analitica') or '').strip(),
        }

    def extract_claims_from_payload(self, payload):
        claims = payload.get('reclamos') if isinstance(payload, dict) else None
        normalized = []
        if isinstance(claims, list):
            for item in claims:
                if isinstance(item, dict):
                    claim_data = self._normalize_claim_dict(item)
                    if any(claim_data.values()):
                        normalized.append(claim_data)
        if not normalized:
            legacy = self._normalize_claim_dict(payload)
            if any(legacy.values()):
                normalized.append(legacy)
        return normalized

    def add_involvement(self):
        idx = len(self.involvements)
        row = InvolvementRow(self.invol_frame, self, idx, self.get_team_options, self.remove_involvement, self.logs, self.tooltip_register)
        self.involvements.append(row)
        self.schedule_summary_refresh('involucramientos')
        return row

    def remove_involvement(self, row):
        if row in self.involvements:
            self.involvements.remove(row)
        self.schedule_summary_refresh('involucramientos')

    def update_client_options(self):
        current = self.client_var.get().strip()
        options = self.get_client_options()
        self.client_cb['values'] = options
        if current and current in options:
            self.client_cb.set(current)
            self.client_var.set(current)
            return

        def _clear_selection():
            self.client_var.set('')
            self.client_cb.set('')

        if self.client_validator:
            self.client_validator.suppress_during(_clear_selection)
        else:
            _clear_selection()

        if current and self.client_validator:
            warning_msg = (
                f"Cliente {current} eliminado. Selecciona un nuevo titular para este producto."
            )
            self.client_validator.show_custom_error(warning_msg)

    def update_team_options(self):
        for inv in self.involvements:
            inv.update_team_options()

    def _register_lookup_sync(self, widget):
        if widget is None:
            return
        widget.bind("<FocusOut>", self._handle_lookup_sync_event, add="+")
        widget.bind("<Return>", self._handle_lookup_sync_event, add="+")
        if isinstance(widget, ttk.Combobox):
            widget.bind("<<ComboboxSelected>>", self._handle_lookup_sync_event, add="+")

    def _handle_lookup_sync_event(self, *_args):
        self.persist_lookup_snapshot()

    def persist_lookup_snapshot(self):
        if not isinstance(self.product_lookup, dict):
            return
        product_id = self.id_var.get().strip()
        if not product_id:
            return
        self.product_lookup[product_id] = {
            'id_cliente': self.client_var.get().strip(),
            'tipo_producto': self.tipo_prod_var.get(),
            'categoria1': self.cat1_var.get(),
            'categoria2': self.cat2_var.get(),
            'modalidad': self.mod_var.get(),
            'canal': self.canal_var.get(),
            'proceso': self.proceso_var.get(),
            'fecha_ocurrencia': self.fecha_oc_var.get().strip(),
            'fecha_descubrimiento': self.fecha_desc_var.get().strip(),
            'monto_investigado': self.monto_inv_var.get().strip(),
            'tipo_moneda': self.moneda_var.get(),
            'monto_perdida_fraude': self.monto_perdida_var.get().strip(),
            'monto_falla_procesos': self.monto_falla_var.get().strip(),
            'monto_contingencia': self.monto_cont_var.get().strip(),
            'monto_recuperado': self.monto_rec_var.get().strip(),
            'monto_pago_deuda': self.monto_pago_var.get().strip(),
            'reclamos': [
                claim_data
                for claim in self.claims
                for claim_data in [claim.get_data()]
                if any(claim_data.values())
            ],
        }

    def set_product_lookup(self, lookup):
        self.product_lookup = lookup or {}
        self._last_missing_lookup_id = None

    def on_id_change(self, from_focus=False, preserve_existing=False, silent=False):
        pid = self.id_var.get().strip()
        self._notify_id_change(pid)
        if not silent:
            self.log_change(f"Producto {self.idx+1}: modificó ID a {pid}")
        if not pid:
            self._last_missing_lookup_id = None
            self.schedule_summary_refresh({'productos', 'reclamos'})
            return
        data = self.product_lookup.get(pid)
        if not data:
            if from_focus and not silent and self.product_lookup and self._last_missing_lookup_id != pid:
                messagebox.showerror(
                    "Producto no encontrado",
                    (
                        f"El ID {pid} no existe en los catálogos de detalle. "
                        "Verifica el código o actualiza product_details.csv."
                    ),
                )
                self._last_missing_lookup_id = pid
            self.schedule_summary_refresh({'productos', 'reclamos'})
            return

        def set_if_present(var, key):
            value = data.get(key)
            if value in (None, ""):
                return
            text_value = str(value).strip()
            if text_value and should_autofill_field(var.get(), preserve_existing):
                var.set(text_value)

        client_id = data.get('id_cliente')
        if client_id:
            values = list(self.client_cb['values'])
            if client_id not in values:
                values.append(client_id)
                self.client_cb['values'] = values
            self.client_var.set(client_id)
            self.client_cb.set(client_id)
        set_if_present(self.canal_var, 'canal')
        set_if_present(self.proceso_var, 'proceso')
        set_if_present(self.tipo_prod_var, 'tipo_producto')
        set_if_present(self.fecha_oc_var, 'fecha_ocurrencia')
        set_if_present(self.fecha_desc_var, 'fecha_descubrimiento')
        set_if_present(self.monto_inv_var, 'monto_investigado')
        set_if_present(self.moneda_var, 'tipo_moneda')
        set_if_present(self.monto_perdida_var, 'monto_perdida_fraude')
        set_if_present(self.monto_falla_var, 'monto_falla_procesos')
        set_if_present(self.monto_cont_var, 'monto_contingencia')
        set_if_present(self.monto_rec_var, 'monto_recuperado')
        set_if_present(self.monto_pago_var, 'monto_pago_deuda')
        cat1 = data.get('categoria1')
        cat2 = data.get('categoria2')
        mod = data.get('modalidad')
        if cat1 in TAXONOMIA:
            self.cat1_var.set(cat1)
            self.on_cat1_change()
            if cat2 in TAXONOMIA[cat1]:
                self.cat2_var.set(cat2)
                self.cat2_cb.set(cat2)
                self.on_cat2_change()
                if mod in TAXONOMIA[cat1][cat2]:
                    self.mod_var.set(mod)
                    self.mod_cb.set(mod)
        claims_payload = self.extract_claims_from_payload(data)
        if claims_payload:
            if not (preserve_existing and self.claims_have_content()):
                self.set_claims_from_data(claims_payload)
        self._last_missing_lookup_id = None
        self.log_change(f"Producto {self.idx+1}: autopoblado desde catálogo")
        self.schedule_summary_refresh({'productos', 'reclamos'})
        self.persist_lookup_snapshot()

    def _notify_id_change(self, new_id):
        if new_id == self._last_tracked_id:
            return
        previous = self._last_tracked_id
        self._last_tracked_id = new_id
        if callable(self.id_change_callback):
            self.id_change_callback(self, previous, new_id)

    def _validate_fecha_descubrimiento(self):
        msg = validate_date_text(self.fecha_desc_var.get(), "la fecha de descubrimiento", allow_blank=False)
        if msg:
            return msg
        producto_label = self.id_var.get().strip() or f"Producto {self.idx+1}"
        return validate_product_dates(
            producto_label,
            self.fecha_oc_var.get(),
            self.fecha_desc_var.get(),
        )

    def _validate_amount_field(self, var, label, allow_blank):
        raw_value = var.get()
        stripped = (raw_value or "").strip()
        if allow_blank and not stripped:
            var.set("0.00")
            return None, Decimal("0.00")
        message, decimal_value, normalized_text = validate_money_bounds(
            raw_value,
            label,
            allow_blank=allow_blank,
        )
        if not message and normalized_text != stripped:
            var.set(normalized_text)
        return message, decimal_value

    def _build_amount_validator(self, var, label, allow_blank):
        def _validate():
            message, _ = self._validate_amount_field(var, label, allow_blank)
            return message

        return _validate

    def _collect_amount_values(self):
        values = {}
        for _, var_attr, label, allow_blank, key in PRODUCT_MONEY_SPECS:
            var = getattr(self, var_attr)
            message, decimal_value = self._validate_amount_field(var, label, allow_blank)
            if message:
                return None
            values[key] = decimal_value if decimal_value is not None else Decimal('0')
        return values

    def _validate_montos_consistentes(self, target_key: str | None = None):
        values = self._collect_amount_values()
        if values is None:
            return None
        componentes = sum_investigation_components(
            perdida=values['perdida'],
            falla=values['falla'],
            contingencia=values['contingencia'],
            recuperado=values['recuperado'],
        )
        errors = {}
        if componentes != values['inv']:
            errors['inv'] = (
                "La suma de las cuatro partidas (pérdida, falla, contingencia y recuperación) "
                "debe ser igual al monto investigado."
            )
        if values['recuperado'] > values['inv']:
            errors['recuperado'] = "El monto recuperado no puede superar el monto investigado."
        if values['pago'] > values['inv']:
            errors['pago'] = "El pago de deuda no puede ser mayor al monto investigado."
        tipo_prod = normalize_without_accents(self.tipo_prod_var.get()).lower()
        if any(word in tipo_prod for word in ('credito', 'tarjeta')):
            if values['contingencia'] != values['inv']:
                errors['contingencia'] = (
                    "El monto de contingencia debe ser igual al monto investigado para créditos o tarjetas."
                )
        target = target_key or 'inv'
        return errors.get(target)

    def _validate_catalog_selection(self, value, label, catalog, catalog_label):
        message = validate_required_text(value, label)
        if message:
            return message
        normalized = (value or '').strip()
        if normalized not in catalog:
            return f"El valor '{value}' no está en el catálogo CM de {catalog_label}."
        return None

    def get_data(self):
        producto_data = {
            "id_producto": self.id_var.get().strip(),
            "id_caso": "",
            "id_cliente": self.client_var.get().strip(),
            "categoria1": self.cat1_var.get(),
            "categoria2": self.cat2_var.get(),
            "modalidad": self.mod_var.get(),
            "canal": self.canal_var.get(),
            "proceso": self.proceso_var.get(),
            "fecha_ocurrencia": self.fecha_oc_var.get().strip(),
            "fecha_descubrimiento": self.fecha_desc_var.get().strip(),
            "monto_investigado": self.monto_inv_var.get().strip(),
            "tipo_moneda": self.moneda_var.get(),
            "monto_perdida_fraude": self.monto_perdida_var.get().strip(),
            "monto_falla_procesos": self.monto_falla_var.get().strip(),
            "monto_contingencia": self.monto_cont_var.get().strip(),
            "monto_recuperado": self.monto_rec_var.get().strip(),
            "monto_pago_deuda": self.monto_pago_var.get().strip(),
            "tipo_producto": self.tipo_prod_var.get(),
        }
        self._normalize_optional_amount_strings(producto_data)
        return {
            "producto": producto_data,
            "reclamos": [claim.get_data() for claim in self.claims],
            "asignaciones": [
                data
                for data in (inv.get_data() for inv in self.involvements)
                if any(data.values())
            ],
        }

    def _normalize_optional_amount_strings(self, producto_data):
        for field_name, var_attr, _label, allow_blank, _ in PRODUCT_MONEY_SPECS:
            if not allow_blank:
                continue
            current_value = (producto_data.get(field_name) or "").strip()
            if current_value:
                continue
            producto_data[field_name] = "0.00"
            getattr(self, var_attr).set("0.00")

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el producto {self.idx+1}?"):
            self.log_change(f"Se eliminó producto {self.idx+1}")
            self.frame.destroy()
            self.remove_callback(self)

    def log_change(self, message: str):
        if callable(self.change_notifier):
            self.change_notifier(message)
        else:
            log_event("navegacion", message, self.logs)


__all__ = [
    "ClaimRow",
    "InvolvementRow",
    "PRODUCT_MONEY_SPECS",
    "ProductFrame",
]
