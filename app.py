#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Nov 1 11:04:14 2025

@author: pabloillescasbuendia
"""
"""
app.py
==================

Esta aplicación implementa una versión de escritorio de la herramienta de
gestión de casos de fraude que previamente se desarrolló como sitio web.

Utiliza la biblioteca estándar ``tkinter`` para construir una interfaz de
usuario gráfica sin necesidad de arrancar un servidor web local. La
aplicación permite crear casos con sus clientes, colaboradores, productos,
riesgos identificados, normas transgredidas y narrativas. Soporta la
adición dinámica de registros, importación desde ficheros CSV, validación
de reglas de negocio, auto‑guardado del estado en un archivo JSON y
exportación de los datos normalizados en múltiples ficheros CSV. Al
almacenar cada entidad en tablas separadas y vincularlas mediante claves
primarias y foráneas, los datos pueden cargarse posteriormente en otros
sistemas o retomarse en otra estación de trabajo.

Para ejecutar la aplicación basta con tener Python 3 instalado; no se
requieren bibliotecas externas. La interfaz se abre en una ventana
independiente. Los datos se validan a medida que el usuario escribe y
se registran en un log interno para fines de análisis y mejora.

Funciones principales:
  * Gestión de los datos del caso (tipo de informe, categorías y
    modalidades, canal y proceso).
  * Gestión dinámica de clientes, colaboradores y productos con listas
    anidadas para teléfonos, correos, direcciones y asignaciones de
    montos.
  * Importación de clientes, colaboradores, productos y registros
    combinados desde ficheros CSV.
  * Auto‑poblado de datos de colaboradores a partir de un fichero
    ``team_details.csv`` si está disponible.
  * Validación de reglas de negocio (unicidad de combinaciones,
    coherencia de fechas y montos, requisitos de reclamos y analíticas,
    patrones de identificadores, etc.).
  * Auto‑guardado del estado del formulario en un archivo JSON cada vez
    que cambian los datos y restauración desde dicho archivo.
  * Exportación de los datos normalizados en varios CSV con la misma
    estructura que el archivo Excel de referencia.
  * Registro de eventos y errores en un log que se descarga junto con
    los demás ficheros.

Nota: el diseño de la interfaz y de las funciones de validación está
orientado a mantener la mayor parte de la funcionalidad del sitio web
original, pero por simplicidad visual se utilizan cuadros de texto
separados por punto y coma para campos con múltiples valores (teléfonos,
correos, direcciones y planes de acción).
"""

import base64
import csv
import io
import json
import math
import os
import random
import re
import shutil
import threading
import wave
import zipfile
from collections import defaultdict
from collections.abc import Mapping
from contextlib import suppress
from datetime import datetime, timedelta
from decimal import Decimal
from importlib import util as importlib_util
from pathlib import Path
from typing import Iterable, Optional

import tkinter as tk
from tkinter import filedialog
from tkinter import font as tkfont
from tkinter import messagebox, scrolledtext, ttk

from inheritance_service import InheritanceService
from models import (AutofillService, build_detail_catalog_id_index,
                    CatalogService, iter_massive_csv_rows,
                    normalize_detail_catalog_key, parse_involvement_entries)
from report_builder import (build_docx, build_report_filename, CaseData,
                            DOCX_AVAILABLE, DOCX_MISSING_MESSAGE, save_md)
from settings import (AUTOSAVE_FILE, BASE_DIR, CANAL_LIST, CLIENT_ID_ALIASES,
                      CRITICIDAD_LIST, DETAIL_LOOKUP_ALIASES,
                      ENABLE_EXTENDED_ANALYSIS_SECTIONS,
                      ensure_external_drive_dir, EXPORTS_DIR,
                      EXTERNAL_LOGS_FILE, FLAG_CLIENTE_LIST,
                      FLAG_COLABORADOR_LIST, LOGS_FILE, MASSIVE_SAMPLE_FILES,
                      NORM_ID_ALIASES, PROCESO_LIST, PRODUCT_ID_ALIASES,
                      RICH_TEXT_MAX_CHARS, RISK_ID_ALIASES, STORE_LOGS_LOCALLY,
                      TAXONOMIA, TEAM_ID_ALIASES, TEMP_AUTOSAVE_COMPRESS_OLD,
                      TEMP_AUTOSAVE_DEBOUNCE_SECONDS,
                      TEMP_AUTOSAVE_MAX_AGE_DAYS, TEMP_AUTOSAVE_MAX_PER_CASE,
                      TIPO_FALTA_LIST, TIPO_ID_LIST, TIPO_INFORME_LIST,
                      TIPO_MONEDA_LIST, TIPO_PRODUCTO_LIST, TIPO_SANCION_LIST)
from theme_manager import ThemeManager
from ui.config import COL_PADX, FONT_BASE, ROW_PADY
from ui.effects.confetti import ConfettiBurst
from ui.frames import (CaseFrame, ClientFrame, NormFrame, PRODUCT_MONEY_SPECS,
                       ProductFrame, RiskFrame, TeamMemberFrame)
from ui.frames.utils import (
    GlobalScrollBinding,
    build_grid_container,
    create_scrollable_container,
    ensure_grid_support,
    grid_and_configure,
    refresh_dynamic_rows,
    resize_scrollable_to_content,
)
from ui.layout import ActionBar
from ui.tooltips import HoverTooltip
from validators import (drain_log_queue, FieldValidator, log_event,
                        LOG_FIELDNAMES, normalize_log_row,
                        normalize_without_accents, parse_decimal_amount,
                        resolve_catalog_product_type, sanitize_rich_text,
                        should_autofill_field, sum_investigation_components,
                        TIPO_PRODUCTO_NORMALIZED, validate_agency_code,
                        validate_case_id, validate_client_id,
                        validate_codigo_analitica, validate_date_text,
                        validate_email_list, validate_money_bounds,
                        validate_multi_selection, validate_norm_id,
                        validate_phone_list, validate_product_dates,
                        validate_product_id, validate_reclamo_id,
                        validate_required_text, validate_risk_id,
                        validate_team_member_id)

PIL_AVAILABLE = importlib_util.find_spec("PIL") is not None
if PIL_AVAILABLE:
    from PIL import Image, ImageTk  # type: ignore
else:  # pragma: no cover - entorno sin Pillow
    Image = None
    ImageTk = None

SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@")
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
POSITIVE_PHRASES = (
    "¡Excelente!",
    "Caso impecable",
    "Listo para avanzar",
    "Buen trabajo",
    "Validación completada",
)
CONFIRMATION_WAV_B64 = (
    "UklGRiQFAABXQVZFZm10IBAAAAABAAEAgD4AAIA+AAABAAgAZGF0YQAFAACAlai2vr63qZeBbFlKQkFHVGZ8kaW0vb+5rJuFcFxMQ0BFUWN4jaKyvL+7r56JdF9PREBET190iZ6vu7+8sqKNeGNRRUBDTFxwhZusub+9tKWRfGZUR0FCSllsgZept76+tqiVf2pXSUFBSFZofpOmtb2+uKuZg25aS0JARlNkeo+js7y/uq6ch3JdTUNARFBhdougsLu/u7Cgi3ZhUERAQ01dcoecrrq/vLOjj3pkU0ZAQktaboOZq7i+vbWmk35oVkhBQUlXaoCVqLa+vrepl4FsWUpCQUdUZnyRpbS9v7msm4VwXExDQEVRY3iNorK8v7uvnol0X09EQERPX3SJnq+7v7yyoo14Y1FFQENMXHCFm6y5v720pZF8ZlRHQUJKWWyBl6m3vr62qJWAaldJQUFIVmh+k6a1vb64q5mDblpLQkBGU2R6j6OzvL+6rpyHcl1NQ0BEUGF2i6Cwu7+7sKCLdmFQREBDTV1yh5yuur+8s6OPemRTRkBCS1pug5mruL69taaTfmhWSEFBSVdqgJWotr6+t6mXgWxZSkJBR1RmfJGltL2/uaybhXBcTENARVFjeI2isry/u6+eiXRfT0RARE9fdImer7u/vLKijXhjUUVAQ0xccIWbrLm/vbSlkXxmVEdBQkpZbIGXqbe+vraolX9qV0lBQUhWaH6TprW9vrirmYNuWktCQEZTZHqPo7O8v7qunIdyXU1DQERQYXaLoLC7v7uwoIt2YVBEQENNXXKHnK66v7yzo496ZFNGQEJLWm6Dmau4vr21ppN+aFZIQUFJV2p/lai2vr63qZeBbFlKQkFHVGZ8kaW0vb+5rJuFcFxMQ0BFUWN4jaKyvL+7r56JdF9PREBET190iZ6vu7+8sqKNeGNRRUBDTFxwhZusub+9tKWRfGZUR0FCSllsgZept76+tqiVgGpXSUFBSFZofpOmtb2+uKuZg25aS0JARlNkeo+js7y/uq6ch3JdTUNARFBhdougsLu/u7Cgi3ZhUERAQ01dcoecrrq/vLOjj3pkU0ZAQktaboOZq7i+vbWmk35oVkhBQUlXaoCVqLa+vrepl4FsWUpCQUdUZnyRpbS9v7msm4VwXExDQEVRY3iNorK8v7uvnol0X09EQERPX3SJnq+7v7yyoo14Y1FFQENMXHCFm6y5v720pZF8ZlRHQUJKWWyBl6m3vr62qJV/aldJQUFIVmh+k6a1vb64q5mDblpLQkBGU2R6j6OzvL+6rpyHcl1NQ0BEUGF2i6Cwu7+7sKCLdmFQREBDTV1yh5yuur+8s6OPemRTRkBCS1pug5mruL69taaTfmhWSEFBSVdqgJWotr6+t6mXgWxZSkJBR1RmfJGltL2/uaybhXBcTENARVFjeI2isry/u6+eiXRfT0RARE9fdImer7u/vLKijXhjUUVAQ0xccIWbrLm/vbSlkXxmVEdBQkpZbIGXqbe+vraolX9qV0lBQUhWaH6TprW9vrirmYNuWktCQEZTZHqPo7O8v7qunIdyXU1DQERQYXaLoLC7v7uwoIt2YVBEQENNXXKHnK66v7yzo496ZFNGQEJLWm6Dmau4vr21ppN+aFZIQUFJV2p/lai2vr63qZeBbFlKQkFHVGZ8kaW0vb+5rJuFcFxMQ0BFUWN4jaKyvL+7r56JdF9PREBET190iZ6vu7+8sqKNeGNRRUBDTFxwhZusub+9tA=="
)



class ValidationPanel(ttk.Frame):
    """Panel compacto para mostrar errores y advertencias de validación."""

    ICONS = {
        "ok": "✅",
        "error": "⚠️",
        "warning": "⚠️",
    }
    COLLAPSED_WIDTH = 90

    def __init__(self, parent, *, on_focus_request=None):
        super().__init__(parent)
        self.on_focus_request = on_focus_request
        self._entries: dict[str, str] = {}
        self._targets: dict[str, dict[str, object] | tk.Widget] = {}
        self._entry_status: dict[str, str] = {}
        self._placeholder_id: Optional[str] = None
        self._collapsed = True
        self._issue_count_var = tk.StringVar(value="⚠️ 0")
        self._init_ui()
        self.collapse(force=True)

    def _init_ui(self) -> None:
        self.columnconfigure(0, weight=1, minsize=self.COLLAPSED_WIDTH)
        self.rowconfigure(0, weight=1)

        self._content_container = ttk.Frame(self)
        self._content_container.grid(row=0, column=0, sticky="nsew")
        self._content_container.columnconfigure(0, weight=1)
        self._content_container.rowconfigure(1, weight=1)

        header = ttk.Frame(self._content_container)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=(5, 0))
        header.columnconfigure(1, weight=1)
        title = ttk.Label(
            header, text="Panel de validación", font=("TkDefaultFont", 10, "bold")
        )
        title.grid(row=0, column=0, sticky="w")

        self._issue_badge = ttk.Label(header, textvariable=self._issue_count_var)
        self._issue_badge.grid(row=0, column=1, sticky="e", padx=(4, 0))
        self._issue_badge.configure(cursor="hand2")
        self._issue_badge.bind("<Button-1>", lambda _e: self.expand())
        self._issue_badge.bind("<Return>", lambda _e: self.expand())
        self._toggle_button = ttk.Button(header, width=3, text="⇤", command=self.toggle)
        self._toggle_button.grid(row=0, column=2, sticky="e")

        columns = ("mensaje", "origen")
        self.tree = ttk.Treeview(
            self._content_container,
            columns=columns,
            show="tree headings",
            height=16,
        )
        self.tree.heading("#0", text="Estado")
        self.tree.heading("mensaje", text="Detalle")
        self.tree.heading("origen", text="Origen")
        self.tree.column("#0", width=48, minwidth=36, anchor="center", stretch=True)
        self.tree.column("mensaje", width=240, minwidth=160, anchor="w", stretch=True)
        self.tree.column("origen", width=120, minwidth=96, anchor="w", stretch=True)
        scrollbar = ttk.Scrollbar(self._content_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(5, 0), pady=5)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=5)
        self.tree.bind("<Double-1>", lambda _e: self.focus_selected())
        self._ensure_placeholder()
        self._focus_button = ttk.Button(
            self._content_container, text="Corregir ahora", command=self.focus_selected
        )
        self._focus_button.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))

        self._collapsed_strip = ttk.Frame(self, cursor="hand2")
        self._collapsed_strip.grid_rowconfigure(0, weight=1)
        self._collapsed_strip.grid_propagate(False)
        self._collapsed_strip.configure(width=self.COLLAPSED_WIDTH)
        strip_label = ttk.Label(
            self._collapsed_strip, textvariable=self._issue_count_var, anchor="center"
        )
        strip_label.grid(row=0, column=0, padx=6, pady=5, sticky="n")
        strip_label.configure(cursor="hand2", takefocus=True)
        strip_label.bind("<Button-1>", lambda _e: self.expand())
        strip_label.bind("<Return>", lambda _e: self.expand())
        self._collapsed_strip.bind("<Button-1>", lambda _e: self.expand())
        expand_button = ttk.Button(
            self._collapsed_strip, width=3, text="⇥", command=self.expand
        )
        expand_button.grid(row=1, column=0, padx=6, pady=5, sticky="s")
        self._collapsed_strip.grid_remove()

    def get_anchor_widget(self) -> tk.Widget | None:
        """Devuelve el widget ideal para anclar overlays o ayudas visuales."""

        try:
            if self._collapsed:
                return self._collapsed_strip
            return self._toggle_button or self
        except tk.TclError:
            return None

    def _ensure_placeholder(self) -> None:
        if self._entries or self._placeholder_id:
            return
        self._placeholder_id = self.tree.insert(
            "", "end", text=self.ICONS["ok"], values=("Sin validaciones registradas", ""),
        )
        self._refresh_issue_count()
        self._update_focus_button_state()

    def _remove_placeholder(self) -> None:
        if self._placeholder_id:
            self.tree.delete(self._placeholder_id)
            self._placeholder_id = None
            self._update_focus_button_state()

    def _update_focus_button_state(self) -> None:
        if not hasattr(self, "_focus_button"):
            return
        if self._entries:
            self._focus_button.state(["!disabled"])
        else:
            self._focus_button.state(["disabled"])

    def _icon_for(self, status: str) -> str:
        return self.ICONS.get(status, self.ICONS["error"])

    def _refresh_issue_count(self) -> None:
        issue_count = sum(1 for status in self._entry_status.values() if status != "ok")
        icon = "⚠️" if issue_count else self.ICONS["ok"]
        self._issue_count_var.set(f"{icon} {issue_count}")

    def toggle(self) -> None:
        if self._collapsed:
            self.expand()
        else:
            self.collapse()

    def collapse(self, *, force: bool = False) -> None:
        if self._collapsed and not force:
            return
        self._collapsed = True
        self._content_container.grid_remove()
        self._collapsed_strip.grid(row=0, column=0, sticky="ns")
        self._toggle_button.configure(text="⇥")

    def expand(self) -> None:
        if not self._collapsed:
            return
        self._collapsed = False
        self._collapsed_strip.grid_remove()
        self._content_container.grid(row=0, column=0, sticky="nsew")
        self._toggle_button.configure(text="⇤")

    def update_entry(
        self,
        key: str,
        message: Optional[str],
        *,
        severity: str = "error",
        origin: str | None = None,
        widget: tk.Widget | None = None,
    ) -> None:
        """Inserta o actualiza una fila en la tabla de validación."""

        status = "ok" if not message else severity
        display_message = message or "Sin errores"
        item_id = self._entries.get(key)
        created = False
        if item_id:
            self.tree.item(item_id, text=self._icon_for(status), values=(display_message, origin or ""))
        else:
            self._remove_placeholder()
            item_id = self.tree.insert(
                "",
                "end",
                text=self._icon_for(status),
                values=(display_message, origin or ""),
            )
            self._entries[key] = item_id
            created = True
        self._entry_status[key] = status
        if widget or origin is not None:
            self._targets[item_id] = {"widget": widget, "origin": origin}
        elif item_id in self._targets:
            self._targets.pop(item_id, None)
        if not self._entries:
            self._ensure_placeholder()
        self._refresh_issue_count()
        self._update_focus_button_state()
        if created and (not self.tree.selection() or self.tree.selection() == (self._placeholder_id,)):
            self._select_first_actionable()

    def focus_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            self._select_first_actionable()
            selection = self.tree.selection()
            if not selection:
                return
        target_info = self._targets.get(selection[0])
        widget = None
        origin = None
        if isinstance(target_info, dict):
            widget = target_info.get("widget")
            origin = target_info.get("origin")
        else:
            widget = target_info
        if widget and self.on_focus_request:
            try:
                self.on_focus_request(widget, origin)
            except TypeError:
                self.on_focus_request(widget)

    def _select_first_actionable(self) -> None:
        for item_id in self.tree.get_children(""):
            if item_id != self._placeholder_id:
                self.tree.selection_set(item_id)
                self.tree.focus(item_id)
                return
        self.tree.selection_remove(self.tree.selection())

    def remove_entries(self, keys: Iterable[str]) -> None:
        removed = False
        for key in keys:
            item_id = self._entries.pop(key, None)
            if not item_id:
                continue
            self.tree.delete(item_id)
            self._targets.pop(item_id, None)
            self._entry_status.pop(key, None)
            removed = True
        if not removed:
            return
        if not self._entries:
            self._ensure_placeholder()
        self._refresh_issue_count()
        self._update_focus_button_state()
        self._select_first_actionable()

    def _clear_batch_entries(self) -> None:
        to_delete = [key for key in self._entries if key.startswith("batch:")]
        for key in to_delete:
            item_id = self._entries.pop(key, None)
            if item_id:
                self.tree.delete(item_id)
                self._targets.pop(item_id, None)
            self._entry_status.pop(key, None)
        self._refresh_issue_count()

    def show_batch_results(
        self,
        errors: list[str],
        warnings: list[str],
        focus_map: Optional[dict[str, tk.Widget]] = None,
        origin: str = "Validación integral",
    ) -> None:
        """Reemplaza el bloque de validaciones globales con los nuevos resultados."""

        self._clear_batch_entries()
        focus_map = focus_map or {}

        def _match_widget(message: str) -> Optional[tk.Widget]:
            lowered = message.lower()
            for hint, widget in focus_map.items():
                if hint.lower() in lowered:
                    return widget
            return None

        for index, message in enumerate(errors):
            widget = _match_widget(message)
            self.update_entry(
                f"batch:error:{index}", message, severity="error", origin=origin, widget=widget
            )
        for index, message in enumerate(warnings):
            widget = _match_widget(message)
            self.update_entry(
                f"batch:warning:{index}", message, severity="warning", origin=origin, widget=widget
            )
        if not errors and not warnings:
            self._ensure_placeholder()

class FraudCaseApp:
    AUTOSAVE_DELAY_MS = 4000
    SUMMARY_REFRESH_DELAY_MS = 250
    LOG_FLUSH_INTERVAL_MS = 5000
    HEATMAP_BUCKET_SIZE = 100
    IMAGE_MAX_BYTES = 3 * 1024 * 1024
    IMAGE_MAX_DIMENSION = 2000
    IMAGE_DISPLAY_MAX = 1000
    TEAM_ROW_DETAIL_WEIGHT = 3
    TEAM_ROW_DETAIL_HIDDEN_WEIGHT = 0
    IMPORT_CONFIG = {
        "clientes": {
            "title": "Seleccionar CSV de clientes",
            "initialfile": Path(MASSIVE_SAMPLE_FILES.get("clientes", "")).name,
            "expected_headers": (
                "id_cliente",
                "nombres",
                "apellidos",
                "tipo_id",
                "flag",
                "telefonos",
                "correos",
                "direcciones",
                "accionado",
            ),
            "expected_keyword": "cliente",
        },
        "colaboradores": {
            "title": "Seleccionar CSV de colaboradores",
            "initialfile": Path(MASSIVE_SAMPLE_FILES.get("colaboradores", "")).name,
            "expected_headers": (
                "id_colaborador",
                "flag",
                "nombres",
                "apellidos",
                "division",
                "area",
                "servicio",
                "puesto",
                "nombre_agencia",
                "codigo_agencia",
                "tipo_falta",
                "tipo_sancion",
            ),
            "expected_keyword": "colaborador",
        },
        "productos": {
            "title": "Seleccionar CSV de productos",
            "initialfile": Path(MASSIVE_SAMPLE_FILES.get("productos", "")).name,
            "expected_headers": (
                "id_producto",
                "id_cliente",
                "tipo_producto",
                "categoria1",
                "categoria2",
                "modalidad",
                "canal",
                "proceso",
                "fecha_ocurrencia",
                "fecha_descubrimiento",
                "monto_investigado",
                "tipo_moneda",
                "monto_perdida_fraude",
                "monto_falla_procesos",
                "monto_contingencia",
                "monto_recuperado",
                "monto_pago_deuda",
                "id_reclamo",
                "nombre_analitica",
                "codigo_analitica",
            ),
            "expected_keyword": "producto",
        },
        "riesgos": {
            "title": "Seleccionar CSV de riesgos",
            "initialfile": Path(MASSIVE_SAMPLE_FILES.get("riesgos", "")).name,
            "expected_headers": (
                "id_riesgo",
                "id_caso",
                "lider",
                "descripcion",
                "criticidad",
                "exposicion_residual",
                "planes_accion",
            ),
            "expected_keyword": "riesgo",
        },
        "normas": {
            "title": "Seleccionar CSV de normas",
            "initialfile": Path(MASSIVE_SAMPLE_FILES.get("normas", "")).name,
            "expected_headers": (
                "id_norma",
                "id_caso",
                "descripcion",
                "fecha_vigencia",
            ),
            "expected_keyword": "norma",
        },
        "reclamos": {
            "title": "Seleccionar CSV de reclamos",
            "initialfile": Path(MASSIVE_SAMPLE_FILES.get("reclamos", "")).name,
            "expected_headers": (
                "id_reclamo",
                "id_caso",
                "id_producto",
                "nombre_analitica",
                "codigo_analitica",
            ),
            "expected_keyword": "reclamo",
        },
        "combinado": {
            "title": "Seleccionar CSV combinado",
            "initialfile": Path(MASSIVE_SAMPLE_FILES.get("combinado", "")).name,
            "expected_headers": (
                "id_producto",
                "id_cliente",
                "tipo_producto",
                "categoria1",
                "categoria2",
                "modalidad",
                "canal",
                "proceso",
                "fecha_ocurrencia",
                "fecha_descubrimiento",
                "monto_investigado",
                "tipo_moneda",
                "monto_perdida_fraude",
                "monto_falla_procesos",
                "monto_contingencia",
                "monto_recuperado",
                "monto_pago_deuda",
                "id_reclamo",
                "nombre_analitica",
                "codigo_analitica",
                "id_colaborador",
            ),
            "expected_keyword": "combinado",
        },
    }
    _external_drive_path: Optional[Path] = None
    _external_log_file_initialized: bool = False
    _extended_sections_enabled: bool = ENABLE_EXTENDED_ANALYSIS_SECTIONS
    _validation_panel: Optional[ValidationPanel] = None

    """Clase que encapsula la aplicación de gestión de casos de fraude."""

    def __init__(self, root):
        self.root = root
        # FIX: Initialize autosave timestamp tracker
        self._last_temp_saved_at = None
        # Lista para logs de navegación y validación
        self.logs = []
        self._streak_file = Path(AUTOSAVE_FILE).with_name("streak_status.json")
        self._streak_info: dict[str, object] = self._load_streak_info()
        self._scroll_binder = GlobalScrollBinding(self.root)
        self.root.title(self._build_window_title())
        self._suppress_messagebox = False
        self._startup_complete = False
        self._reset_navigation_metrics()
        self._hover_tooltips = []
        self.validators = []
        self._validation_feedback_initialized = False
        self._validity_initialized = False
        self._last_all_valid = False
        self._checkmark_overlay = None
        self._last_validated_risk_exposure_total = Decimal('0')
        self._log_flush_job_id: Optional[str] = None
        self._docx_available = DOCX_AVAILABLE
        local_log_path = LOGS_FILE if STORE_LOGS_LOCALLY else None
        self._log_file_initialized = bool(local_log_path and os.path.exists(local_log_path))
        self._external_drive_path = self._prepare_external_drive()
        self._external_log_file_initialized = bool(
            EXTERNAL_LOGS_FILE and os.path.exists(EXTERNAL_LOGS_FILE)
        )
        self._export_base_path: Optional[Path] = None
        self._walkthrough_state_file = Path(AUTOSAVE_FILE).with_name("walkthrough_flags.json")
        self._walkthrough_state: dict[str, object] = self._load_walkthrough_state()
        self._user_settings_file = Path(AUTOSAVE_FILE).with_name("user_settings.json")
        self._user_settings: dict[str, object] = self._load_user_settings()
        self._walkthrough_overlay: Optional[tk.Toplevel] = None
        self._walkthrough_steps: list[dict[str, object]] = []
        self._walkthrough_step_index = 0
        self.catalog_status_var = tk.StringVar(
            value="Catálogos de detalle pendientes. Usa 'Cargar catálogos' para habilitar el autopoblado."
        )
        self._catalog_loading = False
        self._catalog_ready = False
        self._catalog_prompted = False
        self._catalog_progress_visible = False
        self._catalog_loading_thread = None
        self._catalog_dependent_widgets = []
        self.catalog_load_button = None
        self.catalog_skip_button = None
        self._validation_panel: Optional[ValidationPanel] = None
        self.catalog_progress = None
        self.detail_catalogs = {}
        self.detail_lookup_by_id = {}
        self.catalog_service = CatalogService(BASE_DIR)
        self.autofill_service = AutofillService(
            self.catalog_service, warning_handler=self._log_autofill_warning
        )
        self.team_lookup = {}
        self.client_lookup = {}
        self.product_lookup = {}
        self.claim_lookup = {}
        self.risk_lookup = {}
        self.norm_lookup = {}
        self._extended_sections_enabled = ENABLE_EXTENDED_ANALYSIS_SECTIONS
        self._reset_extended_sections()
        self._post_edit_validators = []
        self._rich_text_limiters: dict[tk.Text, "FraudCaseApp._RichTextLimiter"] = {}
        self._encabezado_vars: dict[str, tk.StringVar] = {}
        self._operation_vars: dict[str, tk.StringVar] = {}
        self._anexo_vars: dict[str, tk.StringVar] = {}
        self._recommendation_widgets: dict[str, scrolledtext.ScrolledText] = {}
        self._analysis_tab_container: Optional[ttk.Frame] = None
        self._analysis_group: Optional[ttk.LabelFrame] = None
        self._extended_analysis_group: Optional[ttk.LabelFrame] = None
        self._extended_notebook: Optional[ttk.Notebook] = None
        self._extended_sections_toggle_var: Optional[tk.BooleanVar] = None
        self._suppress_post_edit_validation = False
        self._progress_bar = None
        self._progress_label_var: Optional[tk.StringVar] = None
        self._progress_value_var: Optional[tk.DoubleVar] = None
        self._progress_tracking_started = False
        self._progress_animation_job: Optional[str] = None
        self._progress_target_value = 0.0
        self._completion_highlight_active = False
        self._completion_highlight_color: Optional[str] = None
        self.quality_var = tk.IntVar(value=0)
        self._quality_text_var = tk.StringVar(value="Calidad 0%")
        self._quality_style = None
        try:
            self._base_highlight_thickness = int(self.root.cget("highlightthickness") or 0)
        except Exception:
            self._base_highlight_thickness = 0
        try:
            self._base_highlight_color = (
                str(self.root.cget("highlightbackground"))
                or str(self.root.cget("background"))
                or "#000000"
            )
        except Exception:
            self._base_highlight_color = "#000000"
        self._gold_shine_states: dict[int, dict[str, object]] = {}
        self._gold_shine_jobs: dict[int, str] = {}
        self._sound_bytes: Optional[bytes] = None
        self._user_has_edited = False
        self.import_status_var = tk.StringVar(value="Listo para importar datos masivos.")
        self.import_progress = None
        self._import_progress_visible = False
        self._active_import_jobs = 0
        self.theme_toggle_text = tk.StringVar()
        self._update_theme_toggle_label()
        self.sound_enabled_var = tk.BooleanVar(
            value=bool(self._user_settings.get("sound_enabled", True))
        )

        def register_tooltip(widget, text):
            if widget is None or not text:
                return None
            tip = HoverTooltip(widget, text)
            self._hover_tooltips.append(tip)
            return tip

        self.register_tooltip = register_tooltip
        self.root.protocol("WM_DELETE_WINDOW", self._handle_window_close)
        self._schedule_log_flush()
        # Datos en memoria: listas de frames
        self.client_frames = []
        self.team_frames = []
        self.product_frames = []
        self._active_product_frame = None
        self.risk_frames = []
        self.norm_frames = []
        self._badge_window: Optional[tk.Toplevel] = None
        self._badge_destroy_after_id: Optional[str] = None
        self._client_frames_by_id = {}
        self._team_frames_by_id = {}
        self._product_frames_by_id = {}
        self.next_risk_number = 1
        self.summary_tables = {}
        self.inline_summary_trees = {}
        self.summary_config = {}
        self.summary_context_menus = {}
        self.summary_tab = None
        self._summary_refresh_after_id = None
        self._summary_dirty_sections = set()
        self._summary_pending_dataset = None
        self._autosave_job_id = None
        self._autosave_dirty = False
        self._duplicate_checks_armed = False
        self._duplicate_warning_signature: Optional[str] = None
        self._duplicate_warning_cooldown_until: Optional[datetime] = None
        self._last_duplicate_warning_message: Optional[str] = None
        self._rich_text_images = defaultdict(list)
        self._rich_text_image_sources = {}
        self._rich_text_fonts = {}
        self._toast_window: Optional[tk.Toplevel] = None
        self._toast_after_id: Optional[str] = None
        self.clients_detail_wrapper = None
        self.team_detail_wrapper = None
        self.clients_summary_tree = None
        self.product_summary_tree = None
        self.team_summary_tree = None
        self._client_summary_owner = None
        self._product_summary_owner = None
        self._team_summary_owner = None
        self.products_summary_section = None
        self._clients_detail_visible = False
        self._team_detail_visible = False
        self.clients_scrollable = None
        self.team_scrollable = None
        self.products_scrollable = None
        self.risks_scrollable = None
        self.norms_scrollable = None
        self.analysis_scrollable = None
        self.summary_scrollable = None
        self._scrollable_containers: list[object] = []

        # Variables de caso
        self.id_caso_var = tk.StringVar()
        self.tipo_informe_var = tk.StringVar(value=TIPO_INFORME_LIST[0])
        self.cat_caso1_var = tk.StringVar(value=list(TAXONOMIA.keys())[0])
        subcats = list(TAXONOMIA[self.cat_caso1_var.get()].keys())
        self.cat_caso2_var = tk.StringVar(value=subcats[0])
        mods = TAXONOMIA[self.cat_caso1_var.get()][self.cat_caso2_var.get()]
        self.mod_caso_var = tk.StringVar(value=mods[0])
        self.canal_caso_var = tk.StringVar(value=CANAL_LIST[0])
        self.proceso_caso_var = tk.StringVar(value=PROCESO_LIST[0])
        self.fecha_caso_var = tk.StringVar()
        self.fecha_descubrimiento_caso_var = tk.StringVar()
        self.centro_costo_caso_var = tk.StringVar()
        self.investigator_id_var = tk.StringVar()
        self.investigator_nombre_var = tk.StringVar()
        self.investigator_cargo_var = tk.StringVar(value="Investigador Principal")

        # Referencias a cuadros de texto de análisis
        self.antecedentes_text = None
        self.modus_text = None
        self.hallazgos_text = None
        self.descargos_text = None
        self.conclusiones_text = None
        self.recomendaciones_text = None

        # Construir interfaz
        self.build_ui()
        # Cargar autosave si existe
        self.load_autosave()
        self._trim_all_temp_versions()
        self._schedule_walkthrough()
        self.root.after(250, self._prompt_initial_catalog_loading)
        self._startup_complete = True

    class _PostEditValidator:
        def __init__(
            self,
            widget,
            validate_callback,
            field_label,
            logs,
            suppression_flag,
            on_user_edit=None,
            on_success=None,
        ):
            self.widget = widget
            self.validate_callback = validate_callback
            self.field_label = field_label
            self.logs = logs
            self._suppression_flag = suppression_flag
            self._on_user_edit = on_user_edit
            self._on_success = on_success
            self._armed = False
            self._last_error: Optional[str] = None
            widget.bind("<KeyRelease>", self._arm, add="+")
            widget.bind("<<ComboboxSelected>>", self._on_combobox_selected, add="+")
            widget.bind("<FocusOut>", self._on_edit, add="+")

        def _arm(self, *_args):
            self._armed = True

        def _on_combobox_selected(self, *_args):
            self._arm()
            self.widget.after_idle(self._on_edit)

        def _on_edit(self, *_args):
            if not self._armed:
                return
            self._armed = False
            if callable(self._on_user_edit):
                self._on_user_edit()
            error = self.validate_callback()
            if error and error != self._last_error and not self._suppression_flag():
                try:
                    messagebox.showerror("Dato inválido", error)
                except tk.TclError:
                    return
                log_event("validacion", f"{self.field_label}: {error}", self.logs)
            elif not error and callable(self._on_success):
                self._on_success()
            self._last_error = error

    def _register_post_edit_validation(self, widget, validate_callback, field_label):
        validator = self._PostEditValidator(
            widget,
            validate_callback,
            field_label,
            self.logs,
            lambda: getattr(self, "_suppress_messagebox", False) or self._suppress_post_edit_validation,
            on_user_edit=self._mark_user_edited,
            on_success=self._play_feedback_sound,
        )
        self._post_edit_validators.append(validator)
        return validator

    def _register_rich_text_limit(self, widget: tk.Text, label: str) -> None:
        limiter = self._RichTextLimiter(
            widget, lambda: self._enforce_rich_text_limits(widget, label)
        )
        self._rich_text_limiters[widget] = limiter

    def _mark_rich_text_modified(self, widget: tk.Text) -> None:
        limiter = self._rich_text_limiters.get(widget)
        if limiter:
            limiter.arm()

    def _enforce_rich_text_limits(self, widget: tk.Text, section_label: str) -> None:
        raw_text = self._get_text_content(widget)
        cleaned_text = sanitize_rich_text(raw_text, max_chars=None)
        trimmed_text = sanitize_rich_text(cleaned_text, max_chars=RICH_TEXT_MAX_CHARS)
        over_limit = len(cleaned_text) > RICH_TEXT_MAX_CHARS
        if trimmed_text != raw_text:
            self._set_text_content(widget, trimmed_text)
        if over_limit and not getattr(self, "_suppress_messagebox", False):
            message = (
                f"El campo {section_label} supera el máximo de {RICH_TEXT_MAX_CHARS} caracteres."
            )
            try:
                messagebox.showerror("Texto demasiado largo", message)
            except tk.TclError:
                pass
            else:
                log_event("validacion", message, self.logs)
        self._notify_dataset_changed()

    class _RichTextLimiter:
        def __init__(self, widget: tk.Text, on_commit):
            self.widget = widget
            self._on_commit = on_commit
            self._armed = False
            for event_name in ("<KeyRelease>", "<<Paste>>", "<<Cut>>"):
                widget.bind(event_name, self._arm, add="+")
            widget.bind("<FocusOut>", self._handle_edit, add="+")

        def _arm(self, *_args):
            self._armed = True

        def _handle_edit(self, *_args):
            if not self._armed:
                return
            self._armed = False
            self._on_commit()

        def arm(self):
            self._armed = True

    def _prepare_external_drive(self) -> Optional[Path]:
        try:
            return ensure_external_drive_dir()
        except OSError as exc:
            log_event("validacion", f"No se pudo preparar la carpeta externa: {exc}", self.logs)
            return None

    def _get_external_drive_path(self) -> Optional[Path]:
        path = getattr(self, "_external_drive_path", None)
        if path:
            return Path(path)
        self._external_drive_path = self._prepare_external_drive()
        if self._external_drive_path:
            return Path(self._external_drive_path)
        return None

    def _resolve_external_log_target(self) -> Optional[str]:
        if not EXTERNAL_LOGS_FILE:
            return None
        return EXTERNAL_LOGS_FILE if self._get_external_drive_path() else None

    def _has_log_targets(self) -> bool:
        if STORE_LOGS_LOCALLY and LOGS_FILE:
            return True
        return self._resolve_external_log_target() is not None

    def _reset_navigation_metrics(self) -> None:
        self._widget_event_counts = defaultdict(int)
        self._heatmap_counts = defaultdict(int)

    def _ensure_navigation_metrics_initialized(self) -> None:
        if not hasattr(self, "_widget_event_counts") or not hasattr(
            self, "_heatmap_counts"
        ):
            self._reset_navigation_metrics()

    def _bucket_heatmap_coords(self, coords: Optional[tuple]) -> Optional[tuple]:
        if not coords or coords[0] is None or coords[1] is None:
            return None
        bucket = self.HEATMAP_BUCKET_SIZE
        # FIX: Tkinter sometimes passes coords as strings → convert safely
        # Totalmente defensivo contra None, str, o valores inválidos
        if not coords or coords[0] is None or coords[1] is None:
            return None
        try:
            x = float(coords[0])
            y = float(coords[1])
        except (TypeError, ValueError):
            return None

        x_bucket = int(x // bucket * bucket)
        y_bucket = int(y // bucket * bucket)
        return (x_bucket, y_bucket)

    def _accumulate_navigation_metrics(
        self, widget_id: str, coords: Optional[tuple]
    ) -> None:
        self._ensure_navigation_metrics_initialized()
        if widget_id:
            self._widget_event_counts[widget_id] += 1
        zone = self._bucket_heatmap_coords(coords)
        if zone is None:
            return  # Ignorar coordenadas inválidas (muy común en macOS)
        if zone:
            self._heatmap_counts[zone] += 1

    def _emit_navigation_metrics(self) -> None:
        self._ensure_navigation_metrics_initialized()
        if not self._widget_event_counts and not self._heatmap_counts:
            return
        for widget_id, count in self._widget_event_counts.items():
            log_event(
                "navegacion",
                f"Interacciones acumuladas en {widget_id}: {count}",
                self.logs,
                widget_id=widget_id,
                event_subtipo="focus_metrics",
            )
        for (x_bucket, y_bucket), count in self._heatmap_counts.items():
            log_event(
                "navegacion",
                f"Heatmap zona ({x_bucket},{y_bucket}) acumulada: {count}",
                self.logs,
                widget_id="heatmap",
                coords=(x_bucket, y_bucket),
                event_subtipo="click_heatmap",
            )
        self._reset_navigation_metrics()

    def _handle_global_navigation_event(self, event: tk.Event, subtype: str) -> None:
        # FIX 2: focus_displayof() falla en macOS con widgets temporales (popdown, tooltips, etc.)
        # FIX FINAL: focus_get() explota con widgets temporales como .popdown (macOS)
        try:
            focused = self.root.focus_get()
        except (tk.TclError, KeyError, AttributeError):
            # KeyError ocurre específicamente con 'popdown'
            # TclError ocurre si la ventana perdió foco
            # AttributeError por seguridad extra
            return
        if focused is None:
            return
        # FIX 3: event.widget a veces es str (!) en ciertos eventos sintetizados
        widget = event.widget if hasattr(event, "widget") else None
        if not hasattr(widget, "winfo_class"):
            # Puede ser None, str, o widget destruido → ignorar silenciosamente
            return
        if widget is None:
            return
        coords = (
            getattr(event, "x_root", None),
            getattr(event, "y_root", None),
        )
        # FIX 1: x_root/y_root pueden ser strings en macOS (sí, es un bug real de Tk)
        try:
            x_coord = float(coords[0]) if coords[0] is not None else None
            y_coord = float(coords[1]) if coords[1] is not None else None
        except (TypeError, ValueError):
            x_coord = y_coord = None

        safe_coords = (x_coord, y_coord)
        log_event(
            "navegacion",
            f"Evento {subtype} en {widget.winfo_class()}",
            self.logs,
            widget_id=widget.winfo_name(),
            coords=safe_coords,
            event_subtipo=subtype,
        )
        self._accumulate_navigation_metrics(widget.winfo_name(), safe_coords)

    def _register_navigation_bindings(self) -> None:
        if getattr(self, "_navigation_bindings_registered", False):
            return
        bindings = (
            ("<FocusIn>", "focus_in"),
            ("<FocusOut>", "focus_out"),
            ("<Button-1>", "click"),
        )
        for sequence, subtype in bindings:
            self.root.bind_all(
                sequence,
                lambda event, st=subtype: self._handle_global_navigation_event(
                    event, st
                ),
                add="+",
            )
        self._navigation_bindings_registered = True

    def _get_text_content(self, widget: tk.Text) -> str:
        if widget is None:
            return ""
        return widget.get("1.0", "end-1c")

    def _serialize_rich_text_widget(self, widget: tk.Text) -> dict:
        if widget is None:
            return {"text": "", "tags": [], "images": []}

        text = widget.get("1.0", "end-1c")
        allowed_tags = {"bold", "header", "table", "list"}
        tag_ranges = []
        for tag_name in widget.tag_names():
            if tag_name not in allowed_tags:
                continue
            ranges = widget.tag_ranges(tag_name)
            for start, end in zip(ranges[0::2], ranges[1::2]):
                tag_ranges.append({
                    "tag": tag_name,
                    "start": str(start),
                    "end": str(end),
                })

        images = []
        for element_type, image_name, index in widget.dump("1.0", "end", image=True):
            if element_type != "image":
                continue
            images.append({
                "index": str(index),
                "source": self._rich_text_image_sources.get(image_name),
            })

        return {"text": text, "tags": tag_ranges, "images": images}

    def _deserialize_rich_text_payload(self, payload) -> tuple[str, list, list]:
        if isinstance(payload, Mapping):
            text = payload.get("text", "")
            tags = payload.get("tags") or []
            images = payload.get("images") or []
            return str(text), list(tags), list(images)
        return str(payload or ""), [], []

    def _set_rich_text_content(self, widget: tk.Text, payload) -> None:
        if widget is None:
            return
        text, tags, images = self._deserialize_rich_text_payload(payload)
        widget.delete("1.0", "end")
        self._rich_text_images[widget].clear()
        if text:
            widget.insert("1.0", text)

        for tag_data in tags:
            tag_name = tag_data.get("tag")
            start = tag_data.get("start")
            end = tag_data.get("end")
            if not (tag_name and start and end):
                continue
            with suppress(tk.TclError):
                widget.tag_add(tag_name, start, end)

        for image_data in images:
            index = image_data.get("index")
            source = image_data.get("source")
            if not index:
                continue
            photo = self._create_photo_image_from_source(source)
            if photo is None:
                continue
            try:
                widget.image_create(index, image=photo)
            except tk.TclError:
                continue
            self._record_rich_text_image(widget, photo, source, create=False, pad=False)

    def _set_text_content(self, widget: tk.Text, value: str) -> None:
        self._set_rich_text_content(widget, {"text": value or ""})

    def _record_rich_text_image(
        self, widget: tk.Text, photo: tk.PhotoImage, source, create: bool = True, pad: bool = True
    ):
        image_name = str(photo)
        if source:
            self._rich_text_image_sources[image_name] = source
        if create:
            widget.image_create("insert", image=photo)
        self._rich_text_images[widget].append(photo)
        if pad:
            widget.insert("insert", " ")
            widget.focus_set()
        self._mark_rich_text_modified(widget)

    def _create_photo_image_from_source(self, source):
        if not source:
            return None
        try:
            if isinstance(source, Mapping):
                data = source.get("data")
                if data:
                    return tk.PhotoImage(data=data)
            elif isinstance(source, str):
                if source.startswith("data:"):
                    return tk.PhotoImage(data=source.removeprefix("data:"))
                return tk.PhotoImage(file=source)
        except tk.TclError:
            return None
        return None

    def _bind_rich_text_paste_support(self, text_widget: tk.Text):
        text_widget.bind("<<Paste>>", self._handle_rich_text_paste, add="+")
        text_widget.bind(
            "<Control-Shift-v>",
            lambda event, widget=text_widget: self._insert_clipboard_image(widget) or "break",
            add="+",
        )

    def _analysis_text_widgets(self):
        return {
            "antecedentes": getattr(self, "antecedentes_text", None),
            "modus_operandi": getattr(self, "modus_text", None),
            "hallazgos": getattr(self, "hallazgos_text", None),
            "descargos": getattr(self, "descargos_text", None),
            "conclusiones": getattr(self, "conclusiones_text", None),
            "recomendaciones": getattr(self, "recomendaciones_text", None),
        }

    def _normalize_analysis_texts(self, analysis_payload):
        def _build_entry(value):
            text, tags, images = self._deserialize_rich_text_payload(value)
            sanitized = sanitize_rich_text(text, RICH_TEXT_MAX_CHARS)
            entry = {"text": sanitized, "tags": tags}
            if images:
                entry["images"] = images
            return entry

        sections = [
            "antecedentes",
            "modus_operandi",
            "hallazgos",
            "descargos",
            "conclusiones",
            "recomendaciones",
        ]
        payload = analysis_payload or {}
        normalized = {name: _build_entry(payload.get(name)) for name in sections}
        for name, value in payload.items():
            if name in normalized:
                continue
            normalized[name] = _build_entry(value)
        return normalized

    def _get_exports_folder(self) -> Optional[Path]:
        base_path = getattr(self, "_export_base_path", None) or EXPORTS_DIR
        target = Path(base_path)
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            message = f"No se pudo preparar la carpeta de exportación {target}: {exc}"
            log_event("validacion", message, self.logs)
            if not getattr(self, '_suppress_messagebox', False):
                messagebox.showerror("Error al guardar", message)
            return None
        return target

    def import_combined(self, filename=None):
        """Importa datos combinados de productos, clientes y colaboradores."""

        log_event("navegacion", "Usuario pulsó importar datos combinados", self.logs)
        filename = filename or self._select_csv_file("combinado", "Seleccionar CSV combinado")
        if not filename:
            return
        if not self._validate_import_headers(filename, "combinado"):
            return
        log_event("navegacion", "Inició importación de datos combinados", self.logs)
        def worker():
            prepared_rows = []
            for index, row in enumerate(iter_massive_csv_rows(filename), start=1):
                raw_row = self._sanitize_import_row(row, row_number=index)
                client_row, client_found = self._hydrate_row_from_details(raw_row, 'id_cliente', CLIENT_ID_ALIASES)
                team_row, team_found = self._hydrate_row_from_details(raw_row, 'id_colaborador', TEAM_ID_ALIASES)
                product_row, product_found = self._hydrate_row_from_details(raw_row, 'id_producto', PRODUCT_ID_ALIASES)
                collaborator_id = (team_row.get('id_colaborador') or '').strip()
                involvement_pairs = parse_involvement_entries(raw_row.get('involucramiento', ''))
                if not involvement_pairs and collaborator_id and raw_row.get('monto_asignado'):
                    involvement_pairs = [(collaborator_id, (raw_row.get('monto_asignado') or '').strip())]
                prepared_rows.append(
                    {
                        'raw_row': raw_row,
                        'client_row': client_row,
                        'client_found': client_found,
                        'team_row': team_row,
                        'team_found': team_found,
                        'product_row': product_row,
                        'product_found': product_found,
                        'involvement_pairs': involvement_pairs,
                    }
                )
            return prepared_rows

        self._start_background_import(
            "datos combinados",
            getattr(self, 'import_combined_button', None),
            worker,
            self._apply_combined_import_payload,
            "No se pudo importar el CSV combinado",
        )

    def import_risks(self, filename=None):
        """Importa riesgos desde un archivo CSV."""

        log_event("navegacion", "Usuario pulsó importar riesgos", self.logs)
        filename = filename or self._select_csv_file("riesgos", "Seleccionar CSV de riesgos")
        if not filename:
            return
        if not self._validate_import_headers(filename, "riesgos"):
            return
        log_event("navegacion", "Inició importación de riesgos", self.logs)
        def worker():
            payload = []
            for index, row in enumerate(iter_massive_csv_rows(filename), start=1):
                sanitized_row = self._sanitize_import_row(row, row_number=index)
                hydrated, _ = self._hydrate_row_from_details(sanitized_row, 'id_riesgo', RISK_ID_ALIASES)
                payload.append(hydrated)
            return payload

        self._start_background_import(
            "riesgos",
            getattr(self, 'import_risks_button', None),
            worker,
            self._apply_risk_import_payload,
            "No se pudo importar riesgos",
        )

    def import_norms(self, filename=None):
        """Importa normas transgredidas desde un archivo CSV."""

        log_event("navegacion", "Usuario pulsó importar normas", self.logs)
        filename = filename or self._select_csv_file("normas", "Seleccionar CSV de normas")
        if not filename:
            return
        if not self._validate_import_headers(filename, "normas"):
            return
        log_event("navegacion", "Inició importación de normas", self.logs)
        def worker():
            payload = []
            for index, row in enumerate(iter_massive_csv_rows(filename), start=1):
                sanitized_row = self._sanitize_import_row(row, row_number=index)
                hydrated, _ = self._hydrate_row_from_details(sanitized_row, 'id_norma', NORM_ID_ALIASES)
                payload.append(hydrated)
            return payload

        self._start_background_import(
            "normas",
            getattr(self, 'import_norms_button', None),
            worker,
            self._apply_norm_import_payload,
            "No se pudo importar normas",
        )

    def import_claims(self, filename=None):
        """Importa reclamos desde un archivo CSV."""

        log_event("navegacion", "Usuario pulsó importar reclamos", self.logs)
        filename = filename or self._select_csv_file("reclamos", "Seleccionar CSV de reclamos")
        if not filename:
            return
        if not self._validate_import_headers(filename, "reclamos"):
            return
        log_event("navegacion", "Inició importación de reclamos", self.logs)
        def worker():
            payload = []
            for index, row in enumerate(iter_massive_csv_rows(filename), start=1):
                sanitized_row = self._sanitize_import_row(row, row_number=index)
                hydrated, found = self._hydrate_row_from_details(sanitized_row, 'id_producto', PRODUCT_ID_ALIASES)
                payload.append({'row': hydrated, 'found': found})
            return payload

        self._start_background_import(
            "reclamos",
            getattr(self, 'import_claims_button', None),
            worker,
            self._apply_claim_import_payload,
            "No se pudo importar reclamos",
        )

    # ---------------------------------------------------------------------
    # Construcción de la interfaz

    def build_ui(self):
        """Construye la interfaz del usuario en diferentes pestañas."""
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self._scroll_binder.bind_to_root()

        main_container = ttk.Frame(self.root)
        main_container.grid(row=0, column=0, sticky="nsew")
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(0, weight=1)

        progress_container = ttk.Frame(main_container)
        progress_container.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))
        progress_container.columnconfigure(1, weight=1)
        ttk.Label(progress_container, text="Avance del caso").grid(
            row=0, column=0, padx=(0, 8), pady=(5, 0), sticky="w"
        )
        self._progress_label_var = tk.StringVar(value="0 %")
        self._progress_value_var = tk.DoubleVar(value=0.0)
        self._progress_bar = ttk.Progressbar(
            progress_container,
            variable=self._progress_value_var,
            maximum=100,
            mode="determinate",
        )
        self._progress_bar.grid(row=0, column=1, sticky="ew", pady=(5, 0))
        ttk.Label(progress_container, textvariable=self._progress_label_var).grid(
            row=0, column=2, padx=(8, 0), pady=(5, 0), sticky="e"
        )
        progress_container.columnconfigure(3, weight=0)
        self._quality_badge = ttk.Label(
            progress_container,
            textvariable=self._quality_text_var,
            style="Badge.TLabel",
        )
        self._quality_badge.grid(row=0, column=3, padx=(8, 0), pady=(5, 0), sticky="e")
        self._apply_quality_style(self.quality_var.get())

        self.notebook = ttk.Notebook(main_container)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self.notebook.bind("<<NotebookTabChanged>>", self._handle_notebook_tab_change)
        self._register_navigation_bindings()

        self._validation_panel = ValidationPanel(
            main_container, on_focus_request=self._focus_widget_from_validation_panel
        )
        FieldValidator.set_status_consumer(self._publish_field_validation)
        main_container.grid_columnconfigure(
            1, weight=0, minsize=ValidationPanel.COLLAPSED_WIDTH
        )
        self._validation_panel.grid(row=0, column=1, sticky="ns")

        # --- Pestaña principal: caso y participantes ---
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Caso y participantes")
        self.build_case_and_participants_tab(self.main_tab)

        # --- Pestaña Riesgos ---
        risk_tab = ttk.Frame(self.notebook)
        self.notebook.add(risk_tab, text="Riesgos")
        self.build_risk_tab(risk_tab)

        # --- Pestaña Normas ---
        norm_tab = ttk.Frame(self.notebook)
        self.notebook.add(norm_tab, text="Normas")
        self.build_norm_tab(norm_tab)

        # --- Pestaña Análisis ---
        analysis_tab = ttk.Frame(self.notebook)
        self.notebook.add(analysis_tab, text="Análisis y narrativas")
        self.build_analysis_tab(analysis_tab)

        # --- Pestaña Acciones ---
        actions_tab = ttk.Frame(self.notebook)
        self.notebook.add(actions_tab, text="Acciones")
        self.build_actions_tab(actions_tab)

        # --- Pestaña Resumen ---
        summary_tab = ttk.Frame(self.notebook)
        self.notebook.add(summary_tab, text="Resumen")
        self.build_summary_tab(summary_tab)
        self._current_tab_id = self.notebook.select()
        self._scroll_binder.activate_tab(self._current_tab_id)

    def _focus_widget_from_validation_panel(self, widget, origin: str | None = None) -> None:
        target_widget = self._resolve_focus_target(widget, origin)
        if not target_widget:
            return

        tab_to_select = self._locate_tab_for_widget(target_widget)
        if tab_to_select:
            try:
                self.notebook.select(tab_to_select)
            except Exception:
                pass

        try:
            target_widget.focus_set()
            target_widget.event_generate("<<ValidationFocusRequest>>")
        except Exception:
            return

    @staticmethod
    def _widget_is_focusable(widget) -> bool:
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except Exception:
            return False

    def _resolve_focus_target(self, widget, origin: str | None = None):
        if self._widget_is_focusable(widget):
            return widget
        revived = self._revive_focus_widget(widget, origin)
        if self._widget_is_focusable(revived):
            return revived
        return None

    def _iter_widget_ancestors(self, widget):
        current = widget
        while current is not None:
            yield current
            try:
                parent_name = current.winfo_parent()
            except Exception:
                break
            if not parent_name:
                break
            try:
                current = current.nametowidget(parent_name)
            except Exception:
                break

    def _locate_tab_for_widget(self, widget) -> str | None:
        notebook = getattr(self, "notebook", None)
        if not notebook or not self._widget_is_focusable(widget):
            return None
        try:
            tabs = notebook.tabs()
        except Exception:
            return None
        for tab_id in tabs:
            try:
                tab_widget = notebook.nametowidget(tab_id)
            except Exception:
                continue
            current = widget
            while current is not None:
                if current is tab_widget:
                    return tab_id
                try:
                    parent_name = current.winfo_parent()
                except Exception:
                    current = None
                    break
                if not parent_name:
                    current = None
                    break
                try:
                    current = current.nametowidget(parent_name)
                except Exception:
                    current = None
                    break
        return None

    def _ensure_walkthrough_anchor_visible(
        self, anchor: tk.Widget
    ) -> tuple[int, int, int, int] | None:
        tab_id = self._locate_tab_for_widget(anchor)
        if tab_id:
            try:
                self.notebook.select(tab_id)
                if hasattr(self, "_scroll_binder"):
                    self._scroll_binder.activate_tab(tab_id)
            except Exception:
                pass
        self._safe_update_idletasks()
        scrolled = self._scroll_widget_into_view(anchor)
        if not scrolled:
            self._scroll_to_widget(anchor)
        self._safe_update_idletasks()
        return self._get_widget_geometry(anchor)

    def _scroll_widget_into_view(self, widget: tk.Widget) -> bool:
        if widget is None:
            return False
        if self._scroll_with_see(widget):
            return True
        canvas, inner = self._find_scrollable_canvas(widget)
        if canvas is None or inner is None:
            return False
        self._scroll_with_canvas(canvas, inner, widget)
        return True

    def _scroll_to_widget(self, widget: tk.Widget) -> bool:
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
            inner_frames = [
                child for child in canvas.winfo_children() if isinstance(child, (tk.Frame, ttk.Frame))
            ]
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

    def _scroll_with_see(self, widget: tk.Widget) -> bool:
        for ancestor in self._iter_widget_ancestors(widget):
            see_fn = getattr(ancestor, "see", None)
            if callable(see_fn):
                try:
                    see_fn(widget)
                    return True
                except Exception:
                    continue
        return False

    def _find_scrollable_canvas(self, widget: tk.Widget) -> tuple[tk.Canvas | None, ttk.Frame | None]:
        for ancestor in self._iter_widget_ancestors(widget):
            canvas = getattr(ancestor, "_scroll_canvas", None)
            inner = getattr(ancestor, "_scroll_inner", None)
            if canvas is not None and inner is not None:
                return canvas, inner
        return None, None

    def _compute_offset_in_ancestor(self, widget: tk.Widget, ancestor: tk.Widget) -> int | None:
        offset = 0
        current = widget
        while current is not None and current is not ancestor:
            try:
                offset += current.winfo_y()
            except Exception:
                return None
            try:
                parent_name = current.winfo_parent()
            except Exception:
                return None
            if not parent_name:
                return None
            try:
                current = current.nametowidget(parent_name)
            except Exception:
                return None
        return offset if current is ancestor else None

    def _scroll_with_canvas(self, canvas: tk.Canvas, inner: ttk.Frame, widget: tk.Widget) -> None:
        try:
            first, last = canvas.yview()
        except Exception:
            first = 0.0
            last = 1.0
        self._safe_update_idletasks()
        inner_height = inner.winfo_height()
        view_height = canvas.winfo_height()
        offset = self._compute_offset_in_ancestor(widget, inner)
        widget_height = widget.winfo_height()
        if (
            offset is None
            or inner_height <= 0
            or view_height <= 0
            or widget_height <= 0
        ):
            return
        visible_top = first * inner_height
        visible_bottom = last * inner_height
        widget_top = offset
        widget_bottom = offset + widget_height
        if visible_top <= widget_top and widget_bottom <= visible_bottom:
            return
        center_target = max(0.0, widget_top + (widget_height / 2) - (view_height / 2))
        max_scroll = max(inner_height - view_height, 1)
        fraction = min(max(center_target / max_scroll, 0.0), 1.0)
        try:
            canvas.yview_moveto(fraction)
        except Exception:
            return
        self._safe_update_idletasks()

    def _revive_focus_widget(self, widget, origin: str | None = None):
        origin_hint = origin or getattr(widget, "_validation_origin", None) or ""
        product_match = re.search(r"Producto\s+(\d+)", origin_hint, flags=re.IGNORECASE)
        if product_match:
            target_index = int(product_match.group(1)) - 1
            product_frame = self._ensure_product_frame_for_focus(target_index)
            if not product_frame:
                return None
            claim_match = re.search(r"Reclamo\s+(\d+)", origin_hint, flags=re.IGNORECASE)
            if claim_match:
                claim_index = int(claim_match.group(1)) - 1
                claim_row = self._ensure_claim_row_for_focus(product_frame, claim_index)
                if claim_row:
                    return self._map_claim_origin_to_widget(claim_row, origin_hint) or getattr(
                        claim_row, "id_entry", None
                    )
                return None
            return self._map_product_origin_to_widget(product_frame, origin_hint) or getattr(
                product_frame, "id_entry", None
            )
        risk_match = re.search(r"Riesgo\s+(\d+)", origin_hint, flags=re.IGNORECASE)
        if risk_match:
            risk_index = int(risk_match.group(1)) - 1
            risk_frame = self._ensure_risk_frame_for_focus(risk_index)
            if risk_frame:
                return getattr(risk_frame, "frame", None)
            return None
        norm_match = re.search(r"Norma\s+(\d+)", origin_hint, flags=re.IGNORECASE)
        if norm_match:
            norm_index = int(norm_match.group(1)) - 1
            norm_frame = self._ensure_norm_frame_for_focus(norm_index)
            if norm_frame:
                return getattr(norm_frame, "frame", None)
            return None
        client_match = re.search(r"Cliente\s+(\d+)", origin_hint, flags=re.IGNORECASE)
        if client_match:
            client_index = int(client_match.group(1)) - 1
            client_frame = self._ensure_client_frame_for_focus(client_index)
            if client_frame:
                return getattr(client_frame, "frame", None)
            return None
        team_match = re.search(r"Colaborador\s+(\d+)", origin_hint, flags=re.IGNORECASE)
        if team_match:
            team_index = int(team_match.group(1)) - 1
            team_frame = self._ensure_team_frame_for_focus(team_index)
            if team_frame:
                return getattr(team_frame, "frame", None)
            return None
        return None

    def _ensure_product_frame_for_focus(self, index: int):
        if index < 0:
            return None
        while len(self.product_frames) <= index:
            self.add_product(initialize_rows=False)
        frame = self.product_frames[index]
        self._expand_product_section(frame)
        return frame

    def _ensure_risk_frame_for_focus(self, index: int):
        if index < 0:
            return None
        while len(self.risk_frames) <= index:
            self.add_risk()
        frame = self.risk_frames[index]
        clear = getattr(frame, "clear_values", None)
        if callable(clear):
            clear()
        return frame

    def _ensure_norm_frame_for_focus(self, index: int):
        if index < 0:
            return None
        while len(self.norm_frames) <= index:
            self.add_norm()
        frame = self.norm_frames[index]
        clear = getattr(frame, "clear_values", None)
        if callable(clear):
            clear()
        return frame

    def _ensure_client_frame_for_focus(self, index: int):
        if index < 0:
            return None
        while len(self.client_frames) <= index:
            self.add_client()
        frame = self.client_frames[index]
        clear = getattr(frame, "clear_values", None)
        if callable(clear):
            clear()
        return frame

    def _ensure_team_frame_for_focus(self, index: int):
        if index < 0:
            return None
        while len(self.team_frames) <= index:
            self.add_team_member()
        frame = self.team_frames[index]
        clear = getattr(frame, "clear_values", None)
        if callable(clear):
            clear()
        return frame

    def _expand_product_section(self, frame) -> None:
        section = getattr(frame, "section", None)
        expand = getattr(section, "expand", None)
        if callable(expand):
            try:
                expand()
            except Exception:
                pass

    def _ensure_claim_row_for_focus(self, product_frame, claim_index: int):
        if product_frame is None:
            return None
        claims = getattr(product_frame, "claims", None)
        if claims is None:
            return None
        if not claims:
            product_frame.add_claim()
        while len(product_frame.claims) <= claim_index:
            product_frame.add_claim()
        safe_index = min(max(claim_index, 0), len(product_frame.claims) - 1)
        claim_row = product_frame.claims[safe_index]
        frame_exists = getattr(getattr(claim_row, "frame", None), "winfo_exists", lambda: False)()
        if not frame_exists:
            replacement = product_frame.add_claim()
            claim_row = replacement
        clear = getattr(claim_row, "clear_values", None)
        if callable(clear):
            clear()
        return claim_row

    def _map_product_origin_to_widget(self, product_frame, origin: str):
        origin_lower = (origin or "").lower()
        candidates = [
            ("cliente", getattr(product_frame, "client_cb", None)),
            ("categoría 1", getattr(product_frame, "cat1_cb", None)),
            ("categoria 1", getattr(product_frame, "cat1_cb", None)),
            ("categoría 2", getattr(product_frame, "cat2_cb", None)),
            ("categoria 2", getattr(product_frame, "cat2_cb", None)),
            ("modalidad", getattr(product_frame, "mod_cb", None)),
            ("tipo de producto", getattr(product_frame, "tipo_prod_cb", None)),
            ("ocurrencia", getattr(product_frame, "focc_entry", None)),
            ("descubrimiento", getattr(product_frame, "fdesc_entry", None)),
            ("investigado", getattr(product_frame, "inv_entry", None)),
            ("pérdida", getattr(product_frame, "perdida_entry", None)),
            ("falla", getattr(product_frame, "falla_entry", None)),
            ("contingencia", getattr(product_frame, "cont_entry", None)),
            ("recuperado", getattr(product_frame, "rec_entry", None)),
            ("pago", getattr(product_frame, "pago_entry", None)),
        ]
        for token, candidate in candidates:
            if token in origin_lower and candidate is not None:
                return candidate
        fallback = getattr(product_frame, "id_entry", None)
        return fallback

    def _map_claim_origin_to_widget(self, claim_row, origin: str):
        origin_lower = (origin or "").lower()
        candidates = [
            ("código", getattr(claim_row, "code_entry", None)),
            ("nombre", getattr(claim_row, "name_entry", None)),
            ("id", getattr(claim_row, "id_entry", None)),
        ]
        for token, candidate in candidates:
            if token in origin_lower and candidate is not None:
                return candidate
        fallback = None
        first_missing = getattr(claim_row, "first_missing_widget", None)
        if callable(first_missing):
            fallback = first_missing()
        return fallback or getattr(claim_row, "id_entry", None)

    def _publish_field_validation(
        self, field_name: str, message: Optional[str], widget
    ) -> None:
        if not self._validation_panel:
            return
        target_widget = widget if hasattr(widget, "focus_set") else None
        if target_widget is not None:
            try:
                setattr(target_widget, "_validation_origin", field_name)
            except Exception:
                pass
        target_id = id(target_widget) if target_widget is not None else field_name
        key = f"field:{field_name}:{target_id}"
        severity = "error" if message else "ok"
        self._validation_panel.update_entry(
            key,
            message,
            severity=severity,
            origin=field_name,
            widget=target_widget,
        )
        self._validation_feedback_initialized = True
        self._update_completion_progress()
        self.recalculate_quality()

    def _build_validation_focus_map(self) -> dict[str, tk.Widget]:
        focus_map: dict[str, tk.Widget] = {}
        case_inputs = getattr(self, "_case_inputs", {}) or {}
        focus_map.update(
            {
                "número de caso": case_inputs.get("id_entry"),
                "tipo de informe": case_inputs.get("tipo_cb"),
                "categoría 1": case_inputs.get("cat1_cb"),
                "categoría 2": case_inputs.get("case_cat2_cb"),
                "modalidad": case_inputs.get("case_mod_cb"),
                "canal": case_inputs.get("canal_cb"),
                "proceso": case_inputs.get("proc_cb"),
                "investigador": case_inputs.get("investigator_entry"),
                "ocurrencia": case_inputs.get("fecha_case_entry"),
                "descubrimiento": case_inputs.get("fecha_desc_entry"),
                "centro de costos": case_inputs.get("centro_costo_entry"),
            }
        )
        return {hint: widget for hint, widget in focus_map.items() if widget}

    def _publish_validation_summary(self, errors: list[str], warnings: list[str]) -> None:
        focus_map = self._build_validation_focus_map()
        if self._validation_panel:
            self._validation_panel.show_batch_results(
                errors, warnings, focus_map
            )
        if not errors and not warnings:
            self._shine_validated_fields(focus_map.values())
            self._show_success_toast(self._validation_panel)

    def _activate_progress_tracking(self) -> None:
        """Habilita el cálculo de avance tras la primera interacción del usuario."""

        if not hasattr(self, "_progress_tracking_started"):
            self._progress_tracking_started = False
        if self._progress_tracking_started:
            return
        self._progress_tracking_started = True
        self._update_completion_progress(force=True)

    def _update_completion_progress(self, *, force: bool = False) -> None:
        bar = getattr(self, "_progress_bar", None)
        value_var = getattr(self, "_progress_value_var", None)
        label_var = getattr(self, "_progress_label_var", None)
        if not bar or not value_var or not label_var:
            return
        if not hasattr(self, "_progress_tracking_started"):
            self._progress_tracking_started = False
        if not (self._progress_tracking_started or force):
            value_var.set(0.0)
            label_var.set("0 %")
            self._apply_completion_highlight(0.0)
            return

        completion = self._compute_completion_percentage()
        self._apply_completion_highlight(completion)
        self._start_progress_animation(completion)

    def _compute_completion_percentage(self) -> float:
        counts = {
            "clientes": len(self.client_frames),
            "colaboradores": len(self.team_frames),
            "productos": len(self.product_frames),
            "riesgos": len(self.risk_frames),
            "normas": len(self.norm_frames),
        }
        count_score = (
            sum(1 for count in counts.values() if count > 0) / len(counts)
            if counts
            else 0.0
        )

        total_validators = len(self.validators)
        successful_validators = sum(
            1 for validator in self.validators if getattr(validator, "last_error", None) in {None, ""}
        )
        validation_score = (
            successful_validators / total_validators if total_validators else 0.0
        )

        blended_score = max(0.0, min(1.0, (count_score + validation_score) / 2))
        return blended_score * 100

    def _start_progress_animation(self, target: float) -> None:
        target = max(0.0, min(100.0, target))
        self._progress_target_value = target
        job = getattr(self, "_progress_animation_job", None)
        if job:
            with suppress(tk.TclError):
                self.root.after_cancel(job)
            self._progress_animation_job = None
        self._step_progress_animation()

    def _step_progress_animation(self) -> None:
        bar = getattr(self, "_progress_bar", None)
        value_var = getattr(self, "_progress_value_var", None)
        label_var = getattr(self, "_progress_label_var", None)
        if not bar or not value_var or not label_var:
            return
        current = value_var.get()
        target = getattr(self, "_progress_target_value", 0.0)
        delta = target - current
        if abs(delta) < 0.5:
            new_value = target
        else:
            step = max(1.0, abs(delta) * 0.15)
            new_value = current + step if delta > 0 else current - step
        value_var.set(max(0.0, min(100.0, new_value)))
        label_var.set(f"{value_var.get():.0f} %")
        if abs(target - value_var.get()) < 0.5:
            value_var.set(target)
            label_var.set(f"{target:.0f} %")
            self._progress_animation_job = None
            return
        try:
            self._progress_animation_job = self.root.after(60, self._step_progress_animation)
        except tk.TclError:
            self._progress_animation_job = None

    def _color_to_rgb(self, color: str) -> tuple[int, int, int]:
        try:
            r, g, b = self.root.winfo_rgb(color)
            return (r // 256, g // 256, b // 256)
        except Exception:
            return (255, 255, 255)

    def _blend_color(self, color: str, background: str, alpha: float) -> str:
        fg_r, fg_g, fg_b = self._color_to_rgb(color)
        bg_r, bg_g, bg_b = self._color_to_rgb(background)
        clamped_alpha = max(0.0, min(1.0, alpha))
        blended = (
            round(fg_r * clamped_alpha + bg_r * (1 - clamped_alpha)),
            round(fg_g * clamped_alpha + bg_g * (1 - clamped_alpha)),
            round(fg_b * clamped_alpha + bg_b * (1 - clamped_alpha)),
        )
        return "#{:02x}{:02x}{:02x}".format(*blended)

    def _color_with_optional_alpha(self, color: str, background: str, alpha: float) -> str:
        normalized = (color or "").strip() or "#2ecc71"
        if normalized.startswith("#"):
            hex_value = normalized[1:]
            if len(hex_value) == 3:
                hex_value = "".join(ch * 2 for ch in hex_value)
                normalized = f"#{hex_value}"
            if len(hex_value) == 6:
                try:
                    alpha_byte = int(max(0, min(255, round(alpha * 255))))
                    candidate = f"#{hex_value}{alpha_byte:02x}"
                    self.root.winfo_rgb(candidate)
                    return candidate
                except tk.TclError:
                    pass
        return self._blend_color(normalized, background, max(0.0, min(1.0, alpha)))

    def _apply_completion_highlight(self, completion: float) -> None:
        root = getattr(self, "root", None)
        if root is None:
            return

        palette = ThemeManager.current()
        background = palette.get("background", root.cget("background"))
        accent = palette.get("accent", "#d4af37")
        gold_base = "#d4af37"
        blended_gold = self._blend_color(gold_base, background, 0.78)
        accent_hint = self._blend_color(accent, background, 0.45)
        highlight_color = self._blend_color(blended_gold, accent_hint, 0.65)

        active = completion >= 90.0
        thickness = max(self._base_highlight_thickness, 4) if active else self._base_highlight_thickness
        target_color = highlight_color if active else self._base_highlight_color

        if (
            active == self._completion_highlight_active
            and target_color == self._completion_highlight_color
        ):
            return

        try:
            root.configure(
                highlightthickness=thickness,
                highlightbackground=target_color,
                highlightcolor=target_color,
            )
        except tk.TclError:
            return

        self._completion_highlight_active = active
        self._completion_highlight_color = target_color

    def _iter_all_validators(self):
        for validator in getattr(self, "validators", []) or []:
            yield validator
        for collection_name in (
            "client_frames",
            "team_frames",
            "product_frames",
            "risk_frames",
            "norm_frames",
        ):
            for frame in getattr(self, collection_name, []) or []:
                for validator in getattr(frame, "validators", []) or []:
                    yield validator

    @staticmethod
    def _validators_successful(validators) -> bool:
        items = list(validators)
        if not items:
            return False
        return all(getattr(validator, "last_error", None) in {None, ""} for validator in items)

    def _apply_quality_style(self, score: int) -> None:
        if self._quality_style is None:
            try:
                self._quality_style = ttk.Style(master=self.root)
            except Exception:
                self._quality_style = None
        style = self._quality_style
        if not style or not hasattr(style, "configure"):
            return
        palette = ThemeManager.current()
        if score < 50:
            background = "#dc2626"
            foreground = palette.get("select_foreground", "#ffffff")
        elif score < 80:
            background = "#f97316"
            foreground = palette.get("foreground", "#111827")
        else:
            background = "#16a34a"
            foreground = palette.get("select_foreground", "#ffffff")
        style.configure(
            "Badge.TLabel",
            background=background,
            foreground=foreground,
            padding=(8, 2),
            borderwidth=1,
            relief="solid",
            font=("TkDefaultFont", 9, "bold"),
        )

    def recalculate_quality(self, data=None) -> None:
        if not getattr(self, "_quality_badge", None):
            return
        if not (
            getattr(self, "_user_has_edited", False)
            or getattr(self, "_validation_feedback_initialized", False)
        ):
            return

        dataset = data if isinstance(data, Mapping) else None
        validators = list(self._iter_all_validators())

        def _filter_validators(predicate):
            return [v for v in validators if predicate(getattr(v, "field_name", ""))]

        case_id_valid = self._validators_successful(
            _filter_validators(lambda name: name.lower().startswith("caso - id"))
        )
        case_dates_valid = self._validators_successful(
            _filter_validators(lambda name: name.lower().startswith("caso - fecha"))
        )
        product_date_validators = _filter_validators(
            lambda name: name.lower().startswith("producto") and "fecha" in name.lower()
        )
        product_dates_valid = self._validators_successful(product_date_validators)

        amount_validators = _filter_validators(
            lambda name: name.lower().startswith("producto")
            and ("monto" in name.lower() or "consistencia de montos" in name.lower())
        )
        amounts_consistent = (
            self._validators_successful(amount_validators)
            if amount_validators
            else False
        )

        client_rows = dataset.get("clientes") if dataset else None
        product_rows = dataset.get("productos") if dataset else None
        risk_rows = dataset.get("riesgos") if dataset else None
        norm_rows = dataset.get("normas") if dataset else None

        counts = {
            "clientes": len(client_rows) if client_rows is not None else len(self.client_frames),
            "productos": len(product_rows) if product_rows is not None else len(self.product_frames),
            "riesgos": len(risk_rows) if risk_rows is not None else len(self.risk_frames),
            "normas": len(norm_rows) if norm_rows is not None else len(self.norm_frames),
        }

        checks = [
            case_id_valid,
            counts["clientes"] > 0,
            counts["productos"] > 0,
            counts["riesgos"] > 0,
            counts["normas"] > 0,
            case_dates_valid and (product_dates_valid or counts["productos"] == 0),
        ]

        if counts["productos"] > 0:
            checks.append(amounts_consistent)

        successful = sum(1 for check in checks if check)
        total = len(checks) if checks else 1
        score = round(successful / total * 100)

        self.quality_var.set(score)
        self._quality_text_var.set(f"Calidad {score}%")
        self._apply_quality_style(score)

    def _safe_destroy_checkmark_overlay(self) -> None:
        overlay = getattr(self, "_checkmark_overlay", None)
        if overlay is None:
            return
        try:
            overlay.destroy()
        except tk.TclError:
            pass
        self._checkmark_overlay = None

    def show_big_checkmark(self, duration_ms: int = 1500) -> None:
        if not getattr(self, "root", None):
            return
        self._safe_destroy_checkmark_overlay()
        theme = ThemeManager.current()
        background = theme.get("background", self.root.cget("background"))
        accent = theme.get("accent", "#2ecc71")
        label = tk.Label(
            self.root,
            text="✓",
            font=(FONT_BASE[0], max(int(FONT_BASE[1] * 6), 96), "bold"),
            foreground=self._color_with_optional_alpha(accent, background, 0.8),
            background=self._color_with_optional_alpha(background, background, 0.35),
            borderwidth=0,
            highlightthickness=0,
            takefocus=0,
        )
        label.place(relx=0.5, rely=0.5, anchor="center")
        label.lift()
        self._checkmark_overlay = label

        steps = 6
        interval = max(40, duration_ms // steps)

        def _fade(step: int = 0):
            if not label.winfo_exists():
                self._checkmark_overlay = None
                return
            if step >= steps:
                self._safe_destroy_checkmark_overlay()
                return
            fade_ratio = max(0.0, 1 - step / float(steps))
            label.configure(
                foreground=self._color_with_optional_alpha(
                    accent, background, 0.3 + 0.5 * fade_ratio
                ),
                background=self._color_with_optional_alpha(
                    background, background, 0.2 * fade_ratio
                ),
            )
            try:
                label.after(interval, lambda: _fade(step + 1))
            except tk.TclError:
                self._checkmark_overlay = None

        _fade(0)

    def clipboard_get(self):
        """Proxy para ``Tk.clipboard_get`` que simplifica las pruebas unitarias."""

        return self.root.clipboard_get()

    def build_case_and_participants_tab(self, parent):
        """Agrupa en una sola vista los datos del caso, clientes, productos y equipo.

        Esta función encapsula la experiencia solicitada por los analistas:
        evita tener que cambiar de pestaña para capturar la información básica
        del expediente y coloca, en orden lógico, las secciones de caso,
        clientes, productos y colaboradores.  Para lograrlo, se crean
        ``LabelFrame`` consecutivos que actúan como contenedores y se reutiliza
        la lógica existente de ``build_case_tab``/``build_clients_tab``/etc.

        Args:
            parent (tk.Widget): Contenedor donde se inyectarán las secciones.

        Ejemplo::

            # Durante la construcción de la UI
            self.build_case_and_participants_tab(self.main_tab)
        """

        ensure_grid_support(parent)
        if hasattr(parent, "rowconfigure"):
            try:
                parent.rowconfigure(0, weight=1)
            except Exception:
                pass
        if hasattr(parent, "columnconfigure"):
            try:
                parent.columnconfigure(0, weight=1)
            except Exception:
                pass

        scroll_container, inner_frame = create_scrollable_container(
            parent, scroll_binder=self._scroll_binder, tab_id=parent
        )
        grid_and_configure(
            scroll_container,
            parent,
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
        )
        self.summary_scrollable = scroll_container
        self._register_scrollable(scroll_container)

        self._main_scrollable_frame = inner_frame

        ensure_grid_support(self._main_scrollable_frame)
        if hasattr(self._main_scrollable_frame, "columnconfigure"):
            try:
                self._main_scrollable_frame.columnconfigure(0, weight=1)
            except Exception:
                pass

        case_section = ttk.LabelFrame(
            self._main_scrollable_frame, text="1. Datos generales del caso"
        )
        grid_and_configure(
            case_section,
            self._main_scrollable_frame,
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
            row_weight=0,
        )
        self.build_case_tab(case_section)

        clients_section = ttk.LabelFrame(
            self._main_scrollable_frame, text="2. Clientes implicados"
        )
        grid_and_configure(
            clients_section,
            self._main_scrollable_frame,
            row=1,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
        )
        self.build_clients_tab(clients_section)

        products_section = ttk.LabelFrame(
            self._main_scrollable_frame, text="3. Productos investigados"
        )
        grid_and_configure(
            products_section,
            self._main_scrollable_frame,
            row=2,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
        )
        self.build_products_tab(products_section)

        team_section = ttk.LabelFrame(
            self._main_scrollable_frame, text="4. Colaboradores involucrados"
        )
        grid_and_configure(
            team_section,
            self._main_scrollable_frame,
            row=3,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
        )
        self.build_team_tab(team_section)

    def _safe_update_idletasks(self):
        """Intenta refrescar la UI sin propagar errores cuando la ventana no existe."""

        try:
            self.root.update_idletasks()
        except tk.TclError:
            pass

    def _register_scrollable(self, container):
        if container is None:
            return
        self._scrollable_containers.append(container)

    def _refresh_scrollable(self, container, *, max_height: int | None = None):
        if container is None:
            return

        def _sync():
            resize_scrollable_to_content(container, max_height=max_height)

        try:
            self.root.after_idle(_sync)
        except tk.TclError:
            _sync()

    def _refresh_all_scrollables(self):
        for container in self._scrollable_containers:
            self._refresh_scrollable(container)

    def _set_team_row_weights(self, *, detail_visible: bool) -> None:
        frame = getattr(self, "team_tab_frame", None)
        if frame is None:
            return

        try:
            frame.rowconfigure(0, weight=0 if detail_visible else 1)
            frame.rowconfigure(
                2,
                weight=(
                    self.TEAM_ROW_DETAIL_WEIGHT
                    if detail_visible
                    else self.TEAM_ROW_DETAIL_HIDDEN_WEIGHT
                ),
            )
        except tk.TclError:
            pass

    def _build_window_title(self, *, case_id: Optional[str] = None, streak_days: Optional[int] = None) -> str:
        """Devuelve el título normalizado de la ventana principal."""

        identifier = case_id if case_id is not None else ""
        if not identifier:
            try:
                identifier = self.id_caso_var.get().strip()
            except Exception:
                identifier = ""
        streak = streak_days if streak_days is not None else self._get_streak_days()
        safe_streak = max(int(streak or 0), 0)
        normalized_id = identifier or "sin ID"
        return f"FraudCase | Caso {normalized_id} | Racha: {safe_streak} días 🔥"

    def _update_window_title(self, *, case_id: Optional[str] = None, streak_days: Optional[int] = None) -> None:
        """Refresca el título de la ventana con el ID y la racha actual."""

        if not hasattr(self, "root") or self.root is None:
            return
        try:
            self.root.title(self._build_window_title(case_id=case_id, streak_days=streak_days))
        except tk.TclError:
            pass

    def _get_streak_days(self) -> int:
        info = getattr(self, "_streak_info", {}) or {}
        try:
            return max(int(info.get("streak_days", 0)), 0)
        except Exception:
            return 0

    def _load_streak_info(self) -> dict[str, object]:
        """Carga la racha guardada sin interferir con la validación inicial."""

        default = {"last_active_date": None, "streak_days": 0}
        try:
            path = getattr(self, "_streak_file", None)
            if not path or not Path(path).exists():
                return default
            with Path(path).open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            last_active = data.get("last_active_date")
            if last_active:
                datetime.fromisoformat(str(last_active))
            streak = max(int(data.get("streak_days", 0)), 0)
            return {"last_active_date": last_active, "streak_days": streak}
        except Exception as ex:
            log_event("validacion", f"Error cargando racha: {ex}", self.logs)
            return default

    def _persist_streak_info(self, info: dict[str, object]) -> None:
        try:
            self._streak_file.parent.mkdir(parents=True, exist_ok=True)
            with self._streak_file.open("w", encoding="utf-8") as fh:
                json.dump(info, fh, ensure_ascii=False, indent=2)
        except Exception as ex:
            log_event("validacion", f"Error guardando racha: {ex}", self.logs)

    def _compute_and_persist_streak(self) -> int:
        info = getattr(self, "_streak_info", {}) or {}
        today = datetime.now().date()
        last_active_raw = info.get("last_active_date")
        last_active = None
        if last_active_raw:
            with suppress(Exception):
                last_active = datetime.fromisoformat(str(last_active_raw)).date()
        streak = max(int(info.get("streak_days", 0)), 0)
        if last_active == today:
            updated_streak = max(streak, 1)
        elif last_active == today - timedelta(days=1):
            updated_streak = max(streak, 1) + 1
        else:
            updated_streak = 1
        self._streak_info = {
            "last_active_date": today.isoformat(),
            "streak_days": updated_streak,
        }
        self._persist_streak_info(self._streak_info)
        return updated_streak

    def _update_streak_if_applicable(self) -> int:
        """Actualiza la racha sólo tras ediciones válidas del usuario."""

        if not getattr(self, "_user_has_edited", False):
            return self._get_streak_days()
        return self._compute_and_persist_streak()

    def _handle_session_saved(self, dataset: Optional[CaseData] = None) -> None:
        streak = self._update_streak_if_applicable()
        case_id = None
        if dataset and isinstance(dataset, Mapping):
            case_id = (dataset.get("caso", {}) or {}).get("id_caso")
        self._update_window_title(case_id=case_id, streak_days=streak)
        self._play_save_particles()

    def _mark_user_edited(self) -> None:
        self._user_has_edited = True

    def _get_save_anchor_widget(self) -> Optional[tk.Widget]:
        bar = getattr(self, "actions_action_bar", None)
        if not bar:
            return None
        try:
            return bar.buttons.get("save_send")
        except Exception:
            return None

    def _play_save_particles(self, target_widget: Optional[tk.Widget] = None) -> None:
        """Muestra una animación ligera de partículas junto al botón de guardado."""

        if not hasattr(self, "root") or self.root is None:
            return

        widget = target_widget or self._get_save_anchor_widget()
        if widget is None:
            return

        try:
            self._safe_update_idletasks()
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            widget_x = widget.winfo_rootx()
            widget_y = widget.winfo_rooty()
            width = max(widget.winfo_width(), widget.winfo_reqwidth(), 24)
            height = max(widget.winfo_height(), widget.winfo_reqheight(), 12)
        except tk.TclError:
            return

        offset_x = widget_x - root_x
        offset_y = widget_y - root_y
        canvas_height = height + 20

        try:
            canvas = tk.Canvas(
                self.root,
                width=width,
                height=canvas_height,
                highlightthickness=0,
                bd=0,
                bg=self.root.cget("background"),
            )
        except tk.TclError:
            return

        canvas.place(x=offset_x, y=max(0, offset_y - 10))

        palette = ThemeManager.current()
        base_color = palette.get("accent", "#1d4ed8")
        background = palette.get("background", "#ffffff")

        def _blend(color: str, target: str, factor: float) -> str:
            color = color.lstrip("#")
            target = target.lstrip("#")
            try:
                cr, cg, cb = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
                tr, tg, tb = int(target[0:2], 16), int(target[2:4], 16), int(target[4:6], 16)
            except ValueError:
                return color if color else "#1d4ed8"
            mix = lambda c1, c2: int(c1 + (c2 - c1) * factor)
            return f"#{mix(cr, tr):02x}{mix(cg, tg):02x}{mix(cb, tb):02x}"

        particles = [
            {
                "x": random.uniform(6, max(width - 6, 6)),
                "y": canvas_height - random.uniform(6, 12),
                "vy": random.uniform(1.4, 2.6),
                "size": random.uniform(4, 9),
                "fade": random.uniform(0.08, 0.14),
                "alpha": 1.0,
            }
            for _ in range(10)
        ]

        def _step():
            try:
                canvas.delete("particle")
            except tk.TclError:
                return
            alive = False
            for particle in particles:
                if particle["alpha"] <= 0:
                    continue
                particle["y"] -= particle["vy"]
                particle["alpha"] -= particle["fade"]
                if particle["alpha"] <= 0:
                    continue
                alive = True
                fade_factor = min(1.0, 1.0 - particle["alpha"])
                color = _blend(base_color, background, fade_factor)
                size = particle["size"] * (0.5 + 0.5 * particle["alpha"])
                canvas.create_oval(
                    particle["x"],
                    particle["y"],
                    particle["x"] + size,
                    particle["y"] + size,
                    fill=color,
                    outline="",
                    tags="particle",
                )

            if alive:
                try:
                    self.root.after(40, _step)
                except tk.TclError:
                    pass
            else:
                try:
                    canvas.destroy()
                except tk.TclError:
                    pass

        canvas.after(1200, lambda: canvas.destroy() if canvas.winfo_exists() else None)
        _step()

    def _update_sound_preference(self) -> None:
        self._user_settings["sound_enabled"] = bool(self.sound_enabled_var.get())
        self._persist_user_settings()
        self._mark_user_edited()

    def _should_play_sound(self) -> bool:
        if not hasattr(self, "_user_has_edited"):
            return False
        sound_toggle = getattr(self, "sound_enabled_var", None)
        try:
            enabled = bool(sound_toggle.get()) if sound_toggle is not None else False
        except Exception:
            enabled = False
        return bool(self._user_has_edited and enabled)

    def _load_sound_bytes(self) -> Optional[bytes]:
        if self._sound_bytes is None:
            with suppress(Exception):
                self._sound_bytes = base64.b64decode(CONFIRMATION_WAV_B64)
        return self._sound_bytes

    def _play_sound_with_winsound(self, data: bytes) -> bool:
        if os.name != "nt":
            return False
        with suppress(Exception):
            import winsound

            winsound.PlaySound(data, winsound.SND_MEMORY | winsound.SND_ASYNC)
            return True
        return False

    def _play_sound_with_simpleaudio(self, data: bytes) -> bool:
        try:
            import simpleaudio as sa  # type: ignore
        except Exception:
            return False
        try:
            with wave.open(io.BytesIO(data), "rb") as wav_file:
                wave_obj = sa.WaveObject(
                    wav_file.readframes(wav_file.getnframes()),
                    wav_file.getnchannels(),
                    wav_file.getsampwidth(),
                    wav_file.getframerate(),
                )
            wave_obj.play()
            return True
        except Exception:
            return False

    def _play_feedback_sound(self) -> None:
        if not self._should_play_sound():
            return
        data = self._load_sound_bytes()
        if not data:
            return
        if self._play_sound_with_winsound(data):
            return
        if self._play_sound_with_simpleaudio(data):
            return
        with suppress(tk.TclError):
            self.root.bell()

    def _destroy_badge(self, window: Optional[tk.Toplevel]) -> None:
        if window is None:
            return
        try:
            window.destroy()
        except tk.TclError:
            pass
        if window is self._badge_window:
            self._badge_window = None
            self._badge_destroy_after_id = None

    def show_badge(self, title: str, detail: str | None = None) -> None:
        """Muestra una insignia transitoria con colores acordes al tema activo."""

        with suppress(tk.TclError):
            if self._badge_destroy_after_id:
                self.root.after_cancel(self._badge_destroy_after_id)
        self._destroy_badge(self._badge_window)

        palette = ThemeManager.current()
        background = palette.get("background", "#1f1f1f")
        foreground = palette.get("foreground", "#ffffff")
        accent = palette.get("accent", "#7a8aa6")

        try:
            self.root.update_idletasks()
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            root_width = self.root.winfo_width()
        except tk.TclError:
            root_x = root_y = 0
            root_width = 360
        x = root_x + max(root_width - 260, 40)
        y = root_y + 60

        badge = tk.Toplevel(self.root)
        badge.transient(self.root)
        with suppress(tk.TclError):
            badge.overrideredirect(True)
            badge.attributes("-topmost", True)
        badge.configure(bg=background, highlightbackground=accent, highlightthickness=1)
        badge.geometry(f"+{x}+{y}")
        ThemeManager.register_toplevel(badge)

        container = tk.Frame(badge, bg=background, padx=14, pady=10)
        container.pack(fill="both", expand=True)
        headline = tk.Label(
            container,
            text=title,
            bg=background,
            fg=foreground,
            font=(FONT_BASE, 12, "bold"),
        )
        headline.pack(anchor="w")
        if detail:
            body = tk.Label(
                container,
                text=detail,
                bg=background,
                fg=foreground,
                font=(FONT_BASE, 10),
                wraplength=240,
                justify="left",
            )
            body.pack(anchor="w", pady=(2, 0))

        self._badge_window = badge
        self._badge_destroy_after_id = badge.after(2000, lambda win=badge: self._destroy_badge(win))

    def _destroy_toast(self, toast: Optional[tk.Toplevel]) -> None:
        if toast is None:
            return
        try:
            toast.destroy()
        except tk.TclError:
            pass
        if toast is self._toast_window:
            self._toast_window = None
            self._toast_after_id = None

    def _choose_praise(self) -> str:
        return random.choice(POSITIVE_PHRASES)

    def _show_success_toast(
        self,
        widget: Optional[tk.Widget],
        message: str | None = None,
        *,
        duration_ms: int = 1600,
    ) -> None:
        if not getattr(self, "_user_has_edited", False):
            return
        self._display_toast(widget, message or self._choose_praise(), duration_ms=duration_ms)

    def _display_toast(
        self, widget: Optional[tk.Widget], message: str, *, duration_ms: int = 1600
    ) -> None:
        if not getattr(self, "root", None):
            return
        try:
            if self._toast_after_id:
                self.root.after_cancel(self._toast_after_id)
        except tk.TclError:
            self._toast_after_id = None
        self._destroy_toast(self._toast_window)

        palette = ThemeManager.current()
        background = palette.get("heading_background", palette.get("background", "#1f1f1f"))
        foreground = palette.get("foreground", "#ffffff")
        border = palette.get("border", palette.get("accent", "#7a8aa6"))

        toast = tk.Toplevel(self.root)
        toast.transient(self.root)
        with suppress(tk.TclError):
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
        container = ttk.Frame(toast, padding=(10, 6))
        container.pack(fill="both", expand=True)
        try:
            style = ThemeManager._ensure_style()  # type: ignore[attr-defined]
            style.configure(
                "SuccessToast.TFrame",
                background=background,
                bordercolor=border,
                relief=tk.SOLID,
                borderwidth=1,
            )
            style.configure(
                "SuccessToast.TLabel",
                background=background,
                foreground=foreground,
                font=(FONT_BASE, 10, "bold"),
            )
            container.configure(style="SuccessToast.TFrame")
        except Exception:
            container.configure(background=background, highlightbackground=border, highlightthickness=1)
        label = ttk.Label(container, text=message, style="SuccessToast.TLabel")
        label.pack()

        try:
            target = widget if widget is not None else self.root
            target.update_idletasks()
            base_x = target.winfo_rootx()
            base_y = target.winfo_rooty()
            target_w = target.winfo_width() or 240
            target_h = target.winfo_height() or 40
        except tk.TclError:
            base_x = base_y = 0
            target_w = 260
            target_h = 40
        toast.update_idletasks()
        width = toast.winfo_width() or 160
        height = toast.winfo_height() or 30
        x = base_x + max((target_w - width) // 2, 0)
        y = base_y + target_h + 8
        toast.geometry(f"{width}x{height}+{x}+{y}")
        ThemeManager.register_toplevel(toast)

        self._toast_window = toast
        try:
            self._toast_after_id = self.root.after(
                duration_ms, lambda win=toast: self._destroy_toast(win)
            )
        except tk.TclError:
            self._toast_after_id = None
            self._destroy_toast(toast)

    def _capture_widget_shine_state(self, widget: tk.Widget) -> dict[str, object]:
        state: dict[str, object] = {}
        for option in ("style", "highlightbackground", "highlightcolor", "highlightthickness"):
            try:
                state[option] = widget.cget(option)
            except Exception:
                continue
        return state

    def _restore_gold_shine(self, widget: tk.Widget) -> None:
        widget_id = id(widget)
        previous = self._gold_shine_states.pop(widget_id, None)
        if not previous:
            return
        style = previous.pop("style", None)
        with suppress(tk.TclError):
            if previous:
                widget.configure(**previous)
            if style is not None:
                widget.configure(style=style)

    def _cancel_gold_shine(self, widget: tk.Widget) -> None:
        widget_id = id(widget)
        job = self._gold_shine_jobs.pop(widget_id, None)
        if job and getattr(self, "root", None):
            with suppress(tk.TclError):
                self.root.after_cancel(job)
        self._restore_gold_shine(widget)

    def _apply_gold_style(
        self,
        widget: tk.Widget,
        *,
        border: str,
        glow: str,
        thickness: int,
        style_name: Optional[str],
    ) -> None:
        with suppress(Exception):
            if style_name:
                style = ThemeManager._ensure_style()  # type: ignore[attr-defined]
                style.configure(
                    style_name,
                    bordercolor=border,
                    lightcolor=glow,
                    darkcolor=border,
                    focusthickness=thickness,
                    focuscolor=border,
                )
        with suppress(tk.TclError):
            widget.configure(
                highlightbackground=border,
                highlightcolor=glow,
                highlightthickness=thickness,
            )

    def _schedule_gold_shimmer(
        self,
        widget: tk.Widget,
        *,
        border: str,
        glow: str,
        duration_ms: int,
        thickness: int,
        style_name: Optional[str],
        phase: int = 0,
    ) -> None:
        if not getattr(widget, "winfo_exists", lambda: False)():
            self._cancel_gold_shine(widget)
            return
        if duration_ms <= 0:
            self._cancel_gold_shine(widget)
            return
        shade = glow if phase % 2 == 0 else border
        self._apply_gold_style(widget, border=shade, glow=glow, thickness=thickness, style_name=style_name)
        interval = 180
        try:
            job = self.root.after(
                min(interval, duration_ms),
                lambda: self._schedule_gold_shimmer(
                    widget,
                    border=border,
                    glow=glow,
                    duration_ms=duration_ms - interval,
                    thickness=thickness,
                    style_name=style_name,
                    phase=phase + 1,
                ),
            )
            self._gold_shine_jobs[id(widget)] = job
        except tk.TclError:
            self._cancel_gold_shine(widget)

    def _apply_gold_chrome_shine(
        self, widgets: Iterable[tk.Widget], *, duration_ms: int = 1400
    ) -> None:
        if not getattr(self, "_user_has_edited", False):
            return
        palette = ThemeManager.current()
        glow = palette.get("accent", "#f6d365")
        border = "#d4af37"
        thickness = max(self._base_highlight_thickness, 2)
        seen: set[int] = set()
        for widget in widgets:
            if not widget or not getattr(widget, "winfo_exists", lambda: False)():
                continue
            widget_id = id(widget)
            if widget_id in seen:
                continue
            seen.add(widget_id)
            self._cancel_gold_shine(widget)
            self._gold_shine_states[widget_id] = self._capture_widget_shine_state(widget)
            style_name = None
            try:
                style = ThemeManager._ensure_style()  # type: ignore[attr-defined]
                base_style = widget.cget("style") or widget.winfo_class()
                style_name = f"{base_style}.GoldShine.{widget_id}"
                style.configure(
                    style_name,
                    bordercolor=border,
                    lightcolor=glow,
                    darkcolor=border,
                    focusthickness=thickness,
                    focuscolor=border,
                )
                with suppress(tk.TclError):
                    widget.configure(style=style_name)
            except Exception:
                style_name = None
            self._apply_gold_style(
                widget, border=border, glow=glow, thickness=thickness, style_name=style_name
            )
            self._schedule_gold_shimmer(
                widget,
                border=border,
                glow=glow,
                duration_ms=duration_ms,
                thickness=thickness,
                style_name=style_name,
            )

    def _shine_validated_fields(
        self, widgets: Iterable[tk.Widget], *, duration_ms: int = 1400
    ) -> None:
        self._apply_gold_chrome_shine(widgets, duration_ms=duration_ms)

    def _maybe_show_milestone_badge(
        self, count: int, label: str, *, user_initiated: bool, stride: int = 5
    ) -> None:
        if not user_initiated or count <= 0 or stride <= 0:
            return
        if count % stride != 0:
            return
        detail = f"Llevas {count} {label.lower()} registrados."
        self.show_badge(f"{label} +{stride}", detail)

    def _count_claims(self) -> int:
        return sum(len(getattr(prod, "claims", [])) for prod in self.product_frames)

    def notify_claim_added(self, *, user_initiated: bool = False) -> None:
        total_claims = self._count_claims()
        self._maybe_show_milestone_badge(total_claims, "Reclamos", user_initiated=user_initiated)

    def _load_walkthrough_state(self) -> dict[str, object]:
        try:
            with open(self._walkthrough_state_file, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _load_user_settings(self) -> dict[str, object]:
        try:
            with open(self._user_settings_file, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _persist_user_settings(self) -> None:
        try:
            self._user_settings_file.parent.mkdir(parents=True, exist_ok=True)
            self._user_settings_file.write_text(
                json.dumps(self._user_settings), encoding="utf-8"
            )
        except OSError as ex:
            log_event("validacion", f"No se pudo guardar las preferencias: {ex}", self.logs)

    def _persist_walkthrough_state(self) -> None:
        try:
            self._walkthrough_state_file.parent.mkdir(parents=True, exist_ok=True)
            self._walkthrough_state_file.write_text(
                json.dumps(self._walkthrough_state), encoding="utf-8"
            )
        except OSError as ex:
            log_event("validacion", f"No se pudo guardar la guía: {ex}", self.logs)

    def _schedule_walkthrough(self) -> None:
        if self._walkthrough_state.get("dismissed"):
            return
        try:
            self.root.after(800, self._launch_walkthrough_if_needed)
        except tk.TclError:
            self._launch_walkthrough_if_needed()

    def _launch_walkthrough_if_needed(self) -> None:
        if self._walkthrough_state.get("dismissed"):
            return
        self._walkthrough_steps = self._build_walkthrough_steps()
        if not self._walkthrough_steps:
            return
        self._walkthrough_step_index = 0
        self._show_walkthrough_step()

    def _build_walkthrough_steps(self) -> list[dict[str, object]]:
        headline = "13 pasos para documentar tu caso y exportar sin errores."
        steps = [
            {
                "id": "case",
                "title": "Paso 1 de 13: Datos del caso",
                "message": "Empieza con los datos generales del expediente para habilitar herencias y controles posteriores.",
                "anchor_getter": lambda key="case": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "clients",
                "title": "Paso 2 de 13: Clientes implicados",
                "message": "Relaciona a los clientes afectados o vinculados; aquí se valida unicidad y puedes autocompletar con catálogos.",
                "anchor_getter": lambda key="clients": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "products",
                "title": "Paso 3 de 13: Productos investigados",
                "message": "Registra los productos asociados al caso para consolidar montos y exportar sin errores.",
                "anchor_getter": lambda key="products": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "team",
                "title": "Paso 4 de 13: Colaboradores involucrados",
                "message": (
                    "Agrega colaboradores con sus IDs laborales, división y área; el formulario indica los campos "
                    "obligatorios y mostrará avisos si faltan datos requeridos para validar sanciones y asignaciones."
                ),
                "anchor_getter": lambda key="team": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "risks",
                "title": "Paso 5 de 13: Riesgos identificados",
                "message": (
                    "Registra cada riesgo con su ID, criticidad y exposición residual. Los planes de acción y líderes son "
                    "obligatorios cuando aplique; las alertas de duplicado aparecen al repetir un ID."
                ),
                "anchor_getter": lambda key="risks": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "norms",
                "title": "Paso 6 de 13: Normas transgredidas",
                "message": (
                    "Documenta cada norma con su identificador y fecha de vigencia; los campos resaltan cuando falta "
                    "información mínima para validar transgresiones antes de exportar."
                ),
                "anchor_getter": lambda key="norms": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "analysis",
                "title": "Paso 7 de 13: Narrativas y acciones",
                "message": (
                    "Completa antecedentes, modus operandi, hallazgos y acciones recomendadas. Los campos muestran límites "
                    "de formato y debes cubrir las secciones clave para justificar decisiones y sanciones."
                ),
                "anchor_getter": lambda key="analysis": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "imports",
                "title": "Paso 8 de 13: Importar datos masivos (CSV)",
                "message": (
                    "Usa las opciones de 'Cargar clientes/colaboradores/productos/combinado/riesgos/normas' cuando ya "
                    "sincronizaste catálogos. Cada botón valida formatos y mostrará mensajes si falta información crítica "
                    "o si hay filas duplicadas."
                ),
                "anchor_getter": lambda key="imports": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "actions",
                "title": "Paso 9 de 13: Acciones y combinados",
                "message": (
                    "En la pestaña Acciones puedes alternar entre cargas individuales y el botón 'Cargar combinado' para "
                    "poblar clientes, productos y colaboradores en un paso; asegúrate de que los catálogos estén vigentes "
                    "para pasar las validaciones."
                ),
                "anchor_getter": lambda key="actions": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "actions_bar",
                "title": "Paso 10 de 13: Barra de acciones fijas",
                "message": (
                    "En la sección Guardar, cargar y reportes tienes los botones clave: "
                    "\"Guardar y enviar\" valida todo y genera anexos, \"Generar Word\" crea el informe "
                    "principal y \"Generar informe (.md)\" deja un respaldo en Markdown."
                ),
                "anchor_getter": lambda key="actions_bar": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "export",
                "title": "Paso 11 de 13: Exportar informe",
                "message": (
                    "Cuando no queden errores de validación y los montos coinciden, usa \"Exportar informe\" para generar los archivos. "
                    "El botón se encuentra en la barra de acciones; si un control está deshabilitado revisa las alertas de validación."
                ),
                "anchor_getter": lambda key="export": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "validation",
                "title": "Paso 12 de 13: Panel de validación",
                "message": "Consulta el panel para ver errores y advertencias, lee el contador y usa el botón lateral para contraer o expandirlo según necesites.",
                "anchor_getter": lambda key="validation": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
            {
                "id": "summary_tab",
                "title": "Paso 13 de 13: Resumen",
                "message": (
                    "Revisa la pestaña Resumen para ver tablas compactas actualizadas después de cada guardar o importación. "
                    "Selecciona la sección y desplázate para validar que los datos consolidados coincidan con lo capturado."
                ),
                "anchor_getter": lambda key="summary": self._get_walkthrough_anchor(key),
                "headline": headline,
            },
        ]
        return steps

    def _get_walkthrough_anchor(self, key: str) -> Optional[tk.Widget]:
        candidates: list[Optional[tk.Widget]] = []
        if key == "case":
            candidates = [getattr(self, "_case_anchor_widget", None)]
        elif key == "clients":
            candidates = [
                getattr(self, "_client_anchor_widget", None),
                getattr(self, "_client_action_anchor", None),
            ]
        elif key == "products":
            candidates = [
                getattr(self, "_product_anchor_widget", None),
                getattr(self, "_product_action_anchor", None),
            ]
        elif key == "team":
            detail = getattr(self, "team_detail_wrapper", None)
            if detail is not None and not self._is_widget_mapped(detail):
                try:
                    self.show_team_detail()
                except Exception:
                    pass
                self._safe_update_idletasks()
            candidates = [
                getattr(self, "_team_anchor_widget", None),
                detail,
            ]
        elif key == "risks":
            candidates = [
                getattr(self, "_risk_anchor_widget", None),
                getattr(self, "risk_header_container", None),
            ]
        elif key == "norms":
            candidates = [
                getattr(self, "_norm_anchor_widget", None),
                getattr(self, "norm_header_container", None),
            ]
        elif key == "analysis":
            candidates = [
                getattr(self, "_analysis_anchor_widget", None),
                getattr(self, "_analysis_group", None),
            ]
        elif key == "imports":
            candidates = [
                getattr(self, "_import_anchor_widget", None),
                getattr(self, "import_group_frame", None),
                getattr(self, "import_clients_button", None),
            ]
        elif key == "actions":
            candidates = [
                getattr(self, "import_combined_button", None),
                getattr(self, "import_group_frame", None),
            ]
        elif key == "actions_bar":
            candidates = [
                getattr(self, "_actions_bar_anchor", None),
                getattr(self, "actions_action_bar", None),
                getattr(self, "btn_docx", None),
                getattr(self, "actions_action_bar", None)
                and getattr(self.actions_action_bar, "buttons", {}).get("md"),
            ]
        elif key == "export":
            action_bar = getattr(self, "actions_action_bar", None)
            candidates = [
                getattr(self, "_export_anchor_widget", None),
                getattr(action_bar, "buttons", {}).get("export") if action_bar else None,
                getattr(self, "btn_docx", None),
                getattr(action_bar, "buttons", {}).get("md") if action_bar else None,
                action_bar,
            ]
        elif key == "validation":
            panel = getattr(self, "_validation_panel", None)
            anchor_getter = getattr(panel, "get_anchor_widget", None)
            candidates = [
                anchor_getter() if callable(anchor_getter) else None,
                panel,
            ]
        elif key == "summary":
            candidates = [
                getattr(self, "summary_first_section", None),
                getattr(self, "summary_intro_label", None),
                getattr(self, "summary_tab", None),
            ]
        for widget in candidates:
            if widget is None:
                continue
            if not self._is_widget_mapped(widget):
                self._revive_walkthrough_widget(widget)
            if self._is_widget_mapped(widget):
                return widget
        return None

    def _revive_walkthrough_widget(self, widget: tk.Widget) -> None:
        tab_id = self._locate_tab_for_widget(widget)
        notebook = getattr(self, "notebook", None)
        if not tab_id or notebook is None:
            return
        try:
            notebook.select(tab_id)
            if hasattr(self, "_scroll_binder"):
                self._scroll_binder.activate_tab(tab_id)
        except Exception:
            return
        self._safe_update_idletasks()

    def _is_widget_mapped(self, widget: tk.Widget) -> bool:
        try:
            return bool(widget.winfo_ismapped())
        except tk.TclError:
            return False

    def _show_walkthrough_step(self) -> None:
        if not self._walkthrough_steps:
            return
        step = self._walkthrough_steps[self._walkthrough_step_index]
        anchor_getter: Optional[Callable[[], Optional[tk.Widget]]] = step.get("anchor_getter")  # type: ignore[assignment]
        anchor = anchor_getter() if callable(anchor_getter) else None
        if anchor is None:
            self._advance_walkthrough_on_missing_anchor()
            return

        geometry = self._ensure_walkthrough_anchor_visible(anchor)
        if geometry is None:
            self._advance_walkthrough_on_missing_anchor()
            return

        palette = ThemeManager.current()
        background = palette.get("background", "#1f1f1f")
        foreground = palette.get("foreground", "#ffffff")
        accent = palette.get("accent", "#7a8aa6")

        if not self._walkthrough_overlay or not self._walkthrough_overlay.winfo_exists():
            self._walkthrough_overlay = tk.Toplevel(self.root)
            self._walkthrough_overlay.title("Guía rápida")
            self._walkthrough_overlay.configure(
                bg=background, highlightbackground=accent, highlightthickness=1
            )
            self._walkthrough_overlay.attributes("-topmost", True)
            self._walkthrough_overlay.resizable(False, False)
            ThemeManager.register_toplevel(self._walkthrough_overlay)
            container = ttk.Frame(self._walkthrough_overlay, padding=10)
            container.pack(fill="both", expand=True)
            self._walkthrough_headline = ttk.Label(
                container, text="", wraplength=340, justify="left", font=(FONT_BASE, 11, "bold")
            )
            self._walkthrough_headline.pack(anchor="w", pady=(0, 4))
            self._walkthrough_title_label = ttk.Label(
                container, text="", wraplength=340, justify="left", font=(FONT_BASE, 10, "bold")
            )
            self._walkthrough_title_label.pack(anchor="w", pady=(0, 2))
            self._walkthrough_body_label = ttk.Label(
                container, text="", wraplength=340, justify="left", foreground=foreground
            )
            self._walkthrough_body_label.pack(anchor="w", pady=(0, 6))
            buttons = ttk.Frame(container)
            buttons.pack(fill="x", pady=(4, 0))
            self._walkthrough_next_btn = ttk.Button(
                buttons, text="Siguiente", command=self._advance_walkthrough
            )
            self._walkthrough_next_btn.pack(side="right", padx=(4, 0))
            skip_btn = ttk.Button(buttons, text="Saltar guía", command=self._skip_walkthrough)
            skip_btn.pack(side="right")

        headline_text = step.get("headline", "")
        self._walkthrough_headline.configure(text=headline_text)
        self._walkthrough_title_label.configure(text=step.get("title", ""))
        self._walkthrough_body_label.configure(text=step.get("message", ""))
        is_last = self._walkthrough_step_index == len(self._walkthrough_steps) - 1
        self._walkthrough_next_btn.configure(text="Listo" if is_last else "Siguiente")

        self._safe_update_idletasks()
        self._revalidate_walkthrough_anchor_geometry(anchor)
        self._position_walkthrough(anchor, geometry)

    def _advance_walkthrough_on_missing_anchor(self) -> None:
        if self._walkthrough_step_index + 1 < len(self._walkthrough_steps):
            self._walkthrough_step_index += 1
            self._show_walkthrough_step()
        else:
            self._dismiss_walkthrough()

    def _position_walkthrough(
        self, anchor: tk.Widget, geometry: tuple[int, int, int, int] | None = None
    ) -> None:
        geometry = geometry or self._get_widget_geometry(anchor)
        if geometry is None:
            return
        anchor_x, anchor_y, anchor_width, anchor_height = geometry
        if not self._walkthrough_overlay or not self._walkthrough_overlay.winfo_exists():
            return
        self._safe_update_idletasks()
        width = self._walkthrough_overlay.winfo_width()
        height = self._walkthrough_overlay.winfo_height()
        x = anchor_x + anchor_width + 12
        y = anchor_y
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        if x + width > screen_width - 10:
            x = max(10, anchor_x - width - 12)
        if y + height > screen_height - 10:
            y = max(10, screen_height - height - 10)
        self._walkthrough_overlay.geometry(f"+{x}+{y}")

    def _get_widget_geometry(self, widget: tk.Widget) -> tuple[int, int, int, int] | None:
        try:
            self._safe_update_idletasks()
            return (
                widget.winfo_rootx(),
                widget.winfo_rooty(),
                widget.winfo_width(),
                widget.winfo_height(),
            )
        except tk.TclError:
            return None

    def _revalidate_walkthrough_anchor_geometry(self, anchor: tk.Widget) -> None:
        try:
            anchor.update_idletasks()
        except Exception:
            pass
        self._safe_update_idletasks()

    def _advance_walkthrough(self) -> None:
        if self._walkthrough_step_index + 1 >= len(self._walkthrough_steps):
            self._dismiss_walkthrough()
            return
        self._walkthrough_step_index += 1
        self._show_walkthrough_step()

    def _skip_walkthrough(self) -> None:
        self._dismiss_walkthrough()

    def _dismiss_walkthrough(self) -> None:
        self._walkthrough_state["dismissed"] = True
        self._walkthrough_state["dismissed_at"] = datetime.utcnow().isoformat()
        self._persist_walkthrough_state()
        self._destroy_walkthrough()
        self._return_to_main_screen()

    def _destroy_walkthrough(self) -> None:
        if self._walkthrough_overlay is None:
            return
        try:
            self._walkthrough_overlay.destroy()
        except tk.TclError:
            pass
        self._walkthrough_overlay = None

    def _return_to_main_screen(self) -> None:
        notebook = getattr(self, "notebook", None)
        main_tab = getattr(self, "main_tab", None)
        if notebook is None or main_tab is None:
            return
        try:
            notebook.select(main_tab)
            if hasattr(self, "_scroll_binder"):
                self._scroll_binder.activate_tab(notebook.select())
        except Exception:
            return

    @classmethod
    def _sanitize_import_value(cls, value, column_name: str | None = None, row_number: int | None = None) -> str:
        """Normaliza valores provenientes de CSV para evitar inyección o caracteres de control."""

        if value is None:
            return ""
        text = str(value)
        sanitized = CONTROL_CHAR_PATTERN.sub("", text).strip()
        if not sanitized:
            return ""
        if sanitized.startswith(SPREADSHEET_FORMULA_PREFIXES):
            location = []
            if row_number is not None:
                location.append(f"fila {row_number}")
            if column_name:
                location.append(f"columna '{column_name}'")
            location_hint = f" en {' y '.join(location)}" if location else ""
            raise ValueError(
                f"Se rechazó un valor{location_hint} por iniciar con un prefijo de fórmula: '{sanitized[:32]}'"
            )
        return sanitized

    @classmethod
    def _sanitize_import_row(cls, row, row_number: int | None = None) -> dict[str, str]:
        """Aplica saneamiento consistente a cada celda de una fila importada."""

        sanitized = {}
        if not isinstance(row, Mapping):
            return sanitized
        for key, value in row.items():
            if key is None:
                continue
            normalized_key = cls._sanitize_text(key)
            sanitized[normalized_key] = cls._sanitize_import_value(value, normalized_key, row_number)
        return sanitized

    def _notify_taxonomy_warning(self, message):
        """Centraliza el aviso de inconsistencias en la taxonomía."""

        log_event('validacion', message, self.logs)
        try:
            messagebox.showwarning('Taxonomía inválida', message)
        except tk.TclError:
            pass

    def focus_main_tab(self):
        """Muestra la pestaña principal cuando una importación agrega registros.

        Al terminar de cargar clientes, productos o colaboradores desde la
        pestaña de acciones, los usuarios esperaban ver de inmediato los datos
        recién agregados.  Este helper selecciona la pestaña principal del
        ``Notebook`` (si existe) y registra el cambio en el log para que el
        auto-guardado capture el nuevo estado.
        """

        if getattr(self, "notebook", None) is None or getattr(self, "main_tab", None) is None:
            return
        try:
            self.notebook.select(self.main_tab)
            log_event("navegacion", "Se mostró la pestaña principal tras importar datos", self.logs)
        except tk.TclError:
            # Si el widget ya no existe (por ejemplo, al cerrar la app), se ignora el error.
            pass

    def sync_main_form_after_import(self, section_name, stay_on_summary=False):
        """Sincroniza la interfaz principal después de importar datos masivos.

        La función se diseñó como respuesta directa al feedback de que los
        registros cargados desde la pestaña de *Acciones* no se veían reflejados
        inmediatamente en las secciones de caso, clientes y productos.  Para
        garantizar esa visibilidad, se realizan cuatro pasos en orden:

            1. Se invocan ``update_client_options_global`` y
               ``update_team_options_global`` para notificar a todos los
               ``Combobox`` dependientes que hay nuevos IDs disponibles.
            2. Se llama a ``update_idletasks`` sobre la ventana raíz para que
               Tkinter repinte los marcos dinámicos y muestre los datos recién
               insertados sin esperar a que el usuario interactúe.
            3. Se selecciona la pestaña principal (método ``focus_main_tab``) de
               modo que el usuario visualice de inmediato los clientes,
               productos o colaboradores importados.
            4. Se registra un evento de navegación indicando qué tipo de datos
               disparó la sincronización, lo que permite auditar el proceso.

        Args:
            section_name (str): Nombre en español de la sección importada. Se
                utiliza únicamente para detallar el mensaje del log.
            stay_on_summary (bool): Cuando es ``True`` evita llamar a
                :meth:`focus_main_tab` para que la vista permanezca en la
                pestaña de Resumen tras pegar datos directamente en las tablas
                auxiliares.

        Ejemplo::

            self.sync_main_form_after_import("clientes")
        """

        self.update_client_options_global()
        self.update_team_options_global()
        try:
            self.root.update_idletasks()
        except tk.TclError:
            # Si la ventana ya no existe (por ejemplo al cerrar la app) no es
            # necesario continuar con la sincronización.
            return
        if not stay_on_summary:
            self.focus_main_tab()
        log_event(
            "navegacion",
            f"Sincronizó la pestaña principal tras importar {section_name}",
            self.logs,
        )

    def _notify_dataset_changed(self, summary_sections=None):
        """Marca el formulario como modificado y agenda el autosave diferido."""

        if not hasattr(self, "_autosave_job_id"):
            self._autosave_job_id = None
            self._autosave_dirty = False
        self.request_autosave()
        try:
            self._schedule_summary_refresh(sections=summary_sections)
        except TypeError:
            try:
                self._schedule_summary_refresh(summary_sections)
            except TypeError:
                pass

    def build_case_tab(self, parent):
        """Construye la pestaña de detalles del caso con badges homologados."""
        self.case_frame = CaseFrame(self, parent)
        self._case_anchor_widget = getattr(self.case_frame, "frame", None)

    def _validate_case_occurrence_date(self):
        self._ensure_case_vars()
        return validate_date_text(
            self.fecha_caso_var.get(),
            "La fecha de ocurrencia del caso",
            allow_blank=False,
            enforce_max_today=True,
            must_be_before=(
                self.fecha_descubrimiento_caso_var.get(),
                "la fecha de descubrimiento del caso",
            ),
        )

    def _validate_case_discovery_date(self):
        self._ensure_case_vars()
        return validate_date_text(
            self.fecha_descubrimiento_caso_var.get(),
            "La fecha de descubrimiento del caso",
            allow_blank=False,
            enforce_max_today=True,
            must_be_after=(
                self.fecha_caso_var.get(),
                "la fecha de ocurrencia del caso",
            ),
        )

    def _ensure_case_vars(self) -> None:
        """Garantiza que las variables del caso existan en entornos sin Tk real."""

        def _simple_var(default=""):
            class _SimpleVar:
                def __init__(self, value=default):
                    self._value = value

                def set(self, value):
                    self._value = value

                def get(self):
                    return self._value

            return _SimpleVar()

        required_attrs = (
            "id_caso_var",
            "tipo_informe_var",
            "cat_caso1_var",
            "cat_caso2_var",
            "mod_caso_var",
            "canal_caso_var",
            "proceso_caso_var",
            "fecha_caso_var",
            "fecha_descubrimiento_caso_var",
            "centro_costo_caso_var",
        )
        if all(hasattr(self, attr) for attr in required_attrs):
            return

        try:
            def _maybe_var(name, value=None):
                if hasattr(self, name):
                    return
                setattr(self, name, tk.StringVar(value=value))

            default_cat1 = list(TAXONOMIA.keys())[0]
            default_cat2 = list(TAXONOMIA[default_cat1].keys())[0]
            default_mod = TAXONOMIA[default_cat1][default_cat2][0]

            _maybe_var("id_caso_var")
            _maybe_var("tipo_informe_var", TIPO_INFORME_LIST[0])
            _maybe_var("cat_caso1_var", default_cat1)
            _maybe_var("cat_caso2_var", default_cat2)
            _maybe_var("mod_caso_var", default_mod)
            _maybe_var("canal_caso_var", CANAL_LIST[0])
            _maybe_var("proceso_caso_var", PROCESO_LIST[0])
            _maybe_var("fecha_caso_var")
            _maybe_var("fecha_descubrimiento_caso_var")
            _maybe_var("centro_costo_caso_var")
        except (tk.TclError, RuntimeError):
            def _fallback(name, value=""):
                if hasattr(self, name):
                    return
                setattr(self, name, _simple_var(value))

            default_cat1 = list(TAXONOMIA.keys())[0]
            default_cat2 = list(TAXONOMIA[default_cat1].keys())[0]
            default_mod = TAXONOMIA[default_cat1][default_cat2][0]

            _fallback("id_caso_var")
            _fallback("tipo_informe_var", TIPO_INFORME_LIST[0])
            _fallback("cat_caso1_var", default_cat1)
            _fallback("cat_caso2_var", default_cat2)
            _fallback("mod_caso_var", default_mod)
            _fallback("canal_caso_var", CANAL_LIST[0])
            _fallback("proceso_caso_var", PROCESO_LIST[0])
            _fallback("fecha_caso_var")
            _fallback("fecha_descubrimiento_caso_var")
            _fallback("centro_costo_caso_var")

    def on_case_cat1_change(self):
        """Actualiza las opciones de categoría 2 y modalidad cuando cambia cat1 del caso."""
        cat1 = self.cat_caso1_var.get()
        subcats = list(TAXONOMIA.get(cat1, {}).keys())
        if not subcats:
            subcats = [""]
        self.case_cat2_cb['values'] = subcats
        self.cat_caso2_var.set('')
        self.case_cat2_cb.set('')
        self.case_mod_cb['values'] = []
        self.mod_caso_var.set('')
        self.case_mod_cb.set('')
        self._log_navigation_change("Modificó categoría 1 del caso")

    def on_case_cat2_change(self):
        cat1 = self.cat_caso1_var.get()
        cat2 = self.cat_caso2_var.get()
        mods = TAXONOMIA.get(cat1, {}).get(cat2, [])
        if not mods:
            mods = [""]
        self.case_mod_cb['values'] = mods
        self.mod_caso_var.set('')
        self.case_mod_cb.set('')
        self._log_navigation_change("Modificó categoría 2 del caso")
        if self.cat_caso2_var.get() == 'Fraude Interno':
            messagebox.showwarning(
                "Analítica de fraude interno",
                "Recuerda coordinar con el equipo de reclamos para registrar la analítica correcta en casos de Fraude Interno.",
            )

    def build_clients_tab(self, parent):
        """Construye la pestaña de clientes con lista dinámica."""
        frame = build_grid_container(
            parent,
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
            row_weight=1,
            column_weight=1,
        )
        frame.columnconfigure(0, weight=1)
        self.clients_frame = frame
        self._clients_row_weights = {
            "default": {"summary": 1, "detail": 1},
            "expanded": {"summary": 1, "detail": 3},
        }
        self._apply_clients_row_weights(expanded=False)

        summary_section = ttk.LabelFrame(frame, text="Resumen de clientes")
        summary_section.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        summary_section.columnconfigure(0, weight=1)
        summary_section.rowconfigure(0, weight=1)
        self.clients_summary_section = summary_section

        self.clients_detail_wrapper = ttk.LabelFrame(frame, text="Detalle de clientes")
        ensure_grid_support(self.clients_detail_wrapper)
        self.clients_detail_wrapper.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.clients_detail_wrapper.columnconfigure(0, weight=1)
        self.clients_detail_wrapper.rowconfigure(0, weight=1)
        scrollable, inner = create_scrollable_container(self.clients_detail_wrapper)
        scrollable.grid(row=0, column=0, sticky="nsew")
        self.clients_scrollable = scrollable
        self._register_scrollable(scrollable)
        self.clients_container = inner
        ensure_grid_support(self.clients_container)
        if hasattr(self.clients_container, "columnconfigure"):
            self.clients_container.columnconfigure(0, weight=1)
        # Inicialmente un cliente en blanco
        self.add_client()
        self.hide_clients_detail()
        actions_container = ttk.Frame(frame)
        actions_container.grid(row=2, column=0, sticky="ew")
        actions_container.columnconfigure(0, weight=1)

        toggle_row = ttk.Frame(actions_container)
        toggle_row.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, ROW_PADY // 2))
        toggle_row.columnconfigure(0, weight=1)
        self.clients_toggle_btn = ttk.Button(
            toggle_row,
            text="Mostrar formulario",
            command=self.toggle_clients_detail,
        )
        self.clients_toggle_btn.grid(row=0, column=1, sticky="e", padx=5)

        client_actions = (
            ("Agregar cliente", "add"),
            ("Editar seleccionado", "edit"),
            ("Eliminar seleccionado", "delete"),
        )
        client_commands = {
            "add": self._on_new_client,
            "edit": self._edit_selected_client,
            "delete": self._remove_selected_client,
        }
        client_action_parent = ttk.Frame(actions_container)
        client_action_parent.grid(row=1, column=0, sticky="ew")
        self.clients_action_bar = ActionBar(
            client_action_parent,
            commands=client_commands,
            buttons=client_actions,
        )
        self._client_action_anchor = self.clients_action_bar.buttons.get("add")
        self.register_tooltip(
            self.clients_action_bar.buttons.get("add"), "Añade un nuevo cliente implicado en el caso."
        )
        self.register_tooltip(
            self.clients_action_bar.buttons.get("edit"),
            "Abre el formulario del cliente resaltado en el listado.",
        )
        self.register_tooltip(
            self.clients_action_bar.buttons.get("delete"),
            "Elimina el cliente seleccionado del resumen.",
        )

        self._refresh_client_summary()

    def _apply_clients_row_weights(self, *, expanded: bool) -> None:
        """Actualiza la distribución vertical entre el resumen y el detalle."""

        frame = getattr(self, "clients_frame", None)
        if frame is None:
            return
        weights = self._clients_row_weights["expanded" if expanded else "default"]
        frame.rowconfigure(0, weight=weights.get("summary", 1))
        frame.rowconfigure(1, weight=weights.get("detail", 1))

    def _on_new_client(self):
        self._log_navigation_change("Agregó cliente")
        self.show_clients_detail()
        self.add_client()

    def toggle_clients_detail(self):
        if self._clients_detail_visible:
            self.hide_clients_detail()
        else:
            self.show_clients_detail()

    def show_clients_detail(self):
        if self.clients_detail_wrapper is None:
            return
        try:
            self.clients_detail_wrapper.grid()
        except Exception:
            pass
        self._clients_detail_visible = True
        self._apply_clients_row_weights(expanded=True)
        self._refresh_scrollable(getattr(self, "clients_scrollable", None))
        if getattr(self, "clients_scrollable", None):
            scrollable = self.clients_scrollable

            def _resize_clients_scrollable():
                max_height = None
                root = getattr(self, "root", None)
                if root is not None:
                    try:
                        root.update_idletasks()
                        window_height = root.winfo_height() or root.winfo_reqheight()
                        if window_height:
                            max_height = int(window_height * 3)
                    except Exception:
                        pass

                resize_scrollable_to_content(scrollable, max_height=max_height)

            try:
                scrollable.after_idle(_resize_clients_scrollable)
            except Exception:
                _resize_clients_scrollable()
        if getattr(self, "clients_toggle_btn", None):
            try:
                self.clients_toggle_btn.config(text="Ocultar formulario")
            except Exception:
                pass

    def hide_clients_detail(self):
        if self.clients_detail_wrapper is None:
            return
        remover = getattr(self.clients_detail_wrapper, "grid_remove", None)
        if callable(remover):
            remover()
        self._clients_detail_visible = False
        self._apply_clients_row_weights(expanded=False)
        if getattr(self, "clients_toggle_btn", None):
            try:
                self.clients_toggle_btn.config(text="Mostrar formulario")
            except Exception:
                pass

    def add_client(self, summary_parent=None, user_initiated: bool = False):
        """Crea y añade un nuevo marco de cliente a la interfaz.

        Se utiliza ``self.client_lookup`` para proporcionar datos de autopoblado
        al nuevo cliente, en caso de que exista un registro previo en
        ``client_details.csv``. Luego se actualizan las opciones de clientes
        disponibles para los productos.
        """
        was_visible = self._clients_detail_visible
        self.show_clients_detail()
        idx = len(self.client_frames)
        client = ClientFrame(
            self.clients_container,
            idx,
            self.remove_client,
            self.update_client_options_global,
            self.logs,
            self.register_tooltip,
            owner=self,
            summary_parent=summary_parent or getattr(self, "clients_summary_section", None),
            client_lookup=self.client_lookup,
            summary_refresh_callback=self._schedule_summary_refresh,
            change_notifier=self._log_navigation_change,
            id_change_callback=self._handle_client_id_change,
        )
        if getattr(self, "_client_anchor_widget", None) is None:
            anchor = getattr(client, "section", None)
            header = getattr(anchor, "header", None)
            self._client_anchor_widget = header or anchor
        self.client_frames.append(client)
        self._renumber_clients()
        self._maybe_show_milestone_badge(len(self.client_frames), "Clientes", user_initiated=user_initiated)
        self.update_client_options_global()
        self._schedule_summary_refresh('clientes')
        if self._clients_detail_visible:
            self._refresh_scrollable(getattr(self, "clients_scrollable", None))
        if not was_visible:
            self.hide_clients_detail()
        if user_initiated:
            self._mark_user_edited()
            self._play_feedback_sound()

    def remove_client(self, client_frame):
        self._handle_client_id_change(client_frame, client_frame.id_var.get(), None)
        self.client_frames.remove(client_frame)
        self._renumber_clients()
        if self._client_summary_owner is client_frame:
            self._client_summary_owner = self.client_frames[0] if self.client_frames else None
        self.update_client_options_global()
        self._schedule_summary_refresh('clientes')

    def _refresh_frame_collection(
        self,
        frames,
        *,
        start_row: int = 0,
        columnspan: int = 1,
        padx: int | tuple[int, int] = COL_PADX,
        pady: int | tuple[int, int] = ROW_PADY,
        sticky: str = "nsew",
    ):
        refresh_dynamic_rows(
            frames,
            start_row=start_row,
            columnspan=columnspan,
            padx=padx,
            pady=pady,
            sticky=sticky,
        )

    def _renumber_clients(self):
        self._refresh_frame_collection(self.client_frames)

    def update_client_options_global(self):
        """Actualiza la lista de clientes en todos los productos y envolvimientos."""
        options = [c.id_var.get().strip() for c in self.client_frames if c.id_var.get().strip()]
        # Actualizar combobox de clientes en cada producto
        for prod in self.product_frames:
            prod.update_client_options()
        log_event("navegacion", "Actualizó opciones de cliente", self.logs)

    def _on_add_client_click(self):
        self.show_clients_detail()
        self.add_client(user_initiated=True)

    def _edit_selected_client(self):
        table = self.clients_summary_tree
        if not table:
            return
        selection = table.selection()
        if not selection:
            return
        values = table.item(selection[0], "values")
        client_id = values[0] if values else ""
        frame = self._find_client_frame(client_id)
        if frame:
            self.show_clients_detail()
            try:
                frame.frame.focus_set()
            except tk.TclError:
                pass

    def _remove_selected_client(self):
        table = self.clients_summary_tree
        if not table:
            return
        selection = table.selection()
        if not selection:
            return
        values = table.item(selection[0], "values")
        client_id = values[0] if values else ""
        frame = self._find_client_frame(client_id)
        if frame:
            self._log_navigation_change("Eliminó cliente desde resumen")
            self.remove_client(frame)

    def _on_client_selected(self, _event=None):
        table = self.clients_summary_tree
        if not table:
            return
        selection = table.selection()
        if not selection:
            return
        values = table.item(selection[0], "values")
        client_id = values[0] if values else ""
        frame = self._find_client_frame(client_id)
        if frame:
            try:
                frame.frame.focus_set()
            except tk.TclError:
                pass

    def build_team_tab(self, parent):
        frame = build_grid_container(
            parent,
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
            row_weight=1,
            column_weight=1,
        )
        self.team_tab_frame = frame
        frame.columnconfigure(0, weight=1)
        self._set_team_row_weights(detail_visible=False)

        summary_section = ttk.LabelFrame(frame, text="Resumen de colaboradores")
        summary_section.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        summary_section.columnconfigure(0, weight=1)
        summary_section.rowconfigure(0, weight=1)
        self.team_summary_section = summary_section

        controls = ttk.Frame(frame)
        controls.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        controls.columnconfigure(0, weight=1)
        add_btn = ttk.Button(controls, text="Agregar colaborador", command=self._on_new_team_member)
        add_btn.grid(row=0, column=0, sticky="w", padx=5, pady=ROW_PADY)
        if getattr(self, "_team_anchor_widget", None) is None:
            self._team_anchor_widget = add_btn
        self.register_tooltip(add_btn, "Crea un registro para otro colaborador investigado.")
        self.team_toggle_btn = ttk.Button(
            controls,
            text="Mostrar formulario",
            command=self.toggle_team_detail,
        )
        self.team_toggle_btn.grid(row=0, column=1, sticky="e", padx=5, pady=ROW_PADY)

        self.team_detail_wrapper = ttk.LabelFrame(frame, text="Detalle de colaboradores")
        ensure_grid_support(self.team_detail_wrapper)
        self.team_detail_wrapper.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.team_detail_wrapper.columnconfigure(0, weight=1)
        self.team_detail_wrapper.rowconfigure(0, weight=1)
        scrollable, inner = create_scrollable_container(self.team_detail_wrapper)
        scrollable.grid(row=0, column=0, sticky="nsew")
        self.team_scrollable = scrollable
        self._register_scrollable(scrollable)
        self.team_container = inner
        ensure_grid_support(self.team_container)
        if hasattr(self.team_container, "columnconfigure"):
            self.team_container.columnconfigure(0, weight=1)
        if getattr(self, "_team_anchor_widget", None) is None:
            header = getattr(self.team_detail_wrapper, "header", None)
            self._team_anchor_widget = header or self.team_detail_wrapper
        self.add_team()
        self.hide_team_detail()
        self._refresh_team_summary()

    def _on_new_team_member(self):
        self._log_navigation_change("Agregó colaborador")
        self.show_team_detail()
        self.add_team(user_initiated=True)
        self._refresh_compact_views(sections={"colaboradores"})

    def toggle_team_detail(self):
        if self._team_detail_visible:
            self.hide_team_detail()
        else:
            self.show_team_detail()

    def show_team_detail(self):
        if self.team_detail_wrapper is None:
            return
        try:
            self.team_detail_wrapper.grid()
        except Exception:
            pass
        self._team_detail_visible = True
        self._set_team_row_weights(detail_visible=True)
        scrollable = getattr(self, "team_scrollable", None)

        def _refresh_after_idle():
            max_height = None
            try:
                window_height = int(self.root.winfo_height())
            except Exception:
                window_height = 0
            if scrollable is not None:
                try:
                    scrollable.update_idletasks()
                except Exception:
                    pass
                inner = getattr(scrollable, "_scroll_inner", None)
                required_height = None
                if inner is not None:
                    try:
                        required_height = int(inner.winfo_reqheight())
                    except Exception:
                        required_height = None
                if window_height:
                    allowance = window_height * 3
                    max_height = (
                        min(required_height, allowance)
                        if required_height is not None
                        else allowance
                    )
                elif required_height is not None:
                    max_height = required_height

            resize_scrollable_to_content(scrollable, max_height=max_height)
            self._refresh_scrollable(scrollable, max_height=max_height)

        if scrollable is not None:
            try:
                self.root.after_idle(_refresh_after_idle)
            except tk.TclError:
                _refresh_after_idle()
        else:
            self._refresh_scrollable(scrollable)
        if getattr(self, "team_toggle_btn", None):
            try:
                self.team_toggle_btn.config(text="Ocultar formulario")
            except Exception:
                pass

    def hide_team_detail(self):
        if self.team_detail_wrapper is None:
            return
        remover = getattr(self.team_detail_wrapper, "grid_remove", None)
        if callable(remover):
            remover()
        self._team_detail_visible = False
        self._set_team_row_weights(detail_visible=False)
        if getattr(self, "team_toggle_btn", None):
            try:
                self.team_toggle_btn.config(text="Mostrar formulario")
            except Exception:
                pass

    def add_team(self, summary_parent=None, user_initiated: bool = False):
        idx = len(self.team_frames)
        was_visible = self._team_detail_visible
        self.show_team_detail()
        team = TeamMemberFrame(
            self.team_container,
            idx,
            self.remove_team,
            self.update_team_options_global,
            self.team_lookup,
            self.logs,
            self.register_tooltip,
            owner=self,
            summary_parent=summary_parent or getattr(self, "team_summary_section", None),
            summary_refresh_callback=self._schedule_summary_refresh,
            change_notifier=self._log_navigation_change,
            id_change_callback=self._handle_team_id_change,
            autofill_service=self.autofill_service,
            case_date_getter=lambda: self.fecha_caso_var.get(),
        )
        self.team_frames.append(team)
        self._renumber_team()
        self._maybe_show_milestone_badge(len(self.team_frames), "Colaboradores", user_initiated=user_initiated)
        self.update_team_options_global()
        self._schedule_summary_refresh('colaboradores')
        if self._team_detail_visible:
            self._refresh_scrollable(getattr(self, "team_scrollable", None))
        if not was_visible:
            self.hide_team_detail()
        if user_initiated:
            self._mark_user_edited()
            self._play_feedback_sound()

    def remove_team(self, team_frame):
        self._handle_team_id_change(team_frame, team_frame.id_var.get(), None)
        self.team_frames.remove(team_frame)
        self._renumber_team()
        if self._team_summary_owner is team_frame:
            self._team_summary_owner = self.team_frames[0] if self.team_frames else None
        self.update_team_options_global()
        self._schedule_summary_refresh('colaboradores')

    def _renumber_team(self):
        self._refresh_frame_collection(self.team_frames)

    def update_team_options_global(self):
        """Actualiza listas de colaboradores en productos e involucra."""
        options = [t.id_var.get().strip() for t in self.team_frames if t.id_var.get().strip()]
        for prod in self.product_frames:
            prod.update_team_options()
        log_event("navegacion", "Actualizó opciones de colaborador", self.logs)

    def _toggle_team_detail(self):
        self.toggle_team_detail()

    def _show_team_detail(self):
        self.show_team_detail()

    def _hide_team_detail(self):
        self.hide_team_detail()

    def _on_add_team_click(self):
        self.add_team()

    def _edit_selected_team_member(self):
        if not self.team_summary_tree:
            return
        selection = self.team_summary_tree.selection()
        if not selection:
            return
        values = self.team_summary_tree.item(selection[0], "values")
        collaborator_id = values[0] if values else ""
        frame = self._find_team_frame(collaborator_id)
        if frame:
            self.show_team_detail()
            try:
                frame.frame.focus_set()
            except tk.TclError:
                pass

    def _on_team_selected(self, _event=None):
        if not self.team_summary_tree:
            return
        selection = self.team_summary_tree.selection()
        if not selection:
            return
        values = self.team_summary_tree.item(selection[0], "values")
        collaborator_id = values[0] if values else ""
        frame = self._find_team_frame(collaborator_id)
        if frame:
            try:
                frame.frame.focus_set()
            except tk.TclError:
                pass

    def build_products_tab(self, parent):
        frame = build_grid_container(
            parent,
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
            row_weight=1,
            column_weight=1,
        )
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        summary_section = ttk.LabelFrame(frame, text="Resumen de productos")
        summary_section.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        summary_section.columnconfigure(0, weight=1)
        summary_section.rowconfigure(0, weight=1)
        self.products_summary_section = summary_section

        scrollable, inner = create_scrollable_container(
            frame, scroll_binder=self._scroll_binder, tab_id=parent
        )
        scrollable.grid(row=1, column=0, sticky="nsew", padx=COL_PADX, pady=(0, ROW_PADY))
        self.products_scrollable = scrollable
        self._register_scrollable(scrollable)
        self.product_container = inner
        ensure_grid_support(self.product_container)
        if hasattr(self.product_container, "columnconfigure"):
            self.product_container.columnconfigure(0, weight=1)

        product_actions = (
            ("Crear producto nuevo (vacío)", "add_empty"),
            ("Crear producto heredando del caso", "inherit_case"),
            ("Editar producto activo", "edit"),
            ("Eliminar producto activo", "delete"),
        )
        product_commands = {
            "add_empty": self._on_add_empty_product,
            "inherit_case": self._on_add_inherited_product,
            "edit": self._focus_active_product,
            "delete": self._remove_active_product_from_action,
        }
        product_action_parent = ttk.Frame(frame)
        product_action_parent.grid(row=2, column=0, sticky="ew", padx=COL_PADX, pady=(0, ROW_PADY))
        self.product_action_bar = ActionBar(
            product_action_parent,
            commands=product_commands,
            buttons=product_actions,
        )
        self._product_action_anchor = self.product_action_bar.buttons.get("add_empty")
        self.register_tooltip(
            self.product_action_bar.buttons.get("add_empty"), "Registra un nuevo producto investigado."
        )
        self.register_tooltip(
            self.product_action_bar.buttons.get("inherit_case"),
            "Crea un producto precargado con los datos del caso actual.",
        )
        self.register_tooltip(
            self.product_action_bar.buttons.get("edit"),
            "Lleva el foco al producto que estás editando actualmente.",
        )
        self.register_tooltip(
            self.product_action_bar.buttons.get("delete"),
            "Elimina el producto activo tras confirmar la acción.",
        )
        # No añadimos automáticamente un producto porque los productos están asociados a clientes

    def _on_add_empty_product(self):
        self._log_navigation_change("Agregó producto")
        return self.add_product(user_initiated=True)

    def _on_add_inherited_product(self):
        self._log_navigation_change("Agregó producto heredado")
        return self.add_product_inheriting_case(user_initiated=True)

    def _remove_active_product_from_action(self):
        self._log_navigation_change("Eliminó producto activo")
        self._remove_active_product()

    def _apply_case_taxonomy_defaults(self, product_frame):
        """Configura un producto nuevo con la taxonomía seleccionada en el caso."""

        cat1 = self.cat_caso1_var.get().strip()
        cat2 = self.cat_caso2_var.get().strip()
        modalidad = self.mod_caso_var.get().strip()

        if not cat1 or cat1 not in TAXONOMIA:
            return

        previous_suppression = getattr(product_frame, '_suppress_change_notifications', False)
        product_frame._suppress_change_notifications = True
        try:
            product_frame.cat1_var.set(cat1)
            product_frame.on_cat1_change()
            if cat2 and cat2 in TAXONOMIA[cat1]:
                product_frame.cat2_var.set(cat2)
                if hasattr(product_frame, 'cat2_cb'):
                    product_frame.cat2_cb.set(cat2)
                product_frame.on_cat2_change()
                if modalidad and modalidad in TAXONOMIA[cat1][cat2]:
                    product_frame.mod_var.set(modalidad)
                    if hasattr(product_frame, 'mod_cb'):
                        product_frame.mod_cb.set(modalidad)
        finally:
            product_frame._suppress_change_notifications = previous_suppression

    def _collect_case_state_for_inheritance(self):
        return {
            "categoria_1_caso": self.cat_caso1_var.get().strip(),
            "categoria_2_caso": self.cat_caso2_var.get().strip(),
            "modalidad_caso": self.mod_caso_var.get().strip(),
            "fecha_de_ocurrencia_caso": self.fecha_caso_var.get().strip(),
            "fecha_de_descubrimiento_caso": self.fecha_descubrimiento_caso_var.get().strip(),
            "canal_caso": self.canal_caso_var.get().strip(),
            "proceso_caso": self.proceso_caso_var.get().strip(),
        }

    def _apply_inherited_fields_to_product(self, product_frame, inherited_values):
        previous_suppression = getattr(product_frame, "_suppress_change_notifications", False)
        product_frame._suppress_change_notifications = True
        try:
            def _set_if_blank(var, value, combobox=None, on_change=None):
                if not value:
                    return False
                if var.get().strip():
                    return False
                var.set(value)
                if combobox is not None:
                    combobox.set(value)
                if on_change:
                    on_change()
                return True

            cat1 = inherited_values.get("categoria1")
            _set_if_blank(product_frame.cat1_var, cat1, on_change=product_frame.on_cat1_change)
            cat2 = inherited_values.get("categoria2")
            _set_if_blank(product_frame.cat2_var, cat2, getattr(product_frame, "cat2_cb", None), product_frame.on_cat2_change)
            mod = inherited_values.get("modalidad")
            _set_if_blank(product_frame.mod_var, mod, getattr(product_frame, "mod_cb", None))
            occ = inherited_values.get("fecha_ocurrencia")
            _set_if_blank(product_frame.fecha_oc_var, occ)
            desc = inherited_values.get("fecha_descubrimiento")
            _set_if_blank(product_frame.fecha_desc_var, desc)
            canal = inherited_values.get("canal")
            _set_if_blank(product_frame.canal_var, canal, getattr(product_frame, "canal_cb", None))
            proceso = inherited_values.get("proceso")
            _set_if_blank(product_frame.proceso_var, proceso, getattr(product_frame, "proc_cb", None))
        finally:
            product_frame._suppress_change_notifications = previous_suppression
        product_frame.focus_first_field()

    def _show_inheritance_messages(self, result):
        if getattr(self, "_suppress_messagebox", False):
            return
        if result.has_invalid:
            messagebox.showwarning(
                "Campos heredados", "Fecha heredada inválida; revisar fecha de caso."
            )
        if result.has_missing:
            messagebox.showinfo(
                "Herencia parcial",
                "Algunos campos del caso no estaban definidos; se heredó lo disponible.",
            )

    def add_product_inheriting_case(self, user_initiated: bool = False):
        case_state = self._collect_case_state_for_inheritance()
        result = InheritanceService.inherit_product_fields_from_case(case_state)
        try:
            prod = self.add_product(user_initiated=user_initiated)
        except TypeError:
            prod = self.add_product()
        self._apply_inherited_fields_to_product(prod, result.values)
        self._show_inheritance_messages(result)
        return prod

    def add_product(self, initialize_rows=True, user_initiated: bool = False, summary_parent=None):
        idx = len(self.product_frames)
        prod = ProductFrame(
            self.product_container,
            idx,
            self.remove_product,
            self.get_client_ids,
            self.get_team_ids,
            self.logs,
            self.product_lookup,
            self.register_tooltip,
            claim_lookup=self.claim_lookup,
            summary_refresh_callback=self._schedule_summary_refresh,
            change_notifier=self._log_navigation_change,
            id_change_callback=self._handle_product_id_change,
            initialize_rows=initialize_rows,
            duplicate_key_checker=self._check_duplicate_technical_keys_realtime,
            owner=self,
            summary_parent=summary_parent or getattr(self, "products_summary_section", None),
        )
        if getattr(self, "_product_anchor_widget", None) is None:
            anchor = getattr(prod, "section", None)
            header = getattr(anchor, "header", None)
            self._product_anchor_widget = header or anchor
        self._apply_case_taxonomy_defaults(prod)
        self.product_frames.append(prod)
        self._renumber_products()
        self._maybe_show_milestone_badge(len(self.product_frames), "Productos", user_initiated=user_initiated)
        self._set_active_product_frame(prod)
        self._schedule_summary_refresh({'productos', 'reclamos'})
        self._refresh_scrollable(getattr(self, "products_scrollable", None))
        prod.focus_first_field()
        if user_initiated:
            self._mark_user_edited()
            self._play_feedback_sound()
        return prod

    def remove_product(self, prod_frame):
        self._handle_product_id_change(prod_frame, prod_frame.id_var.get(), None)
        self.product_frames.remove(prod_frame)
        self._renumber_products()
        if getattr(self, "_active_product_frame", None) is prod_frame:
            self._active_product_frame = self.product_frames[-1] if self.product_frames else None
        self._schedule_summary_refresh({'productos', 'reclamos'})

    def _renumber_products(self):
        self._refresh_frame_collection(self.product_frames)

    def _set_active_product_frame(self, frame):
        self._active_product_frame = frame

    def _focus_active_product(self):
        frame = getattr(self, "_active_product_frame", None) or (self.product_frames[0] if self.product_frames else None)
        if frame:
            self.show_tab(self.products_tab)
            self.show_products_tab()
            try:
                frame.focus_first_field()
            except Exception:
                pass

    def _remove_active_product(self):
        frame = getattr(self, "_active_product_frame", None) or (self.product_frames[-1] if self.product_frames else None)
        if frame:
            frame.remove()

    def get_client_ids(self):
        return [c.id_var.get().strip() for c in self.client_frames if c.id_var.get().strip()]

    def get_team_ids(self):
        return [t.id_var.get().strip() for t in self.team_frames if t.id_var.get().strip()]

    def build_risk_tab(self, parent):
        frame = build_grid_container(
            parent,
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
            row_weight=1,
            column_weight=1,
        )
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        header_row = ttk.Frame(frame)
        header_row.grid(row=0, column=0, sticky="nsew")
        header_row.columnconfigure(0, weight=1)
        header_row.rowconfigure(0, weight=1)

        self.risk_header_tree, self.risk_header_container = self._build_shared_header_tree(
            header_row, 0, RiskFrame.build_header_tree
        )

        add_btn = ttk.Button(header_row, text="Agregar riesgo", command=self._on_add_risk)
        add_btn.grid(
            row=0,
            column=1,
            sticky="nw",
            padx=(0, COL_PADX),
            pady=(ROW_PADY, ROW_PADY // 2),
        )
        self.register_tooltip(add_btn, "Registra un nuevo riesgo identificado.")
        if getattr(self, "_risk_anchor_widget", None) is None:
            self._risk_anchor_widget = add_btn

        scrollable, inner = create_scrollable_container(
            frame, scroll_binder=self._scroll_binder, tab_id=parent
        )
        scrollable.grid(row=1, column=0, sticky="nsew", padx=COL_PADX, pady=(0, ROW_PADY))
        self.risks_scrollable = scrollable
        self._register_scrollable(scrollable)
        self.risk_container = inner
        ensure_grid_support(self.risk_container)
        if hasattr(self.risk_container, "columnconfigure"):
            self.risk_container.columnconfigure(0, weight=1)
        self.add_risk()

    def _on_add_risk(self):
        self._log_navigation_change("Agregó riesgo")
        self.add_risk(user_initiated=True)

    def add_risk(self, user_initiated: bool = False):
        idx = len(self.risk_frames)
        default_risk_id = self._generate_next_risk_id()
        risk = RiskFrame(
            self.risk_container,
            idx,
            self.remove_risk,
            self.logs,
            self.register_tooltip,
            change_notifier=self._log_navigation_change,
            default_risk_id=default_risk_id,
            header_tree=self.risk_header_tree,
        )
        risk.set_refresh_callbacks(
            shared_tree_refresher=self._refresh_shared_risk_tree,
            summary_refresher=lambda: self._schedule_summary_refresh('riesgos'),
        )
        self.risk_frames.append(risk)
        self._renumber_risks()
        self._maybe_show_milestone_badge(len(self.risk_frames), "Riesgos", user_initiated=user_initiated)
        self._refresh_risk_auto_ids()
        self._refresh_shared_risk_tree()
        self._refresh_scrollable(getattr(self, "risks_scrollable", None))

    def remove_risk(self, risk_frame):
        self.risk_frames.remove(risk_frame)
        self._renumber_risks()
        self._refresh_risk_auto_ids()
        self._refresh_shared_risk_tree()

    def _renumber_risks(self):
        self._refresh_frame_collection(
            self.risk_frames, pady=(ROW_PADY // 2, ROW_PADY)
        )

    def _generate_next_risk_id(self, used_ids=None):
        """Obtiene el siguiente ID automático disponible para riesgos."""

        normalized_used = {rid for rid in (used_ids or set()) if rid}
        if used_ids is None:
            normalized_used.update(r.id_var.get().strip() for r in self.risk_frames if r.id_var.get().strip())
        while True:
            candidate = f"RSK-{self.next_risk_number:06d}"
            self.next_risk_number += 1
            if candidate not in normalized_used:
                return candidate
            # En caso de colisión continuar buscando
        # Not reachable

    def _refresh_risk_auto_ids(self):
        """Normaliza los IDs automáticos sin afectar los editados manualmente."""

        used_ids = set()
        frames_to_update = []
        for frame in self.risk_frames:
            rid = frame.id_var.get().strip()
            if rid and rid not in used_ids:
                used_ids.add(rid)
                continue
            frames_to_update.append(frame)
        for frame in frames_to_update:
            if frame.has_user_modified_id():
                continue
            new_id = self._generate_next_risk_id(used_ids)
            frame.assign_new_auto_id(new_id)
            used_ids.add(new_id)

    def build_norm_tab(self, parent):
        frame = build_grid_container(
            parent,
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
            row_weight=1,
            column_weight=1,
        )
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        header_row = ttk.Frame(frame)
        header_row.grid(row=0, column=0, sticky="nsew", padx=COL_PADX, pady=(ROW_PADY, ROW_PADY // 2))
        header_row.columnconfigure(0, weight=1)

        self.norm_header_tree, self.norm_header_container = self._build_shared_header_tree(
            header_row, 0, NormFrame.build_header_tree
        )

        add_btn = ttk.Button(header_row, text="Agregar norma", command=self._on_add_norm)
        add_btn.grid(row=0, column=1, sticky="n", padx=(COL_PADX, 0), pady=(ROW_PADY, ROW_PADY // 2))
        self.register_tooltip(add_btn, "Agrega otra norma transgredida.")
        if getattr(self, "_norm_anchor_widget", None) is None:
            self._norm_anchor_widget = add_btn

        scrollable, inner = create_scrollable_container(frame)
        scrollable.grid(row=1, column=0, sticky="nsew", padx=COL_PADX, pady=(0, ROW_PADY))
        self.norms_scrollable = scrollable
        self._register_scrollable(scrollable)
        self.norm_container = inner
        ensure_grid_support(self.norm_container)
        if hasattr(self.norm_container, "columnconfigure"):
            self.norm_container.columnconfigure(0, weight=1)
        self.add_norm()

    def _on_add_norm(self):
        self._log_navigation_change("Agregó norma")
        self.add_norm()

    def add_norm(self):
        idx = len(self.norm_frames)
        norm = NormFrame(
            self.norm_container,
            idx,
            self.remove_norm,
            self.logs,
            self.register_tooltip,
            change_notifier=self._log_navigation_change,
            header_tree=self.norm_header_tree,
        )
        self.norm_frames.append(norm)
        self._renumber_norms()
        self._refresh_shared_norm_tree()
        self._refresh_scrollable(getattr(self, "norms_scrollable", None))

    def remove_norm(self, norm_frame):
        self.norm_frames.remove(norm_frame)
        self._renumber_norms()
        self._refresh_shared_norm_tree()

    def _renumber_norms(self):
        self._refresh_frame_collection(
            self.norm_frames, pady=(ROW_PADY // 2, ROW_PADY)
        )

    def _build_shared_header_tree(self, parent, row_index, tree_builder):
        container = build_grid_container(
            parent,
            row=row_index,
            column=0,
            padx=COL_PADX,
            pady=(0, ROW_PADY // 2),
            sticky="nsew",
            row_weight=1,
            column_weight=1,
        )

        xscrollbar = ttk.Scrollbar(container, orient="horizontal")

        tree = tree_builder(container, xscrollcommand=xscrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=COL_PADX, pady=(ROW_PADY, ROW_PADY // 2))

        yscrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        yscrollbar.grid(row=0, column=1, sticky="ns", pady=(ROW_PADY, ROW_PADY // 2))

        xscrollbar.configure(command=tree.xview)
        xscrollbar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=COL_PADX, pady=(0, ROW_PADY // 2))

        tree.configure(yscrollcommand=yscrollbar.set, xscrollcommand=xscrollbar.set)

        return tree, container

    def _refresh_shared_norm_tree(self):
        if not getattr(self, "norm_header_tree", None):
            return

        for child in self.norm_header_tree.get_children(""):
            self.norm_header_tree.delete(child)

        row_index = 0
        for norm_frame in self.norm_frames:
            data = norm_frame.get_data()
            if not data:
                continue
            values = (
                data.get("id_norma", ""),
                data.get("fecha_vigencia", ""),
                data.get("descripcion", ""),
            )
            tag = "even" if row_index % 2 == 0 else "odd"
            self.norm_header_tree.insert("", "end", values=values, tags=(tag,))
            row_index += 1

        self._schedule_summary_refresh('normas')

    def _refresh_shared_risk_tree(self):
        if not getattr(self, "risk_header_tree", None):
            return

        for child in self.risk_header_tree.get_children(""):
            self.risk_header_tree.delete(child)

        for idx, risk_frame in enumerate(self.risk_frames):
            data = risk_frame.get_data()
            values = (
                data.get("id_riesgo", ""),
                data.get("criticidad", ""),
                data.get("exposicion_residual", ""),
                data.get("lider", ""),
                data.get("descripcion", ""),
            )
            tag = "even" if idx % 2 == 0 else "odd"
            self.risk_header_tree.insert("", "end", values=values, tags=(tag,))
        self._schedule_summary_refresh('riesgos')

        self._schedule_summary_refresh('riesgos')

    def build_analysis_tab(self, parent):
        scrollable_tab, tab_container = create_scrollable_container(
            parent, scroll_binder=self._scroll_binder, tab_id=parent
        )
        grid_and_configure(
            scrollable_tab,
            parent,
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
        )
        self.analysis_scrollable = scrollable_tab
        self._register_scrollable(scrollable_tab)
        self._analysis_tab_container = tab_container
        tab_container.columnconfigure(0, weight=1)
        tab_container.rowconfigure(1, weight=1)

        controls = ttk.Frame(tab_container)
        controls.grid(row=0, column=0, sticky="ew", padx=COL_PADX, pady=(ROW_PADY, 0))
        self._extended_sections_toggle_var = tk.BooleanVar(
            value=self._extended_sections_enabled
        )
        extended_toggle = ttk.Checkbutton(
            controls,
            text="Mostrar secciones extendidas del informe",
            variable=self._extended_sections_toggle_var,
            command=self._handle_extended_sections_toggle,
            style=ThemeManager.CHECKBUTTON_STYLE,
        )
        extended_toggle.pack(side="left")
        self.register_tooltip(
            extended_toggle,
            "Activa o desactiva las secciones extendidas para completar el informe.",
        )

        analysis_group = ttk.LabelFrame(tab_container, text="Análisis narrativo")
        analysis_group.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=COL_PADX,
            pady=ROW_PADY,
        )
        analysis_group.columnconfigure(0, weight=1)
        analysis_group.rowconfigure(1, weight=1)
        self._analysis_group = analysis_group
        if getattr(self, "_analysis_anchor_widget", None) is None:
            self._analysis_anchor_widget = analysis_group

        constraints_label = ttk.Label(
            analysis_group,
            text=(
                "Los campos aceptan texto enriquecido e imágenes PNG, GIF, PPM o PGM. "
                "Puedes pegar imágenes desde el portapapeles o seleccionarlas desde un archivo."
            ),
            wraplength=760,
            justify="left",
        )
        constraints_label.grid(row=0, column=0, sticky="w", padx=COL_PADX, pady=(ROW_PADY // 2, ROW_PADY // 4))

        analysis_container = ttk.Frame(analysis_group)
        analysis_container.grid(row=1, column=0, sticky="nsew")
        analysis_container.columnconfigure(0, weight=1)

        fields = [
            ("Antecedentes:", "Modificó antecedentes", "Resume los hechos previos y contexto del caso."),
            ("Modus operandi:", "Modificó modus operandi", "Describe la forma en que se ejecutó el fraude."),
            ("Hallazgos principales:", "Modificó hallazgos", "Menciona los hallazgos clave de la investigación."),
            ("Descargos del colaborador:", "Modificó descargos", "Registra los descargos formales del colaborador."),
            ("Conclusiones:", "Modificó conclusiones", "Escribe las conclusiones generales del informe."),
            ("Recomendaciones y mejoras:", "Modificó recomendaciones", "Propón acciones correctivas y preventivas."),
        ]

        bold_font, header_font, mono_font = self._get_rich_text_fonts()

        text_widgets = []
        for idx, (label_text, log_message, tooltip) in enumerate(fields):
            section_frame = ttk.Frame(analysis_container)
            section_frame.grid(
                row=idx,
                column=0,
                padx=COL_PADX,
                pady=(ROW_PADY, ROW_PADY),
                sticky="nsew",
            )
            analysis_container.rowconfigure(idx, weight=1)
            section_frame.columnconfigure(0, weight=1)
            section_frame.rowconfigure(1, weight=1)

            ttk.Label(section_frame, text=label_text).grid(
                row=0,
                column=0,
                padx=COL_PADX,
                pady=(0, ROW_PADY // 2),
                sticky="w",
            )

            text_widget = scrolledtext.ScrolledText(
                section_frame,
                height=22,
                width=96,
                wrap="word",
            )
            text_widget.grid(
                row=1,
                column=0,
                padx=COL_PADX,
                pady=(ROW_PADY // 4, ROW_PADY // 2),
                sticky="nsew",
            )
            text_widget.configure(
                takefocus=True,
                font=FONT_BASE,
                padx=COL_PADX,
                pady=ROW_PADY,
                wrap=tk.WORD,
            )
            self._configure_rich_text_tags(text_widget, bold_font, header_font, mono_font)
            self._bind_rich_text_paste_support(text_widget)
            text_widget.bind(
                "<FocusOut>", lambda e, message=log_message: self._log_navigation_change(message)
            )
            self._register_rich_text_limit(text_widget, label_text.rstrip(":"))
            self.register_tooltip(text_widget, tooltip)
            toolbar = ttk.Frame(section_frame)
            toolbar.grid(
                row=2,
                column=0,
                padx=COL_PADX,
                pady=(0, ROW_PADY // 2),
                sticky="w",
            )
            self._add_rich_text_toolbar(toolbar, text_widget)
            text_widgets.append(text_widget)

        (
            self.antecedentes_text,
            self.modus_text,
            self.hallazgos_text,
            self.descargos_text,
            self.conclusiones_text,
            self.recomendaciones_text,
        ) = text_widgets

        if self._extended_sections_enabled:
            self._build_extended_analysis_sections(tab_container)

    def _build_extended_analysis_sections(self, parent):
        if self._extended_analysis_group is not None:
            return self._extended_analysis_group

        if parent is not None:
            parent.rowconfigure(2, weight=1)

        extended_group = ttk.LabelFrame(parent, text="Secciones extendidas del informe")
        extended_group.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=COL_PADX,
            pady=ROW_PADY,
        )
        extended_group.columnconfigure(0, weight=1)
        extended_group.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(extended_group)
        notebook.grid(row=0, column=0, sticky="nsew")
        self._extended_notebook = notebook

        header_tab = ttk.Frame(notebook)
        tables_tab = ttk.Frame(notebook)
        notebook.add(header_tab, text="Encabezado y firmas")
        notebook.add(tables_tab, text="Operaciones y anexos")

        self._build_header_fields(header_tab)
        self._build_recommendations_fields(header_tab)
        self._build_signature_fields(header_tab)
        self._build_operations_section(tables_tab)
        self._build_anexos_section(tables_tab)

        self._extended_analysis_group = extended_group
        return extended_group

    def _handle_extended_sections_toggle(self):
        enabled = bool(self._extended_sections_toggle_var.get()) if self._extended_sections_toggle_var else False
        self._extended_sections_enabled = enabled
        if enabled:
            if self._analysis_tab_container is None:
                return
            self._build_extended_analysis_sections(self._analysis_tab_container)
            self._sync_extended_sections_to_ui()
        else:
            self._destroy_extended_analysis_sections()
            if self._analysis_tab_container is not None:
                self._analysis_tab_container.rowconfigure(2, weight=0)
        self._notify_dataset_changed()

    def _destroy_extended_analysis_sections(self):
        if self._extended_analysis_group is None and self._extended_notebook is None:
            return
        if self._extended_notebook is not None and self._extended_notebook.winfo_exists():
            self._extended_notebook.destroy()
        self._extended_notebook = None
        if self._extended_analysis_group is None:
            return
        try:
            self._extended_analysis_group.destroy()
        finally:
            self._extended_analysis_group = None
            for attr in ("operations_tree", "anexos_tree"):
                if hasattr(self, attr):
                    setattr(self, attr, None)
            if self._analysis_tab_container is not None:
                self._analysis_tab_container.rowconfigure(2, weight=0)

    def _build_header_fields(self, parent):
        header_group = ttk.LabelFrame(parent, text="Encabezado extendido")
        header_group.pack(fill="x", expand=False, padx=COL_PADX, pady=ROW_PADY)
        header_group.columnconfigure(1, weight=1)
        header_group.columnconfigure(3, weight=1)

        field_specs = [
            ("Dirigido a:", "dirigido_a", 0),
            ("Referencia:", "referencia", 1),
            ("Área de reporte:", "area_reporte", 2),
            ("Fecha de reporte (YYYY-MM-DD):", "fecha_reporte", 3),
            ("Tipología de evento:", "tipologia_evento", 4),
            ("Centro de costos (; separados):", "centro_costos", 5),
            ("Procesos impactados:", "procesos_impactados", 6),
            ("N° de reclamos:", "numero_reclamos", 7),
            ("Analítica contable:", "analitica_contable", 8),
            ("Producto (texto opcional):", "producto", 9),
        ]

        for label_text, key, row in field_specs:
            ttk.Label(header_group, text=label_text).grid(
                row=row,
                column=0,
                padx=COL_PADX,
                pady=(ROW_PADY // 2),
                sticky="e",
            )
            var = self._encabezado_vars.get(key) or tk.StringVar(
                value=self._encabezado_data.get(key, "")
            )
            self._encabezado_vars[key] = var
            entry = ttk.Entry(header_group, textvariable=var)
            entry.grid(row=row, column=1, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="we")
            var.trace_add("write", lambda *_args, k=key: self._update_encabezado_value(k))
            if key == "centro_costos":
                self._register_post_edit_validation(entry, self._validate_cost_centers, "Centro de costos")
                self.register_tooltip(
                    entry,
                    "Ingresa centros de costos separados por punto y coma. Cada valor debe ser numérico y de al menos 5 dígitos.",
                )
            elif key == "fecha_reporte":
                self._register_post_edit_validation(
                    entry,
                    lambda: validate_date_text(
                        self._encabezado_vars["fecha_reporte"].get(),
                        "La fecha de reporte",
                        allow_blank=True,
                        enforce_max_today=True,
                    ),
                    "Fecha de reporte",
                )
                self.register_tooltip(entry, "Fecha opcional del informe con formato YYYY-MM-DD.")
            elif key == "numero_reclamos":
                self._register_post_edit_validation(entry, self._validate_reclamos_count, "Número de reclamos")
                self.register_tooltip(entry, "Si se conoce, ingresa la cantidad total de reclamos asociados.")
            else:
                self.register_tooltip(entry, "Campo opcional para complementar el encabezado del informe.")

    def _build_recommendations_fields(self, parent):
        rec_group = ttk.LabelFrame(parent, text="Recomendaciones categorizadas")
        rec_group.pack(fill="both", expand=True, padx=COL_PADX, pady=ROW_PADY)
        rec_group.columnconfigure(0, weight=1)
        rec_group.columnconfigure(1, weight=1)
        rec_group.columnconfigure(2, weight=1)

        text_specs = [
            ("Laboral", "laboral", 0),
            ("Operativo", "operativo", 1),
            ("Legal", "legal", 2),
        ]
        for label, key, column in text_specs:
            container = ttk.Frame(rec_group)
            container.grid(row=0, column=column, padx=COL_PADX, pady=ROW_PADY, sticky="nsew")
            container.columnconfigure(0, weight=1)
            ttk.Label(container, text=label).grid(row=0, column=0, sticky="w", padx=COL_PADX)
            text_widget = scrolledtext.ScrolledText(container, height=6, wrap=tk.WORD)
            text_widget.grid(row=1, column=0, sticky="nsew", padx=COL_PADX, pady=(0, ROW_PADY))
            text_widget.insert("1.0", "\n".join(self._recomendaciones_categorias.get(key, [])))
            text_widget.bind("<KeyRelease>", lambda _e, k=key, w=text_widget: self._update_recommendation_category(k, w))
            self._recommendation_widgets[key] = text_widget
            self.register_tooltip(
                text_widget,
                "Lista recomendaciones separadas por saltos de línea para agruparlas por ámbito (laboral, operativo o legal).",
            )

    def _build_signature_fields(self, parent):
        firmas_group = ttk.LabelFrame(parent, text="Investigador principal")
        firmas_group.pack(fill="x", expand=False, padx=COL_PADX, pady=ROW_PADY)
        firmas_group.columnconfigure(1, weight=1)

        ttk.Label(firmas_group, text="Matrícula/ID:").grid(
            row=0, column=0, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="e"
        )
        matricula_entry = ttk.Entry(
            firmas_group, textvariable=self.investigator_id_var, state="readonly"
        )
        matricula_entry.grid(row=0, column=1, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="we")
        self.register_tooltip(
            matricula_entry,
            "La matrícula se edita en la sección de Datos generales del caso y se refleja aquí automáticamente.",
        )

        ttk.Label(firmas_group, text="Nombre:").grid(
            row=1, column=0, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="e"
        )
        nombre_entry = ttk.Entry(
            firmas_group, textvariable=self.investigator_nombre_var, state="readonly"
        )
        nombre_entry.grid(row=1, column=1, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="we")
        self.register_tooltip(
            nombre_entry,
            "Nombre autocompletado desde team_details.csv al ingresar la matrícula del investigador.",
        )

        ttk.Label(firmas_group, text="Cargo:").grid(
            row=2, column=0, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="e"
        )
        cargo_entry = ttk.Entry(
            firmas_group, textvariable=self.investigator_cargo_var, state="readonly"
        )
        cargo_entry.grid(row=2, column=1, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="we")
        self.register_tooltip(cargo_entry, "Cargo fijo a mostrar en el reporte final.")

    def _build_operations_section(self, parent):
        operations_group = ttk.LabelFrame(parent, text="Tabla de operaciones")
        operations_group.pack(fill="both", expand=True, padx=COL_PADX, pady=ROW_PADY)
        operations_group.columnconfigure(0, weight=1)

        form = ttk.Frame(operations_group)
        form.grid(row=0, column=0, sticky="we", padx=COL_PADX, pady=ROW_PADY)
        for idx in range(6):
            form.columnconfigure(idx, weight=1)

        op_specs = [
            ("N°", "numero", 0, 0),
            ("Fecha aprobación (YYYY-MM-DD)", "fecha_aprobacion", 1, 0),
            ("Cliente/DNI", "cliente", 2, 0),
            ("Ingreso bruto mensual", "ingreso_bruto_mensual", 3, 0),
            ("Empresa empleadora", "empresa_empleadora", 4, 0),
            ("Vendedor inmueble", "vendedor_inmueble", 5, 0),
            ("Vendedor crédito", "vendedor_credito", 0, 1),
            ("Producto", "producto", 1, 1),
            ("Importe desembolsado", "importe_desembolsado", 2, 1),
            ("Saldo deudor", "saldo_deudor", 3, 1),
            ("Status BCP", "status_bcp", 4, 1),
            ("Status SBS", "status_sbs", 5, 1),
        ]
        for label, key, col, row in op_specs:
            ttk.Label(form, text=label).grid(
                row=row * 2,
                column=col,
                padx=COL_PADX,
                pady=(0, ROW_PADY // 2),
                sticky="w",
            )
            var = self._operation_vars.get(key) or tk.StringVar()
            self._operation_vars[key] = var
            entry = ttk.Entry(form, textvariable=var)
            entry.grid(row=row * 2 + 1, column=col, padx=COL_PADX, pady=(0, ROW_PADY), sticky="we")
            if key == "fecha_aprobacion":
                self._register_post_edit_validation(
                    entry,
                    lambda v=var: validate_date_text(v.get(), "La fecha de aprobación", allow_blank=True, enforce_max_today=True),
                    "Fecha de aprobación",
                )
            if key in {"importe_desembolsado", "saldo_deudor"}:
                self._register_post_edit_validation(
                    entry,
                    lambda v=var, label=label: validate_money_bounds(v.get(), label, allow_blank=True)[0],
                    label,
                )

        buttons = ttk.Frame(operations_group)
        buttons.grid(row=1, column=0, sticky="we", padx=COL_PADX, pady=(0, ROW_PADY))
        ttk.Button(buttons, text="Agregar/Actualizar operación", command=self._save_operation).pack(side="left", padx=(0, COL_PADX))
        ttk.Button(buttons, text="Eliminar operación", command=self._delete_operation).pack(side="left")
        ttk.Button(buttons, text="Limpiar formulario", command=self._clear_operation_form).pack(side="left", padx=(COL_PADX, 0))

        columns = [
            "numero",
            "fecha_aprobacion",
            "cliente",
            "ingreso_bruto_mensual",
            "empresa_empleadora",
            "vendedor_inmueble",
            "vendedor_credito",
            "producto",
            "importe_desembolsado",
            "saldo_deudor",
            "status_bcp",
            "status_sbs",
        ]
        self.operations_tree = ttk.Treeview(
            operations_group,
            columns=columns,
            show="headings",
            height=6,
        )
        for col in columns:
            self.operations_tree.heading(col, text=col.replace("_", " ").title())
            self.operations_tree.column(col, width=110, anchor="center")
        self.operations_tree.grid(row=2, column=0, sticky="nsew", padx=COL_PADX, pady=(0, ROW_PADY))
        operations_group.rowconfigure(2, weight=1)
        self.operations_tree.bind("<<TreeviewSelect>>", lambda _e: self._load_selected_operation())
        self._refresh_operations_tree()

    def _build_anexos_section(self, parent):
        anexos_group = ttk.LabelFrame(parent, text="Anexos y respaldos")
        anexos_group.pack(fill="both", expand=True, padx=COL_PADX, pady=ROW_PADY)
        anexos_group.columnconfigure(1, weight=1)
        anexos_group.columnconfigure(3, weight=1)

        ttk.Label(anexos_group, text="Título:").grid(row=0, column=0, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="e")
        titulo_var = self._anexo_vars.get("titulo") or tk.StringVar()
        self._anexo_vars["titulo"] = titulo_var
        titulo_entry = ttk.Entry(anexos_group, textvariable=titulo_var)
        titulo_entry.grid(row=0, column=1, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="we")
        titulo_var.trace_add("write", lambda *_args: self._notify_dataset_changed())

        ttk.Label(anexos_group, text="Descripción:").grid(row=0, column=2, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="e")
        desc_var = self._anexo_vars.get("descripcion") or tk.StringVar()
        self._anexo_vars["descripcion"] = desc_var
        desc_entry = ttk.Entry(anexos_group, textvariable=desc_var)
        desc_entry.grid(row=0, column=3, padx=COL_PADX, pady=(ROW_PADY // 2), sticky="we")
        desc_var.trace_add("write", lambda *_args: self._notify_dataset_changed())

        btns = ttk.Frame(anexos_group)
        btns.grid(row=1, column=0, columnspan=4, sticky="w", padx=COL_PADX, pady=(0, ROW_PADY))
        ttk.Button(btns, text="Agregar/Actualizar anexo", command=self._save_anexo).pack(side="left", padx=(0, COL_PADX))
        ttk.Button(btns, text="Eliminar anexo", command=self._delete_anexo).pack(side="left")
        ttk.Button(btns, text="Limpiar", command=self._clear_anexo_form).pack(side="left", padx=(COL_PADX, 0))

        self.anexos_tree = ttk.Treeview(
            anexos_group,
            columns=("titulo", "descripcion"),
            show="headings",
            height=5,
        )
        self.anexos_tree.heading("titulo", text="Título")
        self.anexos_tree.heading("descripcion", text="Descripción")
        self.anexos_tree.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=COL_PADX, pady=(0, ROW_PADY))
        anexos_group.rowconfigure(2, weight=1)
        self.anexos_tree.bind("<<TreeviewSelect>>", lambda _e: self._load_selected_anexo())
        self._refresh_anexos_tree()

    def _update_encabezado_value(self, key: str) -> None:
        if key not in self._encabezado_vars:
            return
        raw_value = self._encabezado_vars[key].get()
        if key == "centro_costos":
            value = self._sanitize_cost_centers_text(raw_value)
        else:
            value = self._sanitize_text(raw_value)
        self._encabezado_data[key] = value
        self._notify_dataset_changed()

    def _sanitize_cost_centers_text(self, raw_value: str) -> str:
        entries = [item.strip() for item in (raw_value or "").split(";") if item.strip()]
        return "; ".join(entries)

    def _validate_cost_centers(self, *, text: Optional[str] = None) -> Optional[str]:
        text = self._sanitize_cost_centers_text(
            text if text is not None else self._encabezado_vars.get("centro_costos", tk.StringVar()).get()
        )
        if not text:
            return None
        centers = [item for item in text.split(";") if item.strip()]
        for center in centers:
            trimmed = center.strip()
            if not trimmed.isdigit():
                return "Cada centro de costos debe ser numérico."
            if len(trimmed) < 5:
                return "Cada centro de costos debe tener al menos 5 dígitos."
        return None

    def _validate_reclamos_count(self) -> Optional[str]:
        value = (self._encabezado_vars.get("numero_reclamos") or tk.StringVar()).get().strip()
        if not value:
            return None
        if not value.isdigit():
            return "El número de reclamos debe ser numérico."
        return None

    def _update_recommendation_category(self, key: str, widget: scrolledtext.ScrolledText) -> None:
        raw_lines = widget.get("1.0", tk.END).splitlines()
        clean_lines = [line.strip() for line in raw_lines if line.strip()]
        self._recomendaciones_categorias[key] = clean_lines
        self._notify_dataset_changed()

    def _reset_investigator_fields(self) -> None:
        self._ensure_investigator_vars()
        self.investigator_id_var.set("")
        self.investigator_nombre_var.set("")
        self.investigator_cargo_var.set("Investigador Principal")

    def _autofill_investigator(self, *, show_errors: bool = False) -> None:
        self._ensure_investigator_vars()
        raw_id = self.investigator_id_var.get()
        normalized = self._normalize_identifier(raw_id)
        if raw_id != normalized:
            self.investigator_id_var.set(normalized)
        self.investigator_nombre_var.set("")
        self.investigator_cargo_var.set("Investigador Principal")
        if not normalized:
            self._notify_dataset_changed()
            return
        validation_error = validate_team_member_id(normalized)
        if validation_error:
            if show_errors and not getattr(self, "_suppress_messagebox", False):
                messagebox.showerror("ID de investigador inválido", validation_error)
            self._notify_dataset_changed()
            return
        lookup = self.team_lookup.get(normalized)
        if not lookup:
            if show_errors and not getattr(self, "_suppress_messagebox", False):
                messagebox.showerror(
                    "Investigador no encontrado",
                    "No se encontró la matrícula indicada en team_details.csv. Verifica el ID y vuelve a intentarlo.",
                )
            self._notify_dataset_changed()
            return
        composed_name = lookup.get("nombres_apellidos") or lookup.get("nombre_completo")
        if not composed_name:
            nombres = lookup.get("nombres") or lookup.get("nombre") or ""
            apellidos = lookup.get("apellidos") or ""
            composed_name = " ".join(part for part in [nombres, apellidos] if part).strip()
        self.investigator_nombre_var.set(composed_name)
        self._notify_dataset_changed()

    def _ensure_investigator_vars(self) -> None:
        if hasattr(self, "investigator_id_var"):
            return
        try:
            self.investigator_id_var = tk.StringVar()
            self.investigator_nombre_var = tk.StringVar()
            self.investigator_cargo_var = tk.StringVar(value="Investigador Principal")
        except (tk.TclError, RuntimeError):
            class _SimpleVar:
                def __init__(self, value=""):
                    self._value = value

                def set(self, value):
                    self._value = value

                def get(self):
                    return self._value

            self.investigator_id_var = _SimpleVar()
            self.investigator_nombre_var = _SimpleVar()
            self.investigator_cargo_var = _SimpleVar("Investigador Principal")

    def _ensure_case_vars(self) -> None:
        try:
            VarClass = tk.StringVar
        except (tk.TclError, RuntimeError):
            VarClass = None

        class _SimpleVar:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        def _create_var(value=""):
            if VarClass is None:
                return _SimpleVar(value)
            try:
                return VarClass(value=value)
            except Exception:
                return _SimpleVar(value)

        def _current_or_default(attr_name, default_value=""):
            var = getattr(self, attr_name, None)
            try:
                return var.get()
            except Exception:
                return default_value

        cat1_value = _current_or_default("cat_caso1_var", next(iter(TAXONOMIA), ""))
        cat2_candidates = list(TAXONOMIA.get(cat1_value, {}).keys())
        cat2_value = _current_or_default(
            "cat_caso2_var", cat2_candidates[0] if cat2_candidates else ""
        )
        modalidad_candidates = TAXONOMIA.get(cat1_value, {}).get(cat2_value, [])
        mod_value = _current_or_default(
            "mod_caso_var", modalidad_candidates[0] if modalidad_candidates else ""
        )

        self.id_caso_var = getattr(self, "id_caso_var", _create_var())
        self.tipo_informe_var = getattr(
            self, "tipo_informe_var", _create_var(TIPO_INFORME_LIST[0])
        )
        self.cat_caso1_var = getattr(self, "cat_caso1_var", _create_var(cat1_value))
        self.cat_caso2_var = getattr(self, "cat_caso2_var", _create_var(cat2_value))
        self.mod_caso_var = getattr(self, "mod_caso_var", _create_var(mod_value))
        self.canal_caso_var = getattr(
            self, "canal_caso_var", _create_var(_current_or_default("canal_caso_var", CANAL_LIST[0]))
        )
        self.proceso_caso_var = getattr(
            self,
            "proceso_caso_var",
            _create_var(_current_or_default("proceso_caso_var", PROCESO_LIST[0])),
        )
        self.fecha_caso_var = getattr(self, "fecha_caso_var", _create_var())
        self.fecha_descubrimiento_caso_var = getattr(
            self, "fecha_descubrimiento_caso_var", _create_var()
        )
        self.centro_costo_caso_var = getattr(self, "centro_costo_caso_var", _create_var())

    def _collect_operation_form(self) -> dict[str, str]:
        return {key: self._sanitize_text(var.get()) for key, var in self._operation_vars.items()}

    def _validate_operation_payload(self, payload: dict[str, str]) -> Optional[str]:
        if not any(payload.values()):
            return "Debe ingresar al menos un dato de la operación."
        date_error = validate_date_text(
            payload.get("fecha_aprobacion", ""),
            "La fecha de aprobación",
            allow_blank=True,
            enforce_max_today=True,
        )
        if date_error:
            return date_error
        for field in ("importe_desembolsado", "saldo_deudor"):
            message, _, normalized = validate_money_bounds(payload.get(field, ""), field.replace("_", " "), allow_blank=True)
            if message:
                return message
            payload[field] = normalized or payload.get(field, "")
        return None

    def _save_operation(self):
        payload = self._collect_operation_form()
        error = self._validate_operation_payload(payload)
        if error:
            if not getattr(self, "_suppress_messagebox", False):
                messagebox.showerror("Operación inválida", error)
            return
        selection = self.operations_tree.selection()
        if selection:
            index = int(self.operations_tree.index(selection[0]))
            self._operaciones_data[index] = payload
        else:
            self._operaciones_data.append(payload)
        self._refresh_operations_tree()
        self._clear_operation_form()
        self._notify_dataset_changed()

    def _delete_operation(self):
        selection = self.operations_tree.selection()
        if not selection:
            return
        index = int(self.operations_tree.index(selection[0]))
        self._operaciones_data.pop(index)
        self._refresh_operations_tree()
        self._clear_operation_form()
        self._notify_dataset_changed()

    def _clear_operation_form(self):
        for var in self._operation_vars.values():
            var.set("")
        if getattr(self, "operations_tree", None) and self.operations_tree.winfo_exists():
            self.operations_tree.selection_remove(self.operations_tree.selection())

    def _refresh_operations_tree(self):
        tree = getattr(self, "operations_tree", None)
        if not tree or not tree.winfo_exists():
            return
        for item in tree.get_children():
            tree.delete(item)
        for op in getattr(self, "_operaciones_data", []):
            values = [op.get(col, "") for col in tree["columns"]]
            self._insert_themed_row(tree, values)
        self._apply_treeview_theme(tree)

    def _load_selected_operation(self):
        selection = self.operations_tree.selection()
        if not selection:
            return
        index = int(self.operations_tree.index(selection[0]))
        payload = self._operaciones_data[index]
        self._suppress_post_edit_validation = True
        try:
            for key, var in self._operation_vars.items():
                var.set(payload.get(key, ""))
        finally:
            self._suppress_post_edit_validation = False

    def _save_anexo(self):
        titulo = self._sanitize_text(self._anexo_vars.get("titulo", tk.StringVar()).get())
        descripcion = self._sanitize_text(self._anexo_vars.get("descripcion", tk.StringVar()).get())
        if not any([titulo, descripcion]):
            if not getattr(self, "_suppress_messagebox", False):
                messagebox.showerror("Anexo vacío", "Completa el título o la descripción para guardar el anexo.")
            return
        payload = {"titulo": titulo, "descripcion": descripcion}
        selection = self.anexos_tree.selection()
        if selection:
            index = int(self.anexos_tree.index(selection[0]))
            self._anexos_data[index] = payload
        else:
            self._anexos_data.append(payload)
        self._refresh_anexos_tree()
        self._clear_anexo_form()
        self._notify_dataset_changed()

    def _delete_anexo(self):
        selection = self.anexos_tree.selection()
        if not selection:
            return
        index = int(self.anexos_tree.index(selection[0]))
        self._anexos_data.pop(index)
        self._refresh_anexos_tree()
        self._clear_anexo_form()
        self._notify_dataset_changed()

    def _clear_anexo_form(self):
        for var in self._anexo_vars.values():
            var.set("")
        if getattr(self, "anexos_tree", None) and self.anexos_tree.winfo_exists():
            self.anexos_tree.selection_remove(self.anexos_tree.selection())

    def _refresh_anexos_tree(self):
        tree = getattr(self, "anexos_tree", None)
        if not tree or not tree.winfo_exists():
            return
        for item in tree.get_children():
            tree.delete(item)
        for row in getattr(self, "_anexos_data", []):
            self._insert_themed_row(tree, (row.get("titulo", ""), row.get("descripcion", "")))
        self._apply_treeview_theme(tree)

    def _load_selected_anexo(self):
        selection = self.anexos_tree.selection()
        if not selection:
            return
        index = int(self.anexos_tree.index(selection[0]))
        payload = self._anexos_data[index]
        self._suppress_post_edit_validation = True
        try:
            self._anexo_vars["titulo"].set(payload.get("titulo", ""))
            self._anexo_vars["descripcion"].set(payload.get("descripcion", ""))
        finally:
            self._suppress_post_edit_validation = False

    def _sync_extended_sections_to_ui(self) -> None:
        if not (self._extended_sections_enabled and self._extended_analysis_group):
            return
        self._suppress_post_edit_validation = True
        try:
            for key, var in getattr(self, "_encabezado_vars", {}).items():
                var.set(self._encabezado_data.get(key, ""))
            self._refresh_operations_tree()
            self._refresh_anexos_tree()
            for key, widget in getattr(self, "_recommendation_widgets", {}).items():
                try:
                    widget.delete("1.0", tk.END)
                    widget.insert("1.0", "\n".join(self._recomendaciones_categorias.get(key, [])))
                except tk.TclError:
                    continue
        finally:
            self._suppress_post_edit_validation = False

    def _get_rich_text_fonts(self):
        if self._rich_text_fonts:
            return (
                self._rich_text_fonts["bold"],
                self._rich_text_fonts["header"],
                self._rich_text_fonts["mono"],
            )

        base_font = tkfont.nametofont("TkDefaultFont")
        bold_font = base_font.copy()
        bold_font.configure(weight="bold")

        header_font = tkfont.nametofont("TkHeadingFont").copy()
        header_font.configure(weight="bold", size=max(header_font.cget("size"), 12))

        mono_font = tkfont.nametofont("TkFixedFont").copy()

        self._rich_text_fonts = {
            "bold": bold_font,
            "header": header_font,
            "mono": mono_font,
        }
        return bold_font, header_font, mono_font

    def _configure_rich_text_tags(self, widget, bold_font, header_font, mono_font):
        widget.tag_configure("bold", font=bold_font)
        widget.tag_configure("header", font=header_font)
        widget.tag_configure("table", font=mono_font)
        widget.tag_configure("list", lmargin1=20, lmargin2=30)

    def _add_rich_text_toolbar(self, toolbar, text_widget):
        ttk.Button(
            toolbar,
            text="Negrita",
            command=lambda w=text_widget: self._apply_text_tag(w, "bold"),
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            toolbar,
            text="Encabezado",
            command=lambda w=text_widget: self._apply_text_tag(w, "header"),
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            toolbar,
            text="Lista",
            command=lambda w=text_widget: self._apply_text_tag(w, "list"),
        ).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(
            toolbar,
            text="Tabla",
            command=lambda w=text_widget: self._insert_table_template(w),
        ).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(
            toolbar,
            text="Imagen",
            command=lambda w=text_widget: self._insert_image(w),
        ).grid(row=0, column=4, padx=(0, 6))
        ttk.Button(
            toolbar,
            text="Pegar imagen",
            command=lambda w=text_widget: self._insert_clipboard_image(w),
        ).grid(row=0, column=5, padx=(0, 6))

        tips = [
            "Aplica formato en negrita al texto seleccionado.",
            "Resalta la línea actual como encabezado.",
            "Agrega viñetas o números a la selección o línea actual.",
            "Inserta una tabla de texto preformateada.",
            (
                f"Agrega una imagen desde un archivo compatible (PNG, GIF, PPM, PGM), "
                f"máximo {self.IMAGE_MAX_BYTES // (1024 * 1024)} MB y {self.IMAGE_MAX_DIMENSION}px."
                " Las imágenes se previsualizan reducidas."
            ),
            "Pega una imagen disponible en el portapapeles.",
        ]
        for idx, tip in enumerate(tips):
            child = toolbar.grid_slaves(row=0, column=idx)
            if child:
                self.register_tooltip(child[0], tip)

    def _apply_text_tag(self, text_widget, tag_name):
        if not getattr(self, "_startup_complete", True):
            return

        bold_font, header_font, mono_font = self._get_rich_text_fonts()
        self._configure_rich_text_tags(text_widget, bold_font, header_font, mono_font)

        insert_index = text_widget.index("insert")
        try:
            start = text_widget.index("sel.first")
            end = text_widget.index("sel.last")
        except tk.TclError:
            start = text_widget.index("insert linestart")
            end = text_widget.index("insert lineend")

        if text_widget.compare(start, "==", end):
            if not getattr(self, "_suppress_messagebox", False):
                try:
                    messagebox.showinfo(
                        "Selecciona texto",
                        "Selecciona un fragmento de texto para aplicar formato.",
                    )
                except tk.TclError:
                    pass
            return

        tag_ranges = text_widget.tag_ranges(tag_name)
        paired_ranges = list(zip(tag_ranges[0::2], tag_ranges[1::2]))
        toggle_off = any(
            text_widget.compare(start, ">=", r_start)
            and text_widget.compare(end, "<=", r_end)
            for r_start, r_end in paired_ranges
        )

        text_widget.edit_separator()
        if toggle_off:
            text_widget.tag_remove(tag_name, start, end)
        else:
            text_widget.tag_add(tag_name, start, end)

        text_widget.mark_set("insert", insert_index)
        text_widget.focus_set()
        self._mark_rich_text_modified(text_widget)

    def _insert_table_template(self, text_widget):
        table_template = (
            "\n| Columna 1 | Columna 2 | Columna 3 |\n"
            "|-----------|-----------|-----------|\n"
            "| Dato 1    | Dato 2    | Dato 3    |\n"
        )
        insertion_point = text_widget.index("insert")
        text_widget.insert(insertion_point, table_template)
        text_widget.tag_add("table", insertion_point, f"{insertion_point} + {len(table_template)} chars")
        text_widget.focus_set()
        self._mark_rich_text_modified(text_widget)

    def _handle_rich_text_paste(self, event):
        widget = event.widget
        if not isinstance(widget, tk.Text):
            return None
        photo, source = self._get_clipboard_photo()
        if photo is None:
            return None
        self._record_rich_text_image(widget, photo, source)
        self._mark_rich_text_modified(widget)
        return "break"

    def _validate_image_extension(self, ext: str) -> bool:
        allowed_exts = {".png", ".gif", ".ppm", ".pgm"}
        if ext not in allowed_exts:
            messagebox.showerror(
                "Formato no soportado", "Solo se permiten archivos PNG, GIF, PPM o PGM."
            )
            log_event(
                "validacion",
                f"Formato de imagen no permitido: {ext}",
                self.logs,
            )
            return False
        return True

    def _validate_image_size(self, byte_size: int) -> bool:
        if byte_size <= self.IMAGE_MAX_BYTES:
            return True
        limit_mb = self.IMAGE_MAX_BYTES // (1024 * 1024)
        message = f"El archivo supera el límite de {limit_mb} MB permitido para imágenes."
        messagebox.showerror("Imagen demasiado grande", message)
        log_event(
            "validacion",
            f"Imagen rechazada por exceder {self.IMAGE_MAX_BYTES} bytes (tamaño: {byte_size}).",
            self.logs,
        )
        return False

    def _validate_image_dimensions(self, dimensions: Optional[tuple[int, int]]) -> bool:
        if not dimensions:
            messagebox.showerror(
                "Imagen inválida", "No se pudieron leer las dimensiones de la imagen seleccionada."
            )
            log_event("validacion", "Dimensiones de imagen no legibles.", self.logs)
            return False
        width, height = dimensions
        if width > self.IMAGE_MAX_DIMENSION or height > self.IMAGE_MAX_DIMENSION:
            messagebox.showerror(
                "Imagen demasiado grande",
                (
                    f"Las dimensiones {width}x{height} px superan el máximo permitido de "
                    f"{self.IMAGE_MAX_DIMENSION}px por lado."
                ),
            )
            log_event(
                "validacion",
                (
                    f"Dimensiones de imagen excedidas: {width}x{height} (máximo "
                    f"{self.IMAGE_MAX_DIMENSION})."
                ),
                self.logs,
            )
            return False
        return True

    def _probe_image_dimensions_from_bytes(self, data: bytes, ext: str) -> Optional[tuple[int, int]]:
        if Image is not None:
            try:
                with Image.open(io.BytesIO(data)) as img:
                    return img.width, img.height
            except Exception:
                pass
        try:
            if ext == ".png" and len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
                return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
            if ext == ".gif" and len(data) >= 10 and data[:6] in {b"GIF87a", b"GIF89a"}:
                return int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little")
            if ext in {".pgm", ".ppm"}:
                header = data[:1024].decode("ascii", errors="ignore")
                tokens = []
                for line in header.splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    tokens.extend(stripped.split())
                    if len(tokens) >= 3:
                        break
                if tokens and tokens[0] in {"P2", "P3", "P5", "P6"} and len(tokens) >= 3:
                    return int(tokens[1]), int(tokens[2])
        except (OSError, ValueError):
            return None
        return None

    def _validate_image_file(self, image_path: Path) -> tuple[Optional[tuple[int, int]], Optional[str]]:
        ext = image_path.suffix.lower()
        if not self._validate_image_extension(ext):
            return None, f"extensión no soportada ({ext})"
        try:
            file_size = image_path.stat().st_size
        except OSError as exc:  # pragma: no cover - depende del sistema de archivos
            messagebox.showerror("Imagen inválida", f"No se pudo leer el archivo: {exc}")
            log_event("validacion", f"No se pudo leer la imagen: {exc}", self.logs)
            return None, f"error al obtener tamaño ({exc})"
        if not self._validate_image_size(file_size):
            return None, f"tamaño excedido ({file_size} bytes)"
        dimensions = self._probe_image_dimensions(image_path, ext)
        if not self._validate_image_dimensions(dimensions):
            if not dimensions:
                return None, "dimensiones no legibles"
            width, height = dimensions
            return None, f"dimensiones excedidas ({width}x{height})"
        return dimensions, None

    def _get_clipboard_photo(self):
        format_extensions = {
            "image/png": ".png",
            "png": ".png",
            "image/gif": ".gif",
            "gif": ".gif",
            "image/ppm": ".ppm",
            "ppm": ".ppm",
            "image/pgm": ".pgm",
            "pgm": ".pgm",
        }
        formats = (
            "image/png",
            "PNG",
            "image/gif",
            "GIF",
            "image/ppm",
            "PPM",
            "image/pgm",
            "PGM",
        )
        for fmt in formats:
            with suppress(tk.TclError):
                data = self.root.clipboard_get(type=fmt)
                ext = format_extensions.get(fmt.lower())
                photo, stored_data = self._create_photo_from_data(data, ext)
                if photo is not None:
                    return photo, {"data": stored_data or data, "format": fmt}

        with suppress(tk.TclError):
            text_data = self.root.clipboard_get()
            if text_data:
                path = Path(text_data.strip())
                if path.exists():
                    dimensions, rejection_reason = self._validate_image_file(path)
                    if rejection_reason:
                        log_event(
                            "validacion",
                            f"Imagen del portapapeles rechazada ({rejection_reason}) en {path}",
                            self.logs,
                        )
                    if not dimensions:
                        return None, None
                    width, height = dimensions
                    try:
                        photo = self._load_photo_image(path, width, height)
                        return photo, str(path)
                    except Exception as exc:  # pragma: no cover - fallos dependen del archivo del usuario
                        messagebox.showerror("Imagen inválida", f"No se pudo cargar la imagen: {exc}")
                        log_event("validacion", f"No se pudo cargar imagen del portapapeles: {exc}", self.logs)
                        return None, None
        return None, None

    def _create_photo_from_data(self, data, ext: Optional[str] = None):
        if data is None:
            return None, None
        if ext and not self._validate_image_extension(ext):
            return None, None
        raw_bytes: Optional[bytes] = None
        if isinstance(data, bytes):
            raw_bytes = data
        elif isinstance(data, str):
            try:
                raw_bytes = data.encode("latin1")
            except UnicodeEncodeError:
                raw_bytes = data.encode("utf-8", errors="ignore")
        if raw_bytes is not None and not self._validate_image_size(len(raw_bytes)):
            return None, None
        if ext and raw_bytes is not None:
            dimensions = self._probe_image_dimensions_from_bytes(raw_bytes, ext)
            if not self._validate_image_dimensions(dimensions):
                return None, None
        attempts = []
        if isinstance(data, bytes):
            attempts.append(base64.b64encode(data).decode("ascii"))
        if isinstance(data, str):
            attempts.append(data)
            if raw_bytes is not None:
                attempts.append(base64.b64encode(raw_bytes).decode("ascii"))
        for payload in attempts:
            try:
                photo = tk.PhotoImage(data=payload)
                return photo, payload
            except tk.TclError:
                continue
        log_event("validacion", "No se pudo crear imagen desde el portapapeles.", self.logs)
        return None, None

    def _probe_image_dimensions(self, path: Path, ext: str) -> Optional[tuple[int, int]]:
        if Image is not None:
            try:
                with Image.open(path) as img:
                    return img.width, img.height
            except Exception:
                pass
        try:
            with path.open("rb") as file_handle:
                if ext == ".png":
                    header = file_handle.read(24)
                    if len(header) >= 24 and header.startswith(b"\x89PNG\r\n\x1a\n"):
                        return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")
                elif ext == ".gif":
                    header = file_handle.read(10)
                    if len(header) >= 10 and header[:6] in {b"GIF87a", b"GIF89a"}:
                        return int.from_bytes(header[6:8], "little"), int.from_bytes(header[8:10], "little")
                elif ext in {".pgm", ".ppm"}:
                    header = file_handle.read(1024).decode("ascii", errors="ignore")
                    tokens = []
                    for line in header.splitlines():
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            continue
                        tokens.extend(stripped.split())
                        if len(tokens) >= 3:
                            break
                    if tokens and tokens[0] in {"P2", "P3", "P5", "P6"} and len(tokens) >= 3:
                        return int(tokens[1]), int(tokens[2])
        except (OSError, ValueError):
            return None
        return None

    def _load_photo_image(self, path: Path, width: int, height: int):
        if Image is not None and ImageTk is not None:
            with Image.open(path) as img:
                if width > self.IMAGE_DISPLAY_MAX or height > self.IMAGE_DISPLAY_MAX:
                    img.thumbnail((self.IMAGE_DISPLAY_MAX, self.IMAGE_DISPLAY_MAX))
                return ImageTk.PhotoImage(img)
        photo = tk.PhotoImage(file=path)
        if width > self.IMAGE_DISPLAY_MAX or height > self.IMAGE_DISPLAY_MAX:
            factor = max(
                1,
                math.ceil(width / self.IMAGE_DISPLAY_MAX),
                math.ceil(height / self.IMAGE_DISPLAY_MAX),
            )
            photo = photo.subsample(factor, factor)
        return photo

    def _cleanup_failed_image_insertion(self, widget: tk.Text, photo: Optional[tk.PhotoImage]):
        if photo is None:
            return
        image_name = str(photo)
        self._rich_text_image_sources.pop(image_name, None)
        images = self._rich_text_images.get(widget)
        if images and photo in images:
            with suppress(ValueError):
                images.remove(photo)

    def _insert_clipboard_image(self, text_widget):
        photo, source = self._get_clipboard_photo()
        if photo is None:
            messagebox.showinfo(
                "Sin imagen",
                "El portapapeles no contiene una imagen compatible (PNG, GIF, PPM o PGM).",
            )
            return
        self._record_rich_text_image(text_widget, photo, source)
        self._mark_rich_text_modified(text_widget)

    def _insert_image(self, text_widget):
        filetypes = [("Imágenes PNG, GIF, PPM o PGM", "*.png *.gif *.ppm *.pgm")]
        filepath = filedialog.askopenfilename(title="Selecciona una imagen", filetypes=filetypes)
        if not filepath:
            return
        image_path = Path(filepath)
        dimensions, rejection_reason = self._validate_image_file(image_path)
        if rejection_reason:
            log_event(
                "validacion",
                f"Imagen rechazada ({rejection_reason}) en {image_path}",
                self.logs,
            )
        if not dimensions:
            return
        width, height = dimensions
        photo: Optional[tk.PhotoImage] = None
        try:
            photo = self._load_photo_image(image_path, width, height)
            self._record_rich_text_image(text_widget, photo, str(image_path))
        except Exception as exc:  # pragma: no cover - fallos dependen del archivo del usuario
            self._cleanup_failed_image_insertion(text_widget, photo)
            messagebox.showerror("Imagen inválida", f"No se pudo cargar la imagen: {exc}")
            log_event("validacion", f"Error al cargar imagen {image_path}: {exc}", self.logs)
            return
        self._mark_rich_text_modified(text_widget)

    def build_actions_tab(self, parent):
        PRIMARY_PADDING = (12, 6)
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=0)

        scrollable_tab, inner_frame = create_scrollable_container(
            parent, scroll_binder=self._scroll_binder, tab_id=parent
        )
        scrollable_tab.grid(row=0, column=0, sticky="nsew", padx=COL_PADX, pady=ROW_PADY)
        self._register_scrollable(scrollable_tab)
        inner_frame.columnconfigure(0, weight=1)
        inner_frame.columnconfigure(1, weight=1)
        inner_frame.rowconfigure(1, weight=1)

        header_frame = ttk.Frame(inner_frame)
        header_frame.grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=COL_PADX, pady=(0, ROW_PADY)
        )
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=0)
        header_frame.columnconfigure(2, weight=0)

        ttk.Frame(header_frame).grid(row=0, column=0, sticky="ew")
        sound_toggle = ttk.Checkbutton(
            header_frame,
            text="Sonido de confirmación",
            variable=self.sound_enabled_var,
            command=self._update_sound_preference,
            style=ThemeManager.CHECKBUTTON_STYLE,
        )
        sound_toggle.grid(row=0, column=1, sticky="ne", padx=(0, 6))
        self.register_tooltip(
            sound_toggle,
            "Reproduce un tono breve tras validaciones exitosas, altas y exportaciones.",
        )
        self.theme_toggle_button = ttk.Button(
            header_frame,
            textvariable=self.theme_toggle_text,
            command=self._toggle_theme,
            padding=PRIMARY_PADDING,
        )
        self.theme_toggle_button.grid(row=0, column=2, sticky="ne")

        catalog_group = ttk.LabelFrame(inner_frame, text="Catálogos de detalle")
        catalog_group.grid(row=1, column=0, sticky="nsew", padx=COL_PADX, pady=ROW_PADY)
        catalog_group.columnconfigure(0, weight=1)
        catalog_group.columnconfigure(1, weight=1)

        ttk.Label(
            catalog_group,
            textvariable=self.catalog_status_var,
            wraplength=420,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=COL_PADX, pady=(ROW_PADY, ROW_PADY // 2))

        self.catalog_load_button = ttk.Button(
            catalog_group,
            text="Cargar catálogos",
            command=self.request_catalog_loading,
            padding=PRIMARY_PADDING,
        )
        self.catalog_load_button.grid(row=1, column=0, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        ttk.Label(
            catalog_group,
            text="Actualiza los catálogos para validar listas desplegables antes de importar datos.",
            wraplength=320,
            justify="left",
        ).grid(row=1, column=1, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        self.register_tooltip(
            self.catalog_load_button,
            "Descarga y sincroniza los catálogos requeridos para las validaciones.",
        )

        self.catalog_skip_button = ttk.Button(
            catalog_group,
            text="Iniciar sin catálogos",
            command=self._mark_catalogs_skipped,
        )
        self.catalog_skip_button.grid(row=2, column=0, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        ttk.Label(
            catalog_group,
            text="Permite avanzar sin catálogos; usar sólo si ya se cuenta con datos validados.",
            wraplength=320,
            justify="left",
        ).grid(row=2, column=1, sticky="w", padx=COL_PADX, pady=ROW_PADY)

        self.catalog_progress = ttk.Progressbar(catalog_group, mode="indeterminate", length=160)
        self.catalog_progress.grid(row=3, column=0, columnspan=2, sticky="we", padx=COL_PADX, pady=(0, ROW_PADY))
        self.catalog_progress.grid_remove()
        self._catalog_progress_visible = False

        import_group = ttk.LabelFrame(inner_frame, text="Importar datos masivos (CSV)")
        import_group.grid(row=1, column=1, sticky="nsew", padx=COL_PADX, pady=ROW_PADY)
        import_group.columnconfigure(0, weight=0)
        import_group.columnconfigure(1, weight=1)
        self.import_group_frame = import_group

        btn_clientes = ttk.Button(import_group, text="Cargar clientes", command=self.import_clients)
        btn_clientes.grid(row=0, column=0, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        ttk.Label(
            import_group,
            text="Carga un lote de clientes para acelerar el registro masivo.",
            wraplength=360,
            justify="left",
        ).grid(row=0, column=1, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        self.register_tooltip(btn_clientes, "Importa clientes desde un CSV masivo.")
        if getattr(self, "_import_anchor_widget", None) is None:
            self._import_anchor_widget = btn_clientes

        btn_colabs = ttk.Button(import_group, text="Cargar colaboradores", command=self.import_team_members)
        btn_colabs.grid(row=1, column=0, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        ttk.Label(
            import_group,
            text="Incorpora colaboradores y sus datos laborales para vincularlos al caso.",
            wraplength=360,
            justify="left",
        ).grid(row=1, column=1, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        self.register_tooltip(btn_colabs, "Importa colaboradores y sus datos laborales.")

        btn_productos = ttk.Button(import_group, text="Cargar productos", command=self.import_products)
        btn_productos.grid(row=2, column=0, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        ttk.Label(
            import_group,
            text="Agrega productos investigados con sus atributos validados.",
            wraplength=360,
            justify="left",
        ).grid(row=2, column=1, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        self.register_tooltip(btn_productos, "Carga productos investigados desde un CSV.")

        btn_combo = ttk.Button(
            import_group,
            text="Cargar combinado",
            command=self.import_combined,
            padding=PRIMARY_PADDING,
        )
        btn_combo.grid(row=3, column=0, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        ttk.Label(
            import_group,
            text="Importa en un solo paso clientes, productos y colaboradores para iniciar rápido.",
            wraplength=360,
            justify="left",
        ).grid(row=3, column=1, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        self.register_tooltip(btn_combo, "Importa en un solo archivo clientes, productos y colaboradores.")

        btn_riesgos = ttk.Button(import_group, text="Cargar riesgos", command=self.import_risks)
        btn_riesgos.grid(row=4, column=0, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        ttk.Label(
            import_group,
            text="Sincroniza la matriz de riesgos para alimentar la evaluación del caso.",
            wraplength=360,
            justify="left",
        ).grid(row=4, column=1, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        self.register_tooltip(btn_riesgos, "Carga la matriz de riesgos desde CSV.")

        btn_normas = ttk.Button(import_group, text="Cargar normas", command=self.import_norms)
        btn_normas.grid(row=5, column=0, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        ttk.Label(
            import_group,
            text="Añade las normas vulneradas para documentar las transgresiones.",
            wraplength=360,
            justify="left",
        ).grid(row=5, column=1, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        self.register_tooltip(btn_normas, "Importa las normas vulneradas.")

        btn_reclamos = ttk.Button(import_group, text="Cargar reclamos", command=self.import_claims)
        btn_reclamos.grid(row=6, column=0, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        ttk.Label(
            import_group,
            text="Vincula reclamos de clientes con los productos afectados.",
            wraplength=360,
            justify="left",
        ).grid(row=6, column=1, sticky="w", padx=COL_PADX, pady=ROW_PADY)
        self.register_tooltip(btn_reclamos, "Vincula reclamos con los productos.")

        self.import_clients_button = btn_clientes
        self.import_team_button = btn_colabs
        self.import_products_button = btn_productos
        self.import_combined_button = btn_combo
        self.import_risks_button = btn_riesgos
        self.import_norms_button = btn_normas
        self.import_claims_button = btn_reclamos
        for widget in (
            btn_clientes,
            btn_colabs,
            btn_productos,
            btn_combo,
            btn_riesgos,
            btn_normas,
            btn_reclamos,
        ):
            self._register_catalog_dependent_widget(widget)

        ttk.Label(
            import_group,
            textvariable=self.import_status_var,
            wraplength=520,
            justify="left",
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=COL_PADX, pady=(ROW_PADY // 2, 0))
        self.import_progress = ttk.Progressbar(import_group, mode="indeterminate", length=260)
        self.import_progress.grid(row=8, column=0, columnspan=2, sticky="we", padx=COL_PADX, pady=(0, ROW_PADY))
        self.import_progress.grid_remove()
        self._import_progress_visible = False

        action_group = ttk.LabelFrame(parent, text="Guardar, cargar y reportes")
        action_group.grid(row=1, column=0, sticky="we", padx=COL_PADX, pady=(0, ROW_PADY))
        action_group.columnconfigure(0, weight=1)

        ttk.Label(
            action_group,
            text=(
                "Ejecuta las acciones principales de guardado, carga y exportación. "
                "Estas opciones se mantienen visibles aunque el resto del contenido se desplace."
            ),
            wraplength=520,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=COL_PADX, pady=(ROW_PADY, ROW_PADY // 2))

        action_buttons = (
            ("Guardar y enviar", "save_send"),
            ("Cargar versión", "load"),
            ("Borrar todos los datos", "clear"),
            (None, None),
            ("Generar Word (.docx)", "docx"),
            ("Generar informe (.md)", "md"),
        )
        action_commands = {
            "save_send": self.save_and_send,
            "load": self.load_version_dialog,
            "clear": lambda: self.clear_all(notify=True),
            "docx": self.generate_docx_report,
            "md": self.generate_md_report,
        }
        action_bar_parent = ttk.Frame(action_group)
        action_bar_parent.grid(row=1, column=0, sticky="ew", padx=COL_PADX)
        self.actions_action_bar = ActionBar(
            action_bar_parent,
            commands=action_commands,
            buttons=action_buttons,
        )
        self._actions_bar_anchor = (
            self.actions_action_bar.buttons.get("save_send")
            or self.actions_action_bar.buttons.get("docx")
            or self.actions_action_bar
        )
        self.register_tooltip(
            self.actions_action_bar.buttons.get("save_send"),
            "Valida el formulario, previene duplicados y genera los archivos obligatorios.",
        )
        self.register_tooltip(
            self.actions_action_bar.buttons.get("load"),
            "Restaura una versión previa en formato JSON.",
        )
        self.register_tooltip(
            self.actions_action_bar.buttons.get("clear"),
            "Limpia el formulario completo para iniciar desde cero.",
        )

        self.btn_docx = self.actions_action_bar.buttons.get("docx")
        docx_tooltip = (
            "Genera el informe principal en Word utilizando los datos validados."
            if self._docx_available
            else f"{DOCX_MISSING_MESSAGE} Usa el informe Markdown como respaldo."
        )
        if self.btn_docx:
            try:
                self.btn_docx.state(["!disabled"] if self._docx_available else ["disabled"])
            except tk.TclError:
                pass
            self.register_tooltip(self.btn_docx, docx_tooltip)

        md_button = self.actions_action_bar.buttons.get("md")
        self.register_tooltip(
            md_button,
            "Crea una copia del informe en Markdown como respaldo manual.",
        )
        if getattr(self, "_export_anchor_widget", None) is None:
            self._export_anchor_widget = (
                self.actions_action_bar.buttons.get("export")
                or self.btn_docx
                or md_button
                or self.actions_action_bar
            )
        if md_button is not None and self._actions_bar_anchor is None:
            self._actions_bar_anchor = md_button

        if not self._docx_available:
            ttk.Label(
                action_group,
                text=(
                    "El botón de Word está deshabilitado porque falta la "
                    "dependencia opcional. Usa 'pip install python-docx' o "
                    "genera sólo el informe Markdown."
                ),
                foreground="#b26a00",
                wraplength=520,
                justify="left",
            ).grid(row=2, column=0, sticky="w", padx=COL_PADX, pady=(ROW_PADY // 2, 0))

        ttk.Label(
            action_group,
            text="El auto‑guardado se realiza automáticamente en un archivo JSON",
            wraplength=520,
            justify="left",
        ).grid(row=3, column=0, sticky="w", padx=COL_PADX, pady=(ROW_PADY, 0))
        self._set_catalog_dependent_state(self._catalog_loading or self._active_import_jobs > 0)

    def _toggle_theme(self):
        palette = ThemeManager.toggle()
        self._reapply_treeview_styles()
        widget_name = None
        widget = getattr(self, "theme_toggle_button", None)
        if widget is not None:
            try:
                widget_name = widget.winfo_name() or "theme_toggle_button"
            except tk.TclError:
                widget_name = "theme_toggle_button"
        message = f"Cambio de tema a {palette['name']}"
        if widget_name:
            message = f"{message} (boton={widget_name})"
        log_event("navegacion", message, self.logs)
        self._update_theme_toggle_label(palette)
        self._safe_update_idletasks()

    def _update_theme_toggle_label(self, palette=None):
        active_theme = palette or ThemeManager.current()
        if active_theme.get("name") == "dark":
            label = "☀️ Light Mode"
        else:
            label = "🌙 Dark Mode"
        self.theme_toggle_text.set(label)

    def _register_catalog_dependent_widget(self, widget):
        if widget is None:
            return
        self._catalog_dependent_widgets.append(widget)
        if self._catalog_loading:
            try:
                widget.state(['disabled'])
            except tk.TclError:
                pass

    def _set_catalog_dependent_state(self, disabled):
        for widget in self._catalog_dependent_widgets:
            if widget is None:
                continue
            try:
                if disabled:
                    widget.state(['disabled'])
                else:
                    widget.state(['!disabled'])
            except tk.TclError:
                continue

    def _show_catalog_progress(self):
        if not self.catalog_progress:
            return
        if not self._catalog_progress_visible:
            self.catalog_progress.grid()
            self._catalog_progress_visible = True
        try:
            self.catalog_progress.start(10)
        except tk.TclError:
            pass

    def _hide_catalog_progress(self):
        if not self.catalog_progress:
            return
        try:
            self.catalog_progress.stop()
        except tk.TclError:
            pass
        if self._catalog_progress_visible:
            self.catalog_progress.grid_remove()
            self._catalog_progress_visible = False

    def _prompt_initial_catalog_loading(self):
        if self._catalog_prompted or self._catalog_loading or self._catalog_ready:
            return
        self._catalog_prompted = True
        try:
            should_load = messagebox.askyesno(
                "Catálogos de detalle",
                (
                    "El formulario puede autopoblar clientes, productos y colaboradores "
                    "si cargas los catálogos de detalle. ¿Deseas cargarlos ahora?"
                ),
                parent=self.root,
            )
        except tk.TclError:
            should_load = True
        if should_load:
            self.request_catalog_loading()
        else:
            self._mark_catalogs_skipped()

    def _mark_catalogs_skipped(self):
        if self._catalog_loading:
            return
        self._catalog_prompted = True
        self._catalog_ready = False
        self.catalog_status_var.set(
            "Trabajarás sin catálogos. Puedes cargarlos más adelante desde la pestaña Acciones."
        )
        self._set_catalog_dependent_state(False)

    def request_catalog_loading(self):
        if self._catalog_loading:
            return
        self._catalog_prompted = True
        self._catalog_loading = True
        self._catalog_ready = False
        self.catalog_status_var.set(
            "Cargando catálogos de detalle. Este proceso puede tardar algunos segundos..."
        )
        self._show_catalog_progress()
        self._set_catalog_dependent_state(True)
        for button in (self.catalog_load_button, self.catalog_skip_button):
            if button is None:
                continue
            try:
                button.state(['disabled'])
            except tk.TclError:
                pass
        self._catalog_loading_thread = threading.Thread(
            target=self._load_catalogs_in_background,
            daemon=True,
            name="catalog-loader",
        )
        self._catalog_loading_thread.start()

    def _load_catalogs_in_background(self):
        try:
            detail_catalogs, detail_lookup_by_id = self.catalog_service.refresh()
        except Exception as exc:  # pragma: no cover - errores inusuales de IO
            self._dispatch_to_ui(self._handle_catalog_load_failure, exc)
            return
        self._dispatch_to_ui(self._handle_catalog_load_success, detail_catalogs, detail_lookup_by_id)

    def _dispatch_to_ui(self, callback, *args, **kwargs):
        if getattr(self, 'root', None) is None:
            return
        try:
            self.root.after(0, lambda: callback(*args, **kwargs))
        except tk.TclError:
            pass

    def _handle_catalog_load_success(self, detail_catalogs, detail_lookup_by_id):
        self._catalog_ready = True
        self._apply_catalog_lookups(detail_catalogs, detail_lookup_by_id)
        if detail_lookup_by_id:
            self.catalog_status_var.set(
                "Catálogos de detalle cargados. El autopoblado e importación están habilitados."
            )
        else:
            self.catalog_status_var.set(
                "No se encontraron catálogos de detalle. Puedes seguir trabajando manualmente."
            )
        self._finalize_catalog_loading_state()

    def _handle_catalog_load_failure(self, error):
        self._catalog_ready = False
        self.catalog_status_var.set(
            "No se pudieron cargar los catálogos. Intenta nuevamente desde 'Cargar catálogos'."
        )
        self._finalize_catalog_loading_state(failed=True)
        try:
            messagebox.showerror(
                "Catálogos de detalle",
                f"No se pudieron cargar los catálogos: {error}",
            )
        except tk.TclError:
            pass

    def _finalize_catalog_loading_state(self, failed=False):
        self._ensure_import_runtime_state()
        self._catalog_loading = False
        self._hide_catalog_progress()
        self._set_catalog_dependent_state(self._active_import_jobs > 0)
        self._catalog_loading_thread = None
        target_text = "Recargar catálogos" if not failed else "Reintentar carga"
        if self.catalog_load_button is not None:
            try:
                self.catalog_load_button.config(text=target_text)
                self.catalog_load_button.state(['!disabled'])
            except tk.TclError:
                pass
        if self.catalog_skip_button is not None:
            try:
                self.catalog_skip_button.state(['!disabled'])
            except tk.TclError:
                pass

    def _ensure_import_runtime_state(self):
        if not hasattr(self, '_active_import_jobs'):
            self._active_import_jobs = 0
        if not hasattr(self, '_import_progress_visible'):
            self._import_progress_visible = False
        if not hasattr(self, 'import_progress'):
            self.import_progress = None
        if not hasattr(self, 'import_status_var'):
            self.import_status_var = None
        if not hasattr(self, '_catalog_loading'):
            self._catalog_loading = False
        if not hasattr(self, '_catalog_dependent_widgets'):
            self._catalog_dependent_widgets = []

    def _show_import_progress(self):
        self._ensure_import_runtime_state()
        if not self.import_progress:
            return
        if not self._import_progress_visible:
            self.import_progress.grid()
            self._import_progress_visible = True
        try:
            self.import_progress.start(10)
        except tk.TclError:
            pass

    def _hide_import_progress(self):
        self._ensure_import_runtime_state()
        if not self.import_progress:
            return
        try:
            self.import_progress.stop()
        except tk.TclError:
            pass
        if self._import_progress_visible:
            self.import_progress.grid_remove()
            self._import_progress_visible = False

    def _on_import_started(self, task_label):
        self._ensure_import_runtime_state()
        self._active_import_jobs += 1
        if self.import_status_var is not None:
            self.import_status_var.set(f"Importando {task_label}...")
        self._show_import_progress()
        if not self._catalog_loading:
            self._set_catalog_dependent_state(True)

    def _finalize_import_task(self, message, failed=False):
        self._ensure_import_runtime_state()
        self._active_import_jobs = max(0, self._active_import_jobs - 1)
        if self.import_status_var is not None and message:
            self.import_status_var.set(message)
        if self._active_import_jobs == 0:
            self._hide_import_progress()
            if not self._catalog_loading:
                self._set_catalog_dependent_state(False)

    def _refresh_compact_views(self, sections=None, data=None):
        targets = sections or {"clientes", "colaboradores"}
        if "clientes" in targets:
            self._refresh_client_summary()
        if "colaboradores" in targets:
            self._refresh_team_summary()

    def _refresh_client_summary(self):
        host = getattr(self, "_client_summary_owner", None)
        if host and hasattr(host, "refresh_summary"):
            host.refresh_summary()
            return
        tree = getattr(self, "clients_summary_tree", None)
        if not tree:
            return
        try:
            tree.delete(*tree.get_children())
        except tk.TclError:
            return
        for idx, client in enumerate(self.client_frames):
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
            tree.insert("", "end", iid=data.get("id_cliente", f"cliente-{idx}"), values=values, tags=tags)
        self._apply_treeview_theme(tree)

    def _refresh_team_summary(self):
        host = getattr(self, "_team_summary_owner", None)
        if host and hasattr(host, "refresh_summary"):
            host.refresh_summary()
            return
        tree = getattr(self, "team_summary_tree", None)
        if not tree:
            return
        try:
            tree.delete(*tree.get_children())
        except tk.TclError:
            return
        for idx, member in enumerate(self.team_frames):
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
            tags = ("even",) if idx % 2 == 0 else ("odd",)
            tree.insert("", "end", iid=data.get("id_colaborador", f"colaborador-{idx}"), values=values, tags=tags)
        self._apply_treeview_theme(tree)

    def _render_compact_rows(self, tree, rows):
        try:
            tree.delete(*tree.get_children())
        except tk.TclError:
            return
        for idx, row in enumerate(rows):
            tags = ("even",) if idx % 2 == 0 else ("odd",)
            self._insert_themed_row(tree, row, tags=tags)
        self._apply_treeview_theme(tree)

    def _compact_views_present(self, sections):
        return (
            ("clientes" in sections and self.clients_summary_tree is not None)
            or ("colaboradores" in sections and self.team_summary_tree is not None)
        )

    def _build_compact_table(self, parent, columns, height=6, column_width=140, sortable=False):
        frame = ttk.Frame(parent)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=[col for col, _ in columns], show="headings", height=height)
        vscrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hscrollbar = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vscrollbar.set, xscrollcommand=hscrollbar.set)
        for col_id, heading in columns:
            heading_kwargs = {"text": heading}
            if sortable:
                heading_kwargs["command"] = lambda c=col_id: self._sort_treeview(tree, c, False)
            tree.heading(col_id, **heading_kwargs)
            tree.column(col_id, width=column_width, stretch=True)
        tree.grid(row=0, column=0, sticky="nsew")
        vscrollbar.grid(row=0, column=1, sticky="ns")
        hscrollbar.grid(row=1, column=0, sticky="ew")
        return tree, frame

    def _apply_treeview_theme(self, tree):
        palette = ThemeManager.current()

        if hasattr(tree, "tag_configure"):
            try:
                tree.tag_configure(
                    "themed",
                    background=palette.get("background"),
                    foreground=palette.get("foreground"),
                )
                tree.tag_configure(
                    "even",
                    background=palette.get("heading_background", palette.get("background")),
                    foreground=palette.get("foreground"),
                )
                tree.tag_configure(
                    "odd",
                    background=palette.get("background"),
                    foreground=palette.get("foreground"),
                )
            except tk.TclError:
                pass

            tags = set()
            children = ()
            if hasattr(tree, "get_children"):
                try:
                    children = tree.get_children()
                except tk.TclError:
                    children = ()

            for item in children:
                item_tags = ()
                if hasattr(tree, "item"):
                    try:
                        item_tags = tree.item(item, "tags") or ()
                    except tk.TclError:
                        item_tags = ()
                elif hasattr(tree, "tag_has"):
                    try:
                        item_tags = tuple(tag for tag in ("themed",) if tree.tag_has(tag, item))
                    except tk.TclError:
                        item_tags = ()

                tags.update(item_tags)

                if hasattr(tree, "item") and "themed" not in item_tags:
                    try:
                        tree.item(item, tags=(*item_tags, "themed"))
                    except tk.TclError:
                        pass

            for tag in tags:
                try:
                    tree.tag_configure(
                        tag,
                        background=palette.get("background"),
                        foreground=palette.get("foreground"),
                    )
                except tk.TclError:
                    continue

        if hasattr(tree, "heading"):
            try:
                tree.heading("#0", background=palette.get("heading_background"), foreground=palette.get("foreground"))
            except tk.TclError:
                pass

            columns = ()
            if hasattr(tree, "cget"):
                try:
                    columns = tree.cget("columns")
                except tk.TclError:
                    columns = ()

            for column in columns:
                try:
                    tree.heading(
                        column,
                        background=palette.get("heading_background"),
                        foreground=palette.get("foreground"),
                    )
                except tk.TclError:
                    continue

    def _reapply_treeview_styles(self):
        trees = []
        for attr in ("operations_tree", "anexos_tree"):
            tree = getattr(self, attr, None)
            if tree is not None:
                trees.append(tree)
        trees.extend(getattr(self, "summary_tables", {}).values())
        trees.extend(getattr(self, "inline_summary_trees", {}).values())

        seen = set()
        for tree in trees:
            if tree is None or tree in seen:
                continue
            seen.add(tree)
            self._apply_treeview_theme(tree)

    def _apply_zebra_tags(self, tree):
        try:
            children = tree.get_children()
        except tk.TclError:
            return
        for idx, item in enumerate(children):
            try:
                tags = tree.item(item, "tags") or ()
            except tk.TclError:
                continue
            filtered = tuple(tag for tag in tags if tag not in {"even", "odd"})
            try:
                tree.item(item, tags=(*filtered, "even" if idx % 2 == 0 else "odd"))
            except tk.TclError:
                continue
        self._apply_treeview_theme(tree)

    def _sort_treeview(self, tree, column, reverse=False):
        try:
            data = [(tree.set(k, column), k) for k in tree.get_children("")]
        except tk.TclError:
            return
        try:
            data.sort(key=lambda item: (item[0] or "").lower())
        except Exception:
            data.sort(key=lambda item: item[0])
        if reverse:
            data.reverse()
        for index, (_, item) in enumerate(data):
            try:
                tree.move(item, "", index)
            except tk.TclError:
                continue
        try:
            tree.heading(column, command=lambda c=column: self._sort_treeview(tree, c, not reverse))
        except tk.TclError:
            pass
        self._apply_zebra_tags(tree)

    def _insert_themed_row(self, tree, values, tags=()):
        self._apply_treeview_theme(tree)
        try:
            normalized_tags = tuple(tags) if tags else ()
            tree.insert("", "end", values=values, tags=("themed", *normalized_tags))
        except tk.TclError:
            return

    def _start_background_import(self, task_label, button, worker, ui_callback, error_prefix, ui_error_prefix=None):
        self._ensure_import_runtime_state()
        if button is not None:
            try:
                button.state(['disabled'])
            except tk.TclError:
                pass
        self._on_import_started(task_label)
        run_async = getattr(self, 'root', None) is not None
        ui_error_prefix = ui_error_prefix or error_prefix

        def _execute_worker():
            try:
                payload = worker()
            except Exception as exc:  # pragma: no cover - errores inesperados
                self._handle_import_failure(task_label, button, exc, error_prefix)
                return
            self._handle_import_success(task_label, button, ui_callback, payload, ui_error_prefix)

        if not run_async:
            _execute_worker()
            return

        def _thread_target():
            try:
                payload = worker()
            except Exception as exc:  # pragma: no cover - errores inesperados
                self._dispatch_to_ui(self._handle_import_failure, task_label, button, exc, error_prefix)
                return
            self._dispatch_to_ui(self._handle_import_success, task_label, button, ui_callback, payload, ui_error_prefix)

        threading.Thread(
            target=_thread_target,
            name=f"import-{task_label}",
            daemon=True,
        ).start()

    def _handle_import_success(self, task_label, button, ui_callback, payload, error_prefix):
        message = f"Importación de {task_label} finalizada."
        failed = False
        captured_error = None
        try:
            ui_callback(payload)
        except Exception as exc:
            failed = True
            message = f"Importación de {task_label} con errores."
            captured_error = exc
            try:
                messagebox.showerror("Error", f"{error_prefix}: {exc}")
            except tk.TclError:
                pass
        finally:
            if button is not None and not self._catalog_loading:
                try:
                    button.state(['!disabled'])
                except tk.TclError:
                    pass
            self._finalize_import_task(message, failed=failed)
        if captured_error is not None and getattr(self, 'root', None) is None:
            raise captured_error

    def _handle_import_failure(self, task_label, button, error, error_prefix):
        if button is not None and not self._catalog_loading:
            try:
                button.state(['!disabled'])
            except tk.TclError:
                pass
        self._finalize_import_task(f"Error al importar {task_label}.", failed=True)
        try:
            messagebox.showerror("Error", f"{error_prefix}: {error}")
        except tk.TclError:
            pass
        if getattr(self, 'root', None) is None:
            raise error

    def _normalize_detail_catalog_payload(self, raw_catalogs):
        normalized = {
            normalize_detail_catalog_key(key): dict(value or {})
            for key, value in (raw_catalogs or {}).items()
        }
        lookup_by_id = build_detail_catalog_id_index(normalized)
        for canonical_key, aliases in (DETAIL_LOOKUP_ALIASES or {}).items():
            canonical = normalize_detail_catalog_key(canonical_key)
            lookup = normalized.get(canonical) or lookup_by_id.get(canonical)
            if not lookup:
                for alias in aliases or ():
                    alias_key = normalize_detail_catalog_key(alias)
                    alias_lookup = normalized.get(alias_key)
                    if alias_lookup:
                        lookup = alias_lookup
                        break
            if not lookup:
                continue
            normalized[canonical] = lookup
            lookup_by_id[canonical] = lookup
            for alias in aliases or ():
                alias_key = normalize_detail_catalog_key(alias)
                if not alias_key:
                    continue
                normalized[alias_key] = lookup
                lookup_by_id[alias_key] = lookup
        return normalized, lookup_by_id

    def _apply_catalog_lookups(self, detail_catalogs, detail_lookup_by_id):
        self.detail_catalogs = detail_catalogs or {}
        self.detail_lookup_by_id = detail_lookup_by_id or {}
        self.client_lookup = self._extract_lookup_or_empty("id_cliente")
        raw_team_lookup = self._extract_lookup_or_empty("id_colaborador")
        self.team_lookup = {
            normalized: value
            for key, value in raw_team_lookup.items()
            if (normalized := self._normalize_identifier(key))
        }
        self.product_lookup = self._extract_lookup_or_empty("id_producto")
        self.claim_lookup = self._extract_lookup_or_empty("id_reclamo")
        self.risk_lookup = self._extract_lookup_or_empty("id_riesgo")
        self.norm_lookup = self._extract_lookup_or_empty("id_norma")
        for frame in self.client_frames:
            if hasattr(frame, 'set_lookup'):
                frame.set_lookup(self.client_lookup)
                frame.on_id_change(preserve_existing=True, silent=True)
        for frame in self.team_frames:
            if hasattr(frame, 'set_lookup'):
                frame.set_lookup(self.team_lookup)
                frame.on_id_change(preserve_existing=True, silent=True)
        for frame in self.product_frames:
            if hasattr(frame, 'set_product_lookup'):
                frame.set_product_lookup(self.product_lookup)
                frame.on_id_change(preserve_existing=True, silent=True)
            if hasattr(frame, 'set_claim_lookup'):
                frame.set_claim_lookup(self.claim_lookup)
        for frame in self.risk_frames:
            if hasattr(frame, 'set_lookup'):
                frame.set_lookup(self.risk_lookup)
                frame.on_id_change(preserve_existing=True, silent=True)
        for frame in self.norm_frames:
            if hasattr(frame, 'set_lookup'):
                frame.set_lookup(self.norm_lookup)
                frame.on_id_change(preserve_existing=True, silent=True)
        self._autofill_investigator(show_errors=False)

    def _extract_lookup_or_empty(self, canonical_key):
        normalized = normalize_detail_catalog_key(canonical_key)
        lookup = self.detail_lookup_by_id.get(normalized)
        if isinstance(lookup, dict):
            return lookup
        return {}

    def build_summary_tab(self, parent):
        """Construye la pestaña de resumen con tablas compactas."""

        self.summary_tab = parent
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        scrollable_tab, container = create_scrollable_container(
            parent, scroll_binder=self._scroll_binder, tab_id=parent
        )
        scrollable_tab.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self._register_scrollable(scrollable_tab)
        container.columnconfigure(0, weight=1)

        self.summary_intro_label = ttk.Label(
            container,
            text="Resumen compacto de los datos capturados. Las tablas se actualizan tras cada guardado o importación.",
        )
        self.summary_intro_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        config = [
            (
                "clientes",
                "Clientes registrados",
                [
                    ("id", "ID"),
                    ("nombres", "Nombres"),
                    ("apellidos", "Apellidos"),
                    ("tipo", "Tipo ID"),
                    ("flag", "Flag"),
                    ("telefonos", "Teléfonos"),
                    ("correos", "Correos"),
                    ("direcciones", "Direcciones"),
                    ("accionado", "Accionado"),
                ],
            ),
            (
                "colaboradores",
                "Colaboradores involucrados",
                [
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
                ],
            ),
            (
                "involucramientos",
                "Asignaciones por colaborador",
                [
                    ("producto", "Producto"),
                    ("colaborador", "Colaborador"),
                    ("monto", "Monto asignado"),
                ],
            ),
            (
                "productos",
                "Productos investigados",
                [
                    ("id", "ID Producto"),
                    ("cliente", "Cliente"),
                    ("tipo", "Tipo"),
                    ("categoria1", "Categoría 1"),
                    ("categoria2", "Categoría 2"),
                    ("modalidad", "Modalidad"),
                    ("canal", "Canal"),
                    ("proceso", "Proceso"),
                    ("fecha_oc", "Fecha ocurrencia"),
                    ("fecha_desc", "Fecha descubrimiento"),
                    ("moneda", "Moneda"),
                    ("monto_inv", "Monto investigado"),
                    ("monto_perdida", "Pérdida"),
                    ("monto_falla", "Falla procesos"),
                    ("monto_cont", "Contingencia"),
                    ("monto_rec", "Recuperado"),
                    ("monto_pago", "Pago deuda"),
                ],
            ),
            (
                "riesgos",
                "Riesgos registrados",
                [
                    ("id", "ID Riesgo"),
                    ("lider", "Líder"),
                    ("descripcion", "Descripción"),
                    ("criticidad", "Criticidad"),
                    ("exposicion", "Exposición"),
                    ("planes", "Planes de acción"),
                ],
            ),
            (
                "reclamos",
                "Reclamos asociados",
                [
                    ("id", "ID Reclamo"),
                    ("producto", "Producto"),
                    ("analitica", "Analítica"),
                    ("codigo", "Código analítica"),
                ],
            ),
            (
                "normas",
                "Normas transgredidas",
                [
                    ("id", "ID Norma"),
                    ("descripcion", "Descripción"),
                    ("vigencia", "Vigencia"),
                ],
            ),
        ]

        self.summary_tables.clear()
        self.summary_config = {key: columns for key, _, columns in config}
        row_idx = 1
        for key, title, columns in config:
            section = ttk.LabelFrame(container, text=title)
            section.grid(row=row_idx, column=0, sticky="nsew", pady=5)
            container.rowconfigure(row_idx, weight=1)
            if getattr(self, "summary_first_section", None) is None:
                self.summary_first_section = section
            section.columnconfigure(0, weight=1)
            column_width = 130 if key == "colaboradores" else 150
            tree, frame = self._build_compact_table(
                section, columns, height=5, column_width=column_width
            )
            frame.pack(fill="both", expand=True)
            self.summary_tables[key] = tree
            self._register_summary_tree_bindings(tree, key)
            row_idx += 1

        self._schedule_summary_refresh()

    def _handle_notebook_tab_change(self, event):
        notebook = getattr(self, "notebook", None)
        if notebook is None:
            return
        if event.widget is not notebook:
            return

        previous_tab = getattr(self, "_current_tab_id", None)
        selected_tab = notebook.select()
        tab_text = notebook.tab(selected_tab, "text") if selected_tab else ""
        tab_index = notebook.index(selected_tab) if selected_tab else -1
        log_event(
            "navegacion",
            f"Abrió pestaña: {tab_text} (índice {tab_index})",
            self.logs,
        )
        self._scroll_binder.activate_tab(selected_tab)
        ThemeManager.apply_to_widget_tree(self.root)
        self._reapply_treeview_styles()
        previous_tab_text = notebook.tab(previous_tab, "text") if previous_tab else ""
        self._current_tab_id = selected_tab
        if (
            previous_tab_text == "Caso y participantes"
            and selected_tab != previous_tab
            and not getattr(self, "_suppress_messagebox", False)
        ):
            claim_errors = self._collect_claim_requirement_errors()
            if claim_errors:
                messagebox.showerror("Reclamos requeridos", "\n".join(claim_errors))
        if self._is_summary_tab_visible():
            self._flush_summary_refresh()

    def _collect_claim_requirement_errors(self) -> list[str]:
        errors: list[str] = []
        for frame in getattr(self, "product_frames", []):
            errors.extend(frame.claim_requirement_errors())
        return errors

    def _register_summary_tree_bindings(self, tree, key):
        """Configura atajos de pegado y el menú contextual para una tabla."""

        tree.bind("<Control-v>", lambda event, target=key: self._handle_summary_paste(target))
        tree.bind("<Control-V>", lambda event, target=key: self._handle_summary_paste(target))
        menu = tk.Menu(tree, tearoff=False)
        menu.add_command(
            label="Pegar desde portapapeles",
            command=lambda target=key: self._handle_summary_paste(target),
        )
        ThemeManager.register_menu(menu)
        tree.bind(
            "<Button-3>",
            lambda event, context_menu=menu: self._show_summary_context_menu(event, context_menu),
        )
        self.summary_context_menus[key] = menu

    def _show_summary_context_menu(self, event, menu):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _handle_summary_paste(self, key):
        """Lee el portapapeles, valida y carga filas en la tabla indicada."""

        tree = self.summary_tables.get(key)
        columns = self.summary_config.get(key, [])
        if not tree or not columns:
            return "break"
        try:
            clipboard_text = self.clipboard_get()
        except tk.TclError:
            messagebox.showerror("Portapapeles", "No se pudo leer el portapapeles desde el sistema.")
            return "break"
        log_event("navegacion", f"Intento de pegado en resumen:{key}", self.logs)
        try:
            parsed_rows = self._parse_clipboard_rows(clipboard_text, len(columns))
            sanitized_rows = self._transform_summary_clipboard_rows(key, parsed_rows)
        except ValueError as exc:
            messagebox.showerror("Pegado no válido", str(exc))
            log_event("validacion", f"Pegado fallido en {key}: {exc}", self.logs)
            return "break"
        ingestible_sections = {
            "clientes",
            "colaboradores",
            "involucramientos",
            "productos",
            "reclamos",
            "riesgos",
            "normas",
        }
        if key in ingestible_sections:
            try:
                self.ingest_summary_rows(key, sanitized_rows, stay_on_summary=True)
                log_event("navegacion", f"{key} pegados desde resumen: {len(sanitized_rows)}", self.logs)
            except ValueError as exc:
                messagebox.showerror("Pegado no válido", str(exc))
                log_event("validacion", f"Pegado fallido en {key}: {exc}", self.logs)
            return "break"
        tree.delete(*tree.get_children())
        for row in sanitized_rows:
            self._insert_themed_row(tree, row)
        self._apply_treeview_theme(tree)
        return "break"

    def _parse_clipboard_rows(self, text, expected_columns):
        """Convierte el texto del portapapeles en una matriz con ``expected_columns`` celdas."""

        cleaned = (text or "").strip()
        if not cleaned:
            raise ValueError("El portapapeles está vacío.")
        lines = [line for line in cleaned.splitlines() if line.strip()]
        if not lines:
            raise ValueError("No se encontraron filas para pegar.")
        rows = []
        for idx, line in enumerate(lines, start=1):
            delimiter = "\t" if "\t" in line else ";"
            parts = [cell.strip() for cell in line.split(delimiter)]
            if len(parts) != expected_columns:
                raise ValueError(
                    f"La fila {idx} tiene {len(parts)} columnas y se esperaban {expected_columns}."
                )
            rows.append(parts)
        return rows

    def _transform_summary_clipboard_rows(self, key, rows):
        """Valida y normaliza filas de acuerdo al tipo de tabla del resumen."""

        handlers = {
            "clientes": self._transform_clipboard_clients,
            "colaboradores": self._transform_clipboard_colaboradores,
            "involucramientos": self._transform_clipboard_involucramientos,
            "productos": self._transform_clipboard_productos,
            "reclamos": self._transform_clipboard_reclamos,
            "riesgos": self._transform_clipboard_riesgos,
            "normas": self._transform_clipboard_normas,
        }
        handler = handlers.get(key)
        if not handler:
            raise ValueError("Esta tabla no admite pegado desde portapapeles.")
        return handler(rows)

    def _transform_clipboard_clients(self, rows):
        sanitized = []
        for idx, values in enumerate(rows, start=1):
            client_data = {
                "id_cliente": values[0].strip(),
                "tipo_id": values[1].strip(),
                "flag": values[2].strip(),
                "telefonos": values[3].strip(),
                "correos": values[4].strip(),
                "direcciones": values[5].strip(),
                "accionado": values[6].strip(),
            }
            tipo_id = client_data["tipo_id"]
            if tipo_id and tipo_id not in TIPO_ID_LIST:
                raise ValueError(
                    f"Cliente fila {idx}: el tipo de ID '{tipo_id}' no está en el catálogo CM."
                    " Corrige la hoja de Excel antes de volver a intentarlo."
                )
            flag_value = client_data["flag"]
            if flag_value and flag_value not in FLAG_CLIENTE_LIST:
                raise ValueError(
                    f"Cliente fila {idx}: el flag de cliente '{flag_value}' no está en el catálogo CM."
                    " Corrige la hoja de Excel antes de volver a intentarlo."
                )
            message = validate_client_id(client_data["tipo_id"], client_data["id_cliente"])
            if message:
                raise ValueError(f"Cliente fila {idx}: {message}")
            phone_required = validate_required_text(
                client_data["telefonos"], "los teléfonos del cliente"
            )
            if phone_required:
                raise ValueError(f"Cliente fila {idx}: {phone_required}")
            phone_message = validate_phone_list(client_data["telefonos"], "los teléfonos del cliente")
            if phone_message:
                raise ValueError(f"Cliente fila {idx}: {phone_message}")
            email_required = validate_required_text(
                client_data["correos"], "los correos del cliente"
            )
            if email_required:
                raise ValueError(f"Cliente fila {idx}: {email_required}")
            email_message = validate_email_list(client_data["correos"], "los correos del cliente")
            if email_message:
                raise ValueError(f"Cliente fila {idx}: {email_message}")
            sanitized.append(
                (
                    client_data["id_cliente"],
                    client_data["tipo_id"],
                    client_data["flag"],
                    client_data["telefonos"],
                    client_data["correos"],
                    client_data["direcciones"],
                    client_data["accionado"],
                )
            )
        return sanitized

    def _transform_clipboard_colaboradores(self, rows):
        sanitized = []
        for idx, values in enumerate(rows, start=1):
            collaborator = {
                "id_colaborador": values[0].strip(),
                "nombres": values[1].strip(),
                "apellidos": values[2].strip(),
                "division": values[3].strip(),
                "area": values[4].strip(),
                "servicio": values[5].strip(),
                "puesto": values[6].strip(),
                "tipo_sancion": values[7].strip(),
                "fecha_carta_inmediatez": values[8].strip(),
                "fecha_carta_renuncia": values[9].strip(),
            }
            if collaborator["tipo_sancion"] not in TIPO_SANCION_LIST:
                raise ValueError(
                    f"Colaborador fila {idx}: debe seleccionar un tipo de sanción válido."
                )
            message = validate_team_member_id(collaborator["id_colaborador"])
            if message:
                raise ValueError(f"Colaborador fila {idx}: {message}")
            carta_inm_msg = validate_date_text(
                collaborator["fecha_carta_inmediatez"],
                "la fecha de carta de inmediatez",
                enforce_max_today=True,
            )
            if carta_inm_msg:
                raise ValueError(f"Colaborador fila {idx}: {carta_inm_msg}")
            carta_ren_msg = validate_date_text(
                collaborator["fecha_carta_renuncia"],
                "la fecha de carta de renuncia",
                enforce_max_today=True,
            )
            if carta_ren_msg:
                raise ValueError(f"Colaborador fila {idx}: {carta_ren_msg}")
            sanitized.append(
                (
                    collaborator["id_colaborador"],
                    collaborator["nombres"],
                    collaborator["apellidos"],
                    collaborator["division"],
                    collaborator["area"],
                    collaborator["servicio"],
                    collaborator["puesto"],
                    collaborator["tipo_sancion"],
                    collaborator["fecha_carta_inmediatez"],
                    collaborator["fecha_carta_renuncia"],
                )
            )
        return sanitized

    def _resolve_product_type_for_involvement(self, product_id):
        """Busca el tipo de producto desde el resumen o el formulario si está disponible."""

        lookup = getattr(self, "product_lookup", None)
        if isinstance(lookup, dict):
            entry = lookup.get(product_id)
            if isinstance(entry, dict):
                tipo = (entry.get("tipo_producto") or "").strip()
                if tipo:
                    return tipo
        finder = getattr(self, "_find_product_frame", None)
        if callable(finder):
            frame = finder(product_id)
            tipo_var = getattr(frame, "tipo_prod_var", None) if frame else None
            if tipo_var and hasattr(tipo_var, "get"):
                return (tipo_var.get() or "").strip()
        return ""

    def _transform_clipboard_involucramientos(self, rows):
        sanitized = []
        for idx, values in enumerate(rows, start=1):
            product_id = (values[0] or "").strip()
            collaborator_id = (values[1] or "").strip()
            amount_text = (values[2] or "").strip()
            tipo_producto = self._resolve_product_type_for_involvement(product_id)
            if tipo_producto:
                product_message = validate_product_id(tipo_producto, product_id)
            else:
                product_message = validate_required_text(
                    product_id,
                    "el ID del producto involucrado",
                )
            if product_message:
                raise ValueError(f"Involucramiento fila {idx}: {product_message}")
            collaborator_message = validate_team_member_id(collaborator_id)
            if collaborator_message:
                raise ValueError(f"Involucramiento fila {idx}: {collaborator_message}")
            amount_message, _decimal_value, normalized_amount = validate_money_bounds(
                amount_text,
                "el monto asignado",
                allow_blank=False,
            )
            if amount_message:
                raise ValueError(f"Involucramiento fila {idx}: {amount_message}")
            sanitized.append((product_id, collaborator_id, normalized_amount))
        return sanitized

    def _transform_clipboard_productos(self, rows):
        sanitized = []
        field_order = [
            "id_producto",
            "id_cliente",
            "tipo_producto",
            "categoria1",
            "categoria2",
            "modalidad",
            "canal",
            "proceso",
            "fecha_ocurrencia",
            "fecha_descubrimiento",
            "tipo_moneda",
            "monto_investigado",
            "monto_perdida_fraude",
            "monto_falla_procesos",
            "monto_contingencia",
            "monto_recuperado",
            "monto_pago_deuda",
        ]
        for idx, values in enumerate(rows, start=1):
            is_legacy = len(values) == 4
            normalized_values: list[str]
            if len(values) == len(field_order):
                normalized_values = [value.strip() for value in values]
            elif is_legacy:
                normalized_values = [
                    values[0].strip(),
                    values[1].strip(),
                    values[2].strip(),
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    values[3].strip(),
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            else:
                raise ValueError(
                    f"Producto fila {idx}: se esperaban {len(field_order)} columnas para el pegado."
                )
            product = dict(zip(field_order, normalized_values))
            if not product["id_cliente"]:
                raise ValueError(f"Producto fila {idx}: el ID de cliente es obligatorio.")
            tipo_catalogo = resolve_catalog_product_type(product["tipo_producto"])
            if not tipo_catalogo:
                if product["tipo_producto"]:
                    raise ValueError(
                        f"Producto fila {idx}: el tipo de producto '{product['tipo_producto']}' no está en el catálogo CM."
                    )
                raise ValueError(f"Producto fila {idx}: debe ingresar el tipo de producto.")
            product["tipo_producto"] = tipo_catalogo
            message = validate_product_id(product["tipo_producto"], product["id_producto"])
            if message:
                raise ValueError(f"Producto fila {idx}: {message}")
            occ_message = validate_date_text(
                product["fecha_ocurrencia"],
                "la fecha de ocurrencia",
                allow_blank=True,
                enforce_max_today=True,
                must_be_before=(product["fecha_descubrimiento"], "la fecha de descubrimiento"),
            )
            if occ_message:
                raise ValueError(f"Producto fila {idx}: {occ_message}")
            desc_message = validate_date_text(
                product["fecha_descubrimiento"],
                "la fecha de descubrimiento",
                allow_blank=True,
                enforce_max_today=True,
                must_be_after=(product["fecha_ocurrencia"], "la fecha de ocurrencia"),
            )
            if desc_message:
                raise ValueError(f"Producto fila {idx}: {desc_message}")
            moneda = product["tipo_moneda"]
            if moneda and moneda not in TIPO_MONEDA_LIST:
                raise ValueError(
                    f"Producto fila {idx}: la moneda '{moneda}' no está en el catálogo CM."
                )
            amount_message, decimal_value, _ = validate_money_bounds(
                product["monto_investigado"],
                "el monto investigado",
                allow_blank=False,
            )
            if amount_message:
                raise ValueError(f"Producto fila {idx}: {amount_message}")
            product["monto_investigado"] = f"{decimal_value:.2f}"
            amount_fields = [
                ("monto_perdida_fraude", "el monto de pérdida de fraude"),
                ("monto_falla_procesos", "el monto de falla en procesos"),
                ("monto_contingencia", "el monto de contingencia"),
                ("monto_recuperado", "el monto recuperado"),
                ("monto_pago_deuda", "el monto de pago de deuda"),
            ]
            for field_name, label in amount_fields:
                extra_message, _amount_decimal, normalized = validate_money_bounds(
                    product[field_name],
                    label,
                    allow_blank=True,
                )
                if extra_message:
                    raise ValueError(f"Producto fila {idx}: {extra_message}")
                product[field_name] = normalized
            full_row = (
                product["id_producto"],
                product["id_cliente"],
                product["tipo_producto"],
                product["categoria1"],
                product["categoria2"],
                product["modalidad"],
                product["canal"],
                product["proceso"],
                product["fecha_ocurrencia"],
                product["fecha_descubrimiento"],
                product["tipo_moneda"],
                product["monto_investigado"],
                product["monto_perdida_fraude"],
                product["monto_falla_procesos"],
                product["monto_contingencia"],
                product["monto_recuperado"],
                product["monto_pago_deuda"],
            )
            sanitized.append(full_row if not is_legacy else full_row[:3] + (product["monto_investigado"],))
        return sanitized

    def _transform_clipboard_reclamos(self, rows):
        sanitized = []
        for idx, values in enumerate(rows, start=1):
            claim = {
                "id_reclamo": values[0].strip(),
                "id_producto": values[1].strip(),
                "nombre_analitica": values[2].strip(),
                "codigo_analitica": values[3].strip(),
            }
            message = validate_reclamo_id(claim["id_reclamo"])
            if message:
                raise ValueError(f"Reclamo fila {idx}: {message}")
            product_message = validate_required_text(claim["id_producto"], "el ID de producto")
            if product_message:
                raise ValueError(f"Reclamo fila {idx}: {product_message}")
            analytic_message = validate_required_text(
                claim["nombre_analitica"],
                "el nombre de la analítica",
            )
            if analytic_message:
                raise ValueError(f"Reclamo fila {idx}: {analytic_message}")
            code_message = validate_codigo_analitica(claim["codigo_analitica"])
            if code_message:
                raise ValueError(f"Reclamo fila {idx}: {code_message}")
            sanitized.append(
                (
                    claim["id_reclamo"],
                    claim["id_producto"],
                    claim["nombre_analitica"],
                    claim["codigo_analitica"],
                )
            )
        return sanitized

    def _transform_clipboard_riesgos(self, rows):
        sanitized = []
        valid_criticidades = set(CRITICIDAD_LIST)
        valid_criticidades_text = ", ".join(CRITICIDAD_LIST)
        for idx, values in enumerate(rows, start=1):
            if len(values) == 4:
                risk = {
                    "id_riesgo": values[0].strip().upper(),
                    "lider": values[1].strip(),
                    "descripcion": "",
                    "criticidad": values[2].strip() or CRITICIDAD_LIST[0],
                    "exposicion": values[3].strip(),
                    "planes_accion": "",
                }
            elif len(values) >= 6:
                risk = {
                    "id_riesgo": values[0].strip().upper(),
                    "lider": values[1].strip(),
                    "descripcion": values[2].strip(),
                    "criticidad": values[3].strip() or CRITICIDAD_LIST[0],
                    "exposicion": values[4].strip(),
                    "planes_accion": values[5].strip(),
                }
            else:
                raise ValueError(
                    "Riesgo: número de columnas no válido. Se esperaban 4 (versión anterior) o 6 columnas."
                )
            message = validate_risk_id(risk["id_riesgo"])
            if message:
                raise ValueError(f"Riesgo fila {idx}: {message}")
            if risk["criticidad"] not in valid_criticidades:
                raise ValueError(
                    f"Riesgo fila {idx}: la criticidad debe ser una de {valid_criticidades_text}."
                )
            exposure_message, exposure_decimal, _ = validate_money_bounds(
                risk["exposicion"],
                "la exposición residual",
                allow_blank=True,
            )
            if exposure_message:
                raise ValueError(f"Riesgo fila {idx}: {exposure_message}")
            exposure_text = f"{exposure_decimal:.2f}" if exposure_decimal is not None else ""
            sanitized.append(
                (
                    risk["id_riesgo"],
                    risk["lider"],
                    risk["descripcion"],
                    risk["criticidad"],
                    exposure_text,
                    risk["planes_accion"],
                )
            )
        return sanitized

    def _transform_clipboard_normas(self, rows):
        sanitized = []
        for idx, values in enumerate(rows, start=1):
            norm = {
                "id_norma": values[0].strip(),
                "descripcion": values[1].strip(),
                "vigencia": values[2].strip(),
            }
            message = validate_norm_id(norm["id_norma"])
            if message:
                raise ValueError(f"Norma fila {idx}: {message}")
            desc_message = validate_required_text(norm["descripcion"], "la descripción de la norma")
            if desc_message:
                raise ValueError(f"Norma fila {idx}: {desc_message}")
            date_message = validate_date_text(norm["vigencia"], "la fecha de vigencia")
            if date_message:
                raise ValueError(f"Norma fila {idx}: {date_message}")
            sanitized.append(
                (
                    norm["id_norma"],
                    norm["descripcion"],
                    norm["vigencia"],
                )
            )
        return sanitized

    def ingest_summary_rows(self, section_key, rows, stay_on_summary=False):
        """Incorpora filas pegadas en las tablas de resumen al formulario principal."""

        if not rows:
            return 0
        section_key = (section_key or "").strip().lower()
        processed = 0
        missing_ids = []
        if section_key == "clientes":
            for idx, values in enumerate(rows, start=1):
                payload = {
                    "id_cliente": (values[0] or "").strip(),
                    "tipo_id": (values[1] or "").strip(),
                    "flag": (values[2] or "").strip(),
                    "telefonos": (values[3] or "").strip(),
                    "correos": (values[4] or "").strip(),
                    "direcciones": (values[5] or "").strip(),
                    "accionado": (values[6] or "").strip(),
                }
                hydrated, found = self._hydrate_row_from_details(payload, 'id_cliente', CLIENT_ID_ALIASES)
                client_id = (hydrated.get('id_cliente') or '').strip()
                if not client_id:
                    continue
                tipo_id = (hydrated.get('tipo_id') or '').strip()
                if tipo_id and tipo_id not in TIPO_ID_LIST:
                    raise ValueError(
                        f"Cliente fila {idx}: el tipo de ID '{tipo_id}' no está en el catálogo CM."
                        " Corrige la hoja de Excel antes de volver a intentarlo."
                    )
                flag_value = (hydrated.get('flag') or '').strip()
                if flag_value and flag_value not in FLAG_CLIENTE_LIST:
                    raise ValueError(
                        f"Cliente fila {idx}: el flag de cliente '{flag_value}' no está en el catálogo CM."
                        " Corrige la hoja de Excel antes de volver a intentarlo."
                    )
                frame = self._find_client_frame(client_id) or self._obtain_client_slot_for_import()
                merged = self._merge_client_payload_with_frame(frame, hydrated)
                self._populate_client_frame_from_row(frame, merged)
                self._trigger_import_id_refresh(
                    frame,
                    client_id,
                    notify_on_missing=True,
                    preserve_existing=True,
                )
                processed += 1
                if not found and 'id_cliente' in self.detail_catalogs:
                    missing_ids.append(client_id)
            if missing_ids:
                self._report_missing_detail_ids("clientes", missing_ids)
            if processed:
                self._notify_dataset_changed(summary_sections="clientes")
                self.sync_main_form_after_import("clientes", stay_on_summary=stay_on_summary)
            return processed
        if section_key == "colaboradores":
            for values in rows:
                payload = {
                    "id_colaborador": (values[0] or "").strip(),
                    "nombres": (values[1] or "").strip(),
                    "apellidos": (values[2] or "").strip(),
                    "division": (values[3] or "").strip(),
                    "area": (values[4] or "").strip(),
                    "servicio": (values[5] or "").strip(),
                    "puesto": (values[6] or "").strip(),
                    "tipo_sancion": (values[7] or "").strip(),
                    "fecha_carta_inmediatez": (values[8] or "").strip(),
                    "fecha_carta_renuncia": (values[9] or "").strip(),
                    "flag_colaborador": "No aplica",
                    "nombre_agencia": "",
                    "codigo_agencia": "",
                    "tipo_falta": "No aplica",
                }
                hydrated, found = self._hydrate_row_from_details(payload, 'id_colaborador', TEAM_ID_ALIASES)
                collaborator_id = (hydrated.get('id_colaborador') or '').strip()
                if not collaborator_id:
                    continue
                frame = self._find_team_frame(collaborator_id) or self._obtain_team_slot_for_import()
                merged = self._merge_team_payload_with_frame(frame, hydrated)
                self._populate_team_frame_from_row(frame, merged)
                self._trigger_import_id_refresh(
                    frame,
                    collaborator_id,
                    notify_on_missing=True,
                    preserve_existing=True,
                )
                processed += 1
                if not found and 'id_colaborador' in self.detail_catalogs:
                    missing_ids.append(collaborator_id)
            if missing_ids:
                self._report_missing_detail_ids("colaboradores", missing_ids)
            if processed:
                self._notify_dataset_changed(summary_sections="colaboradores")
                self.sync_main_form_after_import("colaboradores", stay_on_summary=stay_on_summary)
            return processed
        if section_key == "involucramientos":
            processed = 0

            def _fallback_frame(frames, identifier):
                normalized = (identifier or '').strip()
                if not normalized:
                    return None
                for frame in frames or []:
                    id_var = getattr(frame, 'id_var', None)
                    current = ''
                    if id_var and hasattr(id_var, 'get'):
                        current = (id_var.get() or '').strip()
                    if current == normalized:
                        return frame
                return None

            for idx, values in enumerate(rows, start=1):
                product_id = (values[0] or "").strip()
                collaborator_id = (values[1] or "").strip()
                amount_text = (values[2] or "").strip()
                if not product_id or not collaborator_id:
                    continue
                product_frame = self._find_product_frame(product_id) or _fallback_frame(getattr(self, 'product_frames', []), product_id)
                if not product_frame:
                    product_payload, product_found = self._hydrate_row_from_details(
                        {"id_producto": product_id},
                        'id_producto',
                        PRODUCT_ID_ALIASES,
                    )
                    if not product_found:
                        raise ValueError(
                            f"Involucramiento fila {idx}: el producto '{product_id}' no existe en el formulario ni en los catálogos de detalle."
                        )
                    client_for_product = (product_payload.get('id_cliente') or '').strip()
                    if client_for_product:
                        client_details, _ = self._hydrate_row_from_details({'id_cliente': client_for_product}, 'id_cliente', CLIENT_ID_ALIASES)
                        self._ensure_client_exists(client_for_product, client_details)
                    product_frame = self._obtain_product_slot_for_import()
                    merged = self._merge_product_payload_with_frame(product_frame, product_payload)
                    self._populate_product_frame_from_row(product_frame, merged)
                self._trigger_import_id_refresh(
                    product_frame,
                    product_id,
                    notify_on_missing=True,
                    preserve_existing=True,
                )
                team_frame = self._find_team_frame(collaborator_id) or _fallback_frame(getattr(self, 'team_frames', []), collaborator_id)
                if not team_frame:
                    collaborator_payload, collaborator_found = self._hydrate_row_from_details(
                        {"id_colaborador": collaborator_id},
                        'id_colaborador',
                        TEAM_ID_ALIASES,
                    )
                    if not collaborator_found:
                        raise ValueError(
                            f"Involucramiento fila {idx}: el colaborador '{collaborator_id}' no existe en el formulario ni en los catálogos de detalle."
                        )
                    team_frame, _created = self._ensure_team_member_exists(collaborator_id, collaborator_payload)
                self._trigger_import_id_refresh(
                    team_frame,
                    collaborator_id,
                    notify_on_missing=True,
                    preserve_existing=True,
                )
                amount_message, _amount_decimal, normalized_amount = validate_money_bounds(
                    amount_text,
                    "el monto asignado",
                    allow_blank=False,
                )
                if amount_message:
                    raise ValueError(f"Involucramiento fila {idx}: {amount_message}")
                existing_row = next(
                    (inv for inv in getattr(product_frame, 'involvements', []) if inv.team_var.get().strip() == collaborator_id),
                    None,
                )
                if not existing_row:
                    existing_row = self._obtain_involvement_slot(product_frame)
                existing_row.team_var.set(collaborator_id)
                team_widget = getattr(existing_row, 'team_cb', None)
                if team_widget is not None:
                    try:
                        team_widget.set(collaborator_id)
                    except tk.TclError:
                        pass
                existing_row.monto_var.set(normalized_amount)
                processed += 1
            if processed:
                self._notify_dataset_changed(summary_sections="involucramientos")
                self.save_auto()
                self.sync_main_form_after_import("involucramientos", stay_on_summary=stay_on_summary)
                self._run_duplicate_check_post_load()
            return processed
        if section_key == "productos":
            for values in rows:
                is_legacy_product = len(values) == 4
                payload = {
                    "id_producto": (values[0] or "").strip(),
                    "id_cliente": (values[1] or "").strip(),
                    "tipo_producto": (values[2] or "").strip(),
                    "categoria1": "" if is_legacy_product else (values[3] or "").strip(),
                    "categoria2": "" if is_legacy_product else (values[4] or "").strip(),
                    "modalidad": "" if is_legacy_product else (values[5] or "").strip(),
                    "canal": "" if is_legacy_product else (values[6] or "").strip(),
                    "proceso": "" if is_legacy_product else (values[7] or "").strip(),
                    "fecha_ocurrencia": "" if is_legacy_product else (values[8] or "").strip(),
                    "fecha_descubrimiento": "" if is_legacy_product else (values[9] or "").strip(),
                    "tipo_moneda": "" if is_legacy_product else (values[10] or "").strip(),
                    "monto_investigado": (
                        (values[11] if not is_legacy_product else values[3] if len(values) > 3 else "")
                        or ""
                    ).strip(),
                    "monto_perdida_fraude": "" if is_legacy_product else (values[12] or "").strip(),
                    "monto_falla_procesos": "" if is_legacy_product else (values[13] or "").strip(),
                    "monto_contingencia": "" if is_legacy_product else (values[14] or "").strip(),
                    "monto_recuperado": "" if is_legacy_product else (values[15] or "").strip(),
                    "monto_pago_deuda": "" if is_legacy_product else (values[16] or "").strip(),
                    "id_reclamo": "",
                    "nombre_analitica": "",
                    "codigo_analitica": "",
                }
                hydrated, found = self._hydrate_row_from_details(payload, 'id_producto', PRODUCT_ID_ALIASES)
                product_id = (hydrated.get('id_producto') or '').strip()
                if not product_id:
                    continue
                frame = self._find_product_frame(product_id) or self._obtain_product_slot_for_import()
                client_id = (hydrated.get('id_cliente') or '').strip()
                if client_id:
                    client_details, _ = self._hydrate_row_from_details({'id_cliente': client_id}, 'id_cliente', CLIENT_ID_ALIASES)
                    self._ensure_client_exists(client_id, client_details)
                merged = self._merge_product_payload_with_frame(frame, hydrated)
                self._populate_product_frame_from_row(frame, merged)
                self._trigger_import_id_refresh(
                    frame,
                    product_id,
                    notify_on_missing=True,
                    preserve_existing=True,
                )
                processed += 1
                if not found and 'id_producto' in self.detail_catalogs:
                    missing_ids.append(product_id)
            if missing_ids:
                self._report_missing_detail_ids("productos", missing_ids)
            if processed:
                self._notify_dataset_changed(summary_sections="productos")
                self.sync_main_form_after_import("productos", stay_on_summary=stay_on_summary)
                self._run_duplicate_check_post_load()
            return processed
        if section_key == "reclamos":
            missing_products = []
            unhydrated_products = []
            for values in rows:
                row_dict = {
                    'id_reclamo': (values[0] or "").strip(),
                    'id_producto': (values[1] or "").strip(),
                    'nombre_analitica': (values[2] or "").strip(),
                    'codigo_analitica': (values[3] or "").strip(),
                }
                hydrated, found = self._hydrate_row_from_details(row_dict, 'id_producto', PRODUCT_ID_ALIASES)
                product_id = (hydrated.get('id_producto') or '').strip()
                if not product_id:
                    continue
                if not found:
                    unhydrated_products.append(product_id)
                product_frame = self._find_product_frame(product_id)
                new_product = False
                if not product_frame:
                    product_frame = self._obtain_product_slot_for_import()
                    new_product = True
                client_id = (hydrated.get('id_cliente') or '').strip()
                if client_id:
                    client_details, _ = self._hydrate_row_from_details({'id_cliente': client_id}, 'id_cliente', CLIENT_ID_ALIASES)
                    self._ensure_client_exists(client_id, client_details)
                if new_product:
                    if found:
                        self._populate_product_frame_from_row(product_frame, hydrated)
                    else:
                        # Solo registrar el ID y mantener defaults hasta que el usuario complete los campos obligatorios.
                        product_frame.id_var.set(product_id)
                self._trigger_import_id_refresh(
                    product_frame,
                    product_id,
                    preserve_existing=False,
                )
                claim_payload = {
                    'id_reclamo': (hydrated.get('id_reclamo') or row_dict.get('id_reclamo') or '').strip(),
                    'nombre_analitica': (hydrated.get('nombre_analitica') or row_dict.get('nombre_analitica') or '').strip(),
                    'codigo_analitica': (hydrated.get('codigo_analitica') or row_dict.get('codigo_analitica') or '').strip(),
                }
                if not any(claim_payload.values()):
                    continue
                target = product_frame.find_claim_by_id(claim_payload['id_reclamo']) if claim_payload['id_reclamo'] else None
                if not target:
                    target = product_frame.obtain_claim_slot()
                target.set_data(claim_payload)
                self._sync_product_lookup_claim_fields(product_frame, product_id)
                product_frame.persist_lookup_snapshot()
                processed += 1
                if not found and 'id_producto' in self.detail_catalogs:
                    missing_products.append(product_id)
            if processed:
                self._notify_dataset_changed(summary_sections="reclamos")
                self.sync_main_form_after_import("reclamos", stay_on_summary=stay_on_summary)
                log_event("navegacion", f"Reclamos pegados desde resumen: {processed}", self.logs)
                self._run_duplicate_check_post_load()
            if missing_products:
                self._report_missing_detail_ids("productos", missing_products)
            if unhydrated_products:
                self._notify_products_created_without_details(unhydrated_products)
            return processed
        if section_key == "riesgos":
            duplicate_ids = []
            for values in rows:
                risk_id = (values[0] or "").strip()
                if not risk_id:
                    continue
                if any(r.id_var.get().strip() == risk_id for r in self.risk_frames):
                    log_event("validacion", f"Riesgo duplicado {risk_id} en pegado", self.logs)
                    duplicate_ids.append(risk_id)
                    continue
                self.add_risk()
                frame = self.risk_frames[-1]
                frame.id_var.set(risk_id)
                frame.lider_var.set((values[1] or "").strip())
                frame.descripcion_var.set((values[2] or "").strip())
                criticidad = (values[3] or CRITICIDAD_LIST[0]).strip()
                if criticidad in CRITICIDAD_LIST:
                    frame.criticidad_var.set(criticidad)
                frame.exposicion_var.set((values[4] or "").strip())
                frame.planes_var.set((values[5] or "").strip())
                self._trigger_import_id_refresh(frame, risk_id, preserve_existing=True)
                processed += 1
            if duplicate_ids:
                messagebox.showwarning(
                    "Riesgos duplicados",
                    "Se ignoraron los siguientes riesgos ya existentes:\n" + ", ".join(duplicate_ids),
                )
            if processed:
                self._notify_dataset_changed(summary_sections="riesgos")
                self.sync_main_form_after_import("riesgos", stay_on_summary=stay_on_summary)
            return processed
        if section_key == "normas":
            duplicate_ids = []
            for values in rows:
                norm_id = (values[0] or "").strip()
                if not norm_id:
                    continue
                if any(n.id_var.get().strip() == norm_id for n in self.norm_frames):
                    log_event("validacion", f"Norma duplicada {norm_id} en pegado", self.logs)
                    duplicate_ids.append(norm_id)
                    continue
                self.add_norm()
                frame = self.norm_frames[-1]
                frame.id_var.set(norm_id)
                frame.descripcion_var.set((values[1] or "").strip())
                frame.fecha_var.set((values[2] or "").strip())
                processed += 1
            if duplicate_ids:
                messagebox.showwarning(
                    "Normas duplicadas",
                    "Se ignoraron las siguientes normas ya existentes:\n" + ", ".join(duplicate_ids),
                )
            if processed:
                self._refresh_shared_norm_tree()
                self._notify_dataset_changed(summary_sections="normas")
                self.sync_main_form_after_import("normas", stay_on_summary=stay_on_summary)
            return processed
        raise ValueError("Esta tabla no admite pegado directo al formulario principal.")

    def _schedule_summary_refresh(self, sections=None, data=None):
        """Marca secciones como sucias y actualiza el resumen cuando proceda."""

        self._refresh_inline_section_tables(sections=sections, data=data)
        self._update_completion_progress()
        if not self.summary_tables:
            return
        normalized = self._normalize_summary_sections(sections)
        requested_sections = set(normalized)
        if not requested_sections:
            if sections is None:
                requested_sections = set(self.summary_tables.keys())
            elif isinstance(sections, str):
                requested_sections = {sections}
            else:
                requested_sections = set(sections or [])
        dataset = data
        if self._compact_views_present(requested_sections):
            if dataset is None:
                dataset = self.gather_data()
            self._refresh_compact_views(sections=requested_sections, data=dataset)
        if not self.summary_tables or not normalized:
            return
        self._summary_dirty_sections.update(normalized)
        self._summary_pending_dataset = dataset
        summary_visible = self._is_summary_tab_visible()
        if not summary_visible:
            self._cancel_summary_refresh_job()
            return
        if self._summary_refresh_after_id:
            return
        try:
            self._summary_refresh_after_id = self.root.after(
                self.SUMMARY_REFRESH_DELAY_MS,
                self._run_scheduled_summary_refresh,
            )
        except tk.TclError:
            self._summary_refresh_after_id = None
            self._flush_summary_refresh(sections=normalized, data=dataset)

    def _run_scheduled_summary_refresh(self):
        self._summary_refresh_after_id = None
        if not self._is_summary_tab_visible():
            return
        self._flush_summary_refresh()

    def _flush_summary_refresh(self, sections=None, data=None):
        if sections is None:
            targets = set(self._summary_dirty_sections)
        else:
            targets = self._normalize_summary_sections(sections)
        if not targets:
            return
        dataset = data
        if dataset is None:
            dataset = self._summary_pending_dataset
        self.refresh_summary_tables(data=dataset, sections=targets)
        self._summary_pending_dataset = None
        self._handle_validation_success_transition()

    def _handle_validation_success_transition(self) -> None:
        if not getattr(self, "_validation_feedback_initialized", False):
            return
        validators = getattr(self, "validators", []) or []
        if not validators:
            return
        all_valid = all(
            getattr(validator, "last_error", None) in {None, ""}
            for validator in validators
        )
        if not self._validity_initialized:
            self._validity_initialized = True
            self._last_all_valid = all_valid
            return
        if all_valid and not getattr(self, "_last_all_valid", False):
            self.show_big_checkmark()
        self._last_all_valid = all_valid

    def _refresh_inline_section_tables(self, sections=None, data=None):
        if sections is None:
            targets = {"clientes", "colaboradores"}
        elif isinstance(sections, str):
            targets = {sections}
        else:
            targets = set(sections)
        inline_trees = getattr(self, "inline_summary_trees", {}) or {}
        dataset = data or (self.gather_data() if targets else {})
        if "clientes" in targets:
            if inline_trees.get("clientes"):
                rows = self._build_summary_rows("clientes", dataset)
                self._render_inline_rows(inline_trees["clientes"], rows)
            else:
                self._refresh_client_summary()
        if "colaboradores" in targets:
            if inline_trees.get("colaboradores"):
                rows = self._build_summary_rows("colaboradores", dataset)
                self._render_inline_rows(inline_trees["colaboradores"], rows)
            else:
                self._refresh_team_summary()

    def _render_inline_rows(self, tree, rows):
        try:
            tree.delete(*tree.get_children())
        except Exception:
            try:
                tree.delete()
            except Exception:
                pass
        for row in rows:
            self._insert_themed_row(tree, row)

    def _normalize_summary_sections(self, sections):
        if not self.summary_tables:
            return set()
        if sections is None:
            return set(self.summary_tables.keys())
        if isinstance(sections, str):
            sections = {sections}
        return {section for section in sections if section in self.summary_tables}

    def _cancel_summary_refresh_job(self):
        if not self._summary_refresh_after_id:
            return
        try:
            self.root.after_cancel(self._summary_refresh_after_id)
        except tk.TclError:
            pass
        self._summary_refresh_after_id = None

    def _is_summary_tab_visible(self):
        if getattr(self, "notebook", None) is None or self.summary_tab is None:
            return False
        try:
            return self.notebook.select() == str(self.summary_tab)
        except tk.TclError:
            return False

    def refresh_summary_tables(self, data=None, sections=None):
        """Actualiza las tablas de resumen con la información actual."""

        if not self.summary_tables:
            return
        normalized = self._normalize_summary_sections(sections)
        if not normalized:
            return
        self._cancel_summary_refresh_job()
        self._summary_dirty_sections.difference_update(normalized)
        dataset = data or self.gather_data()
        ordered_sections = [key for key in self.summary_tables.keys() if key in normalized]
        for key in ordered_sections:
            rows = self._build_summary_rows(key, dataset)
            self._render_summary_rows(key, rows)
        self.recalculate_quality(data=dataset)

    def _build_summary_rows(self, section, dataset):
        if section == "clientes":
            return [
                (
                    client.get("id_cliente", ""),
                    client.get("nombres", ""),
                    client.get("apellidos", ""),
                    client.get("tipo_id", ""),
                    client.get("flag", ""),
                    client.get("telefonos", ""),
                    client.get("correos", ""),
                    client.get("direcciones", ""),
                    client.get("accionado", ""),
                )
                for client in dataset.get("clientes", [])
            ]
        if section == "colaboradores":
            return [
                (
                    col.get("id_colaborador", ""),
                    col.get("nombres", ""),
                    col.get("apellidos", ""),
                    col.get("division", ""),
                    col.get("area", ""),
                    col.get("servicio", ""),
                    col.get("puesto", ""),
                    col.get("tipo_sancion", ""),
                    col.get("fecha_carta_inmediatez", ""),
                    col.get("fecha_carta_renuncia", ""),
                )
                for col in dataset.get("colaboradores", [])
            ]
        if section == "involucramientos":
            return [
                (
                    inv.get("id_producto", ""),
                    inv.get("id_colaborador", ""),
                    inv.get("monto_asignado", ""),
                )
                for inv in dataset.get("involucramientos", [])
            ]
        if section == "productos":
            return [
                (
                    prod.get("id_producto", ""),
                    prod.get("id_cliente", ""),
                    prod.get("tipo_producto", ""),
                    prod.get("categoria1", ""),
                    prod.get("categoria2", ""),
                    prod.get("modalidad", ""),
                    prod.get("canal", ""),
                    prod.get("proceso", ""),
                    prod.get("fecha_ocurrencia", ""),
                    prod.get("fecha_descubrimiento", ""),
                    prod.get("tipo_moneda", ""),
                    prod.get("monto_investigado", ""),
                    prod.get("monto_perdida_fraude", ""),
                    prod.get("monto_falla_procesos", ""),
                    prod.get("monto_contingencia", ""),
                    prod.get("monto_recuperado", ""),
                    prod.get("monto_pago_deuda", ""),
                )
                for prod in dataset.get("productos", [])
            ]
        if section == "riesgos":
            return [
                (
                    risk.get("id_riesgo", ""),
                    risk.get("lider", ""),
                    risk.get("descripcion", ""),
                    risk.get("criticidad", ""),
                    risk.get("exposicion_residual", ""),
                    risk.get("planes_accion", ""),
                )
                for risk in dataset.get("riesgos", [])
            ]
        if section == "reclamos":
            return [
                (
                    rec.get("id_reclamo", ""),
                    rec.get("id_producto", ""),
                    rec.get("nombre_analitica", ""),
                    rec.get("codigo_analitica", ""),
                )
                for rec in dataset.get("reclamos", [])
            ]
        if section == "normas":
            return [
                (
                    norm.get("id_norma", ""),
                    norm.get("descripcion", ""),
                    norm.get("fecha_vigencia", ""),
                )
                for norm in dataset.get("normas", [])
            ]
        return []

    def _render_summary_rows(self, key, rows):
        tree = self.summary_tables.get(key)
        if not tree:
            return
        tree.delete(*tree.get_children())
        for idx, row in enumerate(rows):
            tags = ("even",) if idx % 2 == 0 else ("odd",)
            self._insert_themed_row(tree, row, tags=tags)
        self._apply_treeview_theme(tree)

    # ---------------------------------------------------------------------
    # Importación desde CSV

    def _get_import_config(self, sample_key):
        return self.IMPORT_CONFIG.get(sample_key, {})

    def _select_csv_file(self, sample_key, dialog_title):
        """Obtiene un CSV desde diálogo y registra cancelaciones explícitas."""

        filename = None
        config = self._get_import_config(sample_key)
        dialog_options = {
            "title": dialog_title or config.get("title") or "Seleccionar CSV",
            "filetypes": [("CSV Files", "*.csv")],
        }
        initialfile = config.get("initialfile")
        if initialfile:
            dialog_options["initialfile"] = initialfile
            dialog_options["initialdir"] = str(Path(MASSIVE_SAMPLE_FILES.get(sample_key, "")).parent)
        try:
            filename = filedialog.askopenfilename(**dialog_options)
        except tk.TclError:
            filename = None
        if not filename:
            message = f"Importación cancelada: no se seleccionó un archivo CSV para {sample_key}."
            log_event("cancelado", message, self.logs)
            if not getattr(self, "_suppress_messagebox", False):
                messagebox.showinfo("Importación cancelada", message)
            return None
        expected_keyword = (config.get("expected_keyword") or str(sample_key)).lower()
        basename = os.path.basename(filename).lower()
        if expected_keyword and expected_keyword not in basename:
            try:
                proceed = messagebox.askyesno(
                    "Advertencia",
                    (
                        f"El archivo seleccionado ({os.path.basename(filename)}) no parece ser de {sample_key}.\n"
                        "¿Deseas continuar de todos modos?"
                    ),
                )
            except tk.TclError:
                proceed = True
            if not proceed:
                log_event("cancelado", f"Importación cancelada por posible tipo incorrecto: {filename}", self.logs)
                return None
        return filename

    def _validate_import_headers(self, filename, sample_key):
        config = self._get_import_config(sample_key)
        expected_headers = config.get("expected_headers")
        if not expected_headers:
            return True
        if not os.path.exists(filename):
            log_event(
                "validacion",
                f"No se pudo validar encabezados para {sample_key}: archivo inexistente {filename}",
                self.logs,
            )
            return True
        try:
            with open(filename, newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(line for line in handle if line.strip())
                headers = reader.fieldnames or []
        except Exception as exc:  # pragma: no cover - errores de IO poco frecuentes
            log_event("validacion", f"No se pudo leer {filename} para validar encabezados: {exc}", self.logs)
            if not getattr(self, "_suppress_messagebox", False):
                messagebox.showerror("CSV inválido", f"No se pudo leer el archivo: {exc}")
            return False
        missing = [header for header in expected_headers if header not in headers]
        if missing:
            log_event(
                "validacion",
                f"CSV de {sample_key} con columnas faltantes: {', '.join(missing)}",
                self.logs,
            )
            if not getattr(self, "_suppress_messagebox", False):
                messagebox.showerror(
                    "CSV inválido",
                    f"Faltan columnas requeridas para {sample_key}: {', '.join(missing)}",
                )
            return False
        return True

    def _get_detail_lookup(self, id_column):
        """Obtiene el diccionario de detalles considerando alias configurados."""

        normalized = normalize_detail_catalog_key(id_column)
        lookup = self.detail_lookup_by_id.get(normalized)
        if isinstance(lookup, dict):
            return lookup
        candidate_keys = [normalized]
        candidate_keys.extend(
            normalize_detail_catalog_key(alias)
            for alias in DETAIL_LOOKUP_ALIASES.get(normalized, ())
        )
        seen = set()
        for key in candidate_keys:
            if not key or key in seen:
                continue
            seen.add(key)
            lookup = self.detail_catalogs.get(key)
            if isinstance(lookup, dict):
                return lookup
        return None

    def _hydrate_row_from_details(self, row, id_column, alias_headers):
        """Devuelve una copia de la fila complementada con catálogos de detalle."""

        hydrated = dict(row or {})
        alias_headers = alias_headers or ()
        canonical_id = ""
        for header in (id_column, *alias_headers):
            value = hydrated.get(header)
            if isinstance(value, str):
                value = value.strip()
            if value:
                canonical_id = str(value).strip()
                hydrated[id_column] = canonical_id
                break
        found = False
        lookup = self._get_detail_lookup(id_column)
        if canonical_id and lookup:
            details = lookup.get(canonical_id)
            if details:
                for key, value in details.items():
                    if hydrated.get(key):
                        continue
                    hydrated[key] = value
                found = True
        return hydrated, found

    def _has_meaningful_value(self, value):
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    def _merge_payload_with_frame(self, payload, field_sources):
        merged = dict(payload or {})
        for field, getter in (field_sources or {}).items():
            incoming = merged.get(field)
            if self._has_meaningful_value(incoming):
                continue
            existing = getter() if callable(getter) else getter
            if self._has_meaningful_value(existing):
                merged[field] = existing.strip() if isinstance(existing, str) else existing
        return merged

    def _merge_client_payload_with_frame(self, frame, payload):
        return self._merge_payload_with_frame(
            payload,
            {
                'nombres': frame.nombres_var.get,
                'apellidos': frame.apellidos_var.get,
                'tipo_id': frame.tipo_id_var.get,
                'flag': frame.flag_var.get,
                'telefonos': frame.telefonos_var.get,
                'correos': frame.correos_var.get,
                'direcciones': frame.direcciones_var.get,
                'accionado': frame.accionado_var.get,
            },
        )

    def _merge_team_payload_with_frame(self, frame, payload):
        return self._merge_payload_with_frame(
            payload,
            {
                'nombres': frame.nombres_var.get,
                'apellidos': frame.apellidos_var.get,
                'flag_colaborador': frame.flag_var.get,
                'division': frame.division_var.get,
                'area': frame.area_var.get,
                'servicio': frame.servicio_var.get,
                'puesto': frame.puesto_var.get,
                'fecha_carta_inmediatez': frame.fecha_carta_inmediatez_var.get,
                'fecha_carta_renuncia': frame.fecha_carta_renuncia_var.get,
                'nombre_agencia': frame.nombre_agencia_var.get,
                'codigo_agencia': frame.codigo_agencia_var.get,
                'tipo_falta': frame.tipo_falta_var.get,
                'tipo_sancion': frame.tipo_sancion_var.get,
            },
        )

    def _merge_product_payload_with_frame(self, frame, payload):
        merged = self._merge_payload_with_frame(
            payload,
            {
                'id_cliente': frame.client_var.get,
                'categoria1': frame.cat1_var.get,
                'categoria2': frame.cat2_var.get,
                'modalidad': frame.mod_var.get,
                'canal': frame.canal_var.get,
                'proceso': frame.proceso_var.get,
                'tipo_producto': frame.tipo_prod_var.get,
                'fecha_ocurrencia': frame.fecha_oc_var.get,
                'fecha_descubrimiento': frame.fecha_desc_var.get,
                'tipo_moneda': frame.moneda_var.get,
                'monto_investigado': frame.monto_inv_var.get,
                'monto_perdida_fraude': frame.monto_perdida_var.get,
                'monto_falla_procesos': frame.monto_falla_var.get,
                'monto_contingencia': frame.monto_cont_var.get,
                'monto_recuperado': frame.monto_rec_var.get,
                'monto_pago_deuda': frame.monto_pago_var.get,
            },
        )
        claim_candidates = frame.extract_claims_from_payload(payload or {})
        if claim_candidates:
            merged['reclamos'] = claim_candidates
        elif 'reclamos' not in merged:
            merged['reclamos'] = [claim.get_data() for claim in frame.claims]
        return merged

    def _report_missing_detail_ids(self, entity_label, missing_ids):
        """Registra y muestra un único aviso de IDs sin detalle catalogado."""

        unique_ids = sorted({mid for mid in missing_ids if mid})
        if not unique_ids:
            return
        message = (
            f"No se encontraron detalles catalogados para los {entity_label} con ID: "
            f"{', '.join(unique_ids)}."
        )
        log_event("validacion", message, self.logs)
        try:
            messagebox.showwarning("Detalles faltantes", message)
        except tk.TclError:
            pass

    def _notify_products_created_without_details(self, product_ids):
        """Advierte que ciertos productos se generaron sin información de catálogo."""

        unique_ids = sorted({pid for pid in product_ids if pid})
        if not unique_ids:
            return
        message = (
            "Los siguientes productos se importaron desde reclamos sin detalle"
            " catalogado: "
            + ", ".join(unique_ids)
            + ".\nEl sistema solo puede crear el producto con su ID,"
            " por lo que debes completar manualmente la sección de Productos o"
            " actualizar el catálogo antes de continuar."
        )
        log_event("validacion", message, self.logs)
        try:
            messagebox.showwarning("Productos creados sin datos", message)
        except tk.TclError:
            pass

    def _build_duplicate_dataset_signature(self) -> str:
        """Crea una huella determinística del estado relevante para la clave técnica."""

        normalized_case_id = self._normalize_identifier(self.id_caso_var.get())
        product_snapshots: list[object] = []
        for product in self.product_frames:
            pid_norm = self._normalize_identifier(product.id_var.get())
            client_norm = self._normalize_identifier(product.client_var.get())
            occ_date = (product.fecha_oc_var.get() or "").strip()
            claim_ids: set[str] = set()
            for claim in product.claims:
                claim_data = claim.get_data()
                if not any(claim_data.values()):
                    continue
                claim_ids.add(self._normalize_identifier((claim_data.get("id_reclamo") or "")))
            collaborator_ids: set[str] = set()
            for involvement in product.involvements:
                involvement_data = involvement.get_data()
                collaborator_ids.add(
                    self._normalize_identifier((involvement_data.get("id_colaborador") or ""))
                )
            product_snapshots.append(
                {
                    "pid": pid_norm,
                    "cid": client_norm,
                    "occ": occ_date,
                    "claims": sorted(claim_ids),
                    "collabs": sorted(collaborator_ids),
                }
            )
        fingerprint = {"case": normalized_case_id, "products": product_snapshots}
        return json.dumps(fingerprint, ensure_ascii=False, sort_keys=True)

    def duplicate_dataset_signature(self) -> str:
        """Expuesta para que los frames eviten ejecuciones redundantes."""

        return self._build_duplicate_dataset_signature()

    def is_duplicate_check_on_cooldown(self, dataset_signature: str) -> bool:
        return self._is_duplicate_warning_on_cooldown(dataset_signature)

    def _is_duplicate_warning_on_cooldown(self, dataset_signature: str) -> bool:
        """Indica si ya se alertó por este estado dentro de la ventana de enfriamiento."""

        if self._duplicate_warning_signature != dataset_signature:
            return False
        if not self._duplicate_warning_cooldown_until:
            return False
        return datetime.now() < self._duplicate_warning_cooldown_until

    def _activate_duplicate_warning_cooldown(
        self, dataset_signature: str, message: str
    ) -> None:
        self._duplicate_warning_signature = dataset_signature
        self._duplicate_warning_cooldown_until = datetime.now() + timedelta(minutes=10)
        self._last_duplicate_warning_message = message

    def _update_duplicate_validation_entry(
        self, message: Optional[str], *, severity: Optional[str] = None
    ) -> None:
        if not self._validation_panel:
            return
        resolved_severity = severity or ("warning" if message else "ok")
        self._validation_panel.update_entry(
            "realtime:duplicate",
            message,
            severity=resolved_severity,
            origin="Clave técnica",
        )

    @staticmethod
    def _normalize_identifier(identifier):
        return (identifier or '').strip().upper()

    def _run_duplicate_check_post_load(self, from_background: Optional[bool] = None):
        """Ejecuta la validación de claves técnicas tras cargas masivas.

        Cuando el origen es un hilo en segundo plano, reenvía la ejecución
        al hilo de UI para evitar conflictos con widgets de Tkinter.
        """

        if from_background is None:
            from_background = threading.current_thread() is not threading.main_thread()

        def _perform_check():
            try:
                self._check_duplicate_technical_keys_realtime(armed=True)
            except AttributeError:
                return

        if from_background:
            self._dispatch_to_ui(_perform_check)
        else:
            _perform_check()

    def _check_duplicate_technical_keys_realtime(
        self, armed: bool = False, dataset_signature: Optional[str] = None
    ):
        status_message = "Clave técnica sin validar"
        if armed:
            self._duplicate_checks_armed = True
        if not self._duplicate_checks_armed:
            return status_message
        normalized_case_id = self._normalize_identifier(self.id_caso_var.get())
        if not normalized_case_id:
            return "Ingresa el número de caso para validar duplicados"

        signature = dataset_signature or self._build_duplicate_dataset_signature()

        seen_keys = {}
        duplicate_messages: list[str] = []
        missing_association_messages: list[str] = []
        missing_date_messages: list[str] = []
        missing_assignment_detected = False
        missing_date_detected = False

        def _normalize_occurrence_date(raw_date: str) -> str:
            text = (raw_date or "").strip()
            if not text:
                return text
            sanitized = text.replace("/", "-")
            parsed = None
            for parser in (datetime.fromisoformat, lambda value: datetime.strptime(value, "%Y-%m-%d")):
                try:
                    parsed = parser(sanitized)
                    break
                except ValueError:
                    continue
            return parsed.date().isoformat() if parsed else text
        for product in self.product_frames:
            pid_norm = self._normalize_identifier(product.id_var.get())
            client_norm = self._normalize_identifier(product.client_var.get())
            occ_date_raw = (product.fecha_oc_var.get() or '').strip()
            occ_date_norm = _normalize_occurrence_date(occ_date_raw)
            product_label = product._get_product_label()

            if pid_norm and not occ_date_raw:
                missing_date_detected = True
                missing_date_messages.append(
                    (
                        f"{product_label}: ingresa la fecha de ocurrencia (YYYY-MM-DD) "
                        "para validar la clave técnica."
                    )
                )
            if not (pid_norm and occ_date_raw):
                continue
            claim_rows = [claim.get_data() for claim in product.claims if any(claim.get_data().values())]
            if not claim_rows:
                claim_rows = [{'id_reclamo': ''}]

            assignment_rows = [inv.get_data() for inv in product.involvements if any(inv.get_data().values())]
            collaborator_ids = [
                self._normalize_identifier(assignment.get('id_colaborador'))
                for assignment in assignment_rows
                if (assignment.get('id_colaborador') or '').strip()
            ]

            has_client_association = bool(client_norm)
            has_collaborator_association = bool(collaborator_ids)

            if not has_client_association and not assignment_rows:
                missing_assignment_detected = True
                missing_association_messages.append(
                    (
                        f"{product_label}: asocia un cliente o agrega un colaborador en la sección"
                        " 'Involucramiento de colaboradores'. Solo necesitas uno de ellos para"
                        " validar duplicados."
                    )
                )
            elif not has_client_association and not has_collaborator_association:
                missing_assignment_detected = True
                missing_association_messages.append(
                    (
                        f"{product_label}: registra el cliente o el colaborador (basta uno) para"
                        " validar la clave técnica."
                    )
                )

            if not has_collaborator_association:
                collaborator_ids = [""] if has_client_association else ["<FALTA_ASOCIACION>"]

            for claim in claim_rows:
                claim_id_raw = (claim.get('id_reclamo') or '').strip()
                claim_norm = self._normalize_identifier(claim_id_raw)
                for collaborator_norm in collaborator_ids:
                    key = (
                        normalized_case_id,
                        pid_norm,
                        client_norm,
                        collaborator_norm,
                        occ_date_norm,
                        claim_norm,
                    )
                    if key in seen_keys:
                        base_message = f"Registro duplicado de clave técnica (producto {product_label}"
                        if collaborator_norm:
                            base_message += f", colaborador {collaborator_norm}"
                        if claim_id_raw:
                            base_message += f", reclamo {claim_id_raw}"
                        base_message += ")"
                        if base_message not in duplicate_messages:
                            duplicate_messages.append(base_message)
                    else:
                        seen_keys[key] = True

        error_messages = []
        if duplicate_messages:
            error_messages.append("\n".join(duplicate_messages))
        if missing_association_messages or missing_date_messages:
            guidance_parts = [
                (
                    "La clave técnica se valida con caso, producto, fecha de ocurrencia, ID de reclamo"
                    " y la asociación disponible: cliente o colaborador (no necesitas ambos)."
                )
            ]
            if missing_association_messages:
                guidance_parts.append(
                    "Asocia un cliente o registra un colaborador (uno es suficiente) en 'Involucramiento de colaboradores' antes de continuar."
                )
            if missing_date_messages:
                guidance_parts.append(
                    "Registra la fecha de ocurrencia en cada producto antes de reintentar la validación."
                )
            error_messages.append(" ".join(guidance_parts))
            blocking_messages = missing_association_messages + missing_date_messages
            error_messages.append("\n".join(blocking_messages))

        cooldown_active = (
            False
            if (missing_assignment_detected or missing_date_detected)
            else self._is_duplicate_warning_on_cooldown(signature)
        )

        if error_messages:
            message = "\n\n".join(error_messages)
            if (missing_association_messages or missing_date_messages) and not duplicate_messages:
                if missing_association_messages and missing_date_messages:
                    status = "Bloqueado: agrega cliente/colaborador y fecha de ocurrencia"
                elif missing_association_messages:
                    status = "Bloqueado: asigna cliente o colaborador para validar"
                else:
                    status = "Bloqueado: ingresa fecha de ocurrencia para validar"
            elif missing_association_messages or missing_date_messages:
                status = "Duplicado detectado o datos faltantes (bloqueante)"
            else:
                status = "Duplicado detectado en clave técnica"
            severity = "error"
            log_event("validacion", message, self.logs)
            self._update_duplicate_validation_entry(message, severity=severity)
            if duplicate_messages and not cooldown_active:
                self._activate_duplicate_warning_cooldown(signature, message)
            if not getattr(self, "_suppress_messagebox", False):
                try:
                    messagebox.showerror("Validación de clave técnica", message)
                except tk.TclError:
                    return "Validación interrumpida"
            return status

        self._update_duplicate_validation_entry(None)
        self._last_duplicate_warning_message = None
        self._duplicate_warning_cooldown_until = None
        return "Sin duplicados detectados"

    @staticmethod
    def _frame_entity_label(frame):
        label = getattr(frame, 'ENTITY_LABEL', '')
        if isinstance(label, str) and label.strip():
            return label.strip()
        return 'registro'

    def _update_frame_id_index(self, index, frame, previous_id, new_id):
        if index is None:
            return
        previous = self._normalize_identifier(previous_id)
        new = self._normalize_identifier(new_id)
        existing = index.get(new)
        if new and existing is not None and existing is not frame:
            restore_value = previous_id if isinstance(previous_id, str) else (previous_id or '')
            if not isinstance(restore_value, str):
                restore_value = str(restore_value)
            if hasattr(frame, 'id_var') and hasattr(frame.id_var, 'set'):
                frame.id_var.set(restore_value)
            if hasattr(frame, '_last_tracked_id'):
                frame._last_tracked_id = previous
            entity_label = self._frame_entity_label(frame)
            message = (
                f"El ID '{new}' ya está asignado a otro {entity_label}. "
                f"Cada {entity_label} debe tener un ID único."
            )
            log_event('validacion', message, self.logs)
            if not getattr(self, '_suppress_messagebox', False):
                try:
                    messagebox.showerror('ID duplicado', message)
                except tk.TclError:
                    pass
            return
        for key, value in list(index.items()):
            if value is frame and key != new:
                index.pop(key, None)
        if hasattr(frame, '_last_tracked_id'):
            frame._last_tracked_id = new
        if not new:
            return
        index[new] = frame

    def _handle_client_id_change(self, frame, previous_id, new_id):
        self._ensure_frame_id_maps()
        self._update_frame_id_index(self._client_frames_by_id, frame, previous_id, new_id)

    def _handle_team_id_change(self, frame, previous_id, new_id):
        self._ensure_frame_id_maps()
        self._update_frame_id_index(self._team_frames_by_id, frame, previous_id, new_id)

    def _handle_product_id_change(self, frame, previous_id, new_id):
        self._ensure_frame_id_maps()
        self._update_frame_id_index(self._product_frames_by_id, frame, previous_id, new_id)

    def _rebuild_frame_id_indexes(self):
        self._ensure_frame_id_maps()
        def _rebuild(target, frames):
            target.clear()
            for frame in frames:
                identifier = self._normalize_identifier(frame.id_var.get() if hasattr(frame, 'id_var') else '')
                if hasattr(frame, '_last_tracked_id'):
                    frame._last_tracked_id = identifier
                if identifier:
                    target[identifier] = frame

        _rebuild(self._client_frames_by_id, self.client_frames)
        _rebuild(self._team_frames_by_id, self.team_frames)
        _rebuild(self._product_frames_by_id, self.product_frames)

    def _ensure_frame_id_maps(self):
        if not hasattr(self, '_client_frames_by_id'):
            self._client_frames_by_id = {}
        if not hasattr(self, '_team_frames_by_id'):
            self._team_frames_by_id = {}
        if not hasattr(self, '_product_frames_by_id'):
            self._product_frames_by_id = {}

    def _find_client_frame(self, client_id):
        client_id = self._normalize_identifier(client_id)
        if not client_id:
            return None
        return getattr(self, '_client_frames_by_id', {}).get(client_id)

    def _find_team_frame(self, collaborator_id):
        collaborator_id = self._normalize_identifier(collaborator_id)
        if not collaborator_id:
            return None
        return getattr(self, '_team_frames_by_id', {}).get(collaborator_id)

    def _find_product_frame(self, product_id):
        product_id = self._normalize_identifier(product_id)
        if not product_id:
            return None
        return getattr(self, '_product_frames_by_id', {}).get(product_id)

    def _obtain_client_slot_for_import(self):
        """Obtiene un ``ClientFrame`` vacío o crea uno nuevo para importación.

        Paso a paso:
            1. Recorre la lista existente de clientes y detecta el primero
               cuyo ``id_cliente`` esté en blanco.
            2. Si encuentra un espacio vacío, se reutiliza para mostrar los
               datos recién importados (esto evita que el usuario piense que no
               se cargó nada por tener clientes vacíos al inicio).
            3. Si no existe un espacio vacío, se invoca ``add_client`` para
               crear un nuevo marco y finalmente se devuelve.

        Returns:
            ClientFrame: Instancia lista para llenarse con datos externos.

        Ejemplo::

            slot = self._obtain_client_slot_for_import()
            slot.id_var.set("12345678")
        """

        for frame in self.client_frames:
            if not frame.id_var.get().strip():
                return frame
        self.add_client()
        return self.client_frames[-1]

    def _obtain_team_slot_for_import(self):
        for frame in self.team_frames:
            if not frame.id_var.get().strip():
                return frame
        self.add_team()
        return self.team_frames[-1]

    def _obtain_product_slot_for_import(self):
        for frame in self.product_frames:
            if not frame.id_var.get().strip():
                return frame
        self.add_product(initialize_rows=False)
        new_frame = self.product_frames[-1]
        return new_frame

    def _obtain_involvement_slot(self, product_frame):
        empty = next((inv for inv in product_frame.involvements if not inv.team_var.get().strip()), None)
        if empty:
            return empty
        product_frame.add_involvement()
        return product_frame.involvements[-1]

    def _trigger_import_id_refresh(self, frame, identifier, notify_on_missing=False, preserve_existing=False):
        """Ejecuta ``on_id_change`` tras importaciones evitando mensajes redundantes.

        Args:
            frame: Instancia del frame que contiene el campo ID.
            identifier (str): ID normalizado que se está cargando.
            notify_on_missing (bool): Si es ``True`` se propaga ``from_focus=True``
                para que los cuadros de diálogo de inexistencia aparezcan igual que
                cuando el usuario edita el campo manualmente.
            preserve_existing (bool): Si es ``True`` los campos con datos
                recientes no se sobreescriben durante el autopoblado.
        """

        identifier = (identifier or '').strip()
        if identifier and hasattr(frame, 'on_id_change'):
            frame.on_id_change(from_focus=notify_on_missing, preserve_existing=preserve_existing)

    def _sync_product_lookup_claim_fields(self, frame, product_id):
        """Actualiza ``product_lookup`` con la lista de reclamos visibles."""

        if not frame:
            return
        product_id = (product_id or '').strip()
        if not product_id:
            return
        claim_values = [claim.get_data() for claim in getattr(frame, 'claims', [])]
        lookups = []
        if isinstance(self.product_lookup, dict):
            lookups.append(self.product_lookup)
        frame_lookup = getattr(frame, 'product_lookup', None)
        if isinstance(frame_lookup, dict) and frame_lookup is not self.product_lookup:
            lookups.append(frame_lookup)
        for lookup in lookups:
            entry = lookup.setdefault(product_id, {})
            entry['reclamos'] = claim_values

    def _populate_client_frame_from_row(self, frame, row, preserve_existing=False):
        """Traslada los datos de una fila CSV a un ``ClientFrame``.

        Cada línea de este método tiene como fin dejar explícito qué campo se
        está poblando y por qué::

            1. Se normaliza el texto con ``strip`` para evitar espacios.
            2. Se actualiza el ``StringVar`` correspondiente en el frame.
            3. Se sincroniza el selector múltiple de ``accionado``.
            4. Se actualiza ``client_lookup`` para futuros autopoblados.

        Args:
            frame (ClientFrame): Cliente objetivo.
            row (dict): Fila leída por ``csv.DictReader``.
            preserve_existing (bool): Si es ``True`` solo completa campos vacíos.

        Ejemplo::

            fila = {"id_cliente": "123", "telefonos": "999"}
            self._populate_client_frame_from_row(cliente, fila)
        """

        id_cliente = (row.get('id_cliente') or row.get('IdCliente') or '').strip()
        frame.id_var.set(id_cliente)
        nombres_val = (row.get('nombres') or row.get('nombre') or '').strip()
        if nombres_val and should_autofill_field(frame.nombres_var.get(), preserve_existing):
            frame.nombres_var.set(nombres_val)
        elif not nombres_val and not preserve_existing:
            frame.nombres_var.set('')
        apellidos_val = (row.get('apellidos') or row.get('apellido') or '').strip()
        if apellidos_val and should_autofill_field(frame.apellidos_var.get(), preserve_existing):
            frame.apellidos_var.set(apellidos_val)
        elif not apellidos_val and not preserve_existing:
            frame.apellidos_var.set('')
        tipo_id = (row.get('tipo_id') or row.get('TipoID') or '').strip()
        if tipo_id and should_autofill_field(frame.tipo_id_var.get(), preserve_existing):
            frame.tipo_id_var.set(tipo_id)
        elif not tipo_id and not preserve_existing:
            frame.tipo_id_var.set('')
        flag_value = (row.get('flag') or row.get('Flag') or '').strip()
        if flag_value and should_autofill_field(frame.flag_var.get(), preserve_existing):
            frame.flag_var.set(flag_value)
        elif not flag_value and not preserve_existing:
            frame.flag_var.set('')
        telefonos = (row.get('telefonos') or row.get('Telefono') or '').strip()
        if telefonos and should_autofill_field(frame.telefonos_var.get(), preserve_existing):
            frame.telefonos_var.set(telefonos)
        elif not telefonos and not preserve_existing:
            frame.telefonos_var.set('')
        correos = (row.get('correos') or row.get('Correo') or '').strip()
        if correos and should_autofill_field(frame.correos_var.get(), preserve_existing):
            frame.correos_var.set(correos)
        elif not correos and not preserve_existing:
            frame.correos_var.set('')
        direcciones = (row.get('direcciones') or row.get('Direccion') or '').strip()
        if direcciones and should_autofill_field(frame.direcciones_var.get(), preserve_existing):
            frame.direcciones_var.set(direcciones)
        elif not direcciones and not preserve_existing:
            frame.direcciones_var.set('')
        accionado_val = (row.get('accionado') or row.get('Accionado') or '').strip()
        if accionado_val and should_autofill_field(frame.accionado_var.get(), preserve_existing):
            frame.set_accionado_from_text(accionado_val)
        elif not accionado_val and not preserve_existing:
            frame.set_accionado_from_text('')
        accionado_final = frame.accionado_var.get().strip()
        self.client_lookup[id_cliente] = {
            'nombres': frame.nombres_var.get(),
            'apellidos': frame.apellidos_var.get(),
            'tipo_id': frame.tipo_id_var.get(),
            'flag': frame.flag_var.get(),
            'telefonos': frame.telefonos_var.get(),
            'correos': frame.correos_var.get(),
            'direcciones': frame.direcciones_var.get(),
            'accionado': accionado_final,
        }

    def _populate_team_frame_from_row(self, frame, row, preserve_existing: bool = False):
        id_col = (
            row.get('id_colaborador')
            or row.get('IdColaborador')
            or row.get('IdTeamMember')
            or row.get('id_col')
            or ''
        ).strip()
        normalized_id = self._normalize_identifier(id_col)
        frame.id_var.set(normalized_id or id_col)
        nombres_val = (row.get('nombres') or row.get('nombre') or '').strip()
        if nombres_val and should_autofill_field(frame.nombres_var.get(), preserve_existing):
            frame.nombres_var.set(nombres_val)
        elif not nombres_val and not preserve_existing:
            frame.nombres_var.set('')
        apellidos_val = (row.get('apellidos') or row.get('apellido') or '').strip()
        if apellidos_val and should_autofill_field(frame.apellidos_var.get(), preserve_existing):
            frame.apellidos_var.set(apellidos_val)
        elif not apellidos_val and not preserve_existing:
            frame.apellidos_var.set('')
        flag_val = (
            row.get('flag_colaborador')
            or row.get('flag')
            or row.get('Flag')
            or 'No aplica'
        ).strip()
        frame.flag_var.set(flag_val or 'No aplica')
        division_val = (row.get('division') or '').strip()
        if division_val and should_autofill_field(frame.division_var.get(), preserve_existing):
            frame.division_var.set(division_val)
        elif not division_val and not preserve_existing:
            frame.division_var.set('')
        area_val = (row.get('area') or '').strip()
        if area_val and should_autofill_field(frame.area_var.get(), preserve_existing):
            frame.area_var.set(area_val)
        elif not area_val and not preserve_existing:
            frame.area_var.set('')
        servicio_val = (row.get('servicio') or '').strip()
        if servicio_val and should_autofill_field(frame.servicio_var.get(), preserve_existing):
            frame.servicio_var.set(servicio_val)
        elif not servicio_val and not preserve_existing:
            frame.servicio_var.set('')
        puesto_val = (row.get('puesto') or '').strip()
        if puesto_val and should_autofill_field(frame.puesto_var.get(), preserve_existing):
            frame.puesto_var.set(puesto_val)
        elif not puesto_val and not preserve_existing:
            frame.puesto_var.set('')
        fecha_inm_val = (row.get('fecha_carta_inmediatez') or '').strip()
        if fecha_inm_val and should_autofill_field(frame.fecha_carta_inmediatez_var.get(), preserve_existing):
            frame.fecha_carta_inmediatez_var.set(fecha_inm_val)
        elif not fecha_inm_val and not preserve_existing:
            frame.fecha_carta_inmediatez_var.set('')
        fecha_ren_val = (row.get('fecha_carta_renuncia') or '').strip()
        if fecha_ren_val and should_autofill_field(frame.fecha_carta_renuncia_var.get(), preserve_existing):
            frame.fecha_carta_renuncia_var.set(fecha_ren_val)
        elif not fecha_ren_val and not preserve_existing:
            frame.fecha_carta_renuncia_var.set('')
        nombre_agencia_val = (row.get('nombre_agencia') or '').strip()
        if nombre_agencia_val and should_autofill_field(frame.nombre_agencia_var.get(), preserve_existing):
            frame.nombre_agencia_var.set(nombre_agencia_val)
        elif not nombre_agencia_val and not preserve_existing:
            frame.nombre_agencia_var.set('')
        codigo_agencia_val = (row.get('codigo_agencia') or '').strip()
        if codigo_agencia_val and should_autofill_field(frame.codigo_agencia_var.get(), preserve_existing):
            frame.codigo_agencia_var.set(codigo_agencia_val)
        elif not codigo_agencia_val and not preserve_existing:
            frame.codigo_agencia_var.set('')
        frame.tipo_falta_var.set((row.get('tipo_falta') or '').strip() or 'No aplica')
        frame.tipo_sancion_var.set((row.get('tipo_sancion') or '').strip() or 'No aplica')
        lookup_key = normalized_id or id_col
        if lookup_key:
            self.team_lookup[lookup_key] = {
                'nombres': frame.nombres_var.get(),
                'apellidos': frame.apellidos_var.get(),
                'division': frame.division_var.get(),
                'area': frame.area_var.get(),
                'servicio': frame.servicio_var.get(),
                'puesto': frame.puesto_var.get(),
                'fecha_carta_inmediatez': frame.fecha_carta_inmediatez_var.get(),
                'fecha_carta_renuncia': frame.fecha_carta_renuncia_var.get(),
                'nombre_agencia': frame.nombre_agencia_var.get(),
                'codigo_agencia': frame.codigo_agencia_var.get(),
            }

    def _populate_product_frame_from_row(self, frame, row):
        product_id = (row.get('id_producto') or row.get('IdProducto') or '').strip()
        if not product_id:
            return
        frame.id_var.set(product_id)
        client_id = (row.get('id_cliente') or row.get('IdCliente') or '').strip()
        if client_id:
            values = list(frame.client_cb['values'])
            if client_id not in values:
                values.append(client_id)
                frame.client_cb['values'] = values
            frame.client_var.set(client_id)
            frame.client_cb.set(client_id)
        cat1 = (row.get('categoria1') or '').strip()
        cat2 = (row.get('categoria2') or '').strip()
        mod = (row.get('modalidad') or '').strip()
        if cat1:
            if cat1 in TAXONOMIA:
                if frame.cat1_var.get() != cat1:
                    frame.cat1_var.set(cat1)
                    frame.on_cat1_change()
            else:
                self._notify_taxonomy_warning(
                    f"Producto {product_id}: la categoría 1 '{cat1}' no está en la taxonomía."
                )
                frame.cat1_var.set(cat1)
        if cat2:
            if cat1 in TAXONOMIA and cat2 in TAXONOMIA[cat1]:
                frame.cat2_var.set(cat2)
                frame.cat2_cb.set(cat2)
                frame.on_cat2_change()
            else:
                self._notify_taxonomy_warning(
                    f"Producto {product_id}: la categoría 2 '{cat2}' no corresponde a {cat1}."
                )
                frame.cat2_var.set(cat2)
        if mod:
            valid_mods = TAXONOMIA.get(cat1, {}).get(cat2, [])
            if mod in valid_mods:
                frame.mod_var.set(mod)
                frame.mod_cb.set(mod)
            else:
                self._notify_taxonomy_warning(
                    f"Producto {product_id}: la modalidad '{mod}' no corresponde a {cat1}/{cat2}."
                )
                frame.mod_var.set(mod)
        canal = (row.get('canal') or '').strip()
        if canal in CANAL_LIST:
            frame.canal_var.set(canal)
        proceso = (row.get('proceso') or '').strip()
        if proceso in PROCESO_LIST:
            frame.proceso_var.set(proceso)
        tipo_prod = (row.get('tipo_producto') or row.get('tipoProducto') or '').strip()
        if tipo_prod:
            resolved_tipo = resolve_catalog_product_type(tipo_prod)
            if resolved_tipo:
                frame.tipo_prod_var.set(resolved_tipo)
            else:
                self._notify_taxonomy_warning(
                    f"Producto {product_id}: el tipo de producto '{tipo_prod}' no está en el catálogo CM."
                )
        fecha_occ = (row.get('fecha_ocurrencia') or '').strip()
        if fecha_occ:
            frame.fecha_oc_var.set(fecha_occ)
        fecha_desc = (row.get('fecha_descubrimiento') or '').strip()
        if fecha_desc:
            frame.fecha_desc_var.set(fecha_desc)
        frame.monto_inv_var.set((row.get('monto_investigado') or '').strip())
        moneda = (row.get('tipo_moneda') or '').strip()
        if moneda in TIPO_MONEDA_LIST:
            frame.moneda_var.set(moneda)
        frame.monto_perdida_var.set((row.get('monto_perdida_fraude') or '').strip())
        frame.monto_falla_var.set((row.get('monto_falla_procesos') or '').strip())
        frame.monto_cont_var.set((row.get('monto_contingencia') or '').strip())
        frame.monto_rec_var.set((row.get('monto_recuperado') or '').strip())
        frame.monto_pago_var.set((row.get('monto_pago_deuda') or '').strip())
        frame.set_claims_from_data(frame.extract_claims_from_payload(row))
        frame.persist_lookup_snapshot()

    def _ensure_client_exists(self, client_id, row_data=None):
        client_id = (client_id or '').strip()
        if not client_id:
            return None, False
        frame = self._find_client_frame(client_id)
        created = False
        if not frame:
            frame = self._obtain_client_slot_for_import()
            created = True
        if created and row_data:
            payload = dict(row_data)
            payload['id_cliente'] = client_id
            self._populate_client_frame_from_row(frame, payload)
        return frame, created

    def _ensure_team_member_exists(self, collaborator_id, row_data=None):
        collaborator_id = (collaborator_id or '').strip()
        if not collaborator_id:
            return None, False
        frame = self._find_team_frame(collaborator_id)
        created = False
        if not frame:
            frame = self._obtain_team_slot_for_import()
            created = True
        if created and row_data:
            payload = dict(row_data)
            payload['id_colaborador'] = collaborator_id
            self._populate_team_frame_from_row(frame, payload)
        return frame, created

    @staticmethod
    def _format_import_summary(tipo, nuevos, actualizados, duplicados, errores):
        lines = [
            f"Importación completada de {tipo}:",
            f"{nuevos} registros nuevos",
            f"{actualizados} registros actualizados",
            f"{duplicados} duplicados omitidos",
            f"{errores} filas con errores",
        ]
        return "\n".join(lines)

    @staticmethod
    def _collect_existing_ids(frames, attr_name="id_var"):
        identifiers = set()
        for frame in frames or []:
            attr = getattr(frame, attr_name, None)
            getter = getattr(attr, "get", None)
            if getter is None:
                continue
            value = (getter() or "").strip()
            if value:
                identifiers.add(value)
        return identifiers

    def _apply_client_import_payload(self, entries):
        nuevos = 0
        actualizados = 0
        duplicados = 0
        errores = 0
        missing_ids = []
        existing_ids = self._collect_existing_ids(self.client_frames)
        seen_ids = set()
        for entry in entries or []:
            hydrated = entry.get('row', {})
            found = entry.get('found', False)
            id_cliente = (hydrated.get('id_cliente') or '').strip()
            if not id_cliente:
                errores += 1
                continue
            if id_cliente in seen_ids or id_cliente in existing_ids:
                duplicados += 1
                continue
            seen_ids.add(id_cliente)
            existing_ids.add(id_cliente)
            frame = self._obtain_client_slot_for_import()
            created = True
            self._populate_client_frame_from_row(frame, hydrated, preserve_existing=True)
            self._trigger_import_id_refresh(
                frame,
                id_cliente,
                notify_on_missing=True,
                preserve_existing=False,
            )
            if created:
                nuevos += 1
            if not found and 'id_cliente' in self.detail_catalogs:
                missing_ids.append(id_cliente)
        self._notify_dataset_changed(summary_sections="clientes")
        total = nuevos + actualizados
        log_event(
            "navegacion",
            f"Clientes importados desde CSV: total={total}, nuevos={nuevos}, actualizados={actualizados}, duplicados={duplicados}, errores={errores}",
            self.logs,
        )
        if total:
            self.sync_main_form_after_import("clientes")
            summary = self._format_import_summary("clientes", nuevos, actualizados, duplicados, errores)
            messagebox.showinfo("Importación completa", summary)
        else:
            messagebox.showwarning("Sin cambios", "El archivo no aportó clientes nuevos.")
        self._report_missing_detail_ids("clientes", missing_ids)

    def _apply_team_import_payload(self, entries):
        nuevos = 0
        actualizados = 0
        duplicados = 0
        errores = 0
        missing_ids = []
        existing_ids = self._collect_existing_ids(self.team_frames)
        seen_ids = set()
        for entry in entries or []:
            hydrated = entry.get('row', {})
            found = entry.get('found', False)
            collaborator_id = (hydrated.get('id_colaborador') or '').strip()
            if not collaborator_id:
                errores += 1
                continue
            if collaborator_id in seen_ids or collaborator_id in existing_ids:
                duplicados += 1
                continue
            seen_ids.add(collaborator_id)
            existing_ids.add(collaborator_id)
            frame = self._obtain_team_slot_for_import()
            created = True
            self._populate_team_frame_from_row(frame, hydrated)
            self._trigger_import_id_refresh(
                frame,
                collaborator_id,
                notify_on_missing=True,
                preserve_existing=False,
            )
            if created:
                nuevos += 1
            if not found and 'id_colaborador' in self.detail_catalogs:
                missing_ids.append(collaborator_id)
        self._notify_dataset_changed(summary_sections="colaboradores")
        total = nuevos + actualizados
        log_event(
            "navegacion",
            f"Colaboradores importados desde CSV: total={total}, nuevos={nuevos}, actualizados={actualizados}, duplicados={duplicados}, errores={errores}",
            self.logs,
        )
        if total:
            self.sync_main_form_after_import("colaboradores")
            summary = self._format_import_summary("colaboradores", nuevos, actualizados, duplicados, errores)
            messagebox.showinfo("Importación completa", summary)
        else:
            messagebox.showwarning("Sin cambios", "No se encontraron colaboradores nuevos en el archivo.")
        self._report_missing_detail_ids("colaboradores", missing_ids)

    def _apply_product_import_payload(self, entries):
        nuevos = 0
        actualizados = 0
        duplicados = 0
        errores = 0
        missing_ids = []
        existing_ids = self._collect_existing_ids(self.product_frames)
        seen_ids = set()
        for entry in entries or []:
            hydrated = entry.get('row', {})
            found = entry.get('found', False)
            product_id = (hydrated.get('id_producto') or '').strip()
            if not product_id:
                errores += 1
                continue
            if product_id in seen_ids or product_id in existing_ids:
                duplicados += 1
                continue
            seen_ids.add(product_id)
            existing_ids.add(product_id)
            frame = self._obtain_product_slot_for_import()
            created = True
            client_id = (hydrated.get('id_cliente') or '').strip()
            if client_id:
                client_details, _ = self._hydrate_row_from_details({'id_cliente': client_id}, 'id_cliente', CLIENT_ID_ALIASES)
                self._ensure_client_exists(client_id, client_details)
            self._populate_product_frame_from_row(frame, hydrated)
            self._trigger_import_id_refresh(
                frame,
                product_id,
                notify_on_missing=True,
                preserve_existing=False,
            )
            if created:
                nuevos += 1
            if not found and 'id_producto' in self.detail_catalogs:
                missing_ids.append(product_id)
        self._notify_dataset_changed(summary_sections="productos")
        total = nuevos + actualizados
        log_event(
            "navegacion",
            f"Productos importados desde CSV: total={total}, nuevos={nuevos}, actualizados={actualizados}, duplicados={duplicados}, errores={errores}",
            self.logs,
        )
        if total:
            self.sync_main_form_after_import("productos")
            summary = self._format_import_summary("productos", nuevos, actualizados, duplicados, errores)
            messagebox.showinfo("Importación completa", summary)
        else:
            messagebox.showwarning("Sin cambios", "No se detectaron productos nuevos en el archivo.")
        self._report_missing_detail_ids("productos", missing_ids)
        self._run_duplicate_check_post_load()

    def _apply_combined_import_payload(self, entries):
        created_records = False
        missing_clients = []
        missing_team = []
        missing_products = []
        for entry in entries or []:
            client_row = dict(entry.get('client_row') or {})
            client_found = entry.get('client_found', False)
            client_id = (client_row.get('id_cliente') or '').strip()
            if client_id:
                if not client_row.get('flag') and client_row.get('flag_cliente'):
                    client_row['flag'] = client_row.get('flag_cliente')
                raw_row = entry.get('raw_row', {}) or {}
                for source_key, target_key in (
                    ('nombres_cliente', 'nombres'),
                    ('apellidos_cliente', 'apellidos'),
                ):
                    if not client_row.get(target_key) and raw_row.get(source_key):
                        client_row[target_key] = raw_row[source_key]
                for key in ('nombres', 'apellidos', 'telefonos', 'correos', 'direcciones', 'accionado', 'tipo_id'):
                    value = client_row.get(key)
                    if not value and raw_row.get(key):
                        client_row[key] = raw_row[key]
                client_frame, created_client = self._ensure_client_exists(client_id, client_row)
                if created_client:
                    self._trigger_import_id_refresh(
                        client_frame,
                        client_id,
                        notify_on_missing=False,
                        preserve_existing=False,
                    )
                created_records = created_records or created_client
                if not client_found and 'id_cliente' in self.detail_catalogs:
                    missing_clients.append(client_id)
            team_row = dict(entry.get('team_row') or {})
            team_found = entry.get('team_found', False)
            collaborator_id = (team_row.get('id_colaborador') or '').strip()
            if collaborator_id:
                team_frame, created_team = self._ensure_team_member_exists(collaborator_id, team_row)
                if created_team:
                    self._trigger_import_id_refresh(
                        team_frame,
                        collaborator_id,
                        notify_on_missing=False,
                        preserve_existing=False,
                    )
                created_records = created_records or created_team
                if not team_found and 'id_colaborador' in self.detail_catalogs:
                    missing_team.append(collaborator_id)
            product_row = dict(entry.get('product_row') or {})
            product_found = entry.get('product_found', False)
            product_id = (product_row.get('id_producto') or '').strip()
            product_frame = None
            if product_id:
                product_frame = self._find_product_frame(product_id)
                new_product = False
                if not product_frame:
                    product_frame = self._obtain_product_slot_for_import()
                    new_product = True
                client_for_product = (product_row.get('id_cliente') or '').strip()
                if client_for_product:
                    client_details, _ = self._hydrate_row_from_details({'id_cliente': client_for_product}, 'id_cliente', CLIENT_ID_ALIASES)
                    self._ensure_client_exists(client_for_product, client_details)
                self._populate_product_frame_from_row(product_frame, product_row)
                self._trigger_import_id_refresh(
                    product_frame,
                    product_id,
                    notify_on_missing=False,
                    preserve_existing=False,
                )
                created_records = created_records or new_product
                if not product_found and 'id_producto' in self.detail_catalogs:
                    missing_products.append(product_id)
            involvement_pairs = entry.get('involvement_pairs') or []
            if product_frame and involvement_pairs:
                for collab_id, amount in involvement_pairs:
                    collab_id = (collab_id or '').strip()
                    if not collab_id:
                        continue
                    collab_details, collab_found = self._hydrate_row_from_details({'id_colaborador': collab_id}, 'id_colaborador', TEAM_ID_ALIASES)
                    _, created_team = self._ensure_team_member_exists(collab_id, collab_details)
                    created_records = created_records or created_team
                    if not collab_found and 'id_colaborador' in self.detail_catalogs:
                        missing_team.append(collab_id)
                    inv_row = next((inv for inv in product_frame.involvements if inv.team_var.get().strip() == collab_id), None)
                    if not inv_row:
                        inv_row = self._obtain_involvement_slot(product_frame)
                    inv_row.team_var.set(collab_id)
                    amount_text = (amount or '').strip()
                    label = (
                        f"Monto asignado del colaborador {collab_id or 'sin ID'} "
                        f"en el producto {product_id or 'sin ID'}"
                    )
                    error, _amount, normalized_text = validate_money_bounds(
                        amount_text,
                        label,
                    )
                    if error:
                        raise ValueError(error)
                    inv_row.monto_var.set(normalized_text or amount_text)
                    created_records = True
        self._notify_dataset_changed()
        log_event("navegacion", "Datos combinados importados desde CSV", self.logs)
        if created_records:
            self.sync_main_form_after_import("datos combinados")
            messagebox.showinfo("Importación completa", "Datos combinados importados correctamente.")
        else:
            messagebox.showwarning("Sin cambios", "No se detectaron registros nuevos en el archivo.")
        self._report_missing_detail_ids("clientes", missing_clients)
        self._report_missing_detail_ids("colaboradores", missing_team)
        self._report_missing_detail_ids("productos", missing_products)
        self._run_duplicate_check_post_load()

    def _apply_risk_import_payload(self, entries):
        nuevos = 0
        duplicados = 0
        errores = 0
        existing_ids = self._collect_existing_ids(self.risk_frames)
        seen_ids = set()
        for hydrated in entries or []:
            rid = (hydrated.get('id_riesgo') or '').strip()
            if not rid:
                errores += 1
                continue
            if rid in seen_ids or rid in existing_ids:
                duplicados += 1
                continue
            seen_ids.add(rid)
            existing_ids.add(rid)
            self.add_risk()
            rf = self.risk_frames[-1]
            rf.id_var.set(rid)
            rf.lider_var.set((hydrated.get('lider') or '').strip())
            rf.descripcion_var.set((hydrated.get('descripcion') or '').strip())
            crit = (hydrated.get('criticidad') or '').strip()
            if crit in CRITICIDAD_LIST:
                rf.criticidad_var.set(crit)
            rf.exposicion_var.set((hydrated.get('exposicion_residual') or '').strip())
            rf.planes_var.set((hydrated.get('planes_accion') or '').strip())
            nuevos += 1
        self._notify_dataset_changed(summary_sections="riesgos")
        total = nuevos
        log_event(
            "navegacion",
            f"Riesgos importados desde CSV: total={total}, nuevos={nuevos}, actualizados=0, duplicados={duplicados}, errores={errores}",
            self.logs,
        )
        if total:
            summary = self._format_import_summary("riesgos", nuevos, 0, duplicados, errores)
            messagebox.showinfo("Importación completa", summary)
        else:
            messagebox.showwarning("Sin cambios", "No se añadieron riesgos nuevos.")

    def _apply_norm_import_payload(self, entries):
        nuevos = 0
        duplicados = 0
        errores = 0
        existing_ids = self._collect_existing_ids(self.norm_frames)
        seen_ids = set()
        for hydrated in entries or []:
            nid = (hydrated.get('id_norma') or '').strip()
            if not nid:
                errores += 1
                continue
            if nid in seen_ids or nid in existing_ids:
                duplicados += 1
                continue
            seen_ids.add(nid)
            existing_ids.add(nid)
            self.add_norm()
            nf = self.norm_frames[-1]
            nf.id_var.set(nid)
            nf.descripcion_var.set((hydrated.get('descripcion') or '').strip())
            nf.fecha_var.set((hydrated.get('fecha_vigencia') or '').strip())
            nuevos += 1
        self._refresh_shared_norm_tree()
        self._notify_dataset_changed(summary_sections="normas")
        total = nuevos
        log_event(
            "navegacion",
            f"Normas importadas desde CSV: total={total}, nuevos={nuevos}, actualizados=0, duplicados={duplicados}, errores={errores}",
            self.logs,
        )
        if total:
            summary = self._format_import_summary("normas", nuevos, 0, duplicados, errores)
            messagebox.showinfo("Importación completa", summary)
        else:
            messagebox.showwarning("Sin cambios", "No se añadieron normas nuevas.")

    def _apply_claim_import_payload(self, entries):
        nuevos = 0
        duplicados = 0
        errores = 0
        missing_products = []
        existing_claims = set()
        for product_frame in self.product_frames:
            pid_var = getattr(product_frame, 'id_var', None)
            pid_value = (pid_var.get() if hasattr(pid_var, 'get') else "").strip()
            if not pid_value:
                continue
            for claim in getattr(product_frame, 'claims', []):
                cid_var = getattr(claim, 'id_var', None)
                cid_value = (cid_var.get() if hasattr(cid_var, 'get') else "").strip()
                if cid_value:
                    existing_claims.add((pid_value, cid_value))
        seen_claims = set()
        for entry in entries or []:
            hydrated = entry.get('row', {})
            found = entry.get('found', False)
            product_id = (hydrated.get('id_producto') or '').strip()
            if not product_id:
                errores += 1
                continue
            product_frame = self._find_product_frame(product_id)
            new_product = False
            if not product_frame:
                product_frame = self._obtain_product_slot_for_import()
                new_product = True
            client_id = (hydrated.get('id_cliente') or '').strip()
            if client_id:
                client_details, _ = self._hydrate_row_from_details({'id_cliente': client_id}, 'id_cliente', CLIENT_ID_ALIASES)
                self._ensure_client_exists(client_id, client_details)
            if new_product:
                self._populate_product_frame_from_row(product_frame, hydrated)
            if product_frame:
                self._trigger_import_id_refresh(
                    product_frame,
                    product_id,
                    preserve_existing=False,
                )
            claim_payload = {
                'id_reclamo': (hydrated.get('id_reclamo') or '').strip(),
                'nombre_analitica': (hydrated.get('nombre_analitica') or '').strip(),
                'codigo_analitica': (hydrated.get('codigo_analitica') or '').strip(),
            }
            claim_id = claim_payload['id_reclamo']
            if not any(claim_payload.values()):
                continue
            if not claim_id:
                errores += 1
                continue
            claim_key = (product_id, claim_id)
            if claim_key in seen_claims or claim_key in existing_claims:
                duplicados += 1
                continue
            seen_claims.add(claim_key)
            existing_claims.add(claim_key)
            target = product_frame.find_claim_by_id(claim_id)
            if not target:
                target = product_frame.obtain_claim_slot()
            target.set_data(claim_payload)
            self._sync_product_lookup_claim_fields(product_frame, product_id)
            product_frame.persist_lookup_snapshot()
            nuevos += 1
            if not found and 'id_producto' in self.detail_catalogs:
                missing_products.append(product_id)
        self._notify_dataset_changed(summary_sections="reclamos")
        total = nuevos
        log_event(
            "navegacion",
            f"Reclamos importados desde CSV: total={total}, nuevos={nuevos}, actualizados=0, duplicados={duplicados}, errores={errores}",
            self.logs,
        )
        if total:
            self.sync_main_form_after_import("reclamos")
            summary = self._format_import_summary("reclamos", nuevos, 0, duplicados, errores)
            messagebox.showinfo("Importación completa", summary)
        else:
            messagebox.showwarning("Sin cambios", "Ningún reclamo se pudo vincular a productos existentes.")
        self._report_missing_detail_ids("productos", missing_products)
        self._run_duplicate_check_post_load()

    def import_clients(self, filename=None):
        """Importa clientes desde un archivo CSV y los añade a la lista."""

        log_event("navegacion", "Usuario pulsó importar clientes", self.logs)
        filename = filename or self._select_csv_file("clientes", "Seleccionar CSV de clientes")
        if not filename:
            return
        if not self._validate_import_headers(filename, "clientes"):
            return
        log_event("navegacion", "Inició importación de clientes", self.logs)
        def worker():
            payload = []
            for row in iter_massive_csv_rows(filename):
                hydrated, found = self._hydrate_row_from_details(row, 'id_cliente', CLIENT_ID_ALIASES)
                id_cliente = (hydrated.get('id_cliente') or '').strip()
                if not id_cliente:
                    continue
                payload.append({'row': hydrated, 'found': found})
            return payload

        self._start_background_import(
            "clientes",
            getattr(self, 'import_clients_button', None),
            worker,
            self._apply_client_import_payload,
            "No se pudo importar clientes",
        )

    def import_team_members(self, filename=None):
        """Importa colaboradores desde un archivo CSV y los añade a la lista."""

        log_event("navegacion", "Usuario pulsó importar colaboradores", self.logs)
        filename = filename or self._select_csv_file("colaboradores", "Seleccionar CSV de colaboradores")
        if not filename:
            return
        if not self._validate_import_headers(filename, "colaboradores"):
            return
        log_event("navegacion", "Inició importación de colaboradores", self.logs)
        def worker():
            payload = []
            for row in iter_massive_csv_rows(filename):
                hydrated, found = self._hydrate_row_from_details(row, 'id_colaborador', TEAM_ID_ALIASES)
                collaborator_id = (hydrated.get('id_colaborador') or '').strip()
                if not collaborator_id:
                    continue
                payload.append({'row': hydrated, 'found': found})
            return payload

        self._start_background_import(
            "colaboradores",
            getattr(self, 'import_team_button', None),
            worker,
            self._apply_team_import_payload,
            "No se pudo importar colaboradores",
        )

    def import_products(self, filename=None):
        """Importa productos desde un archivo CSV y los añade a la lista."""

        log_event("navegacion", "Usuario pulsó importar productos", self.logs)
        filename = filename or self._select_csv_file("productos", "Seleccionar CSV de productos")
        if not filename:
            return
        if not self._validate_import_headers(filename, "productos"):
            return
        log_event("navegacion", "Inició importación de productos", self.logs)
        def worker():
            payload = []
            for row in iter_massive_csv_rows(filename):
                hydrated, found = self._hydrate_row_from_details(row, 'id_producto', PRODUCT_ID_ALIASES)
                product_id = (hydrated.get('id_producto') or '').strip()
                if not product_id:
                    continue
                payload.append({'row': hydrated, 'found': found})
            return payload

        self._start_background_import(
            "productos",
            getattr(self, 'import_products_button', None),
            worker,
            self._apply_product_import_payload,
            "No se pudo importar productos",
        )

    # ---------------------------------------------------------------------
    # Autoguardado y carga

    def save_auto(self, data=None):
        """Guarda automáticamente el estado actual en un archivo JSON."""

        dataset = self._ensure_case_data(data or self.gather_data())
        try:
            with open(AUTOSAVE_FILE, 'w', encoding="utf-8") as f:
                json.dump(dataset.as_dict(), f, ensure_ascii=False, indent=2)
            self._handle_session_saved(dataset)
            self._show_success_toast(self._progress_bar, "Autoguardado listo")
        except Exception as ex:
            log_event("validacion", f"Error guardando autosave: {ex}", self.logs)
        self._schedule_summary_refresh(data=dataset)
        return dataset

    def load_autosave(self):
        """Carga el estado guardado automáticamente si el archivo existe."""

        def _iter_candidates():
            seen: set[Path] = set()
            autosave_path = Path(AUTOSAVE_FILE)
            primary_root = autosave_path.parent if autosave_path.parent else Path(BASE_DIR)
            search_roots = [primary_root]
            external_base = self._get_external_drive_path()
            if external_base:
                search_roots.append(Path(external_base))
            patterns = (autosave_path.name, "*autosave*.json", "*_temp_*.json")

            def _yield_matches(root: Path):
                for pattern in patterns:
                    yield from root.glob(pattern)

            for root in search_roots:
                try:
                    root_path = root.resolve()
                except OSError:
                    log_event("validacion", f"No se pudo resolver la ruta {root}", self.logs)
                    continue
                for base in (root_path,) + tuple(p for p in root_path.iterdir() if p.is_dir()):
                    try:
                        for path in _yield_matches(base):
                            try:
                                resolved = path.resolve()
                            except OSError:
                                continue
                            if resolved in seen or not path.is_file():
                                continue
                            seen.add(resolved)
                            yield path
                    except OSError as exc:
                        log_event("validacion", f"No se pudo explorar {base}: {exc}", self.logs)
                        continue

        candidates: list[tuple[float, Path]] = []
        for path in _iter_candidates():
            try:
                mtime = path.stat().st_mtime
            except OSError as exc:
                log_event("validacion", f"No se pudo leer metadatos de {path}: {exc}", self.logs)
                continue
            candidates.append((mtime, path))
        if not candidates:
            return
        candidates.sort(key=lambda item: item[0], reverse=True)

        def _warn_user(title: str, message: str) -> None:
            log_event("validacion", message, self.logs)
            if getattr(self, "_suppress_messagebox", False):
                return
            try:
                messagebox.showwarning(title, message)
            except tk.TclError:
                return

        def _notify_fallback(path: Path) -> None:
            message = (
                "El autosave más reciente no se pudo abrir; se restauró el respaldo "
                f"{path.name}."
            )
            self._last_autosave_notice = message
            log_event("navegacion", message, self.logs)
            if getattr(self, "_suppress_messagebox", False):
                return
            try:
                messagebox.showinfo("Autosave recuperado", message)
            except tk.TclError:
                return

        errors_detected = False
        for index, (_mtime, path) in enumerate(candidates):
            try:
                with path.open('r', encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("El autosave debe ser un objeto JSON válido")
                dataset = self._ensure_case_data(data)
                self.populate_from_data(dataset)
                case_id = (dataset.get("caso", {}) or {}).get("id_caso")
                self._update_window_title(case_id=case_id)
                self._schedule_summary_refresh(sections=self.summary_tables.keys(), data=dataset)
                self._flush_summary_refresh(sections=self.summary_tables.keys(), data=dataset)
                source_msg = f"Se cargó el autosave desde {path}"
                self._last_autosave_source = str(path)
                log_event("navegacion", source_msg, self.logs)
                self._display_toast(self.root, source_msg, duration_ms=2200)
                if errors_detected or index > 0:
                    _notify_fallback(path)
                return
            except Exception as ex:
                errors_detected = True
                _warn_user("Autosave inválido", f"No se pudo cargar {path.name}: {ex}")
                continue

        self._clear_case_state(save_autosave=False)
        _warn_user("Autosave no disponible", "No se pudo cargar ningún autosave válido; se restauró el formulario vacío.")

    def _handle_window_close(self):
        self.flush_autosave()
        self._cancel_summary_refresh_job()
        self.flush_logs_now(reschedule=False)
        with suppress(tk.TclError):
            self.root.destroy()

    def _schedule_log_flush(self) -> None:
        if not self._has_log_targets():
            return
        if self._log_flush_job_id is not None:
            return
        try:
            self._log_flush_job_id = self.root.after(
                self.LOG_FLUSH_INTERVAL_MS,
                self._on_log_flush_timer,
            )
        except tk.TclError:
            self._log_flush_job_id = None
            self._flush_log_queue_to_disk()

    def _on_log_flush_timer(self) -> None:
        self._log_flush_job_id = None
        self._flush_log_queue_to_disk()
        self._schedule_log_flush()

    def _cancel_log_flush_job(self) -> None:
        if self._log_flush_job_id is None:
            return
        try:
            self.root.after_cancel(self._log_flush_job_id)
        except tk.TclError:
            pass
        self._log_flush_job_id = None

    def flush_logs_now(self, reschedule: bool = True) -> None:
        self._cancel_log_flush_job()
        self._flush_log_queue_to_disk()
        if reschedule:
            self._schedule_log_flush()

    def _flush_log_queue_to_disk(self) -> None:
        if not self._has_log_targets():
            return
        self._emit_navigation_metrics()
        rows = drain_log_queue()
        if not rows:
            return
        errors = []
        if STORE_LOGS_LOCALLY and LOGS_FILE:
            try:
                self._append_log_rows(
                    LOGS_FILE,
                    rows,
                    track_attr="_log_file_initialized",
                )
            except OSError as exc:
                errors.append((LOGS_FILE, exc))
        external_path = self._resolve_external_log_target()
        if external_path:
            try:
                self._append_log_rows(
                    external_path,
                    rows,
                    track_attr="_external_log_file_initialized",
                )
            except OSError as exc:
                errors.append((external_path, exc))
        if errors:
            messages = [f"No se pudo escribir el log en {path}: {exc}" for path, exc in errors]
            for message in messages:
                log_event("validacion", message, self.logs)
            if not getattr(self, '_suppress_messagebox', False):
                messagebox.showwarning("Registro no guardado", "\n".join(messages))

    def _append_log_rows(self, file_path: str, rows, *, track_attr: Optional[str] = None) -> None:
        target = Path(file_path)
        if target.parent:
            target.parent.mkdir(parents=True, exist_ok=True)
        file_exists = target.exists()
        if track_attr:
            file_exists = getattr(self, track_attr, False) or file_exists
        with target.open('a', newline='', encoding='utf-8') as file_handle:
            writer = csv.DictWriter(file_handle, fieldnames=LOG_FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            writer.writerows([normalize_log_row(row) for row in rows])
        if track_attr:
            setattr(self, track_attr, True)

    def _log_navigation(self, message: str, autosave: bool = False) -> None:
        log_event("navegacion", message, self.logs)
        if autosave:
            self.request_autosave()

    def _log_navigation_change(self, message: str) -> None:
        self._activate_progress_tracking()
        self._log_navigation(message, autosave=True)

    def _log_autofill_warning(self, message: str) -> None:
        if not message:
            return
        log_event("validacion", message, self.logs)

    def _compute_temp_signature(self, data: CaseData):
        dataset = self._ensure_case_data(data)
        payload = dataset.as_dict()
        case = payload.get("caso") or {}
        clients = payload.get("clientes", [])
        team = payload.get("colaboradores", [])
        products = payload.get("productos", [])
        reclamos = payload.get("reclamos", [])
        involucs = payload.get("involucramientos", [])
        encabezado = self._normalize_mapping_strings(payload.get("encabezado", {}))
        operaciones = self._normalize_table_rows(payload.get("operaciones", []))
        anexos = self._normalize_table_rows(payload.get("anexos", []))
        investigador = self._normalize_mapping_strings(case.get("investigador", {}))
        recomendaciones = self._normalize_recommendation_categories(
            payload.get("recomendaciones_categorias", {})
        )
        analysis = self._normalize_analysis_texts(payload.get("analisis", {}))
        analysis_signature = tuple(
            (
                name,
                value.get("text") if isinstance(value, Mapping) else "",
                tuple(
                    (tag.get("tag"), tag.get("start"), tag.get("end"))
                    for tag in (value.get("tags") if isinstance(value, Mapping) else [])
                ),
            )
            for name, value in sorted(analysis.items())
        )
        total_investigated = self._sum_investigated_amounts(products)
        return (
            str(case.get("id_caso", "")).strip(),
            str(case.get("tipo_informe", "")).strip(),
            str(case.get("fecha_de_ocurrencia", "")).strip(),
            len(clients),
            len(team),
            len(products),
            len([r for r in reclamos if r]),
            len([i for i in involucs if i]),
            total_investigated,
            tuple(sorted(encabezado.items())),
            tuple(tuple(sorted(row.items())) for row in operaciones),
            tuple(tuple(sorted(row.items())) for row in anexos),
            tuple(sorted(investigador.items())),
            tuple((key, tuple(values)) for key, values in sorted(recomendaciones.items())),
            analysis_signature,
        )

    def _sum_investigated_amounts(self, products: list[dict]) -> Decimal:
        total = Decimal("0")
        if not products:
            return total
        for product in products:
            if not isinstance(product, Mapping):
                continue
            amount = parse_decimal_amount(product.get("monto_investigado"))
            if amount is not None:
                total += amount
        return total

    def _should_persist_temp(self, signature, now: datetime) -> bool:
        last_signature = getattr(self, "_last_temp_signature", None)
        last_saved_at = getattr(self, "_last_temp_saved_at", None)
        if last_signature is None or last_saved_at is None:
            return True
        if signature != last_signature:
            return True
        elapsed = (now - last_saved_at).total_seconds()
        return elapsed >= TEMP_AUTOSAVE_DEBOUNCE_SECONDS

    def request_autosave(self) -> None:
        if not hasattr(self, "_autosave_job_id"):
            self._autosave_job_id = None
        if not hasattr(self, "_autosave_dirty"):
            self._autosave_dirty = False
        if not hasattr(self, "root") or self.root is None:
            return
        self._autosave_dirty = True
        if self._autosave_job_id is not None:
            return
        try:
            self._autosave_job_id = self.root.after(
                self.AUTOSAVE_DELAY_MS,
                self._perform_debounced_autosave,
            )
        except tk.TclError:
            self._autosave_job_id = None
            self.flush_autosave()

    def _perform_debounced_autosave(self) -> None:
        self._autosave_job_id = None
        if not self._autosave_dirty:
            return
        self._autosave_dirty = False
        dataset = self.save_auto()
        self.save_temp_version(dataset)

    def flush_autosave(self) -> None:
        if self._autosave_job_id is not None:
            try:
                self.root.after_cancel(self._autosave_job_id)
            except tk.TclError:
                pass
            self._autosave_job_id = None
        if self._autosave_dirty:
            self._autosave_dirty = False
            dataset = self.save_auto()
            self.save_temp_version(dataset)

    def _trim_all_temp_versions(self) -> None:
        base_dir = Path(BASE_DIR)
        if not base_dir.exists():
            return
        case_ids = set()
        for temp_file in base_dir.glob("*_temp_*.json"):
            try:
                name = temp_file.name
            except OSError:
                continue
            if "_temp_" not in name:
                continue
            case_ids.add(name.split("_temp_", 1)[0])
        for case_id in case_ids:
            self._trim_temp_versions(case_id)

    def _trim_temp_versions(self, case_id: str, preserve_filenames: Optional[set[str]] = None) -> None:
        if not case_id:
            case_id = "caso"
        base_dir = Path(BASE_DIR)
        cutoff = datetime.now() - timedelta(days=TEMP_AUTOSAVE_MAX_AGE_DAYS)
        preserve = preserve_filenames or set()
        files = sorted(
            base_dir.glob(f"{case_id}_temp_*.json"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        keep: list[Path] = []
        prune: list[Path] = []
        for temp_file in files:
            try:
                mtime = datetime.fromtimestamp(temp_file.stat().st_mtime)
            except OSError:
                continue
            if temp_file.name in preserve:
                keep.append(temp_file)
                continue
            if mtime < cutoff:
                prune.append(temp_file)
                continue
            if len(keep) < TEMP_AUTOSAVE_MAX_PER_CASE:
                keep.append(temp_file)
            else:
                prune.append(temp_file)
        self._archive_and_remove(case_id, prune, base_dir)
        keep_target = max(len(keep), len(preserve))
        self._trim_external_temp_versions(case_id, keep_target, cutoff, preserve)

    def _archive_and_remove(self, case_id: str, files: list[Path], base_dir: Path) -> None:
        if not files:
            return
        if TEMP_AUTOSAVE_COMPRESS_OLD:
            archive_path = base_dir / f"{case_id}_temp_archive.zip"
            try:
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(archive_path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
                    for file_path in files:
                        try:
                            archive.write(file_path, arcname=file_path.name)
                        except OSError:
                            continue
            except OSError:
                pass
        for file_path in files:
            with suppress(FileNotFoundError, OSError):
                file_path.unlink()

    def _trim_external_temp_versions(
        self, case_id: str, keep_count: int, cutoff: datetime, preserve_filenames: Optional[set[str]] = None
    ) -> None:
        external_base = self._get_external_drive_path()
        if not external_base:
            return
        case_folder = Path(external_base) / case_id
        if not case_folder.exists():
            return
        preserve = preserve_filenames or set()
        files = sorted(
            case_folder.glob(f"{case_id}_temp_*.json"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        kept = 0
        for temp_file in files:
            try:
                mtime = datetime.fromtimestamp(temp_file.stat().st_mtime)
            except OSError:
                continue
            if temp_file.name in preserve:
                kept += 1
                continue
            if mtime < cutoff or kept >= keep_count:
                with suppress(FileNotFoundError, OSError):
                    temp_file.unlink()
                continue
            kept += 1

    def load_version_dialog(self):
        """Abre un diálogo para cargar una versión previa del formulario.

        Esta función solicita al usuario que seleccione un archivo ``.json``
        previamente generado mediante la opción «Guardar y enviar» o un
        autosave temporal.  Tras seleccionar el archivo, se invoca
        ``load_version`` con la ruta escogida para restaurar el estado
        completo del formulario.  Si el usuario cancela la operación no
        se realizan cambios.

        """
        log_event("navegacion", "Usuario pulsó cargar versión", self.logs)
        filename = filedialog.askopenfilename(title="Seleccionar versión JSON", filetypes=[("JSON Files", "*.json")])
        if not filename:
            log_event("navegacion", "Canceló cargar versión", self.logs)
            return
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                data = json.load(f)
            dataset = self._ensure_case_data(data)
            self.populate_from_data(dataset)
            log_event("navegacion", f"Se cargó versión desde {filename}", self.logs)
            messagebox.showinfo("Versión cargada", "La versión se cargó correctamente.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo cargar la versión: {ex}")

    def _clear_case_state(self, *, save_autosave: bool = True) -> None:
        """Elimina los datos cargados y restablece los frames dinámicos."""

        # Limpiar campos del caso
        self._ensure_case_vars()
        self.id_caso_var.set("")
        self.tipo_informe_var.set(TIPO_INFORME_LIST[0])
        self.cat_caso1_var.set(list(TAXONOMIA.keys())[0])
        self.on_case_cat1_change()
        self.canal_caso_var.set(CANAL_LIST[0])
        self.proceso_caso_var.set(PROCESO_LIST[0])
        self.fecha_caso_var.set("")
        self._reset_investigator_fields()
        # Vaciar listas dinámicas
        for cf in self.client_frames:
            cf.frame.destroy()
        self.client_frames.clear()
        for tm in self.team_frames:
            tm.frame.destroy()
        self.team_frames.clear()
        for pr in self.product_frames:
            pr.frame.destroy()
        self.product_frames.clear()
        for rf in self.risk_frames:
            rf.frame.destroy()
        self.risk_frames.clear()
        for nf in self.norm_frames:
            nf.frame.destroy()
        self.norm_frames.clear()
        self.next_risk_number = 1
        self._rebuild_frame_id_indexes()
        # Reiniciar bitácora antes de poblar los frames por defecto
        self.logs.clear()
        drain_log_queue()
        self._reset_navigation_metrics()
        # Volver a crear uno por cada sección donde corresponde
        self.add_client()
        self.add_team()
        self.add_risk()
        if hasattr(self, "norm_container"):
            self.add_norm()
        # Limpiar análisis
        for widget in self._analysis_text_widgets().values():
            self._set_text_content(widget, "")
        self._reset_extended_sections()
        if save_autosave:
            self.save_auto()

    def _reset_form_state(self, confirm=True, save_autosave=True):
        """Restablece el formulario a su estado inicial.

        Args:
            confirm: Si es ``True`` solicita confirmación al usuario antes de
                continuar.
            save_autosave: Si es ``True`` persiste inmediatamente el estado
                vacío mediante ``save_auto``.

        Returns:
            ``True`` si el formulario se restableció, ``False`` si el usuario
            canceló la acción.
        """

        if confirm:
            confirmed = messagebox.askyesno(
                "Confirmar",
                "¿Desea borrar todos los datos? Esta acción no se puede deshacer.",
            )
            if not confirmed:
                return False
        self._clear_case_state(save_autosave=save_autosave)
        return True

    def clear_all(self, notify=True):
        """Elimina todos los datos actuales y restablece el formulario."""

        log_event("navegacion", "Usuario pulsó borrar datos", self.logs)
        if not self._reset_form_state(confirm=True, save_autosave=True):
            log_event("navegacion", "Canceló borrar datos", self.logs)
            return
        log_event("navegacion", "Se borraron todos los datos", self.logs)
        if notify:
            messagebox.showinfo("Datos borrados", "Todos los datos han sido borrados.")

    # ---------------------------------------------------------------------
    # Recolección y población de datos

    def _reset_extended_sections(self) -> None:
        self._ensure_case_vars()
        self._encabezado_data: dict[str, str] = {}
        self._operaciones_data: list[dict[str, str]] = []
        self._anexos_data: list[dict[str, str]] = []
        self._firmas_data: list[dict[str, str]] = []
        self._recomendaciones_categorias: dict[str, list[str]] = {}
        for var_dict in (getattr(self, "_encabezado_vars", {}), getattr(self, "_operation_vars", {}), getattr(self, "_anexo_vars", {})):
            for var in var_dict.values():
                try:
                    var.set("")
                except Exception:
                    continue
        for refresher in (
            getattr(self, "_refresh_operations_tree", None),
            getattr(self, "_refresh_anexos_tree", None),
        ):
            if callable(refresher):
                refresher()
        self._reset_investigator_fields()

    @staticmethod
    def _sanitize_text(value) -> str:
        if value is None:
            return ""
        text = str(value)
        text = CONTROL_CHAR_PATTERN.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text.startswith(SPREADSHEET_FORMULA_PREFIXES):
            text = f"'{text}"
        return text

    @classmethod
    def _sanitize_payload_strings(cls, payload, *, skip_keys: Optional[set[str]] = None):
        if skip_keys is None:
            skip_keys = set()
        if isinstance(payload, dict):
            sanitized = {}
            for key, value in payload.items():
                if key in skip_keys:
                    sanitized[key] = value
                else:
                    sanitized[key] = cls._sanitize_payload_strings(value, skip_keys=skip_keys)
            return sanitized
        if isinstance(payload, list):
            return [cls._sanitize_payload_strings(item, skip_keys=skip_keys) for item in payload]
        if isinstance(payload, str):
            return cls._sanitize_text(payload)
        return payload

    @classmethod
    def _normalize_mapping_strings(cls, payload, keys: Optional[list[str]] = None) -> dict:
        if not isinstance(payload, Mapping):
            payload = {}
        normalized = {}
        keys = keys or []
        for key in keys:
            normalized[key] = cls._sanitize_text(payload.get(key))
        for key, value in payload.items():
            if key in normalized:
                continue
            normalized[str(key)] = cls._sanitize_text(value)
        return normalized

    @classmethod
    def _normalize_table_rows(cls, payload) -> list[dict[str, str]]:
        if not isinstance(payload, list):
            return []
        rows: list[dict[str, str]] = []
        for item in payload:
            if not isinstance(item, Mapping):
                continue
            rows.append({str(key): cls._sanitize_text(value) for key, value in item.items()})
        return rows

    @classmethod
    def _normalize_recommendation_categories(cls, payload) -> dict[str, list[str]]:
        if not isinstance(payload, Mapping):
            payload = {}
        categories: dict[str, list[str]] = {}
        for key in ("laboral", "operativo", "legal"):
            values = payload.get(key) or []
            if not isinstance(values, list):
                values = [values]
            categories[key] = [text for text in (cls._sanitize_text(v) for v in values) if text]
        for key, value in payload.items():
            if key in categories:
                continue
            extra_values: list[str]
            if isinstance(value, list):
                extra_values = [text for text in (cls._sanitize_text(v) for v in value) if text]
            else:
                text = cls._sanitize_text(value)
                extra_values = [text] if text else []
            categories[str(key)] = extra_values
        return categories

    def gather_data(self):
        """Reúne todos los datos del formulario en una estructura de diccionarios."""
        self._ensure_case_vars()
        data = {}
        investigator_id = self._normalize_identifier(self.investigator_id_var.get())
        investigator_name = self._sanitize_text(self.investigator_nombre_var.get())
        investigator_role = self._sanitize_text(self.investigator_cargo_var.get()) or "Investigador Principal"
        data['caso'] = {
            "id_caso": self._sanitize_text(self.id_caso_var.get()),
            "tipo_informe": self._sanitize_text(self.tipo_informe_var.get()),
            "categoria1": self._sanitize_text(self.cat_caso1_var.get()),
            "categoria2": self._sanitize_text(self.cat_caso2_var.get()),
            "modalidad": self._sanitize_text(self.mod_caso_var.get()),
            "canal": self._sanitize_text(self.canal_caso_var.get()),
            "proceso": self._sanitize_text(self.proceso_caso_var.get()),
            "fecha_de_ocurrencia": self._sanitize_text(self.fecha_caso_var.get()),
            "matricula_investigador": investigator_id,
            "investigador": {
                "matricula": investigator_id,
                "nombre": investigator_name,
                "cargo": investigator_role or "Investigador Principal",
            },
        }
        data['clientes'] = [c.get_data() for c in self.client_frames]
        data['colaboradores'] = [t.get_data() for t in self.team_frames]
        productos = []
        reclamos = []
        involucs = []
        for p in self.product_frames:
            prod_data = p.get_data()
            productos.append(prod_data['producto'])
            # Reclamos
            for claim in prod_data['reclamos']:
                if not any(claim.values()):
                    continue
                reclamos.append({
                    "id_reclamo": claim['id_reclamo'],
                    "id_caso": "",  # se añade al exportar
                    "id_producto": prod_data['producto']['id_producto'],
                    "nombre_analitica": claim['nombre_analitica'],
                    "codigo_analitica": claim['codigo_analitica'],
                })
            # Involucramientos
            for inv in prod_data['asignaciones']:
                involucs.append({
                    "id_producto": prod_data['producto']['id_producto'],
                    "id_caso": "",  # se completará al exportar
                    "id_colaborador": inv['id_colaborador'],
                    "monto_asignado": inv['monto_asignado'],
                })
        data['productos'] = productos
        data['reclamos'] = reclamos
        data['involucramientos'] = involucs
        data['riesgos'] = [r.get_data() for r in self.risk_frames]
        normas = []
        for n in self.norm_frames:
            norm_data = n.get_data()
            if not norm_data:
                continue
            normas.append(norm_data)
        data['normas'] = normas
        analysis_widgets = self._analysis_text_widgets()
        data['analisis'] = {
            "antecedentes": self._serialize_rich_text_widget(analysis_widgets["antecedentes"]),
            "modus_operandi": self._serialize_rich_text_widget(analysis_widgets["modus_operandi"]),
            "hallazgos": self._serialize_rich_text_widget(analysis_widgets["hallazgos"]),
            "descargos": self._serialize_rich_text_widget(analysis_widgets["descargos"]),
            "conclusiones": self._serialize_rich_text_widget(analysis_widgets["conclusiones"]),
            "recomendaciones": self._serialize_rich_text_widget(analysis_widgets["recomendaciones"]),
        }
        data['encabezado'] = self._normalize_mapping_strings(
            getattr(self, '_encabezado_data', {}),
            [
                "dirigido_a",
                "referencia",
                "area_reporte",
                "fecha_reporte",
                "tipologia_evento",
                "centro_costos",
                "procesos_impactados",
                "numero_reclamos",
                "analitica_contable",
            ],
        )
        data['operaciones'] = self._normalize_table_rows(getattr(self, '_operaciones_data', []))
        data['anexos'] = self._normalize_table_rows(getattr(self, '_anexos_data', []))
        data['firmas'] = self._normalize_table_rows(getattr(self, '_firmas_data', []))
        data['recomendaciones_categorias'] = self._normalize_recommendation_categories(
            getattr(self, '_recomendaciones_categorias', {})
        )
        sanitized_data = self._sanitize_payload_strings(data, skip_keys={"analisis"})
        return CaseData.from_mapping(sanitized_data)

    def _normalize_export_amount_strings(self, products):
        if not products:
            return
        for product in products:
            if not isinstance(product, dict):
                continue
            for field_name, _var_attr, _label, allow_blank, _ in PRODUCT_MONEY_SPECS:
                if not allow_blank:
                    continue
                raw_value = product.get(field_name)
                if isinstance(raw_value, str):
                    text = raw_value.strip()
                elif raw_value is None:
                    text = ""
                else:
                    text = str(raw_value).strip()
                if text:
                    continue
                product[field_name] = "0.00"

    def _ensure_case_data(self, data) -> CaseData:
        if isinstance(data, CaseData):
            return data
        return CaseData.from_mapping(data or {})

    def populate_from_data(self, data):
        """Puebla el formulario con datos previamente guardados."""

        dataset = self._ensure_case_data(data)
        data = dataset.as_dict()
        self._ensure_case_vars()
        # Limpiar primero sin confirmar ni sobrescribir el autosave
        self._clear_case_state(save_autosave=False)
        self._ensure_investigator_vars()
        # Datos de caso
        def _set_dropdown_value(var, value, valid_values):
            """Establece el valor de un combobox solo si está en el catálogo."""

            normalized = value.strip() if isinstance(value, str) else value
            if normalized and normalized in valid_values:
                var.set(normalized)
            else:
                var.set('')

        caso = data.get('caso', {})
        self.id_caso_var.set(caso.get('id_caso', ''))
        if caso.get('tipo_informe') in TIPO_INFORME_LIST:
            self.tipo_informe_var.set(caso.get('tipo_informe'))
        if caso.get('categoria1') in TAXONOMIA:
            self.cat_caso1_var.set(caso.get('categoria1'))
            self.on_case_cat1_change()
            cat2_list = list(TAXONOMIA[self.cat_caso1_var.get()].keys())
            if caso.get('categoria2') in cat2_list:
                self.cat_caso2_var.set(caso.get('categoria2'))
                self.on_case_cat2_change()
                mod_list = TAXONOMIA[self.cat_caso1_var.get()][self.cat_caso2_var.get()]
                if caso.get('modalidad') in mod_list:
                    self.mod_caso_var.set(caso.get('modalidad'))
        _set_dropdown_value(self.canal_caso_var, caso.get('canal'), CANAL_LIST)
        _set_dropdown_value(self.proceso_caso_var, caso.get('proceso'), PROCESO_LIST)
        self.fecha_caso_var.set(caso.get('fecha_de_ocurrencia', ''))
        self.fecha_descubrimiento_caso_var.set(caso.get('fecha_de_descubrimiento', ''))
        investigator_payload = caso.get('investigador', {}) if isinstance(caso, Mapping) else {}
        matricula_investigador = caso.get('matricula_investigador') or investigator_payload.get('matricula')
        self.investigator_id_var.set(self._normalize_identifier(matricula_investigador))
        nombre_investigador = investigator_payload.get('nombre')
        if nombre_investigador:
            self.investigator_nombre_var.set(nombre_investigador)
        else:
            self.investigator_nombre_var.set("")
        cargo_investigador = investigator_payload.get('cargo') or "Investigador Principal"
        self.investigator_cargo_var.set(cargo_investigador)
        self._autofill_investigator(show_errors=False)
        centro_costo = caso.get('centro_costo') or caso.get('centro_costos')
        self.centro_costo_caso_var.set(centro_costo or '')
        # Clientes
        for i, cliente in enumerate(data.get('clientes', [])):
            if i >= len(self.client_frames):
                self.add_client()
            cl = self.client_frames[i]
            cl.tipo_id_var.set(cliente.get('tipo_id', ''))
            cl.id_var.set(cliente.get('id_cliente', ''))
            cl.flag_var.set(cliente.get('flag', ''))
            cl.telefonos_var.set(cliente.get('telefonos', ''))
            cl.correos_var.set(cliente.get('correos', ''))
            cl.direcciones_var.set(cliente.get('direcciones', ''))
            cl.set_accionado_from_text(cliente.get('accionado', ''))
        # Colaboradores
        for i, col in enumerate(data.get('colaboradores', [])):
            if i >= len(self.team_frames):
                self.add_team()
            tm = self.team_frames[i]
            tm.id_var.set(col.get('id_colaborador', ''))
            tm.flag_var.set(col.get('flag', ''))
            tm.nombres_var.set(col.get('nombres', ''))
            tm.apellidos_var.set(col.get('apellidos', ''))
            tm.division_var.set(col.get('division', ''))
            tm.area_var.set(col.get('area', ''))
            tm.servicio_var.set(col.get('servicio', ''))
            tm.puesto_var.set(col.get('puesto', ''))
            tm.fecha_carta_inmediatez_var.set(col.get('fecha_carta_inmediatez', ''))
            tm.fecha_carta_renuncia_var.set(col.get('fecha_carta_renuncia', ''))
            tm.nombre_agencia_var.set(col.get('nombre_agencia', ''))
            tm.codigo_agencia_var.set(col.get('codigo_agencia', ''))
            tm.tipo_falta_var.set(col.get('tipo_falta', ''))
            tm.tipo_sancion_var.set(col.get('tipo_sancion', ''))
        # Productos y sus reclamos e involuc
        claims_map = {}
        for rec in data.get('reclamos', []):
            pid = (rec.get('id_producto') or '').strip()
            if not pid:
                continue
            claims_map.setdefault(pid, []).append(
                {
                    'id_reclamo': (rec.get('id_reclamo') or '').strip(),
                    'nombre_analitica': (rec.get('nombre_analitica') or '').strip(),
                    'codigo_analitica': (rec.get('codigo_analitica') or '').strip(),
                }
            )
        for i, prod in enumerate(data.get('productos', [])):
            if i >= len(self.product_frames):
                self.add_product(initialize_rows=False)
            pframe = self.product_frames[i]
            pframe.id_var.set(prod.get('id_producto', ''))
            pframe.client_var.set(prod.get('id_cliente', ''))
            cat1 = prod.get('categoria1')
            if cat1 in TAXONOMIA:
                pframe.cat1_var.set(cat1)
                pframe.on_cat1_change()
                cat2 = prod.get('categoria2')
                if cat2 in TAXONOMIA[cat1]:
                    pframe.cat2_var.set(cat2)
                    pframe.on_cat2_change()
                    mod = prod.get('modalidad')
                    if mod in TAXONOMIA[cat1][cat2]:
                        pframe.mod_var.set(mod)
            _set_dropdown_value(pframe.canal_var, prod.get('canal'), CANAL_LIST)
            _set_dropdown_value(pframe.proceso_var, prod.get('proceso'), PROCESO_LIST)
            pframe.fecha_oc_var.set(prod.get('fecha_ocurrencia', ''))
            pframe.fecha_desc_var.set(prod.get('fecha_descubrimiento', ''))
            pframe.monto_inv_var.set(prod.get('monto_investigado', ''))
            _set_dropdown_value(pframe.moneda_var, prod.get('tipo_moneda'), TIPO_MONEDA_LIST)
            pframe.monto_perdida_var.set(prod.get('monto_perdida_fraude', ''))
            pframe.monto_falla_var.set(prod.get('monto_falla_procesos', ''))
            pframe.monto_cont_var.set(prod.get('monto_contingencia', ''))
            pframe.monto_rec_var.set(prod.get('monto_recuperado', ''))
            pframe.monto_pago_var.set(prod.get('monto_pago_deuda', ''))
            tipo_producto = prod.get('tipo_producto')
            if tipo_producto in TIPO_PRODUCTO_LIST:
                pframe.tipo_prod_var.set(tipo_producto)
            pframe.set_claims_from_data(claims_map.get(pframe.id_var.get().strip(), []))
        # Involucramientos
        involvement_map = {}
        for inv in data.get('involucramientos', []):
            pid = (inv.get('id_producto') or '').strip()
            if not pid:
                continue
            involvement_map.setdefault(pid, []).append(inv)

        for pframe in self.product_frames:
            pid = pframe.id_var.get().strip()
            if pid not in involvement_map:
                continue
            pframe.clear_involvements()
            for inv in involvement_map[pid]:
                assign = pframe.add_involvement()
                assign.team_var.set(inv.get('id_colaborador', ''))
                assign.monto_var.set(inv.get('monto_asignado', ''))
        # Riesgos
        for i, risk in enumerate(data.get('riesgos', [])):
            if i >= len(self.risk_frames):
                self.add_risk()
            rf = self.risk_frames[i]
            rf.id_var.set(risk.get('id_riesgo', ''))
            rf.lider_var.set(risk.get('lider', ''))
            rf.descripcion_var.set(risk.get('descripcion', ''))
            rf.criticidad_var.set(risk.get('criticidad', CRITICIDAD_LIST[0]))
            rf.exposicion_var.set(risk.get('exposicion_residual', ''))
            rf.planes_var.set(risk.get('planes_accion', ''))
        # Normas
        for i, norm in enumerate(data.get('normas', [])):
            if i >= len(self.norm_frames):
                self.add_norm()
            nf = self.norm_frames[i]
            nf.id_var.set(norm.get('id_norma', ''))
            nf.descripcion_var.set(norm.get('descripcion', ''))
            nf.fecha_var.set(norm.get('fecha_vigencia', ''))
        self._refresh_shared_norm_tree()
        # Analisis
        analisis = data.get('analisis', {})
        analysis_widgets = self._analysis_text_widgets()
        self._set_rich_text_content(analysis_widgets['antecedentes'], analisis.get('antecedentes', ''))
        self._set_rich_text_content(analysis_widgets['modus_operandi'], analisis.get('modus_operandi', ''))
        self._set_rich_text_content(analysis_widgets['hallazgos'], analisis.get('hallazgos', ''))
        self._set_rich_text_content(analysis_widgets['descargos'], analisis.get('descargos', ''))
        self._set_rich_text_content(analysis_widgets['conclusiones'], analisis.get('conclusiones', ''))
        self._set_rich_text_content(analysis_widgets['recomendaciones'], analisis.get('recomendaciones', ''))
        self._encabezado_data = self._normalize_mapping_strings(
            data.get('encabezado', {}),
            [
                "dirigido_a",
                "referencia",
                "area_reporte",
                "fecha_reporte",
                "tipologia_evento",
                "centro_costos",
                "procesos_impactados",
                "numero_reclamos",
                "analitica_contable",
            ],
        )
        self._operaciones_data = self._normalize_table_rows(data.get('operaciones', []))
        self._anexos_data = self._normalize_table_rows(data.get('anexos', []))
        self._firmas_data = self._normalize_table_rows(data.get('firmas', []))
        self._recomendaciones_categorias = self._normalize_recommendation_categories(
            data.get('recomendaciones_categorias', {})
        )
        self._sync_extended_sections_to_ui()
        self._rebuild_frame_id_indexes()
        self._run_duplicate_check_post_load()
        self._schedule_summary_refresh(data=data)

    # ---------------------------------------------------------------------
    # Validación de reglas de negocio

    def validate_data(self):
        """Valida los datos del formulario y retorna errores y advertencias."""
        errors = []
        warnings = []

        def _report_catalog_error(message):
            """Acumula los errores de catálogo para notificarlos en bloque."""

            errors.append(message)

        def _validate_product_catalog_field(value, label, catalog, catalog_label, product_label):
            text = (value or '').strip()
            message = validate_required_text(text, label)
            if message:
                return f"Producto {product_label}: {message}"
            if text not in catalog:
                catalog_message = (
                    f"Producto {product_label}: El {catalog_label} '{text}' no está en el catálogo CM."
                )
                _report_catalog_error(catalog_message)
                return None
            return None

        def _validate_product_taxonomy(producto, product_label):
            """Valida que categoría 1, 2 y modalidad del producto existan en TAXONOMIA."""

            messages = []
            cat1 = (producto.get('categoria1') or '').strip()
            cat2 = (producto.get('categoria2') or '').strip()
            modalidad = (producto.get('modalidad') or '').strip()

            cat1_message = validate_required_text(cat1, "la categoría 1 del producto")
            if cat1_message:
                messages.append(f"Producto {product_label}: {cat1_message}")
            elif cat1 not in TAXONOMIA:
                messages.append(
                    f"Producto {product_label}: La categoría 1 '{cat1}' no está en el catálogo CM."
                )
            cat1_valid = bool(cat1) and cat1 in TAXONOMIA

            cat2_message = validate_required_text(cat2, "la categoría 2 del producto")
            if cat2_message:
                messages.append(f"Producto {product_label}: {cat2_message}")
                cat2_valid = False
            else:
                if not cat1_valid:
                    messages.append(
                        f"Producto {product_label}: La categoría 2 '{cat2}' no puede validarse porque la categoría 1 es inválida."
                    )
                    cat2_valid = False
                elif cat2 not in TAXONOMIA[cat1]:
                    messages.append(
                        f"Producto {product_label}: La categoría 2 '{cat2}' no pertenece a la categoría 1 '{cat1}' del catálogo CM."
                    )
                    cat2_valid = False
                else:
                    cat2_valid = True

            mod_message = validate_required_text(modalidad, "la modalidad del producto")
            if mod_message:
                messages.append(f"Producto {product_label}: {mod_message}")
            else:
                if not (cat1_valid and cat2_valid):
                    messages.append(
                        f"Producto {product_label}: La modalidad '{modalidad}' no puede validarse porque las categorías registradas son inválidas."
                    )
                elif modalidad not in TAXONOMIA[cat1][cat2]:
                    messages.append(
                        f"Producto {product_label}: La modalidad '{modalidad}' no pertenece a la categoría 1 '{cat1}' y categoría 2 '{cat2}' del catálogo CM."
                    )
            return messages

        def _validate_team_catalog_value(value, label, catalog, collaborator_idx):
            text = (value or '').strip()
            if not text:
                errors.append(f"Colaborador {collaborator_idx}: Debe seleccionar {label}.")
            elif text not in catalog:
                errors.append(
                    f"Colaborador {collaborator_idx}: El {label} '{text}' no está en el catálogo CM."
                )
        # Validar número de caso
        id_caso = self.id_caso_var.get().strip()
        normalized_case_id = self._normalize_identifier(id_caso)
        case_message = validate_case_id(id_caso)
        if case_message:
            errors.append(case_message)
        # Validar campos obligatorios del caso antes de validar entidades hijas
        tipo_informe_value = (self.tipo_informe_var.get() or '').strip()
        tipo_message = validate_required_text(tipo_informe_value, "el tipo de informe")
        if tipo_message:
            errors.append(tipo_message)
        elif tipo_informe_value not in TIPO_INFORME_LIST:
            _report_catalog_error(
                f"El tipo de informe '{tipo_informe_value}' no está en el catálogo CM."
            )
        cat1_value = (self.cat_caso1_var.get() or '').strip()
        cat1_message = validate_required_text(cat1_value, "la categoría nivel 1")
        cat1_valid = False
        if cat1_message:
            errors.append(cat1_message)
        elif cat1_value not in TAXONOMIA:
            _report_catalog_error(
                f"La categoría nivel 1 '{cat1_value}' no está en el catálogo CM."
            )
        else:
            cat1_valid = True
        cat2_value = (self.cat_caso2_var.get() or '').strip()
        cat2_message = validate_required_text(cat2_value, "la categoría nivel 2")
        cat2_valid = False
        if cat2_message:
            errors.append(cat2_message)
        elif cat1_valid:
            if cat2_value not in TAXONOMIA[cat1_value]:
                _report_catalog_error(
                    f"La categoría nivel 2 '{cat2_value}' no está dentro de la categoría '{cat1_value}' del catálogo CM."
                )
            else:
                cat2_valid = True
        mod_value = (self.mod_caso_var.get() or '').strip()
        mod_message = validate_required_text(mod_value, "la modalidad del caso")
        if mod_message:
            errors.append(mod_message)
        elif cat1_valid and cat2_valid:
            modalidades = TAXONOMIA[cat1_value][cat2_value]
            if mod_value not in modalidades:
                _report_catalog_error(
                    f"La modalidad '{mod_value}' no existe dentro de la categoría '{cat1_value}'/'{cat2_value}' del catálogo CM."
                )
        canal_value = (self.canal_caso_var.get() or '').strip()
        canal_message = validate_required_text(canal_value, "el canal del caso")
        if canal_message:
            errors.append(canal_message)
        elif canal_value not in CANAL_LIST:
            _report_catalog_error(
                f"El canal del caso '{canal_value}' no está en el catálogo CM."
            )
        proceso_value = (self.proceso_caso_var.get() or '').strip()
        proceso_message = validate_required_text(proceso_value, "el proceso impactado")
        if proceso_message:
            errors.append(proceso_message)
        elif proceso_value not in PROCESO_LIST:
            _report_catalog_error(
                f"El proceso del caso '{proceso_value}' no está en el catálogo CM."
            )
        fecha_caso_message = self._validate_case_occurrence_date()
        if fecha_caso_message:
            errors.append(fecha_caso_message)
        fecha_descubrimiento_message = self._validate_case_discovery_date()
        if fecha_descubrimiento_message:
            errors.append(fecha_descubrimiento_message)
        centro_costo_message = self._validate_cost_centers(text=self.centro_costo_caso_var.get())
        if centro_costo_message:
            errors.append(centro_costo_message)
        # Validar IDs de clientes
        client_id_occurrences = {}
        for idx, cframe in enumerate(self.client_frames, start=1):
            tipo_id_value = (cframe.tipo_id_var.get() or "").strip()
            tipo_message = validate_required_text(tipo_id_value, "el tipo de ID del cliente")
            if tipo_message:
                errors.append(f"Cliente {idx}: {tipo_message}")
            else:
                if tipo_id_value not in TIPO_ID_LIST:
                    errors.append(
                        f"Cliente {idx}: El tipo de ID '{tipo_id_value}' no está en el catálogo CM."
                    )
                else:
                    client_id_value = (cframe.id_var.get() or "").strip()
                    message = validate_client_id(tipo_id_value, client_id_value)
                    if message:
                        errors.append(f"Cliente {idx}: {message}")
                    normalized_client_id = self._normalize_identifier(client_id_value)
                    if normalized_client_id:
                        occurrences = client_id_occurrences.setdefault(normalized_client_id, [])
                        occurrences.append((idx, client_id_value or normalized_client_id))

            flag_var = getattr(cframe, "flag_var", None)
            if flag_var is not None:
                flag_value = (flag_var.get() or "").strip()
                flag_message = validate_required_text(flag_value, "el flag del cliente")
                if flag_message:
                    errors.append(f"Cliente {idx}: {flag_message}")
                elif flag_value not in FLAG_CLIENTE_LIST:
                    errors.append(
                        f"Cliente {idx}: El flag de cliente '{flag_value}' no está en el catálogo CM."
                    )
            if hasattr(cframe, 'telefonos_var'):
                phone_value = cframe.telefonos_var.get()
                phone_required = validate_required_text(
                    phone_value, "los teléfonos del cliente"
                )
                if phone_required:
                    errors.append(f"Cliente {idx}: {phone_required}")
                else:
                    phone_message = validate_phone_list(
                        phone_value, "los teléfonos del cliente"
                    )
                    if phone_message:
                        errors.append(f"Cliente {idx}: {phone_message}")
            if hasattr(cframe, 'correos_var'):
                email_value = cframe.correos_var.get()
                email_required = validate_required_text(
                    email_value, "los correos del cliente"
                )
                if email_required:
                    errors.append(f"Cliente {idx}: {email_required}")
                else:
                    email_message = validate_email_list(
                        email_value, "los correos del cliente"
                    )
                    if email_message:
                        errors.append(f"Cliente {idx}: {email_message}")
            if hasattr(cframe, 'accionado_var'):
                accionado_message = validate_multi_selection(
                    cframe.accionado_var.get(), "Accionado"
                )
                if accionado_message:
                    errors.append(f"Cliente {idx}: {accionado_message}")
        for normalized_client_id, occurrences in client_id_occurrences.items():
            if len(occurrences) > 1:
                formatted_positions = ", ".join(str(pos) for pos, _ in occurrences)
                display_value = occurrences[0][1] or normalized_client_id
                errors.append(
                    (
                        f"El ID de cliente {display_value} está duplicado en los clientes {formatted_positions}. "
                        "Cada cliente debe tener un ID único."
                    )
                )
        # Validar duplicidad del key técnico (caso, producto, cliente, colaborador, fecha ocurrencia, reclamo)
        key_set = set()
        product_client_map = {}
        total_investigado = Decimal('0')
        total_componentes = Decimal('0')
        total_pago_deuda = Decimal('0')
        normalized_amounts = []
        team_id_occurrences = {}
        for idx, tm in enumerate(self.team_frames, start=1):
            current_idx = idx
            team_id_value = (tm.id_var.get() or "").strip()
            tm_id_message = validate_team_member_id(team_id_value)
            if tm_id_message:
                errors.append(f"Colaborador {current_idx}: {tm_id_message}")
            normalized_team_id = self._normalize_identifier(team_id_value)
            if normalized_team_id:
                team_id_occurrences.setdefault(normalized_team_id, []).append(current_idx)
            agency_message = validate_agency_code(tm.codigo_agencia_var.get(), allow_blank=True)
            if agency_message:
                errors.append(f"Colaborador {current_idx}: {agency_message}")
            flag_value = (tm.flag_var.get() if hasattr(tm, 'flag_var') else '').strip()
            flag_message = validate_required_text(flag_value, "el flag del colaborador")
            if flag_message:
                errors.append(f"Colaborador {current_idx}: {flag_message}")
            elif flag_value not in FLAG_COLABORADOR_LIST:
                errors.append(
                    f"Colaborador {current_idx}: El flag del colaborador '{flag_value}' no está en el catálogo CM."
                )
            falta_value = tm.tipo_falta_var.get() if hasattr(tm, 'tipo_falta_var') else ''
            sancion_value = tm.tipo_sancion_var.get() if hasattr(tm, 'tipo_sancion_var') else ''
            _validate_team_catalog_value(
                falta_value,
                "el tipo de falta del colaborador",
                TIPO_FALTA_LIST,
                current_idx,
            )
            _validate_team_catalog_value(
                sancion_value,
                "el tipo de sanción del colaborador",
                TIPO_SANCION_LIST,
                current_idx,
            )
            division_value = (tm.division_var.get() if hasattr(tm, 'division_var') else '').strip()
            area_value = (tm.area_var.get() if hasattr(tm, 'area_var') else '').strip()
            division_norm = normalize_without_accents(division_value).lower()
            area_norm = normalize_without_accents(area_value).lower()
            needs_agency = (
                ('dca' in division_norm or 'canales de atencion' in division_norm)
                and ('area comercial' in area_norm)
            )
            if needs_agency:
                nombre_agencia = (
                    tm.nombre_agencia_var.get().strip()
                    if hasattr(tm, 'nombre_agencia_var')
                    else ''
                )
                codigo_agencia = (
                    tm.codigo_agencia_var.get().strip()
                    if hasattr(tm, 'codigo_agencia_var')
                    else ''
                )
                if not nombre_agencia or not codigo_agencia:
                    errors.append(
                        "El colaborador {idx} debe registrar nombre y código de agencia por pertenecer a canales comerciales.".format(
                            idx=current_idx
                        )
                    )
        for collaborator_id, positions in team_id_occurrences.items():
            if len(positions) > 1:
                formatted_positions = ", ".join(str(pos) for pos in positions)
                errors.append(
                    (
                        f"El ID de colaborador {collaborator_id} está duplicado en los colaboradores {formatted_positions}. "
                        "Cada colaborador debe tener un ID único."
                    )
                )
        collaborator_ids = set()
        for tm in self.team_frames:
            normalized_team_id = self._normalize_identifier(tm.id_var.get())
            if normalized_team_id:
                collaborator_ids.add(normalized_team_id)
        for idx, p in enumerate(self.product_frames, start=1):
            prod_data = p.get_data()
            producto = prod_data['producto']
            pid = producto.get('id_producto', '')
            pid_norm = self._normalize_identifier(pid)
            pid_key = pid_norm or pid or ''
            producto_label = pid_norm or pid or f"Producto {idx}"
            pid_message = validate_product_id(p.tipo_prod_var.get(), p.id_var.get())
            if pid_message:
                errors.append(f"Producto {idx}: {pid_message}")
            cid = producto['id_cliente']
            cid_norm = self._normalize_identifier(cid)
            if not cid:
                errors.append(
                    f"Producto {idx}: el cliente vinculado fue eliminado. Selecciona un nuevo titular antes de exportar."
                )
            if pid_key in product_client_map:
                prev_entry = product_client_map[pid_key]
                if prev_entry['client_norm'] != cid_norm:
                    prev_client_display = prev_entry['client_display'] or prev_entry['client_norm'] or 'sin ID'
                    current_client_display = cid or cid_norm or 'sin ID'
                    errors.append(
                        f"El producto {producto_label} está asociado a dos clientes distintos ({prev_client_display} y {current_client_display})."
                    )
                else:
                    errors.append(f"El producto {producto_label} está duplicado en el formulario.")
            else:
                product_client_map[pid_key] = {
                    'client_norm': cid_norm,
                    'client_display': cid,
                }
            for taxonomy_error in _validate_product_taxonomy(producto, producto_label):
                errors.append(taxonomy_error)
            catalog_validations = [
                (
                    producto.get('canal'),
                    "el canal del producto",
                    CANAL_LIST,
                    "canal",
                ),
                (
                    producto.get('proceso'),
                    "el proceso del producto",
                    PROCESO_LIST,
                    "proceso",
                ),
                (
                    producto.get('tipo_moneda'),
                    "la moneda del producto",
                    TIPO_MONEDA_LIST,
                    "tipo de moneda",
                ),
            ]
            for value, label, catalog, catalog_label in catalog_validations:
                catalog_error = _validate_product_catalog_field(
                    value,
                    label,
                    catalog,
                    catalog_label,
                    producto_label,
                )
                if catalog_error:
                    errors.append(catalog_error)
            # For each involvement; require collaborator IDs to validate clave técnica
            claim_rows = prod_data['reclamos'] or []
            product_occurrence_date = prod_data['producto'].get('fecha_ocurrencia')
            assignments = prod_data['asignaciones'] or []
            product_has_involvements = hasattr(p, "involvements")
            enforce_assignations = bool(product_has_involvements)
            if enforce_assignations and not assignments:
                errors.append(
                    (
                        f"Producto {producto_label}: agrega al menos un colaborador en"
                        " 'Involucramiento de colaboradores' para validar la clave técnica."
                    )
                )
                continue
            for inv_idx, inv in enumerate(assignments, start=1):
                collaborator_id = (inv.get('id_colaborador') or '').strip()
                collaborator_norm = self._normalize_identifier(collaborator_id)
                amount_value = (inv.get('monto_asignado') or '').strip()
                amount_label = (
                    f"Monto asignado del colaborador {collaborator_id or f'sin ID ({inv_idx})'} "
                    f"en el producto {producto_label}"
                )
                amount_error, _amount, normalized_amount = validate_money_bounds(
                    amount_value,
                    amount_label,
                )
                if amount_error:
                    errors.append(amount_error)
                else:
                    inv['monto_asignado'] = normalized_amount or amount_value
                if amount_value and not collaborator_id:
                    errors.append(
                        f"Producto {pid}: la asignación {inv_idx} tiene un monto sin colaborador."
                    )
                if collaborator_id and not amount_value:
                    errors.append(
                        f"Producto {pid}: la asignación {inv_idx} tiene un colaborador sin monto."
                    )
                if collaborator_id and collaborator_norm not in collaborator_ids:
                    errors.append(
                        f"Producto {pid}: la asignación {inv_idx} referencia un colaborador eliminado (ID {collaborator_id})."
                    )
                if not collaborator_norm:
                    errors.append(
                        (
                            f"Producto {producto_label}: la asignación {inv_idx} requiere un ID"
                            " de colaborador para validar duplicados."
                        )
                    )
                    continue
                collaborator_label = collaborator_norm or collaborator_id or 'sin ID'
                if not claim_rows:
                    key = (
                        normalized_case_id,
                        pid_norm,
                        cid_norm,
                        collaborator_norm,
                        product_occurrence_date,
                        "",
                    )
                    if key in key_set:
                        errors.append(
                            f"Registro duplicado de clave técnica (producto {producto_label}, colaborador {collaborator_label})"
                        )
                    key_set.add(key)
                    continue
                for claim in claim_rows:
                    claim_id = (claim.get('id_reclamo') or '').strip()
                    key = (
                        normalized_case_id,
                        pid_norm,
                        cid_norm,
                        collaborator_norm,
                        product_occurrence_date,
                        self._normalize_identifier(claim_id),
                    )
                    if key in key_set:
                        errors.append(
                            f"Registro duplicado de clave técnica (producto {producto_label}, colaborador {collaborator_label})"
                        )
                    key_set.add(key)
        # Validar fechas y montos por producto
        for p in self.product_frames:
            data = p.get_data()
            producto = data['producto']
            tipo_producto = (producto.get('tipo_producto') or '').strip()
            normalized_tipo = (
                normalize_without_accents(tipo_producto).lower() if tipo_producto else ''
            )
            if not tipo_producto:
                errors.append(f"Producto {producto['id_producto']}: Debe ingresar el tipo de producto.")
            else:
                if normalized_tipo not in TIPO_PRODUCTO_NORMALIZED:
                    errors.append(
                        f"Producto {producto['id_producto']}: El tipo de producto '{tipo_producto}' no está en el catálogo."
                    )
            # Fechas
            date_message = validate_product_dates(
                producto.get('id_producto'),
                producto.get('fecha_ocurrencia'),
                producto.get('fecha_descubrimiento'),
            )
            if date_message:
                errors.append(date_message)
            # Montos
            money_values = {}
            money_error = False
            for field, _, label, allow_blank, _ in PRODUCT_MONEY_SPECS:
                message, decimal_value, normalized_text = validate_money_bounds(
                    producto.get(field, ''),
                    f"{label} del producto {producto['id_producto']}",
                    allow_blank=allow_blank,
                )
                if message:
                    errors.append(message)
                    money_error = True
                if not message and normalized_text is not None:
                    producto[field] = normalized_text if normalized_text else ''
                money_values[field] = decimal_value if decimal_value is not None else Decimal('0')
            if money_error:
                continue
            m_inv = money_values['monto_investigado']
            m_perd = money_values['monto_perdida_fraude']
            m_fall = money_values['monto_falla_procesos']
            m_cont = money_values['monto_contingencia']
            m_rec = money_values['monto_recuperado']
            m_pago = money_values['monto_pago_deuda']
            if normalized_tipo and any(word in normalized_tipo for word in ['credito', 'tarjeta']):
                if m_cont != m_inv:
                    errors.append(
                        f"El monto de contingencia debe ser igual al monto investigado en el producto {producto['id_producto']} porque es un crédito o tarjeta"
                    )
            normalized_amounts.append({
                'perdida': m_perd,
                'falla': m_fall,
                'contingencia': m_cont,
            })
            componentes = sum_investigation_components(
                perdida=m_perd,
                falla=m_fall,
                contingencia=m_cont,
                recuperado=m_rec,
            )
            if componentes != m_inv:
                errors.append(
                    f"Las cuatro partidas (pérdida, falla, contingencia y recuperación) deben ser iguales al monto investigado en el producto {producto['id_producto']}"
                )
            if m_rec > m_inv:
                errors.append(
                    f"El monto recuperado no puede superar el monto investigado en el producto {producto['id_producto']}"
                )
            if m_pago > m_inv:
                errors.append(f"El monto pagado de deuda excede el monto investigado en el producto {producto['id_producto']}")
            total_investigado += m_inv
            total_componentes += componentes
            total_pago_deuda += m_pago
            # Reclamo y analíticas
            requiere_reclamo = m_perd > 0 or m_fall > 0 or m_cont > 0
            complete_claim_found = False
            seen_claim_ids = set()
            for claim in data['reclamos'] or []:
                claim_id = (claim.get('id_reclamo') or '').strip()
                normalized_claim_id = self._normalize_identifier(claim_id)
                claim_name = (claim.get('nombre_analitica') or '').strip()
                claim_code = (claim.get('codigo_analitica') or '').strip()
                has_any_value = any([claim_id, claim_name, claim_code])
                if claim_id:
                    if normalized_claim_id in seen_claim_ids:
                        errors.append(
                            f"Producto {producto['id_producto']}: El ID de reclamo {claim_id} está duplicado."
                        )
                    seen_claim_ids.add(normalized_claim_id)
                    reclamo_message = validate_reclamo_id(claim_id)
                    if reclamo_message:
                        errors.append(f"Producto {producto['id_producto']}: {reclamo_message}")
                if claim_code:
                    codigo_message = validate_codigo_analitica(claim_code)
                    if codigo_message:
                        errors.append(f"Producto {producto['id_producto']}: {codigo_message}")
                if has_any_value:
                    if not (claim_id and claim_name and claim_code):
                        errors.append(
                            f"Producto {producto['id_producto']}: El reclamo {claim_id or '(sin ID)'} debe tener ID, nombre y código de analítica."
                        )
                    else:
                        complete_claim_found = True
            if requiere_reclamo and not complete_claim_found:
                errors.append(
                    f"Debe ingresar al menos un reclamo completo en el producto {producto['id_producto']} porque hay montos de pérdida, falla o contingencia"
                )
            # Longitud id_producto
            # Fraude externo
            if producto['categoria2'] == 'Fraude Externo':
                warnings.append(
                    f"Producto {producto['id_producto']} con categoría 2 'Fraude Externo': verifique la analítica registrada."
                )
        aggregate_payment_error = None
        if self.product_frames and total_pago_deuda > total_investigado:
            aggregate_payment_error = (
                "La suma de pagos de deuda no puede superar el monto investigado total del caso."
            )
            errors.append(aggregate_payment_error)
        if aggregate_payment_error and not getattr(self, '_suppress_messagebox', False):
            messagebox.showerror("Monto de pago de deuda", aggregate_payment_error)
        if self.product_frames and total_componentes != total_investigado:
            errors.append(
                "Las cuatro partidas (pérdida, falla, contingencia y recuperación) sumadas en el caso no coinciden con el total investigado."
            )
        # Validar que al menos un producto coincida con categorías del caso
        match_found = False
        for p in self.product_frames:
            pd = p.get_data()['producto']
            if pd['categoria1'] == self.cat_caso1_var.get() and pd['categoria2'] == self.cat_caso2_var.get() and pd['modalidad'] == self.mod_caso_var.get():
                match_found = True
                break
        if not match_found:
            errors.append("Ningún producto coincide con las categorías y modalidad seleccionadas para el caso.")
        # Validar reporte tipo Interno vs pérdidas y sanciones
        if self.tipo_informe_var.get() == 'Interno':
            any_loss = any(
                amounts['perdida'] > Decimal('0')
                or amounts['falla'] > Decimal('0')
                or amounts['contingencia'] > Decimal('0')
                for amounts in normalized_amounts
            )
            any_sanction = any(
                t.tipo_sancion_var.get() not in ('No aplica', '')
                for t in self.team_frames
            )
            if any_loss or any_sanction:
                errors.append("No se puede seleccionar tipo de informe 'Interno' si hay pérdidas, fallas, contingencias o sanciones registradas.")
        # Validar riesgos
        risk_exposure_total = Decimal('0')
        risk_ids = set()
        plan_ids = set()
        for idx, r in enumerate(self.risk_frames, start=1):
            rd = r.get_data()
            rid = rd['id_riesgo']
            risk_message = validate_risk_id(rid)
            if risk_message:
                errors.append(f"Riesgo {idx}: {risk_message}")
            elif rid in risk_ids:
                errors.append(f"ID de riesgo duplicado: {rid}")
            if rid:
                risk_ids.add(rid)
            criticidad_value = (rd.get('criticidad') or '').strip()
            if not criticidad_value:
                errors.append(
                    f"Riesgo {idx}: Debe seleccionar la criticidad del riesgo."
                )
            elif criticidad_value not in CRITICIDAD_LIST:
                errors.append(
                    f"Riesgo {idx}: La criticidad '{criticidad_value}' no está en el catálogo CM."
                )
            # Exposición
            message, exposure_decimal, normalized_text = validate_money_bounds(
                rd['exposicion_residual'],
                f"Exposición residual del riesgo {rid}",
                allow_blank=True,
            )
            if message:
                errors.append(message)
            elif exposure_decimal is not None:
                risk_exposure_total += exposure_decimal
            if (
                not message
                and normalized_text
                and normalized_text != (rd.get('exposicion_residual') or '').strip()
            ):
                if hasattr(r, 'exposicion_var'):
                    r.exposicion_var.set(normalized_text)
                rd['exposicion_residual'] = normalized_text
            # Planes de acción
            for plan in [p.strip() for p in rd['planes_accion'].split(';') if p.strip()]:
                if plan in plan_ids:
                    errors.append(f"Plan de acción {plan} duplicado entre riesgos")
                plan_ids.add(plan)
        self._last_validated_risk_exposure_total = risk_exposure_total
        # Validar normas
        norm_ids = set()
        for idx, n in enumerate(self.norm_frames, start=1):
            nd = n.get_data()
            if not nd:
                continue
            nid = nd['id_norma']
            descripcion = nd['descripcion']
            message = validate_norm_id(nid)
            if message:
                errors.append(f"Norma {idx}: {message}")
            elif nid in norm_ids:
                errors.append(f"ID de norma duplicado: {nid}")
            else:
                norm_ids.add(nid)
            if not descripcion:
                errors.append(f"Norma {idx}: Debe ingresar la descripción de la norma.")
            # Fecha vigencia
            fvig = (nd.get('fecha_vigencia') or '').strip()
            fvig_message = validate_date_text(fvig, "la fecha de vigencia", allow_blank=False)
            if fvig_message:
                errors.append(f"Norma {idx}: {fvig_message}")
            else:
                fv = datetime.strptime(fvig, "%Y-%m-%d")
                if fv > datetime.now():
                    errors.append(f"Fecha de vigencia futura en norma {nid or 'sin ID'}")
        self._publish_validation_summary(errors, warnings)
        return errors, warnings

    # ---------------------------------------------------------------------
    # Exportación de datos

    def _attach_case_ids(self, data: CaseData) -> None:
        case_id = data.get("caso", {}).get("id_caso", "")
        for collection in (
            "clientes",
            "colaboradores",
            "productos",
            "reclamos",
            "involucramientos",
            "riesgos",
            "normas",
        ):
            for row in data.get(collection, []):
                if isinstance(row, dict):
                    row["id_caso"] = case_id

    def _validate_amount_consistency_before_export(self) -> bool:
        """Verifica montos consistentes antes de exportar y bloquea si hay errores."""

        blocking_messages: list[str] = []
        for product in self.product_frames:
            if not hasattr(product, "collect_amount_consistency_errors"):
                continue
            product_label = product._get_product_label() if hasattr(product, "_get_product_label") else "Producto"
            for message in product.collect_amount_consistency_errors():
                blocking_messages.append(f"{product_label}: {message}")

        if not blocking_messages:
            return True

        unique_messages = list(dict.fromkeys(blocking_messages))
        combined_message = "\n".join(unique_messages)
        log_event("validacion", combined_message, self.logs)
        if not getattr(self, "_suppress_messagebox", False):
            messagebox.showerror("Montos inconsistentes", combined_message)
        return False

    def _prepare_case_data_for_export(self) -> tuple[Optional[CaseData], Optional[Path], Optional[str]]:
        """Valida y normaliza los datos antes de exportarlos."""

        self.flush_autosave()
        self.flush_logs_now()
        if not self._validate_amount_consistency_before_export():
            return None, None, None
        errors, warnings = self.validate_data()
        if errors:
            messagebox.showerror("Errores de validación", "\n".join(errors))
            log_event("validacion", f"Errores al guardar: {errors}", self.logs)
        if warnings:
            messagebox.showwarning("Advertencias de validación", "\n".join(warnings))
            log_event("validacion", f"Advertencias al guardar: {warnings}", self.logs)
        if errors:
            return None, None, None
        self._play_feedback_sound()
        folder = self._get_exports_folder()
        if not folder:
            return None, None, None
        data = self._ensure_case_data(self.gather_data())
        self._normalize_export_amount_strings(data.get("productos"))
        self._attach_case_ids(data)
        case_id = data["caso"].get("id_caso") or "caso"
        return data, folder, case_id

    @staticmethod
    def _build_report_path(data: CaseData, folder: Path, extension: str) -> Path:
        case = data.get("caso", {}) if isinstance(data, Mapping) else {}
        report_name = build_report_filename(
            case.get("tipo_informe"), case.get("id_caso"), extension
        )
        return Path(folder) / report_name

    @staticmethod
    def _build_report_prefix(data: CaseData) -> str:
        """Devuelve el prefijo normalizado para los reportes y exportaciones.

        Se apoya en ``build_report_filename`` para reutilizar la misma lógica
        de limpieza aplicada a los informes DOCX/MD, eliminando la extensión
        para poder reutilizar el prefijo en los CSV y en el JSON.
        """

        case = data.get("caso", {}) if isinstance(data, Mapping) else {}
        return Path(
            build_report_filename(case.get("tipo_informe"), case.get("id_caso"), "csv")
        ).stem

    def _generate_report_file(
        self, extension: str, builder, description: str, *, source_widget: Optional[tk.Widget] = None
    ) -> None:
        data, folder, case_id = self._prepare_case_data_for_export()
        if not data or not folder or not case_id:
            return
        if extension == "docx" and not self._docx_available:
            warning = f"No se puede generar Word sin python-docx. {DOCX_MISSING_MESSAGE}"
            messagebox.showwarning("Informe Word no disponible", warning)
            log_event("validacion", warning, self.logs)
            return
        report_path = self._build_report_path(data, folder, extension)
        try:
            created_path = builder(data, report_path)
        except Exception as exc:  # pragma: no cover - protección frente a fallos externos
            messagebox.showerror(
                "Error al generar informe",
                f"No se pudo generar el informe {description.lower()}: {exc}",
            )
            log_event("validacion", f"Error al generar informe {extension}: {exc}", self.logs)
            return
        self._mirror_exports_to_external_drive([created_path], case_id)
        messagebox.showinfo(
            "Informe generado",
            f"El informe {description} se ha guardado como {created_path.name}.",
        )
        log_event("navegacion", f"Informe {extension} generado", self.logs)
        self.flush_logs_now()
        self._play_feedback_sound()
        self._show_success_toast(source_widget)

    def generate_docx_report(self):
        self._generate_report_file(
            "docx", build_docx, "Word (.docx)", source_widget=self.btn_docx
        )

    def generate_md_report(self):
        md_button = self.actions_action_bar.buttons.get("md") if hasattr(self, "actions_action_bar") else None
        self._generate_report_file(
            "md", save_md, "Markdown (.md)", source_widget=md_button
        )

    def save_and_send(self):
        """Valida los datos y guarda CSVs normalizados y JSON en la carpeta de exportación."""
        log_event("navegacion", "Usuario pulsó guardar y enviar", self.logs)
        data, folder, case_id = self._prepare_case_data_for_export()
        if not data or not folder or not case_id:
            return
        folder = Path(folder)
        report_prefix = self._build_report_prefix(data)
        # Guardar CSVs
        created_files = []

        def _sanitize_csv_value(value):
            sanitized = sanitize_rich_text("" if value is None else value, max_chars=None)
            if sanitized.startswith(("=", "+", "-", "@")):
                return f"'{sanitized}"
            return sanitized

        def write_csv(file_name, rows, header):
            path = folder / f"{report_prefix}_{file_name}"
            with path.open('w', newline='', encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                for row in rows:
                    sanitized_row = {
                        field: _sanitize_csv_value(row.get(field, "")) for field in header
                    }
                    writer.writerow(sanitized_row)
            created_files.append(path)
        # CASOS
        write_csv(
            'casos.csv',
            [data['caso']],
            [
                'id_caso',
                'tipo_informe',
                'categoria1',
                'categoria2',
                'modalidad',
                'canal',
                'proceso',
                'fecha_de_ocurrencia',
                'fecha_de_descubrimiento',
                'centro_costos',
                'matricula_investigador',
                'investigador_nombre',
                'investigador_cargo',
            ],
        )
        # CLIENTES
        write_csv(
            'clientes.csv',
            data['clientes'],
            [
                'id_cliente',
                'id_caso',
                'nombres',
                'apellidos',
                'tipo_id',
                'flag',
                'telefonos',
                'correos',
                'direcciones',
                'accionado',
            ],
        )
        # COLABORADORES
        write_csv(
            'colaboradores.csv',
            data['colaboradores'],
            [
                'id_colaborador',
                'id_caso',
                'flag',
                'nombres',
                'apellidos',
                'division',
                'area',
                'servicio',
                'puesto',
                'fecha_carta_inmediatez',
                'fecha_carta_renuncia',
                'nombre_agencia',
                'codigo_agencia',
                'tipo_falta',
                'tipo_sancion',
            ],
        )
        # PRODUCTOS
        write_csv('productos.csv', data['productos'], ['id_producto', 'id_caso', 'id_cliente', 'categoria1', 'categoria2', 'modalidad', 'canal', 'proceso', 'fecha_ocurrencia', 'fecha_descubrimiento', 'monto_investigado', 'tipo_moneda', 'monto_perdida_fraude', 'monto_falla_procesos', 'monto_contingencia', 'monto_recuperado', 'monto_pago_deuda', 'tipo_producto'])
        # PRODUCTO_RECLAMO
        write_csv('producto_reclamo.csv', data['reclamos'], ['id_reclamo', 'id_caso', 'id_producto', 'nombre_analitica', 'codigo_analitica'])
        # INVOLUCRAMIENTO
        write_csv('involucramiento.csv', data['involucramientos'], ['id_producto', 'id_caso', 'id_colaborador', 'monto_asignado'])
        # DETALLES_RIESGO
        write_csv('detalles_riesgo.csv', data['riesgos'], ['id_riesgo', 'id_caso', 'lider', 'descripcion', 'criticidad', 'exposicion_residual', 'planes_accion'])
        # DETALLES_NORMA
        write_csv('detalles_norma.csv', data['normas'], ['id_norma', 'id_caso', 'descripcion', 'fecha_vigencia'])
        # ANALISIS
        analysis_texts = self._normalize_analysis_texts(data['analisis'])
        analysis_row = {
            "id_caso": data['caso']['id_caso'],
            **{
                key: (value.get("text") if isinstance(value, Mapping) else "")
                for key, value in analysis_texts.items()
            },
        }
        write_csv('analisis.csv', [analysis_row], ['id_caso', 'antecedentes', 'modus_operandi', 'hallazgos', 'descargos', 'conclusiones', 'recomendaciones'])
        # LOGS
        if self.logs:
            write_csv('logs.csv', [normalize_log_row(row) for row in self.logs], LOG_FIELDNAMES)
        # Guardar JSON
        json_path = folder / f"{report_prefix}_version.json"
        with json_path.open('w', encoding="utf-8") as f:
            json.dump(data.as_dict(), f, ensure_ascii=False, indent=2)
        created_files.append(json_path)
        # Guardar informe Markdown
        md_path = self._build_report_path(data, folder, "md")
        created_files.append(save_md(data, md_path))
        docx_path: Optional[Path] = None
        if self._docx_available:
            docx_path = self._build_report_path(data, folder, "docx")
            created_files.append(build_docx(data, docx_path))
        else:
            warning = (
                f"El informe Word no se generó para el caso {case_id}: {DOCX_MISSING_MESSAGE}"
            )
            log_event("validacion", warning, self.logs)
            if not getattr(self, '_suppress_messagebox', False):
                messagebox.showwarning("Informe Word no disponible", warning)
        if hasattr(self, "root") and self.root:
            ConfettiBurst(
                self.root,
                self.root.winfo_pointerx(),
                self.root.winfo_pointery(),
            )
        self._mirror_exports_to_external_drive(created_files, case_id)
        reports = [md_path.name]
        if docx_path:
            reports.append(docx_path.name)
        messagebox.showinfo(
            "Datos guardados",
            (
                f"Los archivos se han guardado como {report_prefix}_*.csv, {report_prefix}_version.json "
                "y {informes}."
            ).format(informes=" y ".join(reports)),
        )
        log_event("navegacion", "Datos guardados y enviados", self.logs)
        self.flush_logs_now()
        self._play_feedback_sound()
        self._handle_session_saved(data)
        save_button = self.actions_action_bar.buttons.get("save_send") if hasattr(self, "actions_action_bar") else None
        self._show_success_toast(save_button)

    def _mirror_exports_to_external_drive(self, file_paths, case_id: str) -> None:
        normalized_sources = [Path(path) for path in file_paths or [] if path]
        if not normalized_sources:
            return
        external_base = self._get_external_drive_path()
        if not external_base:
            return
        case_label = case_id or 'caso'
        case_folder = external_base / case_label
        try:
            case_folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            message = f"No se pudo crear la carpeta de respaldo {case_folder}: {exc}"
            log_event("validacion", message, self.logs)
            if not getattr(self, '_suppress_messagebox', False):
                messagebox.showwarning("Copia pendiente", message)
            return
        autosave_abs = Path(AUTOSAVE_FILE).resolve()
        failures = []
        for source in normalized_sources:
            if not source.exists():
                continue
            if source.resolve() == autosave_abs:
                continue
            destination = case_folder / source.name
            try:
                shutil.copy2(source, destination)
            except OSError as exc:
                failures.append((source, exc))
                log_event(
                    "validacion",
                    f"No se pudo copiar {source} a {destination}: {exc}",
                    self.logs,
                )
        if failures and not getattr(self, '_suppress_messagebox', False):
            lines = [
                "Se exportaron los archivos, pero algunos no se copiaron al respaldo externo:",
            ]
            for source, exc in failures:
                lines.append(f"- {source.name}: {exc}")
            messagebox.showwarning("Copia incompleta", "\n".join(lines))

    def save_temp_version(self, data=None):
        """Guarda una versión temporal del estado actual del formulario.

        Este método recoge los datos actuales mediante ``gather_data`` y los
        escribe en un archivo JSON con un sufijo de marca de tiempo. El
        fichero se guarda en el mismo directorio que el script y se nombra
        ``<id_caso>_temp_<YYYYMMDD_HHMMSS>.json``. Si no se ha especificado
        un ID de caso todavía, se utiliza ``caso`` como prefijo. El planificador
        de autosave lo ejecuta de forma diferida para consolidar múltiples
        ediciones cercanas.

        Examples:
            >>> app.save_temp_version()
            # Crea un archivo como ``2025-0001_temp_20251114_154501.json`` con
            # el contenido completo del formulario.
        """
        data = self._ensure_case_data(data or self.gather_data())
        now = datetime.now()
        if self._last_temp_saved_at and now <= self._last_temp_saved_at:
            now = self._last_temp_saved_at + timedelta(seconds=1)
        signature = self._compute_temp_signature(data)
        if not self._should_persist_temp(signature, now):
            return
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        case_id = data.get('caso', {}).get('id_caso', '') or 'caso'
        filename = f"{case_id}_temp_{timestamp}.json"
        target_path = Path(BASE_DIR) / filename
        while target_path.exists():
            now += timedelta(seconds=1)
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            filename = f"{case_id}_temp_{timestamp}.json"
            target_path = Path(BASE_DIR) / filename
        json_payload = json.dumps(data.as_dict(), ensure_ascii=False, indent=2)
        primary_written = False
        preserved = set()
        external_written = False
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log_event(
                "validacion",
                f"No se pudo preparar la carpeta local para la versión temporal: {exc}",
                self.logs,
            )
        else:
            try:
                target_path.write_text(json_payload, encoding='utf-8')
                primary_written = True
                preserved.add(filename)
            except OSError as ex:
                # Registrar en el log pero no interrumpir
                log_event(
                    "validacion",
                    f"Error guardando versión temporal en la carpeta principal: {ex}",
                    self.logs,
                )
        external_base = self._get_external_drive_path()
        if external_base:
            case_folder = Path(external_base) / case_id
            try:
                case_folder.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                log_event(
                    "validacion",
                    f"No se pudo preparar la carpeta externa para {case_id}: {exc}",
                    self.logs,
                )
            else:
                mirror_path = case_folder / filename
                if primary_written:
                    try:
                        shutil.copy2(target_path, mirror_path)
                        preserved.add(filename)
                        external_written = True
                    except OSError as exc:
                        log_event(
                            "validacion",
                            f"No se pudo copiar la versión temporal a la carpeta externa: {exc}",
                            self.logs,
                        )
                if not primary_written or not external_written:
                    try:
                        mirror_path.write_text(json_payload, encoding='utf-8')
                        preserved.add(filename)
                        external_written = True
                    except OSError as exc:
                        log_event(
                            "validacion",
                            f"No se pudo escribir la versión temporal en la carpeta externa: {exc}",
                            self.logs,
                        )
        if primary_written or external_written:
            self._last_temp_saved_at = now
            self._last_temp_signature = signature
            self._trim_temp_versions(case_id, preserved)


# ---------------------------------------------------------------------------
# API pública

__all__ = ["FraudCaseApp", "should_autofill_field"]


# ---------------------------------------------------------------------------
# Ejecución de la aplicación

def run_app():
    root = tk.Tk()
    style = ThemeManager.build_style(root)
    saved_theme = ThemeManager.load_saved_theme()
    ThemeManager.apply(saved_theme, root=root, style=style)
    app = FraudCaseApp(root)
    ThemeManager.apply_to_widget_tree(root)
    root.mainloop()
