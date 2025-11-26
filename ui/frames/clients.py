"""Componentes de interfaz relacionados a clientes."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from settings import ACCIONADO_OPTIONS, FLAG_CLIENTE_LIST, TIPO_ID_LIST
from validators import (FieldValidator, log_event, should_autofill_field,
                        validate_client_id, validate_email_list,
                        validate_multi_selection, validate_phone_list,
                        validate_required_text)
from ui.frames.utils import build_required_label, ensure_grid_support
from ui.config import COL_PADX, ROW_PADY
from ui.layout import CollapsibleSection
from theme_manager import ThemeManager


ENTRY_STYLE = ThemeManager.ENTRY_STYLE
COMBOBOX_STYLE = ThemeManager.COMBOBOX_STYLE


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
        owner=None,
        summary_parent=None,
        client_lookup=None,
        summary_refresh_callback=None,
        change_notifier=None,
        id_change_callback=None,
    ):
        self.parent = parent
        self.owner = owner
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
        self._tree_sort_state: dict[str, bool] = {}
        self.summary_tree = None

        self.tipo_id_var = tk.StringVar()
        self.id_var = tk.StringVar()
        self.nombres_var = tk.StringVar()
        self.apellidos_var = tk.StringVar()
        self.flag_var = tk.StringVar()
        self.telefonos_var = tk.StringVar()
        self.correos_var = tk.StringVar()
        self.direcciones_var = tk.StringVar()
        self.accionado_var = tk.StringVar()
        self.accionado_options_var = tk.StringVar(value=ACCIONADO_OPTIONS)

        self.section = CollapsibleSection(
            parent, title="", on_toggle=lambda _section: self._sync_section_title()
        )
        self.section.pack(fill="x", padx=COL_PADX, pady=ROW_PADY)
        self._register_title_traces()

        if summary_parent is not None and owner is not None and not getattr(owner, "clients_summary_tree", None):
            self.summary_tree = self._build_summary(summary_parent)
            owner.clients_summary_tree = self.summary_tree
            owner.inline_summary_trees["clientes"] = self.summary_tree
            owner._client_summary_owner = self
        else:
            self.summary_tree = getattr(owner, "clients_summary_tree", None)

        self.frame = ttk.LabelFrame(self.section.content, text=f"Cliente {self.idx+1}")
        self.section.pack_content(self.frame, fill="x", expand=True)
        ensure_grid_support(self.frame)
        if hasattr(self.frame, "columnconfigure"):
            self.frame.columnconfigure(0, weight=0)
            self.frame.columnconfigure(1, weight=1)
            self.frame.columnconfigure(2, weight=0)

        tipo_id_label = build_required_label(
            self.frame,
            "Tipo de ID:",
            tooltip_register=self.tooltip_register,
        )
        tipo_id_label.grid(
            row=0, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        tipo_id_cb = ttk.Combobox(
            self.frame,
            textvariable=self.tipo_id_var,
            values=TIPO_ID_LIST,
            state="readonly",
            width=20,
            style=COMBOBOX_STYLE,
        )
        tipo_id_cb.grid(row=0, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=0, column=2, padx=COL_PADX, pady=ROW_PADY)
        tipo_id_cb.set('')
        self.tooltip_register(tipo_id_cb, "Selecciona el tipo de documento del cliente.")

        client_id_label = build_required_label(
            self.frame,
            "ID del cliente:",
            tooltip_register=self.tooltip_register,
        )
        client_id_label.grid(
            row=1, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        id_entry = ttk.Entry(self.frame, textvariable=self.id_var, width=20, style=ENTRY_STYLE)
        id_entry.grid(row=1, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=1, column=2, padx=COL_PADX, pady=ROW_PADY)
        self._bind_identifier_triggers(id_entry)
        self.tooltip_register(id_entry, "Escribe el número de documento del cliente.")

        nombres_label = build_required_label(
            self.frame,
            "Nombres:",
            tooltip_register=self.tooltip_register,
        )
        nombres_label.grid(
            row=2, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        nombres_entry = ttk.Entry(
            self.frame, textvariable=self.nombres_var, width=25, style=ENTRY_STYLE
        )
        nombres_entry.grid(row=2, column=1, columnspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        nombres_entry.bind(
            "<FocusOut>", lambda _e: self._log_change(f"Cliente {self.idx+1}: modificó nombres"), add="+"
        )
        self.tooltip_register(nombres_entry, "Ingresa los nombres del cliente.")

        apellidos_label = build_required_label(
            self.frame,
            "Apellidos:",
            tooltip_register=self.tooltip_register,
        )
        apellidos_label.grid(
            row=3, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        apellidos_entry = ttk.Entry(
            self.frame, textvariable=self.apellidos_var, width=25, style=ENTRY_STYLE
        )
        apellidos_entry.grid(row=3, column=1, columnspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        apellidos_entry.bind(
            "<FocusOut>", lambda _e: self._log_change(f"Cliente {self.idx+1}: modificó apellidos"), add="+"
        )
        self.tooltip_register(apellidos_entry, "Ingresa los apellidos del cliente.")

        flag_label = build_required_label(
            self.frame,
            "Flag:",
            tooltip_register=self.tooltip_register,
        )
        flag_label.grid(
            row=4, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        flag_cb = ttk.Combobox(
            self.frame,
            textvariable=self.flag_var,
            values=FLAG_CLIENTE_LIST,
            state="readonly",
            width=20,
            style=COMBOBOX_STYLE,
        )
        flag_cb.grid(row=4, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=4, column=2, padx=COL_PADX, pady=ROW_PADY)
        flag_cb.set('')
        self.tooltip_register(flag_cb, "Indica si el cliente es afectado, vinculado u otro estado.")

        accionado_label = build_required_label(
            self.frame,
            "Accionado (seleccione uno o varios):",
            tooltip_register=self.tooltip_register,
        )
        accionado_label.grid(
            row=5, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        accionado_list_container = ttk.Frame(self.frame)
        ensure_grid_support(accionado_list_container)
        accionado_list_container.grid(
            row=5, column=1, columnspan=2, padx=COL_PADX, pady=ROW_PADY, sticky="we"
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

        tel_label = build_required_label(
            self.frame,
            "Teléfonos (separados por ;):",
            tooltip_register=self.tooltip_register,
        )
        tel_label.grid(
            row=6, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        tel_entry = ttk.Entry(
            self.frame, textvariable=self.telefonos_var, width=30, style=ENTRY_STYLE
        )
        tel_entry.grid(row=6, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=6, column=2, padx=COL_PADX, pady=ROW_PADY)
        tel_entry.bind("<FocusOut>", lambda e: self._log_change(f"Cliente {self.idx+1}: modificó teléfonos"))
        self.tooltip_register(
            tel_entry,
            "Campo obligatorio. Ingresa al menos un número telefónico separado por ; sin guiones.",
        )

        correo_label = build_required_label(
            self.frame,
            "Correos (separados por ;):",
            tooltip_register=self.tooltip_register,
        )
        correo_label.grid(
            row=7, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        cor_entry = ttk.Entry(
            self.frame, textvariable=self.correos_var, width=30, style=ENTRY_STYLE
        )
        cor_entry.grid(row=7, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=7, column=2, padx=COL_PADX, pady=ROW_PADY)
        cor_entry.bind("<FocusOut>", lambda e: self._log_change(f"Cliente {self.idx+1}: modificó correos"))
        self.tooltip_register(
            cor_entry,
            "Campo obligatorio. Coloca al menos un correo electrónico separado por ;.",
        )

        ttk.Label(self.frame, text="Direcciones (separados por ;):").grid(
            row=8, column=0, padx=COL_PADX, pady=ROW_PADY, sticky="e"
        )
        dir_entry = ttk.Entry(
            self.frame, textvariable=self.direcciones_var, width=30, style=ENTRY_STYLE
        )
        dir_entry.grid(row=8, column=1, padx=COL_PADX, pady=ROW_PADY, sticky="we")
        ttk.Label(self.frame, text="").grid(row=8, column=2, padx=COL_PADX, pady=ROW_PADY)
        dir_entry.bind("<FocusOut>", lambda e: self._log_change(f"Cliente {self.idx+1}: modificó direcciones"))
        self.tooltip_register(dir_entry, "Puedes capturar varias direcciones separadas por ;.")

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
        self._sync_section_title()

    def set_lookup(self, lookup):
        self.client_lookup = lookup or {}
        self._last_missing_lookup_id = None

    def _register_title_traces(self):
        for var in (self.id_var, self.nombres_var, self.apellidos_var):
            var.trace_add("write", self._on_identity_field_change)

    def _build_section_title(self) -> str:
        base_title = f"Cliente {self.idx+1}"
        if getattr(self, "section", None) and not self.section.is_open:
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

            set_if_present(self.nombres_var, 'nombres')
            set_if_present(self.apellidos_var, 'apellidos')
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
            "nombres": self.nombres_var.get(),
            "apellidos": self.apellidos_var.get(),
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
            if hasattr(self, "section"):
                self.section.destroy()
            self.remove_callback(self)

    def clear_values(self):
        """Vacía los valores capturados manteniendo visibles los widgets."""

        def _reset():
            for var in (
                self.tipo_id_var,
                self.id_var,
                self.nombres_var,
                self.apellidos_var,
                self.flag_var,
                self.telefonos_var,
                self.correos_var,
                self.direcciones_var,
                self.accionado_var,
            ):
                var.set("")
            try:
                self.accionado_listbox.selection_clear(0, tk.END)
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

    def _log_change(self, message: str):
        if callable(self.change_notifier):
            self.change_notifier(message)
        else:
            log_event("navegacion", message, self.logs)
        self.schedule_summary_refresh('clientes')

    # ------------------------------------------------------------------
    # Resumen
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
            ("tipo_id", "Tipo ID"),
            ("flag", "Flag"),
            ("telefonos", "Teléfonos"),
            ("correos", "Correos"),
            ("direcciones", "Direcciones"),
            ("accionado", "Accionado"),
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
            tree.column(col_id, width=140, anchor="w")

        palette = ThemeManager.current()
        if hasattr(tree, "tag_configure"):
            tree.tag_configure("even", background=palette.get("heading_background", palette.get("background")), foreground=palette.get("foreground"))
            tree.tag_configure("odd", background=palette.get("background"), foreground=palette.get("foreground"))

        tree.bind("<<TreeviewSelect>>", self._on_summary_select)
        tree.bind("<Double-1>", self._on_summary_double_click)
        summary_frame.pack(fill="both", expand=True)
        return tree

    def refresh_summary(self):
        tree = self.summary_tree or getattr(self.owner, "clients_summary_tree", None)
        if not tree or not hasattr(tree, "get_children"):
            return
        try:
            children = tree.get_children()
            if children:
                tree.delete(*children)
        except Exception:
            return
        clients = getattr(self.owner, "client_frames", []) if self.owner else []
        seen_iids: set[str] = set()
        base_counters: dict[str, int] = {}
        for idx, client in enumerate(clients):
            data = client.get_data()
            values = (
                data.get("id_cliente", ""),
                data.get("nombres", ""),
                data.get("apellidos", ""),
                data.get("tipo_id", ""),
                data.get("flag", ""),
                data.get("telefonos", ""),
                data.get("correos", ""),
                data.get("direcciones", ""),
                data.get("accionado", ""),
            )
            tags = ("even",) if idx % 2 == 0 else ("odd",)
            base_iid = str(data.get("id_cliente") or f"cliente-{idx}")
            base_counters.setdefault(base_iid, 0)
            candidate_iid = base_iid
            if candidate_iid in seen_iids:
                base_counters[base_iid] += 1
                candidate_iid = f"{base_iid}-{base_counters[base_iid]}"
                while candidate_iid in seen_iids:
                    base_counters[base_iid] += 1
                    candidate_iid = f"{base_iid}-{base_counters[base_iid]}"
                log_event(
                    "validacion",
                    f"IID de cliente duplicado '{base_iid}' detectado, usando '{candidate_iid}'",
                    self.logs,
                )
            try:
                tree.insert("", "end", iid=candidate_iid, values=values, tags=tags)
                seen_iids.add(candidate_iid)
            except Exception:
                fallback_suffix = base_counters[base_iid] + 1
                fallback_iid = f"{base_iid}-{fallback_suffix}"
                while fallback_iid in seen_iids:
                    fallback_suffix += 1
                    fallback_iid = f"{base_iid}-{fallback_suffix}"
                log_event(
                    "validacion",
                    (
                        f"No se pudo insertar el IID '{candidate_iid}'. "
                        f"Reintentando con '{fallback_iid}'"
                    ),
                    self.logs,
                )
                try:
                    tree.insert("", "end", iid=fallback_iid, values=values, tags=tags)
                    seen_iids.add(fallback_iid)
                    base_counters[base_iid] = fallback_suffix
                except Exception:
                    log_event(
                        "validacion",
                        (
                            f"Se omitió el cliente con IID '{candidate_iid}' al fallar los intentos "
                            f"de inserción inclusive con '{fallback_iid}'"
                        ),
                        self.logs,
                    )
        self._apply_summary_theme(tree)
        self._on_summary_select()

    def _sort_summary(self, column):
        tree = self.summary_tree or getattr(self.owner, "clients_summary_tree", None)
        if not tree or not hasattr(tree, "get_children"):
            return
        reverse = self._tree_sort_state.get(column, False)
        items = list(tree.get_children(""))
        col_index = tree["columns"].index(column)
        items.sort(key=lambda item: tree.item(item, "values")[col_index], reverse=reverse)
        for idx, item in enumerate(items):
            tree.move(item, "", idx)
            tag = "even" if idx % 2 == 0 else "odd"
            tree.item(item, tags=(tag,))
        self._tree_sort_state[column] = not reverse

    def _on_summary_select(self, _event=None):
        tree = self.summary_tree or getattr(self.owner, "clients_summary_tree", None)
        if not tree or not hasattr(tree, "selection"):
            return
        if callable(getattr(self.owner, "_on_client_selected", None)):
            try:
                self.owner._on_client_selected()
            except Exception:
                pass

    def _on_summary_double_click(self, _event=None):
        self._on_summary_select()
        if callable(getattr(self.owner, "_edit_selected_client", None)):
            try:
                self.owner._edit_selected_client()
            except Exception:
                pass

    def _apply_summary_theme(self, tree):
        palette = ThemeManager.current()
        if hasattr(tree, "tag_configure"):
            tree.tag_configure("even", background=palette.get("heading_background", palette.get("background")), foreground=palette.get("foreground"))
            tree.tag_configure("odd", background=palette.get("background"), foreground=palette.get("foreground"))


__all__ = ["ClientFrame"]
