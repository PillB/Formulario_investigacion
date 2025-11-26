"""Componentes de interfaz relacionados a productos, reclamos e involucramientos."""

from __future__ import annotations

from decimal import Decimal

import tkinter as tk
from tkinter import messagebox, ttk

from settings import (CANAL_LIST, PROCESO_LIST, TAXONOMIA, TIPO_MONEDA_LIST,
                      TIPO_PRODUCTO_LIST)
from theme_manager import ThemeManager
from ui.config import COL_PADX, ROW_PADY
from ui.frames.utils import ensure_grid_support
from ui.layout import CollapsibleSection
from validators import (FieldValidator, log_event, normalize_without_accents,
                        should_autofill_field, sum_investigation_components,
                        validate_codigo_analitica, validate_date_text,
                        validate_money_bounds, validate_product_dates,
                        validate_product_id, validate_reclamo_id,
                        validate_required_text)

ENTRY_STYLE = ThemeManager.ENTRY_STYLE
COMBOBOX_STYLE = ThemeManager.COMBOBOX_STYLE
SPINBOX_STYLE = ThemeManager.SPINBOX_STYLE
BUTTON_STYLE = ThemeManager.BUTTON_STYLE


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

        self.section = self._create_section(parent)
        self.section.grid(
            row=idx + 1, column=0, columnspan=5, padx=COL_PADX, pady=ROW_PADY, sticky="we"
        )

        self.frame = ttk.Frame(self.section.content)
        ensure_grid_support(self.frame)
        if hasattr(self.frame, "grid_columnconfigure"):
            self.frame.grid_columnconfigure(1, weight=1)
            self.frame.grid_columnconfigure(3, weight=1)
        self.section.pack_content(self.frame, fill="x", expand=True)

        ttk.Label(self.frame, text="Colaborador:").grid(
            row=0, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        self.team_cb = ttk.Combobox(
            self.frame,
            textvariable=self.team_var,
            values=self.team_getter(),
            state="readonly",
            width=20,
            style=COMBOBOX_STYLE,
        )
        self.team_cb.grid(row=0, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.team_cb.set('')
        self.team_cb.bind("<FocusOut>", lambda _e: self._handle_team_focus_out(), add="+")
        self.team_cb.bind("<<ComboboxSelected>>", lambda _e: self._handle_team_focus_out(), add="+")
        self.tooltip_register(self.team_cb, "Elige al colaborador que participa en este producto.")

        ttk.Label(self.frame, text="Monto asignado:").grid(
            row=0, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        monto_entry = ttk.Entry(
            self.frame, textvariable=self.monto_var, width=15, style=ENTRY_STYLE
        )
        monto_entry.grid(row=0, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        monto_entry.bind("<FocusOut>", lambda _e: self._handle_amount_focus_out(), add="+")
        self.tooltip_register(monto_entry, "Monto en soles asignado a este colaborador.")

        remove_btn = ttk.Button(
            self.frame, text="Eliminar", command=self.remove, style=BUTTON_STYLE
        )
        remove_btn.grid(row=0, column=4, padx=COL_PADX, pady=ROW_PADY, sticky="e")
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

        self._register_title_traces()
        self._sync_section_title()

    def _create_section(self, parent):
        try:
            return CollapsibleSection(
                parent,
                title="",
                on_toggle=lambda _section: self._sync_section_title(),
            )
        except Exception as exc:
            log_event(
                "validacion",
                f"No se pudo crear sección colapsable para involucramiento {self.idx+1}: {exc}",
                self.logs,
            )
            fallback = ttk.Frame(parent)
            ensure_grid_support(fallback)
            fallback.content = ttk.Frame(fallback)
            ensure_grid_support(fallback.content)
            fallback.content.pack(fill="both", expand=True)

            def _pack_content(widget, **pack_kwargs):
                defaults = {"fill": "both", "expand": True}
                defaults.update(pack_kwargs)
                widget.pack(**defaults)
                return widget

            fallback.pack_content = _pack_content  # type: ignore[attr-defined]
            fallback.is_open = True  # type: ignore[attr-defined]
            fallback.set_title = lambda _title: None  # type: ignore[attr-defined]
            return fallback

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
            if getattr(self, "section", None):
                self.section.destroy()
            else:
                self.frame.destroy()
            self.remove_callback(self)

    def _handle_amount_focus_out(self):
        self.product_frame.log_change(
            f"Producto {self.product_frame.idx+1}, asignación {self.idx+1}: modificó monto"
        )
        self.product_frame.trigger_duplicate_check()

    def _handle_team_focus_out(self):
        self.product_frame.log_change(
            f"Producto {self.product_frame.idx+1}, asignación {self.idx+1}: modificó colaborador"
        )
        self.product_frame.trigger_duplicate_check()

    def _notify_summary_change(self):
        self.product_frame._schedule_product_summary_refresh()

    def _register_title_traces(self):
        for var in (self.team_var, self.monto_var):
            trace_add = getattr(var, "trace_add", None)
            if callable(trace_add):
                trace_add("write", self._sync_section_title)

    def _build_section_title(self) -> str:
        base_title = f"Asignación {self.idx+1}"
        if getattr(self, "section", None) and not self.section.is_open:
            team_value = self.team_var.get().strip()
            monto_value = self.monto_var.get().strip()
            details = [value for value in (team_value, monto_value) if value]
            if details:
                base_title = f"{base_title} – {' | '.join(details)}"
        return base_title

    def _sync_section_title(self, *_args):
        if not getattr(self, "section", None):
            return
        set_title = getattr(self.section, "set_title", None)
        if callable(set_title):
            self.section.set_title(self._build_section_title())

    def _create_section(self, parent):
        try:
            return CollapsibleSection(
                parent, title="", on_toggle=lambda _section: self._sync_section_title()
            )
        except Exception as exc:
            log_event(
                "validacion",
                f"No se pudo crear sección colapsable para reclamo {self.idx+1}: {exc}",
                self.logs,
            )
            fallback = ttk.Frame(parent)
            ensure_grid_support(fallback)
            fallback.content = ttk.Frame(fallback)
            ensure_grid_support(fallback.content)
            fallback.content.pack(fill="both", expand=True)

            def _pack_content(widget, **pack_kwargs):
                defaults = {"fill": "both", "expand": True}
                defaults.update(pack_kwargs)
                widget.pack(**defaults)
                return widget

            fallback.pack_content = _pack_content  # type: ignore[attr-defined]
            fallback.is_open = True  # type: ignore[attr-defined]
            fallback.set_title = lambda _title: None  # type: ignore[attr-defined]
            return fallback

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

    def clear_values(self):
        """Limpia las variables asociadas sin eliminar el UI."""

        def _reset():
            self.team_var.set("")
            self.monto_var.set("")
            try:
                self.team_cb.set("")
            except Exception:
                pass

        managed = False
        for validator in self.validators:
            suppress = getattr(validator, "suppress_during", None)
            if callable(suppress):
                suppress(_reset)
                managed = True
                break
        if not managed:
            _reset()


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
        self._claims_required = bool(getattr(product_frame, "claim_fields_required", True))
        self._refresh_after_id = None

        self.id_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.code_var = tk.StringVar()

        self.section = self._create_section(parent)
        self.section.grid(
            row=idx + 1, column=0, columnspan=5, padx=COL_PADX, pady=ROW_PADY, sticky="we"
        )

        self.frame = ttk.Frame(self.section.content)
        ensure_grid_support(self.frame)
        if hasattr(self.frame, "grid_columnconfigure"):
            self.frame.grid_columnconfigure(1, weight=1)
            self.frame.grid_columnconfigure(3, weight=1)
        self.section.pack_content(self.frame, fill="x", expand=True)

        ttk.Label(self.frame, text="ID reclamo:").grid(
            row=0, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        id_entry = ttk.Entry(
            self.frame, textvariable=self.id_var, width=15, style=ENTRY_STYLE
        )
        id_entry.grid(row=0, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.id_entry = id_entry
        self.tooltip_register(id_entry, "Número del reclamo (C + 8 dígitos).")
        self._bind_identifier_triggers(id_entry)

        ttk.Label(self.frame, text="Código:").grid(
            row=0, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        code_entry = ttk.Entry(
            self.frame, textvariable=self.code_var, width=12, style=ENTRY_STYLE
        )
        code_entry.grid(row=0, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.code_entry = code_entry
        self.tooltip_register(code_entry, "Código numérico de 10 dígitos.")
        self._bind_claim_field_triggers(code_entry)

        ttk.Label(self.frame, text="Analítica nombre:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        name_entry = ttk.Entry(
            self.frame, textvariable=self.name_var, width=20, style=ENTRY_STYLE
        )
        name_entry.grid(row=1, column=1, columnspan=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.name_entry = name_entry
        self.tooltip_register(name_entry, "Nombre descriptivo de la analítica.")
        self._bind_claim_field_triggers(name_entry)

        remove_btn = ttk.Button(
            self.frame, text="Eliminar", command=self.remove, style=BUTTON_STYLE
        )
        remove_btn.grid(row=0, column=4, rowspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="e")
        self.tooltip_register(remove_btn, "Elimina este reclamo del producto.")

        self.product_frame._register_lookup_sync(id_entry)
        self.product_frame._register_lookup_sync(name_entry)
        self.product_frame._register_lookup_sync(code_entry)

        self.id_validator = FieldValidator(
            id_entry,
            self._validate_claim_id,
            self.logs,
            f"Producto {self.product_frame.idx+1} - Reclamo {self.idx+1} ID",
            variables=[self.id_var],
        )
        self.validators.append(self.id_validator)
        self.name_validator = FieldValidator(
            name_entry,
            self._validate_claim_name,
            self.logs,
            f"Producto {self.product_frame.idx+1} - Reclamo {self.idx+1} Nombre analítica",
            variables=[self.name_var],
        )
        self.validators.append(self.name_validator)

        self.code_validator = FieldValidator(
            code_entry,
            self._validate_claim_code,
            self.logs,
            f"Producto {self.product_frame.idx+1} - Reclamo {self.idx+1} Código",
            variables=[self.code_var],
        )
        self.validators.append(self.code_validator)

        self._last_missing_lookup_id = None
        self._last_summary_snapshot = self.get_data()

        self._register_title_traces()
        self._sync_section_title()

    def _bind_identifier_triggers(self, widget) -> None:
        widget.bind("<FocusOut>", lambda _e: self.on_id_change(from_focus=True), add="+")
        widget.bind("<KeyRelease>", lambda _e: self.on_id_change(), add="+")
        widget.bind("<Return>", lambda _e: self.on_id_change(from_focus=True), add="+")
        widget.bind("<<Paste>>", lambda _e: self.on_id_change(), add="+")
        widget.bind("<<ComboboxSelected>>", lambda _e: self.on_id_change(from_focus=True), add="+")

    def _bind_claim_field_triggers(self, widget) -> None:
        for event_name in ("<FocusOut>", "<KeyRelease>", "<<Paste>>", "<<Cut>>"):
            widget.bind(event_name, lambda _e: self._refresh_claim_summary(), add="+")

    def _refresh_claim_summary(self):
        snapshot = self.get_data()
        if snapshot == getattr(self, "_last_summary_snapshot", None):
            return
        self._last_summary_snapshot = snapshot
        current_after_id = getattr(self, "_refresh_after_id", None)
        if current_after_id:
            try:
                self.frame.after_cancel(current_after_id)
            except Exception:
                self._refresh_after_id = None
        try:
            self._refresh_after_id = self.frame.after(120, self._run_claim_refresh)
        except Exception:
            self._refresh_after_id = None
            self._run_claim_refresh()

    def _run_claim_refresh(self):
        self._refresh_after_id = None
        refresher = getattr(self.product_frame, "schedule_summary_refresh", None)
        if callable(refresher):
            refresher('reclamos')

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
        self.on_id_change(preserve_existing=True, silent=True)
        self.set_claim_requirement(getattr(self.product_frame, "claim_fields_required", self._claims_required))
        refresher = getattr(self.product_frame, "refresh_claim_guidance", None)
        if callable(refresher):
            refresher()
        self._refresh_claim_summary()

    def on_id_change(self, from_focus=False, preserve_existing=False, silent=False):
        rid = self.id_var.get().strip()
        if not rid:
            self._last_missing_lookup_id = None
            self._refresh_claim_summary()
            return
        lookup = getattr(self.product_frame, "claim_lookup", None) or {}
        data = lookup.get(rid)
        if not data:
            if from_focus and not silent and lookup and self._last_missing_lookup_id != rid:
                messagebox.showerror(
                    "Reclamo no encontrado",
                    (
                        f"El ID {rid} no existe en los catálogos de detalle. "
                        "Verifica el código o actualiza claim_details.csv."
                    ),
                )
                self._last_missing_lookup_id = rid
            self._refresh_claim_summary()
            return

        def set_if_present(var, key):
            value = data.get(key)
            if value in (None, ""):
                return
            text_value = str(value).strip()
            if text_value and should_autofill_field(var.get(), preserve_existing):
                var.set(text_value)

        set_if_present(self.name_var, "nombre_analitica")
        set_if_present(self.code_var, "codigo_analitica")
        self._last_missing_lookup_id = None
        if not silent:
            self.product_frame.log_change(
                f"Producto {self.product_frame.idx+1}: autopobló reclamo {rid} desde catálogo"
            )
        self.product_frame.persist_lookup_snapshot()
        if from_focus:
            self.product_frame.trigger_duplicate_check()
        refresher = getattr(self.product_frame, "refresh_claim_guidance", None)
        if callable(refresher):
            refresher()
        self._refresh_claim_summary()

    def is_empty(self):
        snapshot = self.get_data()
        return not any(snapshot.values())

    def remove(self):
        if messagebox.askyesno("Confirmar", "¿Desea eliminar este reclamo?"):
            self.product_frame.log_change(
                f"Se eliminó reclamo del producto {self.product_frame.idx+1}"
            )
            if getattr(self, "section", None):
                self.section.destroy()
            else:
                self.frame.destroy()
            self.remove_callback(self)

    def set_claim_requirement(self, required: bool):
        previously_required = self._claims_required
        self._claims_required = required
        if previously_required and not required:
            for validator in self.validators:
                validator.show_custom_error(None)

    def _register_title_traces(self):
        for var in (self.id_var, self.name_var):
            trace_add = getattr(var, "trace_add", None)
            if callable(trace_add):
                trace_add("write", self._sync_section_title)

    def _build_section_title(self) -> str:
        base_title = f"Reclamo {self.idx+1}"
        if getattr(self, "section", None) and not self.section.is_open:
            rid = self.id_var.get().strip()
            name = self.name_var.get().strip()
            details = [value for value in (rid, name) if value]
            if details:
                base_title = f"{base_title} – {' | '.join(details)}"
        return base_title

    def _sync_section_title(self, *_args):
        if not getattr(self, "section", None):
            return
        set_title = getattr(self.section, "set_title", None)
        if callable(set_title):
            self.section.set_title(self._build_section_title())

    def _create_section(self, parent):
        try:
            return CollapsibleSection(
                parent, title="", on_toggle=lambda _section: self._sync_section_title()
            )
        except Exception as exc:
            log_event(
                "validacion",
                f"No se pudo crear sección colapsable para reclamo {self.idx+1}: {exc}",
                self.logs,
            )
            fallback = ttk.Frame(parent)
            ensure_grid_support(fallback)
            fallback.content = ttk.Frame(fallback)
            ensure_grid_support(fallback.content)
            fallback.content.pack(fill="both", expand=True)

            def _pack_content(widget, **pack_kwargs):
                defaults = {"fill": "both", "expand": True}
                defaults.update(pack_kwargs)
                widget.pack(**defaults)
                return widget

            fallback.pack_content = _pack_content  # type: ignore[attr-defined]
            fallback.is_open = True  # type: ignore[attr-defined]
            fallback.set_title = lambda _title: None  # type: ignore[attr-defined]
            return fallback

    def _validate_claim_id(self):
        value = self.id_var.get()
        if not value.strip():
            return validate_reclamo_id(value) if self._claims_required else None
        return validate_reclamo_id(value)

    def _validate_claim_name(self):
        value = self.name_var.get()
        if not value.strip():
            return validate_required_text(value, "el nombre de la analítica") if self._claims_required else None
        return validate_required_text(value, "el nombre de la analítica")

    def _validate_claim_code(self):
        value = self.code_var.get()
        if not value.strip():
            return validate_codigo_analitica(value) if self._claims_required else None
        return validate_codigo_analitica(value)

    def clear_values(self):
        """Restablece los campos del reclamo sin quitarlo del layout."""

        def _reset():
            self.id_var.set("")
            self.name_var.set("")
            self.code_var.set("")
            try:
                self.id_cb.set("")
            except Exception:
                pass

        managed = False
        for validator in self.validators:
            suppress = getattr(validator, "suppress_during", None)
            if callable(suppress):
                suppress(_reset)
                managed = True
                break
        if not managed:
            _reset()

    def show_completion_feedback(self):
        validation_matrix = [
            (self.id_validator, validate_reclamo_id, self.id_var.get()),
            (
                self.name_validator,
                lambda v: validate_required_text(v, "el nombre de la analítica"),
                self.name_var.get(),
            ),
            (self.code_validator, validate_codigo_analitica, self.code_var.get()),
        ]
        for validator, checker, value in validation_matrix:
            if validator:
                validator.show_custom_error(checker(value))

    def first_missing_widget(self):
        data = self.get_data()
        if not data.get("id_reclamo"):
            return self.id_entry
        if not data.get("nombre_analitica"):
            return self.name_entry
        if not data.get("codigo_analitica"):
            return self.code_entry
        return None


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
        claim_lookup=None,
        summary_refresh_callback=None,
        change_notifier=None,
        id_change_callback=None,
        initialize_rows=True,
        duplicate_key_checker=None,
        owner=None,
    ):
        self.parent = parent
        self.idx = idx
        self.owner = owner
        self.remove_callback = remove_callback
        self.get_client_options = get_client_options
        self.get_team_options = get_team_options
        self.logs = logs
        self.product_lookup = product_lookup or {}
        self.claim_lookup = claim_lookup or {}
        self.tooltip_register = tooltip_register
        self.duplicate_key_checker = duplicate_key_checker
        self.validators = []
        self.client_validator = None
        self.involvements = []
        self.claims = []
        self._last_missing_lookup_id = None
        self._claim_requirement_active = False
        self._claim_nudge_shown = False
        self.schedule_summary_refresh = summary_refresh_callback or (lambda _sections=None: None)
        self.change_notifier = change_notifier
        self.id_change_callback = id_change_callback
        self._last_tracked_id = ''
        self._suppress_change_notifications = False
        self._badge_styles = {}
        self.amount_badge = None
        self.date_badge = None
        self._amount_validation_ready = False
        self._last_duplicate_result = "Pendiente"
        self._duplicate_status_var = tk.StringVar()
        self._duplicate_status_style = None
        self.duplicate_status_label = None

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
        self.claim_hint_var = tk.StringVar(value="")
        self.claim_hint_frame = None
        self.claim_template_btn = None

        self.section = self._create_section(parent)
        self.section.pack(fill="x", padx=COL_PADX, pady=ROW_PADY)
        self._tree_sort_state: dict[str, bool] = {}
        self._build_header_table()
        self._register_title_traces()
        self._sync_section_title()

        self.frame = ttk.Frame(self.section.content)
        self.section.pack_content(self.frame, fill="x", expand=True)
        ensure_grid_support(self.frame)
        if hasattr(self.frame, "columnconfigure"):
            self.frame.columnconfigure(1, weight=1)
            self.frame.columnconfigure(3, weight=1)
        if hasattr(self.owner, "_set_active_product_frame"):
            self.frame.bind("<FocusIn>", lambda _e: self.owner._set_active_product_frame(self), add="+")
        self._configure_badge_styles()

        ttk.Label(self.frame, text="ID del producto:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        id_entry = ttk.Entry(self.frame, textvariable=self.id_var, width=20)
        id_entry.grid(row=1, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.id_entry = id_entry
        self._bind_identifier_triggers(id_entry)
        self._register_duplicate_triggers(id_entry)
        self.tooltip_register(id_entry, "Código único del producto investigado.")

        ttk.Label(self.frame, text="Cliente:").grid(
            row=1, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        self.client_cb = ttk.Combobox(
            self.frame,
            textvariable=self.client_var,
            values=self.get_client_options(),
            state="readonly",
            width=20,
        )
        self.client_cb.grid(row=1, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.client_cb.set('')
        self.client_cb.bind(
            "<FocusOut>",
            lambda e: self._handle_client_focus_out(),
        )
        self.client_cb.bind("<<ComboboxSelected>>", lambda _e: self._handle_client_focus_out(), add="+")
        self.tooltip_register(self.client_cb, "Selecciona al cliente dueño del producto.")

        ttk.Label(self.frame, text="Categoría 1:").grid(
            row=2, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        cat1_cb = ttk.Combobox(
            self.frame,
            textvariable=self.cat1_var,
            values=list(TAXONOMIA.keys()),
            state="readonly",
            width=20,
        )
        cat1_cb.grid(row=2, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.cat1_cb = cat1_cb
        cat1_cb.set('')
        cat1_cb.bind("<FocusOut>", lambda e: self.on_cat1_change())
        cat1_cb.bind("<<ComboboxSelected>>", lambda e: self.on_cat1_change())
        self.tooltip_register(cat1_cb, "Define la categoría principal del riesgo de producto.")

        ttk.Label(self.frame, text="Categoría 2:").grid(
            row=2, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        self.cat2_cb = ttk.Combobox(
            self.frame,
            textvariable=self.cat2_var,
            values=first_subcats,
            state="readonly",
            width=20,
        )
        self.cat2_cb.grid(row=2, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.cat2_cb.set('')
        self.cat2_cb.bind("<FocusOut>", lambda e: self.on_cat2_change())
        self.cat2_cb.bind("<<ComboboxSelected>>", lambda e: self.on_cat2_change())
        self.tooltip_register(self.cat2_cb, "Selecciona la subcategoría específica.")

        ttk.Label(self.frame, text="Modalidad:").grid(
            row=3, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        self.mod_cb = ttk.Combobox(
            self.frame,
            textvariable=self.mod_var,
            values=first_modalities,
            state="readonly",
            width=25,
        )
        self.mod_cb.grid(row=3, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.mod_cb.set('')
        self.tooltip_register(self.mod_cb, "Indica la modalidad concreta del fraude.")

        ttk.Label(self.frame, text="Canal:").grid(
            row=3, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        canal_cb = ttk.Combobox(
            self.frame,
            textvariable=self.canal_var,
            values=CANAL_LIST,
            state="readonly",
            width=20,
        )
        canal_cb.grid(row=3, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        canal_cb.set('')
        self.tooltip_register(canal_cb, "Canal por donde ocurrió el evento.")

        ttk.Label(self.frame, text="Proceso:").grid(
            row=4, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        proc_cb = ttk.Combobox(
            self.frame,
            textvariable=self.proceso_var,
            values=PROCESO_LIST,
            state="readonly",
            width=25,
        )
        proc_cb.grid(row=4, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        proc_cb.set('')
        self.tooltip_register(proc_cb, "Proceso impactado por el incidente.")

        ttk.Label(self.frame, text="Tipo de producto:").grid(
            row=4, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        tipo_prod_cb = ttk.Combobox(
            self.frame,
            textvariable=self.tipo_prod_var,
            values=TIPO_PRODUCTO_LIST,
            state="readonly",
            width=25,
        )
        tipo_prod_cb.grid(row=4, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.tipo_prod_cb = tipo_prod_cb
        tipo_prod_cb.set('')
        self.tooltip_register(tipo_prod_cb, "Clasificación comercial del producto.")

        ttk.Label(self.frame, text="Fecha de ocurrencia (YYYY-MM-DD):").grid(
            row=5, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        focc_entry = ttk.Entry(self.frame, textvariable=self.fecha_oc_var, width=15)
        focc_entry.grid(row=5, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.focc_entry = focc_entry
        self.tooltip_register(focc_entry, "Fecha exacta del evento.")
        self._register_duplicate_triggers(focc_entry)

        ttk.Label(self.frame, text="Fecha de descubrimiento (YYYY-MM-DD):").grid(
            row=5, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        fdesc_entry = ttk.Entry(self.frame, textvariable=self.fecha_desc_var, width=15)
        fdesc_entry.grid(row=5, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.fdesc_entry = fdesc_entry
        self.date_badge = self._create_badge_label(row=5)
        self.tooltip_register(fdesc_entry, "Fecha en la que se detectó el evento.")

        ttk.Label(self.frame, text="Monto investigado:").grid(
            row=6, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        inv_entry = ttk.Entry(self.frame, textvariable=self.monto_inv_var, width=15)
        inv_entry.grid(row=6, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.inv_entry = inv_entry
        self.amount_badge = self._create_badge_label(row=6)
        self.tooltip_register(inv_entry, "Monto total bajo investigación.")

        ttk.Label(self.frame, text="Moneda:").grid(
            row=6, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        moneda_cb = ttk.Combobox(
            self.frame,
            textvariable=self.moneda_var,
            values=TIPO_MONEDA_LIST,
            state="readonly",
            width=12,
        )
        moneda_cb.grid(row=6, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        moneda_cb.set('')
        self.tooltip_register(moneda_cb, "Tipo de moneda principal del caso.")

        ttk.Label(self.frame, text="Monto pérdida fraude:").grid(
            row=7, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        perdida_entry = ttk.Entry(self.frame, textvariable=self.monto_perdida_var, width=12)
        perdida_entry.grid(row=7, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.perdida_entry = perdida_entry
        self.tooltip_register(
            perdida_entry,
            (
                "Relaciónalo con un reclamo para visibilizar el impacto y acelerar el flujo de aprobación. "
                "Si falta un dato, usa “Ir al primer faltante” para saltar directo a la fila incompleta."
            ),
        )

        ttk.Label(self.frame, text="Monto falla procesos:").grid(
            row=7, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        falla_entry = ttk.Entry(self.frame, textvariable=self.monto_falla_var, width=12)
        falla_entry.grid(row=7, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.falla_entry = falla_entry
        self.tooltip_register(
            falla_entry,
            (
                "Al vincularlo con un reclamo mantenemos trazabilidad de recuperación y hallazgos. "
                "Pulsa “Ir al primer faltante” si necesitas llegar al reclamo pendiente."
            ),
        )

        ttk.Label(self.frame, text="Monto contingencia:").grid(
            row=8, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        cont_entry = ttk.Entry(self.frame, textvariable=self.monto_cont_var, width=12)
        cont_entry.grid(row=8, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.cont_entry = cont_entry
        self.tooltip_register(
            cont_entry,
            (
                "Completar el reclamo asociado permite priorizar recuperos y evidencias. "
                "Apóyate en “Ir al primer faltante” para navegar al reclamo incompleto."
            ),
        )

        self._register_claim_requirement_triggers(
            cont_entry,
            falla_entry,
            perdida_entry,
        )

        ttk.Label(self.frame, text="Monto recuperado:").grid(
            row=8, column=2, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        rec_entry = ttk.Entry(self.frame, textvariable=self.monto_rec_var, width=12)
        rec_entry.grid(row=8, column=3, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.rec_entry = rec_entry
        self.tooltip_register(rec_entry, "Monto efectivamente recuperado.")

        ttk.Label(self.frame, text="Monto pago deuda:").grid(
            row=9, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        pago_entry = ttk.Entry(self.frame, textvariable=self.monto_pago_var, width=12)
        pago_entry.grid(row=9, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        self.pago_entry = pago_entry
        self.tooltip_register(pago_entry, "Pago realizado por deuda vinculada.")

        self._build_claim_guidance_banner(row=10)

        self._build_duplicate_status_label(row=11)

        self.claims_frame = ttk.LabelFrame(self.frame, text="Reclamos asociados")
        ensure_grid_support(self.claims_frame)
        self.claims_frame.grid(row=12, column=0, columnspan=5, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        if hasattr(self.claims_frame, "columnconfigure"):
            self.claims_frame.columnconfigure(1, weight=1)
            self.claims_frame.columnconfigure(3, weight=1)
        claim_add_btn = ttk.Button(
            self.claims_frame, text="Añadir reclamo", command=lambda: self.add_claim(user_initiated=True)
        )
        claim_add_btn.grid(row=0, column=4, padx=COL_PADX, pady=ROW_PADY, sticky="e")
        self.tooltip_register(
            claim_add_btn,
            (
                "Añade reclamos para ligar los montos a evidencias y reducir reprocesos. "
                "Si ya existe un faltante puedes usar “Ir al primer faltante” para llegar directo."
            ),
        )

        self.invol_frame = ttk.LabelFrame(self.frame, text="Involucramiento de colaboradores")
        ensure_grid_support(self.invol_frame)
        self.invol_frame.grid(row=13, column=0, columnspan=5, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        if hasattr(self.invol_frame, "columnconfigure"):
            self.invol_frame.columnconfigure(1, weight=1)
            self.invol_frame.columnconfigure(3, weight=1)
        inv_add_btn = ttk.Button(self.invol_frame, text="Añadir involucrado", command=self.add_involvement)
        inv_add_btn.grid(row=0, column=4, padx=COL_PADX, pady=ROW_PADY, sticky="e")
        self.tooltip_register(
            inv_add_btn,
            "Registra un colaborador asociado a este producto. Es obligatorio para validar duplicados.",
        )

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
                    self._validate_fecha_ocurrencia,
                    self.logs,
                    f"Producto {self.idx+1} - Fecha ocurrencia",
                    variables=[self.fecha_oc_var, self.fecha_desc_var, self.id_var],
                ),
                FieldValidator(
                    fdesc_entry,
                    self._validate_fecha_descubrimiento,
                    self.logs,
                    f"Producto {self.idx+1} - Fecha descubrimiento",
                    variables=[self.fecha_desc_var, self.fecha_oc_var, self.id_var],
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
        amount_widgets = [
            inv_entry,
            perdida_entry,
            falla_entry,
            cont_entry,
            rec_entry,
            pago_entry,
        ]
        self._attach_amount_listeners(amount_vars, amount_widgets)
        self._sync_amount_validation_state()
        self._create_amount_consistency_validators(
            shared_amount_vars,
            {
                'inv': (inv_entry, "Monto investigado"),
                'recuperado': (rec_entry, "Monto recuperado"),
                'pago': (pago_entry, "Monto pago de deuda"),
                'contingencia': (cont_entry, "Monto contingencia"),
            },
            related_widgets=amount_widgets,
        )

        if initialize_rows:
            self.add_claim()
            self.add_involvement()

        self._populate_header_tree()

    def _iter_amount_vars(self):
        return (
            self.monto_inv_var,
            self.monto_perdida_var,
            self.monto_falla_var,
            self.monto_cont_var,
            self.monto_rec_var,
            self.monto_pago_var,
        )

    def _sync_amount_validation_state(self, *_args):
        if self._amount_validation_ready:
            return
        if any((var.get() or "").strip() for var in self._iter_amount_vars()):
            self._amount_validation_ready = True

    def _enable_amount_validation(self, *_args):
        if not self._amount_validation_ready:
            self._amount_validation_ready = True

    def _attach_amount_listeners(self, amount_vars, amount_widgets):
        for var in amount_vars:
            trace_add = getattr(var, "trace_add", None)
            if callable(trace_add):
                trace_add("write", self._sync_amount_validation_state)
        for widget in amount_widgets:
            widget.bind("<KeyRelease>", self._enable_amount_validation, add="+")
            widget.bind("<<Paste>>", self._enable_amount_validation, add="+")
            widget.bind("<<Cut>>", self._enable_amount_validation, add="+")

    def _create_section(self, parent):
        try:
            return CollapsibleSection(
                parent, title="", on_toggle=lambda _section: self._sync_section_title()
            )
        except Exception as exc:
            log_event(
                "validacion",
                f"No se pudo crear sección colapsable para producto {self.idx+1}: {exc}",
                self.logs,
            )
            fallback = ttk.Frame(parent)
            ensure_grid_support(fallback)
            fallback.content = ttk.Frame(fallback)
            fallback.content.pack(fill="both", expand=True)

            def _pack_content(widget, **pack_kwargs):
                defaults = {"fill": "both", "expand": True}
                defaults.update(pack_kwargs)
                widget.pack(**defaults)
                return widget

            fallback.pack_content = _pack_content  # type: ignore[attr-defined]
            fallback.is_open = True  # type: ignore[attr-defined]
            fallback.set_title = lambda _title: None  # type: ignore[attr-defined]
            return fallback

    def _register_title_traces(self):
        for var in (self.id_var, self.client_var):
            trace_add = getattr(var, "trace_add", None)
            if callable(trace_add):
                trace_add("write", self._sync_section_title)

    def _build_section_title(self) -> str:
        base_title = f"Producto {self.idx+1}"
        if getattr(self, "section", None) and not self.section.is_open:
            id_value = self.id_var.get().strip()
            client_value = self.client_var.get().strip()
            details = [value for value in (id_value, client_value) if value]
            if details:
                base_title = f"{base_title} – {' | '.join(details)}"
        return base_title

    def _sync_section_title(self, *_args):
        if not getattr(self, "section", None):
            return
        set_title = getattr(self.section, "set_title", None)
        if callable(set_title):
            self.section.set_title(self._build_section_title())

    def _build_header_table(self):
        container = ttk.Frame(self.section.content)
        self.section.pack_content(container, fill="x", expand=False)
        ensure_grid_support(container)
        if hasattr(container, "columnconfigure"):
            container.columnconfigure(0, weight=1)

        columns = (
            ("id_producto", "ID"),
            ("id_cliente", "Cliente"),
            ("tipo_producto", "Tipo"),
            ("canal", "Canal"),
            ("fecha_ocurrencia", "Fecha ocurrencia"),
        )
        tree_columns = [c[0] for c in columns]
        self.header_tree = self._create_treeview(container, tree_columns)
        if hasattr(self.header_tree, "grid"):
            self.header_tree.grid(
                row=0,
                column=0,
                sticky="nsew",
                padx=COL_PADX,
                pady=(ROW_PADY, ROW_PADY // 2),
            )
        if hasattr(ttk, "Scrollbar"):
            try:
                scrollbar = ttk.Scrollbar(
                    container, orient="vertical", command=getattr(self.header_tree, "yview", None)
                )
                if hasattr(scrollbar, "grid"):
                    scrollbar.grid(row=0, column=1, sticky="ns", pady=(ROW_PADY, ROW_PADY // 2))
                if hasattr(self.header_tree, "configure") and hasattr(scrollbar, "set"):
                    self.header_tree.configure(yscrollcommand=scrollbar.set)
            except Exception as exc:  # pragma: no cover - defensive in headless
                log_event(
                    "validacion",
                    f"No se pudo crear scrollbar para producto {self.idx+1}: {exc}",
                    self.logs,
                )

        for col_id, text in columns:
            if hasattr(self.header_tree, "heading"):
                self.header_tree.heading(col_id, text=text, command=lambda c=col_id: self._sort_treeview(c))
            if hasattr(self.header_tree, "column"):
                self.header_tree.column(col_id, anchor="w", width=150)

        if hasattr(self.header_tree, "tag_configure"):
            self.header_tree.tag_configure("even", background="#f7f7f7")
            self.header_tree.tag_configure("odd", background="#ffffff")
        if hasattr(self.header_tree, "bind"):
            self.header_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
            self.header_tree.bind("<Double-1>", self._on_tree_double_click)

    def _create_treeview(self, container, columns):
        class _DummyTree:
            def __init__(self, cols):
                self._columns = list(cols)
                self._items: list[str] = []
                self._values: dict[str, tuple] = {}

            def grid(self, *args, **kwargs):
                return None

            def configure(self, **kwargs):
                if "columns" in kwargs:
                    self._columns = list(kwargs["columns"])
                return None

            def heading(self, *_args, **_kwargs):
                return None

            def column(self, *_args, **_kwargs):
                return None

            def tag_configure(self, *_args, **_kwargs):
                return None

            def bind(self, *_args, **_kwargs):
                return None

            def get_children(self, _item=""):
                return list(self._items)

            def delete(self, item):
                if item == "":
                    self._items.clear()
                    self._values.clear()
                    return None
                if item in self._items:
                    self._items.remove(item)
                    self._values.pop(item, None)
                return None

            def insert(self, _parent, _index, iid=None, values=None, tags=None):  # noqa: ARG002
                key = iid or str(len(self._items))
                self._items.append(key)
                self._values[key] = tuple(values or ())
                return key

            def move(self, item, _parent, index):  # noqa: ARG002
                if item in self._items:
                    self._items.remove(item)
                    self._items.insert(index, item)
                return None

            def item(self, item, option=None):
                if option == "values":
                    return self._values.get(item, ())
                return {}

            def selection(self):
                return tuple(self._items[:1])

            def yview(self, *_args, **_kwargs):
                return None

            def __getitem__(self, key):
                if key == "columns":
                    return tuple(self._columns)
                return ()

        tree_cls = getattr(ttk, "Treeview", None)
        if tree_cls is None:
            return _DummyTree(columns)
        try:
            return tree_cls(container, columns=columns, show="headings", height=4)
        except Exception as exc:  # pragma: no cover - defensive for headless environments
            log_event(
                "validacion",
                f"No se pudo crear tabla de producto {self.idx+1}: {exc}",
                self.logs,
            )
            return _DummyTree(columns)

    def _populate_header_tree(self):
        if not hasattr(self, "header_tree"):
            return

        for child in self.header_tree.get_children(""):
            self.header_tree.delete(child)

        for row_index, (pid, data) in enumerate(sorted((self.product_lookup or {}).items())):
            values = (
                str(pid),
                str((data or {}).get("id_cliente", "")),
                str((data or {}).get("tipo_producto", "")),
                str((data or {}).get("canal", "")),
                str((data or {}).get("fecha_ocurrencia", "")),
            )
            tag = "even" if row_index % 2 == 0 else "odd"
            self.header_tree.insert("", "end", iid=str(pid), values=values, tags=(tag,))

    def _sort_treeview(self, column):
        if not hasattr(self, "header_tree"):
            return

        reverse = self._tree_sort_state.get(column, False)
        items = list(self.header_tree.get_children(""))
        column_index = self.header_tree["columns"].index(column)
        items.sort(key=lambda item: self.header_tree.item(item, "values")[column_index], reverse=reverse)
        for new_index, item in enumerate(items):
            self.header_tree.move(item, "", new_index)
            tag = "even" if new_index % 2 == 0 else "odd"
            self.header_tree.item(item, tags=(tag,))
        self._tree_sort_state[column] = not reverse

    def _on_tree_select(self, _event=None):
        item = self._first_selected_item()
        if not item:
            return
        values = self.header_tree.item(item, "values")
        if not values:
            return
        self.id_var.set(values[0])
        self.on_id_change(preserve_existing=True, silent=True)
        self.trigger_duplicate_check()

    def _on_tree_double_click(self, _event=None):
        item = self._first_selected_item()
        if not item:
            return
        values = self.header_tree.item(item, "values")
        if not values:
            return
        self.id_var.set(values[0])
        self.on_id_change(from_focus=True)
        self.trigger_duplicate_check()

    def _first_selected_item(self):
        selection = self.header_tree.selection()
        return selection[0] if selection else None

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

    def add_claim(self, user_initiated: bool = False):
        idx = len(self.claims)
        row = ClaimRow(self.claims_frame, self, idx, self.remove_claim, self.logs, self.tooltip_register)
        row.set_claim_requirement(self._claim_requirement_active)
        self.claims.append(row)
        self.schedule_summary_refresh('reclamos')
        self.persist_lookup_snapshot()
        self.refresh_claim_guidance()
        if self.owner and hasattr(self.owner, "notify_claim_added"):
            try:
                self.owner.notify_claim_added(user_initiated=user_initiated)
            except Exception:
                pass
        return row

    def remove_claim(self, row):
        if row in self.claims:
            self.claims.remove(row)
        if not self.claims:
            self.add_claim()
        self.schedule_summary_refresh('reclamos')
        self.persist_lookup_snapshot()
        self.refresh_claim_guidance()

    def clear_claims(self):
        for claim in self.claims:
            if getattr(claim, "section", None):
                claim.section.destroy()
            else:
                claim.frame.destroy()
        self.claims.clear()

    def clear_involvements(self):
        for inv in self.involvements:
            if getattr(inv, "section", None):
                inv.section.destroy()
            else:
                inv.frame.destroy()
        self.involvements.clear()

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

    def _create_amount_consistency_validators(self, variables, widget_map, *, related_widgets=None):
        for key, (widget, label) in widget_map.items():
            validator = FieldValidator(
                widget,
                lambda key=key: self._validate_amount_consistency_for_field(key),
                self.logs,
                f"Producto {self.idx+1} - Consistencia de montos ({label})",
                variables=variables,
            )
            if related_widgets:
                for extra_widget in related_widgets:
                    if extra_widget is not widget:
                        validator.add_widget(extra_widget)
            self.validators.append(validator)

    def _configure_badge_styles(self):
        style = None
        try:
            style = ThemeManager.build_style(self.frame)
        except Exception:
            if hasattr(ttk, "Style"):
                try:
                    style = ttk.Style(master=self.frame)
                except Exception:
                    style = None
        if not style or not hasattr(style, "configure"):
            self._badge_styles = {"success": "TLabel", "warning": "TLabel"}
            return
        palette = ThemeManager.current()
        success_style = "SuccessBadge.TLabel"
        warning_style = "WarningBadge.TLabel"
        style.configure(
            success_style,
            background=palette.get("accent", "#2e7d32"),
            foreground=palette.get("select_foreground", "#ffffff"),
            padding=(6, 2),
            borderwidth=1,
            relief="solid",
            font=("TkDefaultFont", 9, "bold"),
        )
        style.configure(
            warning_style,
            background="#f0ad4e",
            foreground=palette.get("foreground", "#000000"),
            padding=(6, 2),
            borderwidth=1,
            relief="solid",
            font=("TkDefaultFont", 9, "bold"),
        )
        self._badge_styles = {"success": success_style, "warning": warning_style}

    def _configure_duplicate_status_style(self):
        if self._duplicate_status_style:
            return self._duplicate_status_style
        style = None
        try:
            style = ThemeManager.build_style(self.frame)
        except Exception:
            style = None
        palette = ThemeManager.current()
        style_name = "DuplicateStatus.TLabel"
        if style and hasattr(style, "configure"):
            style.configure(
                style_name,
                background=palette.get("background", "#f5f5f5"),
                foreground=palette.get("foreground", "#1f1f1f"),
                padding=(6, 4),
            )
        self._duplicate_status_style = style_name
        return style_name

    def _create_badge_label(self, row: int):
        styles = self._badge_styles or {"warning": "TLabel"}
        badge = ttk.Label(
            self.frame,
            text="Pendiente",
            style=styles.get("warning", "TLabel"),
            anchor="w",
        )
        badge.grid(row=row, column=4, padx=COL_PADX, pady=ROW_PADY, sticky="w")
        return badge

    def _set_badge_state(self, badge, is_ok: bool, message: str | None):
        if badge is None:
            return
        styles = self._badge_styles or {"success": "TLabel", "warning": "TLabel"}
        style_name = styles["success"] if is_ok else styles["warning"]
        text = "Cuadra" if is_ok else (message or "Revisa la información")
        badge.configure(text=text, style=style_name)

    def _build_duplicate_status_label(self, row: int):
        style_name = self._configure_duplicate_status_style()
        self._duplicate_status_var.set(self._format_duplicate_status_text())
        label = ttk.Label(
            self.frame,
            textvariable=self._duplicate_status_var,
            style=style_name,
            justify="left",
            anchor="w",
            wraplength=520,
        )
        label.grid(row=row, column=0, columnspan=5, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        tooltip_text = (
            "Si el sistema marca un duplicado, ajusta cualquiera de los campos de la "
            "clave técnica (caso, producto, cliente, colaborador, fecha de ocurrencia "
            "o reclamo) hasta que la combinación sea única y vuelve a editar un campo "
            "para revalidar. Debes tener al menos un colaborador asignado en "
            "'Involucramiento de colaboradores' para que la validación sea completa."
        )
        self.tooltip_register(label, tooltip_text)
        self.duplicate_status_label = label

    def _compose_duplicate_key_tuple(self) -> str:
        case_var = getattr(self.owner, "id_caso_var", None)
        case_id = (case_var.get().strip() if case_var else "")
        product_id = self.id_var.get().strip()
        client_id = self.client_var.get().strip()
        collaborator_id = self._get_primary_collaborator()
        occ_date = self.fecha_oc_var.get().strip()
        desc_date = self.fecha_desc_var.get().strip()
        date_block = f"{occ_date or '—'} / {desc_date or '—'}"
        claim_id = self._get_primary_claim_id()
        tuple_parts = (
            case_id or "—",
            product_id or "—",
            client_id or "—",
            collaborator_id or "—",
            date_block,
            claim_id or "—",
        )
        return f"({', '.join(tuple_parts)})"

    def _get_primary_collaborator(self) -> str:
        for inv in self.involvements:
            collaborator_id = (inv.team_var.get() if hasattr(inv, "team_var") else "").strip()
            if collaborator_id:
                return collaborator_id
        return ""

    def _get_primary_claim_id(self) -> str:
        for claim in self.claims:
            data = claim.get_data()
            claim_id = (data.get("id_reclamo") or "").strip()
            if claim_id:
                return claim_id
        return ""

    def _format_duplicate_status_text(self, result_text: str | None = None) -> str:
        if result_text:
            self._last_duplicate_result = result_text
        status = self._last_duplicate_result or "Pendiente"
        key_tuple = self._compose_duplicate_key_tuple()
        return f"Clave técnica: {key_tuple}\nÚltimo chequeo: {status}"

    def _update_duplicate_status_label(self, result_text: str | None = None):
        new_text = self._format_duplicate_status_text(result_text)
        self._duplicate_status_var.set(new_text)

    def _update_date_badge(self, message: str | None, is_valid: bool):
        self._set_badge_state(self.date_badge, is_valid, message)

    def _update_amount_badge(self, message: str | None, is_valid: bool):
        self._set_badge_state(self.amount_badge, is_valid, message)

    def _refresh_badges(self) -> None:
        pair_message, pair_ok = self._validate_product_date_pair()
        self._update_date_badge(pair_message, pair_ok)
        self._validate_montos_consistentes()

    def _register_duplicate_triggers(self, widget) -> None:
        widget.bind("<FocusOut>", self._handle_duplicate_check_event, add="+")
        if isinstance(widget, ttk.Combobox):
            widget.bind("<<ComboboxSelected>>", self._handle_duplicate_check_event, add="+")

    def _handle_duplicate_check_event(self, *_args):
        signature = None
        owner_has_signature = hasattr(self.owner, "duplicate_dataset_signature")
        owner_has_cooldown = hasattr(self.owner, "is_duplicate_check_on_cooldown")
        if owner_has_signature:
            try:
                signature = self.owner.duplicate_dataset_signature()
            except Exception:
                signature = None
        if signature and owner_has_cooldown:
            try:
                if self.owner.is_duplicate_check_on_cooldown(signature):
                    self._update_duplicate_status_label(
                        "Advertencia reciente: revisa el panel de validación"
                    )
                    self._refresh_badges()
                    return
            except Exception:
                pass
        self.trigger_duplicate_check(dataset_signature=signature)
        self._refresh_badges()

    def _register_claim_requirement_triggers(self, cont_entry, falla_entry, perdida_entry):
        for entry in (cont_entry, falla_entry, perdida_entry):
            entry.bind(
                "<FocusOut>",
                lambda _e: self._handle_claim_requirement_change(source_is_user=True),
                add="+",
            )
        for var in (self.monto_cont_var, self.monto_falla_var, self.monto_perdida_var):
            trace_add = getattr(var, "trace_add", None)
            if callable(trace_add):
                trace_add("write", lambda *_: self._handle_claim_requirement_change())
        self._handle_claim_requirement_change(initial=True)

    def _build_claim_guidance_banner(self, row: int):
        frame = ttk.Frame(self.frame)
        ensure_grid_support(frame)
        frame.grid(row=row, column=0, columnspan=5, padx=COL_PADX, pady=(ROW_PADY // 2, ROW_PADY), sticky="we")
        hide_fn = getattr(frame, "grid_remove", None) or getattr(frame, "grid_forget", None)
        if callable(hide_fn):
            hide_fn()
        label = ttk.Label(
            frame,
            textvariable=self.claim_hint_var,
            wraplength=520,
            justify="left",
            anchor="w",
        )
        label.grid(row=0, column=0, padx=COL_PADX, pady=(ROW_PADY // 2, ROW_PADY // 4), sticky="w")
        actions = ttk.Frame(frame)
        ensure_grid_support(actions)
        actions.grid(row=0, column=1, padx=COL_PADX, pady=(ROW_PADY // 2, ROW_PADY // 4), sticky="e")
        ttk.Button(
            actions,
            text="Ir al primer faltante",
            command=self._focus_first_incomplete_claim,
            style=BUTTON_STYLE,
        ).grid(row=0, column=0, padx=(0, COL_PADX // 2), sticky="e")
        template_btn = ttk.Button(
            actions,
            text="Autocompletar analítica",
            command=self._apply_claim_template,
            style=BUTTON_STYLE,
        )
        template_btn.grid(row=0, column=1, sticky="e")
        self.claim_template_btn = template_btn
        self.claim_hint_frame = frame
        self._refresh_claim_template_button_state()

    def _handle_claim_requirement_change(self, *_args, initial=False, source_is_user=False):
        required = self._claim_fields_required()
        required_changed = required != self._claim_requirement_active
        if required_changed:
            self._claim_requirement_active = required
            for claim in self.claims:
                claim.set_claim_requirement(required)
            self.schedule_summary_refresh({'reclamos'})
            if not required:
                self._claim_nudge_shown = False
        self.refresh_claim_guidance()
        if initial:
            return
        has_complete = self._has_complete_claim()
        if required and source_is_user and (required_changed or not has_complete):
            if self.claims:
                self._apply_inline_claim_feedback()
                log_event(
                    "nudges",
                    f"Producto {self.idx+1}: aviso inline de reclamo requerido",
                    self.logs,
                )
            if (self._claim_nudge_shown or required_changed) and not has_complete:
                self._show_claim_requirement_error()
            self._claim_nudge_shown = True
        elif not required:
            self._claim_nudge_shown = False

    def _refresh_claim_template_button_state(self):
        if not self.claim_template_btn:
            return
        state_fn = getattr(self.claim_template_btn, "state", None)
        if not callable(state_fn):
            return
        if self.claim_lookup:
            state_fn(["!disabled"])
        else:
            state_fn(["disabled"])

    def refresh_claim_guidance(self):
        self._refresh_claim_template_button_state()
        self._update_claim_hint_banner()

    def _update_claim_hint_banner(self):
        if not self.claim_hint_frame:
            return
        required = self._claim_fields_required()
        claim, missing = self._first_incomplete_claim()
        has_complete = self._has_complete_claim()
        if required and not has_complete and claim:
            missing_text = ", ".join(missing) if missing else "datos del reclamo"
            self.claim_hint_var.set(
                (
                    f"Falta registrar {missing_text} para enlazar los montos con su reclamo y "
                    "destrabar el proceso. Puedes usar la plantilla de analítica cuando haya catálogo disponible."
                )
            )
            self.claim_hint_frame.grid()
        else:
            hide_fn = getattr(self.claim_hint_frame, "grid_remove", None) or getattr(
                self.claim_hint_frame, "grid_forget", None
            )
            if callable(hide_fn):
                hide_fn()

    def _first_incomplete_claim(self):
        labels = {
            "id_reclamo": "ID de reclamo",
            "nombre_analitica": "nombre de analítica",
            "codigo_analitica": "código de analítica",
        }
        for claim in self.claims:
            data = claim.get_data()
            missing = [label for key, label in labels.items() if not data.get(key)]
            if missing:
                return claim, missing
        return None, []

    def _focus_first_incomplete_claim(self):
        claim, missing = self._first_incomplete_claim()
        target_widget = claim.first_missing_widget() if claim else None
        if not claim or target_widget is None:
            return
        self._scroll_to_widget(target_widget)
        try:
            target_widget.focus_set()
        except tk.TclError:
            pass
        log_event(
            "nudges",
            f"Producto {self.idx+1}: navegación al reclamo pendiente ({', '.join(missing)})",
            self.logs,
        )
        self.refresh_claim_guidance()

    def _scroll_to_widget(self, widget):
        if widget is None:
            return False
        try:
            widget.update_idletasks()
        except tk.TclError:
            return False
        parent = getattr(widget, "master", None)
        canvas = None
        while parent is not None:
            if isinstance(parent, tk.Canvas):
                canvas = parent
                break
            parent = getattr(parent, "master", None)
        if canvas is None:
            return False
        try:
            inner_frames = [child for child in canvas.winfo_children() if isinstance(child, (tk.Frame, ttk.Frame))]
            inner = inner_frames[0] if inner_frames else None
            if inner is None or inner.winfo_height() == 0:
                return False
            widget_y = widget.winfo_rooty()
            inner_y = inner.winfo_rooty()
            offset = max(0, widget_y - inner_y - 20)
            fraction = offset / max(1, inner.winfo_height())
            canvas.yview_moveto(min(1.0, fraction))
            return True
        except tk.TclError:
            return False

    def _apply_claim_template(self):
        claim, missing = self._first_incomplete_claim()
        if not claim:
            return
        lookup = self.claim_lookup or {}
        claim_id = claim.id_var.get().strip()
        template_data = lookup.get(claim_id) if claim_id else None
        if template_data is None and lookup:
            template_id, template_data = next(iter(lookup.items()))
            if template_data is None:
                template_data = {}
            template_data = dict(template_data)
            template_data.setdefault("id_reclamo", template_id)
        if not template_data:
            log_event("nudges", f"Producto {self.idx+1}: plantilla de reclamo no disponible", self.logs)
            return

        def _set_if_present(var, key):
            value = template_data.get(key)
            if value in (None, ""):
                return
            text_value = str(value).strip()
            if should_autofill_field(var.get(), preserve_existing=True):
                var.set(text_value)

        _set_if_present(claim.id_var, "id_reclamo")
        _set_if_present(claim.name_var, "nombre_analitica")
        _set_if_present(claim.code_var, "codigo_analitica")
        self.refresh_claim_guidance()
        self._apply_inline_claim_feedback()
        log_event(
            "nudges",
            f"Producto {self.idx+1}: aplicó plantilla de reclamo ({', '.join(missing)})",
            self.logs,
        )

    def _show_claim_requirement_error(self):
        messagebox.showerror(
            "Reclamo requerido",
            (
                "Debe ingresar al menos un reclamo completo en "
                f"{self._get_product_label()} porque hay montos de pérdida, falla o contingencia."
            ),
        )
        log_event("nudges", f"Producto {self.idx+1}: modal de reclamo requerido", self.logs)

    def _has_complete_claim(self) -> bool:
        return any(all(data.values()) for data in (claim.get_data() for claim in self.claims))

    def _apply_inline_claim_feedback(self):
        previous_modal_setting = FieldValidator.modal_notifications_enabled
        FieldValidator.modal_notifications_enabled = False
        try:
            for claim in self.claims:
                claim.show_completion_feedback()
        finally:
            FieldValidator.modal_notifications_enabled = previous_modal_setting

    def _claim_fields_required(self) -> bool:
        return any(
            self._has_positive_amount(var)
            for var in (self.monto_perdida_var, self.monto_falla_var, self.monto_cont_var)
        )

    def _has_positive_amount(self, var: tk.StringVar) -> bool:
        message, value, _normalized = validate_money_bounds(
            var.get(),
            "monto",
            allow_blank=True,
        )
        return message is None and value is not None and value > 0

    @property
    def claim_fields_required(self) -> bool:
        return self._claim_requirement_active

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

    def claim_requirement_errors(self):
        if not self.claim_fields_required:
            return []
        errors = []
        complete_claim_found = False
        for idx, claim in enumerate(self.claims, start=1):
            data = claim.get_data()
            has_any_value = any(data.values())
            has_all_values = all(data.values())
            if has_any_value and not has_all_values:
                claim_label = data.get('id_reclamo') or f"reclamo {idx}"
                errors.append(
                    f"{self._get_product_label()}: El {claim_label} debe tener ID, nombre y código de analítica."
                )
            if has_all_values:
                complete_claim_found = True
        if not complete_claim_found:
            errors.append(
                f"Debe ingresar al menos un reclamo completo en {self._get_product_label()} porque hay montos de pérdida, falla o contingencia."
            )
        return errors

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
        self._populate_header_tree()

    def set_product_lookup(self, lookup):
        self.product_lookup = lookup or {}
        self._last_missing_lookup_id = None
        self._populate_header_tree()

    def set_claim_lookup(self, lookup):
        self.claim_lookup = lookup or {}
        for claim in self.claims:
            claim.on_id_change(preserve_existing=True, silent=True)
        self.refresh_claim_guidance()

    def on_id_change(self, from_focus=False, preserve_existing=False, silent=False):
        pid = self.id_var.get().strip()
        self._notify_id_change(pid)
        if not silent:
            self.log_change(f"Producto {self.idx+1}: modificó ID a {pid}")
        if not pid:
            self._last_missing_lookup_id = None
            if silent:
                self._schedule_product_summary_refresh()
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
            if silent:
                self._schedule_product_summary_refresh()
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
        if not silent:
            self.log_change(f"Producto {self.idx+1}: autopoblado desde catálogo")
        else:
            self._schedule_product_summary_refresh()
        self.persist_lookup_snapshot()

    def _notify_id_change(self, new_id):
        if new_id == self._last_tracked_id:
            return
        previous = self._last_tracked_id
        self._last_tracked_id = new_id
        if callable(self.id_change_callback):
            self.id_change_callback(self, previous, new_id)

    def trigger_duplicate_check(self, dataset_signature=None):
        result = None
        if callable(self.duplicate_key_checker):
            try:
                result = self.duplicate_key_checker(
                    armed=True, dataset_signature=dataset_signature
                )
            except TypeError:
                result = self.duplicate_key_checker(armed=True)
        self._update_duplicate_status_label(result)
        return result

    def _bind_identifier_triggers(self, widget) -> None:
        widget.bind("<FocusOut>", lambda _e: self.on_id_change(from_focus=True), add="+")
        widget.bind("<KeyRelease>", lambda _e: self.on_id_change(), add="+")
        widget.bind("<Return>", lambda _e: self.on_id_change(from_focus=True), add="+")
        widget.bind("<<Paste>>", lambda _e: self.on_id_change(), add="+")
        widget.bind("<<ComboboxSelected>>", lambda _e: self.on_id_change(from_focus=True), add="+")

    def _validate_product_date_pair(self):
        fecha_oc = (self.fecha_oc_var.get() or "").strip()
        fecha_desc = (self.fecha_desc_var.get() or "").strip()
        if not (fecha_oc and fecha_desc):
            return ("Ingresa ambas fechas para validar la secuencia.", False)
        producto_label = self.id_var.get().strip() or f"Producto {self.idx+1}"
        message = validate_product_dates(
            producto_label,
            fecha_oc,
            fecha_desc,
        )
        return (message, message is None)

    def _validate_fecha_ocurrencia(self):
        message = validate_date_text(
            self.fecha_oc_var.get(),
            "la fecha de ocurrencia",
            allow_blank=False,
            enforce_max_today=True,
            must_be_before=(
                self.fecha_desc_var.get(),
                "la fecha de descubrimiento",
            ),
        )
        if message:
            self._update_date_badge(message, False)
            return message
        pair_message, pair_ok = self._validate_product_date_pair()
        final_message = message or pair_message
        self._update_date_badge(final_message, pair_ok and message is None)
        return final_message

    def _validate_fecha_descubrimiento(self):
        msg = validate_date_text(
            self.fecha_desc_var.get(),
            "la fecha de descubrimiento",
            allow_blank=False,
            enforce_max_today=True,
            must_be_after=(self.fecha_oc_var.get(), "la fecha de ocurrencia"),
        )
        if msg:
            self._update_date_badge(msg, False)
            return msg
        pair_message, pair_ok = self._validate_product_date_pair()
        final_message = msg or pair_message
        self._update_date_badge(final_message, pair_ok and msg is None)
        return final_message

    def _validate_amount_field(self, var, label, allow_blank):
        raw_value = var.get()
        stripped = (raw_value or "").strip()
        message, decimal_value, normalized_text = validate_money_bounds(
            raw_value,
            label,
            allow_blank=allow_blank,
        )
        if not message and decimal_value is not None and normalized_text != stripped:
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
            if decimal_value is None:
                decimal_value = Decimal("0") if allow_blank else None
            values[key] = decimal_value
        return values

    def _validate_montos_consistentes(self, target_key: str | None = None):
        self._sync_amount_validation_state()
        if not self._amount_validation_ready:
            return (None, False)
        values = self._collect_amount_values()
        if values is None:
            self._update_amount_badge("Corrige los montos individuales para validar.", False)
            return (None, False)
        errors = {}
        inv = values.get('inv')
        componentes_dict = {
            'perdida': values.get('perdida'),
            'falla': values.get('falla'),
            'contingencia': values.get('contingencia'),
            'recuperado': values.get('recuperado'),
        }
        if inv is not None:
            componentes = sum_investigation_components(**componentes_dict)
            if componentes != inv:
                errors['inv'] = (
                    "La suma de las cuatro partidas (pérdida, falla, contingencia y recuperación) "
                    "debe ser igual al monto investigado."
                )
        if inv is not None and values['recuperado'] is not None and values['recuperado'] > inv:
            errors['recuperado'] = "El monto recuperado no puede superar el monto investigado."
        if inv is not None and values['pago'] is not None and values['pago'] > inv:
            errors['pago'] = "El pago de deuda no puede ser mayor al monto investigado."
        tipo_prod = normalize_without_accents(self.tipo_prod_var.get()).lower()
        if inv is not None and values['contingencia'] is not None and any(
            word in tipo_prod for word in ('credito', 'tarjeta')
        ):
            if values['contingencia'] != inv:
                errors['contingencia'] = (
                    "El monto de contingencia debe ser igual al monto investigado para créditos o tarjetas."
                )
        badge_message = next(iter(errors.values()), None)
        is_consistent = not errors
        self._update_amount_badge(badge_message, is_consistent)
        target = target_key or 'inv'
        return (errors.get(target), is_consistent)

    def _validate_amount_consistency_for_field(self, target_key: str):
        message, _is_valid = self._validate_montos_consistentes(target_key)
        return message

    def _validate_catalog_selection(self, value, label, catalog, catalog_label):
        message = validate_required_text(value, label)
        if message:
            return message
        normalized = (value or '').strip()
        if normalized not in catalog:
            return f"El valor '{value}' no está en el catálogo CM de {catalog_label}."
        return None

    def _get_product_label(self) -> str:
        return self.id_var.get().strip() or f"Producto {self.idx+1}"

    def clear_values(self):
        """Limpia los valores del producto y sus filas dinámicas sin eliminar widgets."""

        def _reset():
            for var in (
                self.id_var,
                self.client_var,
                self.cat1_var,
                self.cat2_var,
                self.mod_var,
                self.canal_var,
                self.proceso_var,
                self.fecha_oc_var,
                self.fecha_desc_var,
                self.monto_inv_var,
                self.moneda_var,
                self.monto_perdida_var,
                self.monto_falla_var,
                self.monto_cont_var,
                self.monto_rec_var,
                self.monto_pago_var,
                self.tipo_prod_var,
            ):
                var.set("")
            try:
                self.client_cb.set("")
            except Exception:
                pass
            for claim in self.claims:
                if hasattr(claim, "clear_values"):
                    claim.clear_values()
            for involvement in self.involvements:
                if hasattr(involvement, "clear_values"):
                    involvement.clear_values()

        managed = False
        for validator in self.validators:
            suppress = getattr(validator, "suppress_during", None)
            if callable(suppress):
                suppress(_reset)
                managed = True
                break
        if not managed:
            _reset()

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
            producto_data[field_name] = current_value
            if current_value and getattr(self, var_attr).get() != current_value:
                getattr(self, var_attr).set(current_value)

    def focus_first_field(self):
        if hasattr(self, "id_entry") and hasattr(self.id_entry, "focus_set"):
            try:
                self.id_entry.focus_set()
            except Exception:
                return

    def _handle_client_focus_out(self):
        self.log_change(f"Producto {self.idx+1}: seleccionó cliente")
        self.trigger_duplicate_check()

    def _schedule_product_summary_refresh(self):
        if hasattr(self, 'schedule_summary_refresh'):
            self.schedule_summary_refresh({'productos', 'reclamos', 'involucramientos'})

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el producto {self.idx+1}?"):
            self.log_change(f"Se eliminó producto {self.idx+1}")
            self.frame.destroy()
            self.remove_callback(self)

    def log_change(self, message: str):
        if self._suppress_change_notifications:
            return
        if callable(self.change_notifier):
            self.change_notifier(message)
        else:
            log_event("navegacion", message, self.logs)
        self._schedule_product_summary_refresh()


__all__ = [
    "ClaimRow",
    "InvolvementRow",
    "PRODUCT_MONEY_SPECS",
    "ProductFrame",
]
