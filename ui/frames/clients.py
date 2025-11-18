"""Componentes de interfaz relacionados a clientes."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from settings import ACCIONADO_OPTIONS, FLAG_CLIENTE_LIST, TIPO_ID_LIST
from validators import (FieldValidator, log_event, should_autofill_field,
                        validate_client_id, validate_email_list,
                        validate_multi_selection, validate_phone_list,
                        validate_required_text)


class ClientFrame:
    """Representa un cliente y su interfaz dentro de la sección de clientes."""

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

        self.frame = ttk.LabelFrame(parent, text=f"Cliente {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)

        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="Tipo de ID:").pack(side="left")
        tipo_id_cb = ttk.Combobox(row1, textvariable=self.tipo_id_var, values=TIPO_ID_LIST, state="readonly", width=20)
        tipo_id_cb.pack(side="left", padx=5)
        tipo_id_cb.set('')
        self.tooltip_register(tipo_id_cb, "Selecciona el tipo de documento del cliente.")
        ttk.Label(row1, text="ID del cliente:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=5)
        id_entry.bind("<FocusOut>", lambda e: self.on_id_change(from_focus=True))
        id_entry.bind("<KeyRelease>", lambda e: self.on_id_change())
        self.tooltip_register(id_entry, "Escribe el número de documento del cliente.")

        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="Flag:").pack(side="left")
        flag_cb = ttk.Combobox(row2, textvariable=self.flag_var, values=FLAG_CLIENTE_LIST, state="readonly", width=20)
        flag_cb.pack(side="left", padx=5)
        flag_cb.set('')
        self.tooltip_register(flag_cb, "Indica si el cliente es afectado, vinculado u otro estado.")

        accionado_frame = ttk.Frame(self.frame)
        accionado_frame.pack(fill="x", pady=1)
        ttk.Label(accionado_frame, text="Accionado (seleccione uno o varios):").pack(anchor="w")
        self.accionado_listbox = tk.Listbox(
            accionado_frame,
            listvariable=tk.StringVar(value=ACCIONADO_OPTIONS),
            selectmode="multiple",
            exportselection=False,
            height=4,
            width=40,
        )
        self.accionado_listbox.pack(fill="x", padx=5)
        self.accionado_listbox.bind("<<ListboxSelect>>", self.update_accionado_var)
        self.tooltip_register(
            self.accionado_listbox,
            "Marca las tribus o equipos accionados por la alerta. Puedes escoger varias opciones.",
        )

        row3 = ttk.Frame(self.frame)
        row3.pack(fill="x", pady=1)
        ttk.Label(row3, text="Teléfonos (separados por ;):").pack(side="left")
        tel_entry = ttk.Entry(row3, textvariable=self.telefonos_var, width=30)
        tel_entry.pack(side="left", padx=5)
        tel_entry.bind("<FocusOut>", lambda e: self._log_change(f"Cliente {self.idx+1}: modificó teléfonos"))
        self.tooltip_register(tel_entry, "Ingresa números separados por ; sin guiones.")
        ttk.Label(row3, text="Correos (separados por ;):").pack(side="left")
        cor_entry = ttk.Entry(row3, textvariable=self.correos_var, width=30)
        cor_entry.pack(side="left", padx=5)
        cor_entry.bind("<FocusOut>", lambda e: self._log_change(f"Cliente {self.idx+1}: modificó correos"))
        self.tooltip_register(cor_entry, "Coloca correos electrónicos separados por ;.")
        ttk.Label(row3, text="Direcciones (separados por ;):").pack(side="left")
        dir_entry = ttk.Entry(row3, textvariable=self.direcciones_var, width=30)
        dir_entry.pack(side="left", padx=5)
        dir_entry.bind("<FocusOut>", lambda e: self._log_change(f"Cliente {self.idx+1}: modificó direcciones"))
        self.tooltip_register(dir_entry, "Puedes capturar varias direcciones separadas por ;.")

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=2)
        remove_btn = ttk.Button(btn_frame, text="Eliminar cliente", command=self.remove)
        remove_btn.pack(side="right")
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
        self.validators.append(
            FieldValidator(
                tel_entry,
                lambda: validate_phone_list(self.telefonos_var.get(), "los teléfonos del cliente"),
                self.logs,
                f"Cliente {self.idx+1} - Teléfonos",
                variables=[self.telefonos_var],
            )
        )
        self.validators.append(
            FieldValidator(
                cor_entry,
                lambda: validate_email_list(self.correos_var.get(), "los correos del cliente"),
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
        self.accionado_var.set(value.strip())
        self.accionado_listbox.selection_clear(0, tk.END)
        if not value:
            return
        targets = [item.strip() for item in value.split(';') if item.strip()]
        for idx, name in enumerate(ACCIONADO_OPTIONS):
            if name in targets:
                self.accionado_listbox.selection_set(idx)

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
