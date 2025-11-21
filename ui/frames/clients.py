"""Componentes de interfaz relacionados a clientes."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from settings import ACCIONADO_OPTIONS, FLAG_CLIENTE_LIST, TIPO_ID_LIST
from validators import (FieldValidator, log_event, should_autofill_field,
                        validate_client_id, validate_email_list,
                        validate_multi_selection, validate_phone_list,
                        validate_required_text)
from ui.frames.utils import ensure_grid_support
from ui.config import COL_PADX, ROW_PADY


class ClientFrame:
    """Representa un cliente y su interfaz dentro de la sección de clientes."""

    ENTITY_LABEL = "cliente"

    def __init__(
        self,
        parent,
        idx,
        remove_callback,
        update_client_options,
        logs,
        tooltip_register,
        client_lookup=None,
        summary_refresh_callback=None,
        change_notifier=None,
        id_change_callback=None,
    ):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.update_client_options = update_client_options
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.client_lookup = client_lookup or {}
        self.validators = []
        self._last_missing_lookup_id = None
        self.schedule_summary_refresh = summary_refresh_callback or (lambda _sections=None: None)
        self.change_notifier = change_notifier
        self.id_change_callback = id_change_callback
        self._last_tracked_id = ''

        self.tipo_id_var = tk.StringVar()
        self.id_var = tk.StringVar()
        self.flag_var = tk.StringVar()
        self.telefonos_var = tk.StringVar()
        self.correos_var = tk.StringVar()
        self.direcciones_var = tk.StringVar()
        self.accionado_var = tk.StringVar()
        self.accionado_options_var = tk.StringVar(value=ACCIONADO_OPTIONS)

        self.frame = ttk.LabelFrame(parent, text=f"Cliente {self.idx+1}")
        self.frame.pack(fill="x", padx=COL_PADX, pady=ROW_PADY)
        ensure_grid_support(self.frame)
        if hasattr(self.frame, "columnconfigure"):
            self.frame.columnconfigure(0, weight=0)
            self.frame.columnconfigure(1, weight=1)
            self.frame.columnconfigure(2, weight=0)

        ttk.Label(self.frame, text="Tipo de ID:").grid(
            row=0, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        tipo_id_cb = ttk.Combobox(
            self.frame,
            textvariable=self.tipo_id_var,
            values=TIPO_ID_LIST,
            state="readonly",
            width=20,
        )
        tipo_id_cb.grid(row=0, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=0, column=2, padx=COL_PADX, pady=ROW_PADY)
        tipo_id_cb.set('')
        self.tooltip_register(tipo_id_cb, "Selecciona el tipo de documento del cliente.")

        ttk.Label(self.frame, text="ID del cliente:").grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        id_entry = ttk.Entry(self.frame, textvariable=self.id_var, width=20)
        id_entry.grid(row=1, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=1, column=2, padx=COL_PADX, pady=ROW_PADY)
        self._bind_identifier_triggers(id_entry)
        self.tooltip_register(id_entry, "Escribe el número de documento del cliente.")

        ttk.Label(self.frame, text="Flag:").grid(
            row=2, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        flag_cb = ttk.Combobox(
            self.frame, textvariable=self.flag_var, values=FLAG_CLIENTE_LIST, state="readonly", width=20
        )
        flag_cb.grid(row=2, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=2, column=2, padx=COL_PADX, pady=ROW_PADY)
        flag_cb.set('')
        self.tooltip_register(flag_cb, "Indica si el cliente es afectado, vinculado u otro estado.")

        ttk.Label(self.frame, text="Accionado (seleccione uno o varios):").grid(
            row=3, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        accionado_list_container = ttk.Frame(self.frame)
        ensure_grid_support(accionado_list_container)
        accionado_list_container.grid(
            row=3, column=1, columnspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="we"
        )
        if hasattr(accionado_list_container, "columnconfigure"):
            accionado_list_container.columnconfigure(0, weight=1)
            accionado_list_container.columnconfigure(1, weight=0)

        accionado_scrollbar = None
        scrollbar_class = getattr(tk, "Scrollbar", None) or getattr(ttk, "Scrollbar", None)
        if scrollbar_class:
            accionado_scrollbar = scrollbar_class(
                accionado_list_container,
                orient="vertical",
            )

        listbox_kwargs = dict(
            master=accionado_list_container,
            listvariable=self.accionado_options_var,
            selectmode="multiple",
            exportselection=False,
            height=8,
            width=40,
        )
        if accionado_scrollbar:
            listbox_kwargs["yscrollcommand"] = accionado_scrollbar.set

        self.accionado_listbox = tk.Listbox(**listbox_kwargs)
        self.accionado_listbox.grid(row=0, column=0, sticky="nsew")
        if accionado_scrollbar:
            accionado_scrollbar.grid(row=0, column=1, sticky="ns")
            accionado_scrollbar.configure(command=self.accionado_listbox.yview)
        self.accionado_listbox.bind("<<ListboxSelect>>", self.update_accionado_var)
        self.tooltip_register(
            self.accionado_listbox,
            "Marca las tribus o equipos accionados por la alerta. Puedes escoger varias opciones.",
        )

        ttk.Label(self.frame, text="Teléfonos (separados por ;):").grid(
            row=4, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        tel_entry = ttk.Entry(self.frame, textvariable=self.telefonos_var, width=30)
        tel_entry.grid(row=4, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=4, column=2, padx=COL_PADX, pady=ROW_PADY)
        tel_entry.bind("<FocusOut>", lambda e: self._log_change(f"Cliente {self.idx+1}: modificó teléfonos"))
        self.tooltip_register(
            tel_entry,
            "Campo obligatorio. Ingresa al menos un número telefónico separado por ; sin guiones.",
        )

        ttk.Label(self.frame, text="Correos (separados por ;):").grid(
            row=5, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        cor_entry = ttk.Entry(self.frame, textvariable=self.correos_var, width=30)
        cor_entry.grid(row=5, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=5, column=2, padx=COL_PADX, pady=ROW_PADY)
        cor_entry.bind("<FocusOut>", lambda e: self._log_change(f"Cliente {self.idx+1}: modificó correos"))
        self.tooltip_register(
            cor_entry,
            "Campo obligatorio. Coloca al menos un correo electrónico separado por ;.",
        )

        ttk.Label(self.frame, text="Direcciones (separados por ;):").grid(
            row=6, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        dir_entry = ttk.Entry(self.frame, textvariable=self.direcciones_var, width=30)
        dir_entry.grid(row=6, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=6, column=2, padx=COL_PADX, pady=ROW_PADY)
        dir_entry.bind("<FocusOut>", lambda e: self._log_change(f"Cliente {self.idx+1}: modificó direcciones"))
        self.tooltip_register(dir_entry, "Puedes capturar varias direcciones separadas por ;.")

        action_row = ttk.Frame(self.frame)
        ensure_grid_support(action_row)
        action_row.grid(row=7, column=0, columnspan=3, padx=COL_PADX, pady=ROW_PADY, sticky="ew")
        if hasattr(action_row, "columnconfigure"):
            action_row.columnconfigure(0, weight=1)
            action_row.columnconfigure(1, weight=0)
        remove_btn = ttk.Button(action_row, text="Eliminar cliente", command=self.remove)
        remove_btn.grid(row=0, column=1, sticky="e", padx=COL_PADX)
        self.tooltip_register(remove_btn, "Quita por completo al cliente de la lista.")

        self.validators.append(
            FieldValidator(
                id_entry,
                lambda: validate_client_id(self.tipo_id_var.get(), self.id_var.get()),
                self.logs,
                f"Cliente {self.idx+1} - ID",
                variables=[self.id_var, self.tipo_id_var],
            )
        )
        self.validators.append(
            FieldValidator(
                tipo_id_cb,
                lambda: validate_required_text(self.tipo_id_var.get(), "el tipo de ID del cliente"),
                self.logs,
                f"Cliente {self.idx+1} - Tipo de ID",
                variables=[self.tipo_id_var],
            )
        )
        def _validate_flag():
            required_message = validate_required_text(self.flag_var.get(), "el flag del cliente")
            if required_message:
                return required_message
            value = (self.flag_var.get() or "").strip()
            if value and value not in FLAG_CLIENTE_LIST:
                return f"El flag de cliente '{value}' no está en el catálogo CM."
            return None

        self.validators.append(
            FieldValidator(
                flag_cb,
                _validate_flag,
                self.logs,
                f"Cliente {self.idx+1} - Flag",
                variables=[self.flag_var],
            )
        )
        def _validate_required_phones():
            value = self.telefonos_var.get()
            error = validate_required_text(value, "al menos un teléfono del cliente")
            if error:
                return error
            return validate_phone_list(value, "los teléfonos del cliente")

        def _validate_required_emails():
            value = self.correos_var.get()
            error = validate_required_text(value, "al menos un correo del cliente")
            if error:
                return error
            return validate_email_list(value, "los correos del cliente")

        self.validators.append(
            FieldValidator(
                tel_entry,
                _validate_required_phones,
                self.logs,
                f"Cliente {self.idx+1} - Teléfonos",
                variables=[self.telefonos_var],
            )
        )
        self.validators.append(
            FieldValidator(
                cor_entry,
                _validate_required_emails,
                self.logs,
                f"Cliente {self.idx+1} - Correos",
                variables=[self.correos_var],
            )
        )
        self.validators.append(
            FieldValidator(
                self.accionado_listbox,
                lambda: validate_multi_selection(self.accionado_var.get(), "Accionado"),
                self.logs,
                f"Cliente {self.idx+1} - Accionado",
                variables=[self.accionado_var],
            )
        )

    def set_lookup(self, lookup):
        self.client_lookup = lookup or {}
        self._last_missing_lookup_id = None

    def _bind_identifier_triggers(self, widget) -> None:
        widget.bind("<FocusOut>", lambda _e: self.on_id_change(from_focus=True), add="+")
        widget.bind("<KeyRelease>", lambda _e: self.on_id_change(), add="+")
        widget.bind("<Return>", lambda _e: self.on_id_change(from_focus=True), add="+")
        widget.bind("<<Paste>>", lambda _e: self.on_id_change(), add="+")
        widget.bind("<<ComboboxSelected>>", lambda _e: self.on_id_change(from_focus=True), add="+")

    def on_id_change(self, from_focus=False, preserve_existing=False, silent=False):
        if not silent:
            self._log_change(f"Cliente {self.idx+1}: cambió ID a {self.id_var.get()}")
        self._notify_id_change()
        self.update_client_options()
        cid = self.id_var.get().strip()
        if not cid:
            self._last_missing_lookup_id = None
            self.schedule_summary_refresh('clientes')
            return
        data = self.client_lookup.get(cid)
        if data:
            def set_if_present(var, key):
                value = data.get(key, "").strip()
                if value and should_autofill_field(var.get(), preserve_existing):
                    var.set(value)

            set_if_present(self.tipo_id_var, 'tipo_id')
            set_if_present(self.flag_var, 'flag')
            set_if_present(self.telefonos_var, 'telefonos')
            set_if_present(self.correos_var, 'correos')
            set_if_present(self.direcciones_var, 'direcciones')
            accionado = data.get('accionado', '').strip()
            if accionado and should_autofill_field(self.accionado_var.get(), preserve_existing):
                self.set_accionado_from_text(accionado)
            self._last_missing_lookup_id = None
            self._log_change(f"Autopoblado datos del cliente {cid}")
        elif from_focus and not silent and self.client_lookup:
            if self._last_missing_lookup_id != cid:
                messagebox.showerror(
                    "Cliente no encontrado",
                    (
                        f"El ID {cid} no existe en los catálogos de detalle. "
                        "Verifica el documento o actualiza client_details.csv."
                    ),
                )
                self._last_missing_lookup_id = cid
        self.schedule_summary_refresh('clientes')

    def _notify_id_change(self):
        new_id = self.id_var.get().strip()
        if new_id == self._last_tracked_id:
            return
        previous = self._last_tracked_id
        self._last_tracked_id = new_id
        if callable(self.id_change_callback):
            self.id_change_callback(self, previous, new_id)

    def get_data(self):
        return {
            "id_cliente": self.id_var.get().strip(),
            "id_caso": "",
            "tipo_id": self.tipo_id_var.get(),
            "flag": self.flag_var.get(),
            "telefonos": self.telefonos_var.get().strip(),
            "correos": self.correos_var.get().strip(),
            "direcciones": self.direcciones_var.get().strip(),
            "accionado": self.accionado_var.get().strip(),
        }

    def update_accionado_var(self, _event=None):
        selections = [ACCIONADO_OPTIONS[i] for i in self.accionado_listbox.curselection()]
        self.accionado_var.set("; ".join(selections))

    def set_accionado_from_text(self, value):
        raw_value = (value or "").strip()
        tokens = [item.strip() for item in raw_value.split(';') if item.strip()]
        valid_tokens = []
        invalid_tokens = []

        for token in tokens:
            (valid_tokens if token in ACCIONADO_OPTIONS else invalid_tokens).append(token)

        self.accionado_listbox.selection_clear(0, tk.END)
        if valid_tokens:
            valid_set = set(valid_tokens)
            for idx, name in enumerate(ACCIONADO_OPTIONS):
                if name in valid_set:
                    self.accionado_listbox.selection_set(idx)
        self.update_accionado_var()

        if invalid_tokens:
            message = (
                "Los siguientes valores de 'Accionado' no están en el catálogo y fueron ignorados: "
                + "; ".join(invalid_tokens)
            )
            log_event("validacion", message, self.logs)
            messagebox.showerror("Valores de Accionado no reconocidos", message)

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el cliente {self.idx+1}?"):
            self._log_change(f"Se eliminó cliente {self.idx+1}")
            self.frame.destroy()
            self.remove_callback(self)

    def _log_change(self, message: str):
        if callable(self.change_notifier):
            self.change_notifier(message)
        else:
            log_event("navegacion", message, self.logs)


__all__ = ["ClientFrame"]
