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

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import csv
import json
import os
import random
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import partial

# ---------------------------------------------------------------------------
# Constantes y listas de opciones
# Estas constantes definen las listas de opciones disponibles en los distintos
# campos de la interfaz. Se trasladan de la implementación en JavaScript y
# tienen el mismo significado.

# Taxonomía de fraude: nivel 1 -> nivel 2 -> modalidades
TAXONOMIA = {
    "Riesgo de Fraude": {
        "Fraude Interno": [
            "Apropiación de fondos",
            "Transferencia ilegal de fondos",
            "Solicitud fraudulenta",
            "Hurto",
            "Fraude de venta de productos/servicios",
        ],
        "Fraude Externo": [
            "Apropiación de fondos",
            "Estafa",
            "Extorsión",
            "Fraude en valorados",
            "Solicitud fraudulenta",
        ],
    },
    "Riesgo de Ciberseguridad": {
        "Perdida de Confidencialidad": [
            "Robo de información",
            "Revelación de secreto bancario",
        ],
        "Perdida de Disponibilidad": [
            "Destrucción de información",
            "Interrupción de servicio",
        ],
        "Perdida de Integridad": [
            "Modificación no autorizada de información",
            "Operaciones no autorizadas",
        ],
    },
    "Riesgo Legal y Cumplimiento": {
        "Abuso del mercado": [
            "Conflicto de interés",
            "Manipulación de mercado",
        ],
        "Conducta de mercado": [
            "Gestión de reclamos",
            "Malas prácticas de negocio",
        ],
        "Corrupción": [
            "Cohecho público",
            "Corrupción entre privados",
        ],
        "Cumplimiento Normativo": [
            "Implementación de normas",
            "Reportes y requerimientos regulatorios",
        ],
    },
}

# Lista de canales disponibles para productos y casos
CANAL_LIST = [
    "A través de funcionario",
    "Agencias",
    "App IO",
    "Agentes BCP",
    "Banca Móvil",
    "Centro de contacto",
    "Homebanking",
    "Kioskos",
    "Mesa de partes",
    "Página Web Mi Negocio",
    "Página Web Yape",
    "Web Ventas Digitales",
    "No aplica",
]

# Lista de procesos impactados disponibles
PROCESO_LIST = [
    "Activación de Tarjeta de crédito",
    "Actualización de datos de cliente",
    "Afiliación al servicio",
    "Bloqueo de cuentas",
    "Compras de deuda de Tarjeta de Crédito",
    "Venta de crédito Pyme",
    "Venta de crédito hipotecario",
    "Venta de crédito comercial",
    "Venta de crédito vehicular",
    "Venta de Leasing",
    "Venta de descuento de letras",
    "Venta de Efectivo Preferente",
    "Venta de crédito digital",
    "Venta en Banca Móvil",
    "Venta en Homebanking",
]

# Lista de tipos de producto
TIPO_PRODUCTO_LIST = [
    "Adelanto de sueldo",
    "autodesembolso",
    "Billeteras digitales",
    "Cambios Spot",
    "Carta fianza",
    "Cartas Crédito de Exportación",
    "Cartas de Crédito de Importación",
    "Certificados bancarios",
    "Cheque de gerencia",
    "Cobranza de Exportación",
    "Cobranza de importación",
    "Cobranza de letras",
    "Comercio exterior",
    "Crédito efectivo",
    "Crédito flexible",
    "Crédito hipotecario",
    "Crédito personal",
    "Crédito Pyme",
    "Crédito vehicular",
    "Crédito a la construcción",
    "Crédito comercial",
    "CTS",
    "Cuenta a plazo",
    "Cuenta corriente",
    "Cuenta de ahorro",
    "Débito automático",
    "Depósito a plazo",
    "Depósito estructurado DTV",
    "Descuento de letras",
    "Factoring electrónico",
    "Facturas negociables",
    "Financiamiento electrónico de Compras FEC",
    "Fondos mutuos",
    "Forex Spot",
    "Forwards",
    "Forwards OM",
    "Garantías",
    "Leasing",
    "Letras y Facturas",
    "Mediano Plazo",
    "Opciones tipo de cambio",
    "Pago de haberes",
    "Pago electrónico de tributos y obligaciones",
    "Partidas pendientes",
    "Remesas migratorias",
    "Seguros optativos",
    "Servicios de recaudación",
    "Swaps",
    "Tarjeta de crédito",
    "Tarjeta de crédito digital iO",
    "Tarjeta de débito",
    "Tarjeta Solución Negocio",
    "Telecrédito",
    "Transferencias país",
    "Transferencias al exterior",
    "Transferencias del exterior",
    "Transferencias interbancarias",
    "Transversal a varios productos Banca Personas y Empresas",
    "Yape",
    "Reclamos",
    "No aplica",
]

# Listas para otros campos
TIPO_INFORME_LIST = ["Gerencia", "Interno", "Credicorp"]
TIPO_ID_LIST = ["DNI", "Pasaporte", "RUC", "Carné de extranjería", "No aplica"]
FLAG_CLIENTE_LIST = ["Involucrado", "Afectado", "No aplica"]
FLAG_COLABORADOR_LIST = ["Involucrado", "Relacionado", "No aplica"]
TIPO_FALTA_LIST = ["Inconducta funcional", "Negligencia funcional", "No aplica"]
TIPO_SANCION_LIST = [
    "Amonestación",
    "Sin sanción - Cesado",
    "Despido",
    "Desvinculación",
    "Exhortación",
    "No aplica",
    "Renuncia",
    "Suspensión 1 día",
    "Suspensión 2 días",
    "Suspensión de 3 días",
    "Suspensión de 4 días",
    "Suspensión de 5 días",
]
TIPO_MONEDA_LIST = ["Soles", "Dólares", "No aplica"]
CRITICIDAD_LIST = ["Bajo", "Moderado", "Relevante", "Alto", "Crítico"]


# ---------------------------------------------------------------------------
# Ficheros de datos externos
#
# Esta aplicación puede cargar características adicionales de colaboradores y clientes
# desde ficheros CSV externos ubicados en el mismo directorio que el script. Si
# existen, se utilizarán para autopoblar campos y validar que los IDs ingresados
# correspondan a registros reales. El fichero ``team_details.csv`` contiene
# información sobre colaboradores (división, área, servicio, puesto, agencia y
# código). El fichero ``client_details.csv`` contiene información sobre
# clientes (tipo de documento, flag, teléfonos, correos, direcciones y
# accionados). Estos ficheros son opcionales: si no se encuentran, la
# aplicación seguirá funcionando, pero no se autopoblarán datos adicionales.

# Archivo con detalles de colaboradores para autopoblado
TEAM_DETAILS_FILE = os.path.join(os.path.dirname(__file__), "team_details.csv")
# Archivo con detalles de clientes para autopoblado
CLIENT_DETAILS_FILE = os.path.join(os.path.dirname(__file__), "client_details.csv")
# Archivo con detalles de productos para autopoblado
PRODUCT_DETAILS_FILE = os.path.join(os.path.dirname(__file__), "productos_masivos.csv")

# Ruta de autosave
AUTOSAVE_FILE = os.path.join(os.path.dirname(__file__), "autosave.json")

# Ruta de logs si se desea guardar de forma permanente
LOGS_FILE = os.path.join(os.path.dirname(__file__), "logs.csv")

# Opciones de áreas accionadas disponibles para el selector múltiple
ACCIONADO_OPTIONS = [
    "Tribu Producto Afectado",
    "Tribu Canal Impactado",
    "Centro de Contacto",
    "Canal presencial",
    "Fuerza de Ventas",
    "Mesa de Partes",
    "Unidad de Fraude",
    "No aplica",
]


# ---------------------------------------------------------------------------
# Funciones de utilidad

def load_team_details():
    """Carga los datos de colaboradores desde team_details.csv si existe.

    Devuelve un diccionario donde la clave es el ID del colaborador y el
    valor es un diccionario con las claves: division, area, servicio,
    puesto, nombre_agencia, codigo_agencia.
    """
    lookup = {}
    try:
        with open(TEAM_DETAILS_FILE, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get("id_colaborador") or row.get("IdTeamMember") or row.get("Id")
                if key:
                    lookup[key.strip()] = {
                        "division": row.get("division", "").strip(),
                        "area": row.get("area", "").strip(),
                        "servicio": row.get("servicio", "").strip(),
                        "puesto": row.get("puesto", "").strip(),
                        "nombre_agencia": row.get("nombre_agencia", "").strip(),
                        "codigo_agencia": row.get("codigo_agencia", "").strip(),
                    }
    except FileNotFoundError:
        pass
    return lookup

def load_client_details():
    """Carga los datos de clientes desde ``client_details.csv`` si existe.

    Devuelve un diccionario donde la clave es el ID del cliente y el valor es
    un diccionario con las claves: ``tipo_id``, ``flag``, ``telefonos``,
    ``correos``, ``direcciones`` y ``accionado``. Esta función se utiliza
    para autopoblar los campos de un cliente cuando se reconoce su ID.

    Formato del CSV esperado (con encabezados en español)::

        id_cliente,tipo_id,flag,telefonos,correos,direcciones,accionado
        12345678,DNI,Involucrado,987654321;912345678,cliente@ejemplo.com,Av La Paz 123 Lima,
        C00001,RUC,Afectado,999999999,otro@ejemplo.pe,Calle 5 345 Lima,Centro de Contacto

    Returns:
        dict[str, dict[str, str]]: Mapa de ID a datos del cliente.
    """
    lookup = {}
    try:
        with open(CLIENT_DETAILS_FILE, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get("id_cliente") or row.get("IdCliente") or row.get("IDCliente")
                if key:
                    lookup[key.strip()] = {
                        "tipo_id": row.get("tipo_id", row.get("TipoID", "")).strip(),
                        "flag": row.get("flag", row.get("Flag", "")).strip(),
                        "telefonos": row.get("telefonos", row.get("Telefono", "")).strip(),
                        "correos": row.get("correos", row.get("Correo", "")).strip(),
                        "direcciones": row.get("direcciones", row.get("Direccion", "")).strip(),
                        "accionado": row.get("accionado", row.get("Accionado", "")).strip(),
                    }
    except FileNotFoundError:
        # Si no existe el archivo de clientes se devuelve diccionario vacío
        pass
    return lookup


def load_product_details():
    """Carga detalles de productos desde ``productos_masivos.csv`` si existe.

    La función devuelve un diccionario con los datos necesarios para
    autopoblar un producto (cliente, taxonomía, montos, fechas y reclamo)
    cuando el usuario escribe el identificador.  Si el archivo no existe,
    se retorna un diccionario vacío para mantener la compatibilidad.

    Example:
        >>> productos = load_product_details()
        >>> productos.get('PRD001', {}).get('id_cliente')
        '12345678'

    Returns:
        dict[str, dict[str, str]]: Mapa de ID de producto con su metadata.
    """
    lookup = {}
    try:
        with open(PRODUCT_DETAILS_FILE, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get("id_producto", "").strip()
                if not key:
                    continue
                lookup[key] = {
                    "id_cliente": row.get("id_cliente", "").strip(),
                    "tipo_producto": row.get("tipo_producto", "").strip(),
                    "categoria1": row.get("categoria1", "").strip(),
                    "categoria2": row.get("categoria2", "").strip(),
                    "modalidad": row.get("modalidad", "").strip(),
                    "canal": row.get("canal", "").strip(),
                    "proceso": row.get("proceso", "").strip(),
                    "fecha_ocurrencia": row.get("fecha_ocurrencia", "").strip(),
                    "fecha_descubrimiento": row.get("fecha_descubrimiento", "").strip(),
                    "monto_investigado": row.get("monto_investigado", "").strip(),
                    "tipo_moneda": row.get("tipo_moneda", "").strip(),
                    "monto_perdida_fraude": row.get("monto_perdida_fraude", "").strip(),
                    "monto_falla_procesos": row.get("monto_falla_procesos", "").strip(),
                    "monto_contingencia": row.get("monto_contingencia", "").strip(),
                    "monto_recuperado": row.get("monto_recuperado", "").strip(),
                    "monto_pago_deuda": row.get("monto_pago_deuda", "").strip(),
                    "id_reclamo": row.get("id_reclamo", "").strip(),
                    "nombre_analitica": row.get("nombre_analitica", "").strip(),
                    "codigo_analitica": row.get("codigo_analitica", "").strip(),
                }
    except FileNotFoundError:
        pass
    return lookup


# ---------------------------------------------------------------------------
# Validadores reutilizables y componentes de ayuda visual

def validate_required_text(value, label):
    """Valida que un texto obligatorio tenga contenido.

    Args:
        value (str): Texto a evaluar.
        label (str): Nombre del campo que se mostrará al usuario.

    Returns:
        Optional[str]: Mensaje de error si está vacío, ``None`` si es válido.
    """
    if not value.strip():
        return f"Debe ingresar {label}."
    return None


def validate_case_id(value):
    """Valida el formato del número de caso AAAA-NNNN.

    Example:
        >>> validate_case_id('2024-0001')
        None
        >>> validate_case_id('24-1')
        'El número de caso debe seguir el formato AAAA-NNNN.'
    """
    if not value.strip():
        return "Debe ingresar el número de caso."
    if not re.match(r"^\d{4}-\d{4}$", value.strip()):
        return "El número de caso debe seguir el formato AAAA-NNNN."
    return None


def validate_date_text(value, label, allow_blank=True):
    """Valida fechas en formato ISO ``YYYY-MM-DD``.

    Args:
        value (str): Fecha a validar.
        label (str): Nombre descriptivo del campo.
        allow_blank (bool): Si es ``True`` permite valores vacíos.
    """
    if not value.strip():
        return None if allow_blank else f"Debe ingresar {label}."
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return f"{label} debe tener el formato YYYY-MM-DD."
    return None


AMOUNT_PATTERN = re.compile(r"^\d{1,12}(\.\d{1,2})?$")


def validate_amount_text(value, label, allow_blank=True):
    """Valida montos positivos con hasta 12 enteros y dos decimales."""

    text = value.strip()
    if not text:
        return None if allow_blank else f"Debe ingresar {label}."
    if not AMOUNT_PATTERN.match(text):
        return (
            f"{label} debe usar solo dígitos, con máximo 12 enteros y hasta dos decimales."
        )
    return None


def parse_decimal_amount(value):
    """Devuelve un ``Decimal`` para montos o ``None`` si el texto no es válido."""

    text = (value or "").strip()
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def validate_address_list(value, label):
    """Valida direcciones peruanas permisivas separadas por ``;``."""

    if not value.strip():
        return None
    pattern = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ0-9 #.,'/-]+$")
    for addr in [item.strip() for item in value.split(';') if item.strip()]:
        if not pattern.match(addr):
            return f"Cada dirección en {label} debe usar letras, números y separadores comunes."
    return None


def validate_client_identifier(doc_type, value):
    """Valida IDs de cliente según el tipo de documento peruano seleccionado."""

    clean = value.strip().upper()
    if not clean:
        return "Debe ingresar el ID del cliente."
    doc = (doc_type or "").lower()
    doc_normalized = doc.replace("é", "e")
    patterns = {
        "dni": r"^\d{8}$",
        "ruc": r"^\d{11}$",
        "carne de extranjeria": r"^[A-Z0-9]{9}$",
        "pasaporte": r"^[A-Z0-9]{6,12}$",
    }
    if doc_normalized in patterns and not re.match(patterns[doc_normalized], clean):
        return f"El ID del cliente no cumple el formato requerido para {doc_type}."
    return None


def validate_team_member_id(value):
    """Valida IDs de colaboradores con una letra y cinco dígitos (ej. T12345)."""

    clean = value.strip().upper()
    if not clean:
        return "Debe ingresar el ID del colaborador."
    if not re.match(r"^[A-Z][0-9]{5}$", clean):
        return "El ID del colaborador debe ser una letra seguida de cinco dígitos (ej. T12345)."
    return None


def validate_agency_code(value):
    """Valida códigos de agencia opcionales compuestos por seis dígitos."""

    clean = value.strip()
    if not clean:
        return None
    if not re.match(r"^\d{6}$", clean):
        return "El código de agencia debe tener exactamente 6 dígitos."
    return None


def validate_email_list(value, label):
    """Valida listas separadas por ``;`` asegurando que cada correo tenga ``@``."""
    if not value.strip():
        return None
    for email in [item.strip() for item in value.split(';') if item.strip()]:
        if '@' not in email or email.startswith('@') or email.endswith('@'):
            return f"Cada correo en {label} debe contener '@'."
    return None


def validate_phone_list(value, label):
    """Valida que los teléfonos sean números peruanos de al menos 6 dígitos."""
    if not value.strip():
        return None
    for phone in [item.strip() for item in value.split(';') if item.strip()]:
        if not phone.isdigit() or len(phone) < 6:
            return f"Cada teléfono en {label} debe tener solo dígitos y al menos 6 caracteres."
    return None


def validate_reclamo_id(value):
    """Valida que el ID de reclamo siga el patrón ``CXXXXXXXX``."""
    if not value.strip():
        return None
    if not re.match(r"^C\d{8}$", value.strip()):
        return "El ID de reclamo debe iniciar con C seguido de 8 dígitos."
    return None


def validate_codigo_analitica(value):
    """Valida que el código de analítica tenga 10 dígitos y prefijo permitido."""
    if not value.strip():
        return None
    if not (value.isdigit() and len(value) == 10 and value.startswith(('43', '45', '46', '56'))):
        return "El código de analítica debe tener 10 dígitos y comenzar con 43, 45, 46 o 56."
    return None


def validate_norm_id(value):
    """Valida IDs de norma en formato ``XXXX.XXX.XX.XX``."""
    if not value.strip():
        return None
    if not re.match(r"^\d{4}\.\d{3}\.\d{2}\.\d{2}$", value.strip()):
        return "El ID de norma debe seguir el formato XXXX.XXX.XX.XX."
    return None


def validate_multi_selection(value, label, allow_empty=False, valid_options=None):
    """Valida campos multiselección opcionales u obligatorios.

    Args:
        value (str): Cadena separada por ``;`` que representa las
            selecciones actuales.
        label (str): Nombre amigable del campo para los mensajes.
        allow_empty (bool): Cuando es ``True`` no se exige al menos un
            valor; el campo puede quedar sin selección.
        valid_options (Iterable[str], opcional): Lista de valores
            permitidos que se utilizará para detectar entradas inválidas.

    Returns:
        str | None: Mensaje de error en español o ``None`` si la entrada
            es válida.
    """

    clean = value.strip()
    if not clean:
        return None if allow_empty else f"Debe seleccionar al menos una opción en {label}."

    selections = [item.strip() for item in clean.split(';') if item.strip()]
    if valid_options:
        invalid = [sel for sel in selections if sel not in valid_options]
        if invalid:
            return f"{label} solo admite opciones conocidas. Revise: {', '.join(invalid)}."
    return None


class HoverTooltip:
    """Muestra mensajes contextuales cuando el usuario pasa el mouse sobre un widget.

    Este tooltip ayuda a los usuarios nuevos a entender el propósito de cada
    campo.  Se activa con un pequeño retardo para no resultar intrusivo y se
    oculta automáticamente al mover el cursor.

    Example:
        >>> HoverTooltip(mi_boton, "Guarda el formulario actual")
    """

    def __init__(self, widget, text, delay=300):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow = None
        self.after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)
        widget.bind("<Destroy>", self._on_destroy)

    def _schedule(self, _event=None):
        """Programa la aparición del tooltip tras el retardo configurado."""
        self._cancel()
        self.after_id = self.widget.after(self.delay, self.show)

    def _cancel(self):
        """Cancela cualquier tooltip pendiente para evitar acumulación."""
        if self.after_id is not None:
            try:
                self.widget.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None

    def show(self):
        """Crea la ventana emergente y la posiciona debajo del widget."""
        if self.tipwindow or not self.text:
            return
        try:
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        except tk.TclError:
            return
        self.tipwindow = tk.Toplevel(self.widget)
        self.tipwindow.wm_overrideredirect(True)
        self.tipwindow.configure(bg="#333333")
        label = tk.Label(
            self.tipwindow,
            text=self.text,
            justify="left",
            background="#333333",
            foreground="#ffffff",
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=3,
            wraplength=280,
        )
        label.pack()
        self.tipwindow.wm_geometry(f"+{x}+{y}")

    def _hide(self, _event=None):
        """Elimina el tooltip cuando el cursor sale del widget."""
        self._cancel()
        if self.tipwindow is not None:
            try:
                self.tipwindow.destroy()
            except tk.TclError:
                pass
            self.tipwindow = None

    def _on_destroy(self, _event=None):
        """Garantiza que la ventana se cierre si el widget se destruye."""
        self._hide()


class ValidationTooltip:
    """Muestra mensajes de error en rojo justo debajo del widget asociado."""

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        widget.bind("<Destroy>", self._on_destroy)

    def show(self, text):
        """Crea o actualiza la burbuja de error con el mensaje indicado."""
        if not text:
            self.hide()
            return
        self.hide()
        try:
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        except tk.TclError:
            return
        self.tipwindow = tk.Toplevel(self.widget)
        self.tipwindow.wm_overrideredirect(True)
        self.tipwindow.configure(bg="#8B0000")
        label = tk.Label(
            self.tipwindow,
            text=text,
            justify="left",
            background="#8B0000",
            foreground="#ffffff",
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=3,
            wraplength=320,
        )
        label.pack()
        self.tipwindow.wm_geometry(f"+{x}+{y}")

    def hide(self):
        """Oculta el tooltip de validación si está visible."""
        if self.tipwindow is not None:
            try:
                self.tipwindow.destroy()
            except tk.TclError:
                pass
            self.tipwindow = None

    def _on_destroy(self, _event=None):
        """Evita errores cuando el widget asociado se elimina."""
        self.hide()


class FieldValidator:
    """Vincula un widget con una función de validación en tiempo real.

    Este helper adjunta *traces* a las variables observadas y muestra
    automáticamente un ``ValidationTooltip`` con el mensaje retornado por la
    función ``validate_callback``.  El tooltip se oculta cuando el valor vuelve
    a ser válido.  También registra eventos en el log para mantener trazabilidad
    y, si el widget es un ``ttk.Combobox``, escucha ``<<ComboboxSelected>>`` para
    reaccionar apenas el usuario cambie la opción.

    Args:
        widget (tk.Widget): Control que recibirá el mensaje de error.
        validate_callback (Callable[[], Optional[str]]): Función que devuelve
            ``None`` si el campo es válido o el mensaje de error en español.
        logs (list): Referencia al arreglo de logs para documentar errores.
        field_name (str): Nombre legible usado en el log.
        variables (Optional[list[tk.Variable]]): Lista de variables a observar.
    """

    def __init__(self, widget, validate_callback, logs, field_name, variables=None):
        self.widget = widget
        self.validate_callback = validate_callback
        self.logs = logs
        self.field_name = field_name
        self.tooltip = ValidationTooltip(widget)
        self.variables = variables or []
        self._traces = []
        self.last_error = None
        for var in self.variables:
            self._traces.append(var.trace_add("write", self._on_change))
        widget.bind("<FocusOut>", self._on_change)
        widget.bind("<KeyRelease>", self._on_change)
        if isinstance(widget, ttk.Combobox):
            widget.bind("<<ComboboxSelected>>", self._on_change)
        self._on_change()

    def _on_change(self, *_args):
        """Ejecuta la validación y actualiza el tooltip sólo si cambió el estado."""
        error = self.validate_callback()
        if error == self.last_error:
            return
        if error:
            self.tooltip.show(error)
            log_event("validacion", f"{self.field_name}: {error}", self.logs)
        else:
            self.tooltip.hide()
        self.last_error = error

# Callback global opcional para guardar versiones temporales
SAVE_TEMP_CALLBACK = None

def log_event(event_type, message, logs):
    """Registra un evento en la lista de logs y realiza un guardado temporal.

    Cada vez que se registra un evento (de navegación o de validación), se añade
    una entrada al log con la marca de tiempo actual. Además, si existe una
    función ``SAVE_TEMP_CALLBACK`` definida, se invoca inmediatamente para
    generar un archivo JSON temporal del estado actual del formulario. Esto
    permite llevar un registro de versiones sucesivas del formulario cada vez
    que el usuario edita un campo.

    Args:
        event_type (str): Tipo del evento (por ejemplo ``'navegacion'`` o
            ``'validacion'``).
        message (str): Descripción del evento.
        logs (list): Lista de registros donde se añadirá el nuevo log.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {"timestamp": timestamp, "tipo": event_type, "mensaje": message}
    logs.append(row)
    _append_log_to_disk(row)
    # Ejecutar callback de guardado temporal si está definido y el evento es de navegación
    if SAVE_TEMP_CALLBACK is not None and event_type == 'navegacion':
        try:
            SAVE_TEMP_CALLBACK()
        except Exception:
            # Ignorar errores en el guardado temporal para no interrumpir el uso
            pass


def _append_log_to_disk(row):
    """Persiste cada entrada de log en ``LOGS_FILE``."""

    if not LOGS_FILE:
        return
    folder = os.path.dirname(LOGS_FILE)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    file_exists = os.path.exists(LOGS_FILE)
    try:
        with open(LOGS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'tipo', 'mensaje'])
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except OSError:
        pass


def escape_csv(value):
    """Escapa un valor para ser escrito en CSV.

    Si el valor contiene comas, saltos de línea o comillas, se encierra
    entre comillas dobles y se escapan las comillas internas.
    """
    if value is None:
        return ""
    s = str(value)
    if any(ch in s for ch in [',', '\n', '"']):
        s = s.replace('"', '""')
        s = f'"{s}"'
    return s


# ---------------------------------------------------------------------------
# Clases de componentes dinámicos

class ClientFrame:
    """Representa un cliente y su interfaz dentro de la sección de clientes."""

    def __init__(self, parent, idx, remove_callback, update_client_options, logs, tooltip_register, client_lookup=None):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.update_client_options = update_client_options
        self.logs = logs
        self.tooltip_register = tooltip_register
        # Diccionario con datos de clientes para autopoblado
        self.client_lookup = client_lookup or {}
        self.validators = []

        # Variables de control
        self.tipo_id_var = tk.StringVar(value=TIPO_ID_LIST[0])
        self.id_var = tk.StringVar()
        self.flag_var = tk.StringVar(value=FLAG_CLIENTE_LIST[0])
        self.telefonos_var = tk.StringVar()
        self.correos_var = tk.StringVar()
        self.direcciones_var = tk.StringVar()
        self.accionado_var = tk.StringVar()

        # Crear el contenedor
        self.frame = ttk.LabelFrame(parent, text=f"Cliente {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)

        # Fila 1: Tipo de ID e ID
        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="Tipo de ID:").pack(side="left")
        tipo_id_cb = ttk.Combobox(row1, textvariable=self.tipo_id_var, values=TIPO_ID_LIST, state="readonly", width=20)
        tipo_id_cb.pack(side="left", padx=5)
        self.tooltip_register(tipo_id_cb, "Selecciona el tipo de documento del cliente.")
        ttk.Label(row1, text="ID del cliente:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=5)
        id_entry.bind("<FocusOut>", lambda e: self.on_id_change())
        id_entry.bind("<KeyRelease>", lambda e: self.on_id_change())
        self.tooltip_register(id_entry, "Escribe el número de documento del cliente.")

        # Fila 2: Flag y Accionado
        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="Flag:").pack(side="left")
        flag_cb = ttk.Combobox(row2, textvariable=self.flag_var, values=FLAG_CLIENTE_LIST, state="readonly", width=20)
        flag_cb.pack(side="left", padx=5)
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
            "Marca las tribus o equipos accionados por la alerta. Puedes escoger varias opciones."
        )

        # Fila 3: Teléfonos, correos, direcciones
        row3 = ttk.Frame(self.frame)
        row3.pack(fill="x", pady=1)
        ttk.Label(row3, text="Teléfonos (separados por ;):").pack(side="left")
        tel_entry = ttk.Entry(row3, textvariable=self.telefonos_var, width=30)
        tel_entry.pack(side="left", padx=5)
        tel_entry.bind("<FocusOut>", lambda e: log_event("navegacion", f"Cliente {self.idx+1}: modificó teléfonos", self.logs))
        self.tooltip_register(tel_entry, "Ingresa números separados por ; sin guiones.")
        ttk.Label(row3, text="Correos (separados por ;):").pack(side="left")
        cor_entry = ttk.Entry(row3, textvariable=self.correos_var, width=30)
        cor_entry.pack(side="left", padx=5)
        cor_entry.bind("<FocusOut>", lambda e: log_event("navegacion", f"Cliente {self.idx+1}: modificó correos", self.logs))
        self.tooltip_register(cor_entry, "Coloca correos electrónicos separados por ;.")
        ttk.Label(row3, text="Direcciones (separados por ;):").pack(side="left")
        dir_entry = ttk.Entry(row3, textvariable=self.direcciones_var, width=30)
        dir_entry.pack(side="left", padx=5)
        dir_entry.bind("<FocusOut>", lambda e: log_event("navegacion", f"Cliente {self.idx+1}: modificó direcciones", self.logs))
        self.tooltip_register(dir_entry, "Puedes capturar varias direcciones separadas por ;.")

        # Botón eliminar
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=2)
        remove_btn = ttk.Button(btn_frame, text="Eliminar cliente", command=self.remove)
        remove_btn.pack(side="right")
        self.tooltip_register(remove_btn, "Quita por completo al cliente de la lista.")

        # Validaciones por campo
        self.validators.append(
            FieldValidator(
                id_entry,
                lambda: validate_client_identifier(self.tipo_id_var.get(), self.id_var.get()),
                self.logs,
                f"Cliente {self.idx+1} - ID",
                variables=[self.id_var, self.tipo_id_var],
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
                dir_entry,
                lambda: validate_address_list(self.direcciones_var.get(), "las direcciones del cliente"),
                self.logs,
                f"Cliente {self.idx+1} - Direcciones",
                variables=[self.direcciones_var],
            )
        )
        self.validators.append(
            FieldValidator(
                self.accionado_listbox,
                lambda: validate_multi_selection(
                    self.accionado_var.get(),
                    "Accionado",
                    allow_empty=True,
                    valid_options=ACCIONADO_OPTIONS,
                ),
                self.logs,
                f"Cliente {self.idx+1} - Accionado",
                variables=[self.accionado_var],
            )
        )

    def on_id_change(self):
        """Cuando cambia el ID, actualiza las listas dependientes."""
        # Registrar evento
        log_event("navegacion", f"Cliente {self.idx+1}: cambió ID a {self.id_var.get()}", self.logs)
        # Actualizar los desplegables de clientes en productos
        self.update_client_options()
        # Autopoblar datos si el ID existe en client_lookup
        cid = self.id_var.get().strip()
        if cid and cid in self.client_lookup:
            data = self.client_lookup[cid]
            def set_if_present(var, key):
                value = data.get(key, "").strip()
                if value:
                    var.set(value)

            set_if_present(self.tipo_id_var, 'tipo_id')
            set_if_present(self.flag_var, 'flag')
            set_if_present(self.telefonos_var, 'telefonos')
            set_if_present(self.correos_var, 'correos')
            set_if_present(self.direcciones_var, 'direcciones')
            accionado = data.get('accionado', '').strip()
            if accionado:
                self.set_accionado_from_text(accionado)
            log_event("navegacion", f"Autopoblado datos del cliente {cid}", self.logs)

    def get_data(self):
        """Devuelve los datos del cliente como un diccionario."""
        return {
            "id_cliente": self.id_var.get().strip(),
            "id_caso": "",  # el id_caso se asignará al guardar
            "tipo_id": self.tipo_id_var.get(),
            "flag": self.flag_var.get(),
            "telefonos": self.telefonos_var.get().strip(),
            "correos": self.correos_var.get().strip(),
            "direcciones": self.direcciones_var.get().strip(),
            "accionado": self.accionado_var.get().strip(),
        }

    def update_accionado_var(self, _event=None):
        """Actualiza la cadena de accionados cuando cambia la selección."""
        selections = [
            ACCIONADO_OPTIONS[i]
            for i in self.accionado_listbox.curselection()
        ]
        self.accionado_var.set("; ".join(selections))

    def set_accionado_from_text(self, value):
        """Sincroniza el listbox con un texto existente de accionados."""
        self.accionado_var.set(value.strip())
        self.accionado_listbox.selection_clear(0, tk.END)
        if not value:
            return
        targets = [item.strip() for item in value.split(';') if item.strip()]
        for idx, name in enumerate(ACCIONADO_OPTIONS):
            if name in targets:
                self.accionado_listbox.selection_set(idx)

    def remove(self):
        """Elimina el cliente de la interfaz y de las estructuras internas."""
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el cliente {self.idx+1}?"):
            log_event("navegacion", f"Se eliminó cliente {self.idx+1}", self.logs)
            self.frame.destroy()
            self.remove_callback(self)


class TeamMemberFrame:
    """Representa un colaborador y su interfaz en la sección de colaboradores."""

    def __init__(self, parent, idx, remove_callback, update_team_options, team_lookup, logs, tooltip_register):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.update_team_options = update_team_options
        self.team_lookup = team_lookup
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self._last_missing_lookup_id = None

        # Variables
        self.id_var = tk.StringVar()
        self.flag_var = tk.StringVar(value=FLAG_COLABORADOR_LIST[0])
        self.division_var = tk.StringVar()
        self.area_var = tk.StringVar()
        self.servicio_var = tk.StringVar()
        self.puesto_var = tk.StringVar()
        self.nombre_agencia_var = tk.StringVar()
        self.codigo_agencia_var = tk.StringVar()
        self.tipo_falta_var = tk.StringVar(value=TIPO_FALTA_LIST[0])
        self.tipo_sancion_var = tk.StringVar(value=TIPO_SANCION_LIST[0])

        # Contenedor
        self.frame = ttk.LabelFrame(parent, text=f"Colaborador {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)

        # Fila 1: ID y Flag
        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="ID del colaborador:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=5)
        id_entry.bind("<FocusOut>", lambda e: self.on_id_change())
        id_entry.bind("<KeyRelease>", lambda e: self.on_id_change())
        self.tooltip_register(id_entry, "Coloca el código único del colaborador investigado.")
        ttk.Label(row1, text="Flag:").pack(side="left")
        flag_cb = ttk.Combobox(row1, textvariable=self.flag_var, values=FLAG_COLABORADOR_LIST, state="readonly", width=20)
        flag_cb.pack(side="left", padx=5)
        self.tooltip_register(flag_cb, "Define el rol del colaborador en el caso.")
        flag_cb.bind("<FocusOut>", lambda e: log_event("navegacion", f"Colaborador {self.idx+1}: modificó flag", self.logs))

        # Fila 2: División, Área, Servicio, Puesto
        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="División:").pack(side="left")
        div_entry = ttk.Entry(row2, textvariable=self.division_var, width=20)
        div_entry.pack(side="left", padx=5)
        self.tooltip_register(div_entry, "Ingresa la división o gerencia del colaborador.")
        ttk.Label(row2, text="Área:").pack(side="left")
        area_entry = ttk.Entry(row2, textvariable=self.area_var, width=20)
        area_entry.pack(side="left", padx=5)
        self.tooltip_register(area_entry, "Detalla el área específica.")
        ttk.Label(row2, text="Servicio:").pack(side="left")
        serv_entry = ttk.Entry(row2, textvariable=self.servicio_var, width=20)
        serv_entry.pack(side="left", padx=5)
        self.tooltip_register(serv_entry, "Describe el servicio o célula.")
        ttk.Label(row2, text="Puesto:").pack(side="left")
        puesto_entry = ttk.Entry(row2, textvariable=self.puesto_var, width=20)
        puesto_entry.pack(side="left", padx=5)
        self.tooltip_register(puesto_entry, "Define el cargo actual del colaborador.")

        # Fila 3: Agencia nombre y código
        row3 = ttk.Frame(self.frame)
        row3.pack(fill="x", pady=1)
        ttk.Label(row3, text="Nombre agencia:").pack(side="left")
        nombre_ag_entry = ttk.Entry(row3, textvariable=self.nombre_agencia_var, width=25)
        nombre_ag_entry.pack(side="left", padx=5)
        self.tooltip_register(nombre_ag_entry, "Especifica la agencia u oficina de trabajo.")
        ttk.Label(row3, text="Código agencia:").pack(side="left")
        cod_ag_entry = ttk.Entry(row3, textvariable=self.codigo_agencia_var, width=10)
        cod_ag_entry.pack(side="left", padx=5)
        self.tooltip_register(cod_ag_entry, "Código interno de la agencia (solo números).")

        # Fila 4: Tipo de falta y sanción
        row4 = ttk.Frame(self.frame)
        row4.pack(fill="x", pady=1)
        ttk.Label(row4, text="Tipo de falta:").pack(side="left")
        falta_cb = ttk.Combobox(row4, textvariable=self.tipo_falta_var, values=TIPO_FALTA_LIST, state="readonly", width=20)
        falta_cb.pack(side="left", padx=5)
        self.tooltip_register(falta_cb, "Selecciona la falta disciplinaria tipificada.")
        ttk.Label(row4, text="Tipo de sanción:").pack(side="left")
        sanc_cb = ttk.Combobox(row4, textvariable=self.tipo_sancion_var, values=TIPO_SANCION_LIST, state="readonly", width=20)
        sanc_cb.pack(side="left", padx=5)
        self.tooltip_register(sanc_cb, "Describe la sanción propuesta o aplicada.")

        # Botón eliminar
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=2)
        remove_btn = ttk.Button(btn_frame, text="Eliminar colaborador", command=self.remove)
        remove_btn.pack(side="right")
        self.tooltip_register(remove_btn, "Quita al colaborador y sus datos del caso.")

        # Validadores clave
        self.validators.append(
            FieldValidator(
                id_entry,
                lambda: validate_team_member_id(self.id_var.get()),
                self.logs,
                f"Colaborador {self.idx+1} - ID",
                variables=[self.id_var],
            )
        )
        self.validators.append(
            FieldValidator(
                cod_ag_entry,
                lambda: validate_agency_code(self.codigo_agencia_var.get()),
                self.logs,
                f"Colaborador {self.idx+1} - Código agencia",
                variables=[self.codigo_agencia_var],
            )
        )

    def on_id_change(self):
        """Se ejecuta al salir del campo ID: autopuebla y actualiza listas."""
        cid = self.id_var.get().strip()
        if cid:
            # Autopoblado si existe en lookup
            data = self.team_lookup.get(cid)
            if data:
                def set_if_present(var, key):
                    value = data.get(key, "").strip()
                    if value:
                        var.set(value)

                set_if_present(self.division_var, "division")
                set_if_present(self.area_var, "area")
                set_if_present(self.servicio_var, "servicio")
                set_if_present(self.puesto_var, "puesto")
                set_if_present(self.nombre_agencia_var, "nombre_agencia")
                set_if_present(self.codigo_agencia_var, "codigo_agencia")
                self._last_missing_lookup_id = None
                log_event("navegacion", f"Autopoblado colaborador {self.idx+1} desde team_details.csv", self.logs)
            else:
                log_event("validacion", f"ID de colaborador {cid} no encontrado en team_details.csv", self.logs)
                if self._last_missing_lookup_id != cid:
                    messagebox.showwarning(
                        "Colaborador no encontrado",
                        (
                            f"El ID {cid} no existe en el catálogo team_details.csv. "
                            "Verifica el código o actualiza el archivo maestro."
                        ),
                    )
                    self._last_missing_lookup_id = cid
        # Actualizar desplegables de colaboradores
        self.update_team_options()

    def get_data(self):
        return {
            "id_colaborador": self.id_var.get().strip(),
            "id_caso": "",  # se completará al guardar
            "flag": self.flag_var.get(),
            "division": self.division_var.get().strip(),
            "area": self.area_var.get().strip(),
            "servicio": self.servicio_var.get().strip(),
            "puesto": self.puesto_var.get().strip(),
            "nombre_agencia": self.nombre_agencia_var.get().strip(),
            "codigo_agencia": self.codigo_agencia_var.get().strip(),
            "tipo_falta": self.tipo_falta_var.get(),
            "tipo_sancion": self.tipo_sancion_var.get(),
        }

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el colaborador {self.idx+1}?"):
            log_event("navegacion", f"Se eliminó colaborador {self.idx+1}", self.logs)
            self.frame.destroy()
            self.remove_callback(self)


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

        # Variables
        self.team_var = tk.StringVar()
        self.monto_var = tk.StringVar()

        # Contenedor
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", pady=1)

        # Desplegable de colaboradores y monto
        ttk.Label(self.frame, text="Colaborador:").pack(side="left")
        self.team_cb = ttk.Combobox(self.frame, textvariable=self.team_var, values=self.team_getter(), state="readonly", width=20)
        self.team_cb.pack(side="left", padx=5)
        self.tooltip_register(self.team_cb, "Elige al colaborador que participa en este producto.")
        ttk.Label(self.frame, text="Monto asignado:").pack(side="left")
        monto_entry = ttk.Entry(self.frame, textvariable=self.monto_var, width=15)
        monto_entry.pack(side="left", padx=5)
        monto_entry.bind("<FocusOut>", lambda e: log_event("navegacion", f"Producto {self.product_frame.idx+1}, asignación {self.idx+1}: modificó monto", self.logs))
        self.tooltip_register(monto_entry, "Monto en soles asignado a este colaborador.")

        # Botón eliminar
        remove_btn = ttk.Button(self.frame, text="Eliminar", command=self.remove)
        remove_btn.pack(side="left", padx=5)
        self.tooltip_register(remove_btn, "Elimina esta asignación específica.")

        self.validators.append(
            FieldValidator(
                monto_entry,
                lambda: validate_amount_text(self.monto_var.get(), "el monto asignado", allow_blank=True),
                self.logs,
                f"Producto {self.product_frame.idx+1} - Asignación {self.idx+1}",
                variables=[self.monto_var],
            )
        )

    def get_data(self):
        return {
            "id_colaborador": self.team_var.get().strip(),
            "monto_asignado": self.monto_var.get().strip(),
        }

    def update_team_options(self):
        self.team_cb['values'] = self.team_getter()

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar esta asignación?"):
            log_event("navegacion", f"Se eliminó asignación de colaborador en producto {self.product_frame.idx+1}", self.logs)
            self.frame.destroy()
            self.remove_callback(self)


class ProductFrame:
    """Representa un producto y su interfaz en la sección de productos."""

    def __init__(self, parent, idx, remove_callback, get_client_options, get_team_options, logs, product_lookup, tooltip_register):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.get_client_options = get_client_options
        self.get_team_options = get_team_options
        self.logs = logs
        self.product_lookup = product_lookup or {}
        self.tooltip_register = tooltip_register
        self.validators = []
        self.involvements = []

        # Variables
        self.id_var = tk.StringVar()
        self.client_var = tk.StringVar()
        self.cat1_var = tk.StringVar(value=list(TAXONOMIA.keys())[0])
        # set category2 to first subcategory
        first_subcats = list(TAXONOMIA[self.cat1_var.get()].keys())
        self.cat2_var = tk.StringVar(value=first_subcats[0])
        # set modality to first modality of first subcat
        first_modalities = TAXONOMIA[self.cat1_var.get()][self.cat2_var.get()]
        self.mod_var = tk.StringVar(value=first_modalities[0])
        self.canal_var = tk.StringVar(value=CANAL_LIST[0])
        self.proceso_var = tk.StringVar(value=PROCESO_LIST[0])
        self.fecha_oc_var = tk.StringVar()
        self.fecha_desc_var = tk.StringVar()
        self.monto_inv_var = tk.StringVar()
        self.moneda_var = tk.StringVar(value=TIPO_MONEDA_LIST[0])
        self.monto_perdida_var = tk.StringVar()
        self.monto_falla_var = tk.StringVar()
        self.monto_cont_var = tk.StringVar()
        self.monto_rec_var = tk.StringVar()
        self.monto_pago_var = tk.StringVar()
        self.tipo_prod_var = tk.StringVar(value=TIPO_PRODUCTO_LIST[0])
        # Reclamo y analítica
        self.id_reclamo_var = tk.StringVar()
        self.nombre_analitica_var = tk.StringVar()
        self.codigo_analitica_var = tk.StringVar()

        # Contenedor
        self.frame = ttk.LabelFrame(parent, text=f"Producto {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)

        # Fila 1: ID, Cliente
        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="ID del producto:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=5)
        id_entry.bind("<FocusOut>", lambda e: self.on_id_change())
        id_entry.bind("<KeyRelease>", lambda e: self.on_id_change())
        self.tooltip_register(id_entry, "Código único del producto investigado.")
        ttk.Label(row1, text="Cliente:").pack(side="left")
        self.client_cb = ttk.Combobox(row1, textvariable=self.client_var, values=self.get_client_options(), state="readonly", width=20)
        self.client_cb.pack(side="left", padx=5)
        self.client_cb.bind("<FocusOut>", lambda e: log_event("navegacion", f"Producto {self.idx+1}: seleccionó cliente", self.logs))
        self.tooltip_register(self.client_cb, "Selecciona al cliente dueño del producto.")

        # Fila 2: Categoría 1, 2, Modalidad
        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="Categoría 1:").pack(side="left")
        cat1_cb = ttk.Combobox(row2, textvariable=self.cat1_var, values=list(TAXONOMIA.keys()), state="readonly", width=20)
        cat1_cb.pack(side="left", padx=5)
        cat1_cb.bind("<<ComboboxSelected>>", lambda e: self.on_cat1_change())
        self.tooltip_register(cat1_cb, "Define la categoría principal del riesgo de producto.")
        ttk.Label(row2, text="Categoría 2:").pack(side="left")
        self.cat2_cb = ttk.Combobox(row2, textvariable=self.cat2_var, values=first_subcats, state="readonly", width=20)
        self.cat2_cb.pack(side="left", padx=5)
        self.cat2_cb.bind("<<ComboboxSelected>>", lambda e: self.on_cat2_change())
        self.tooltip_register(self.cat2_cb, "Selecciona la subcategoría específica.")
        ttk.Label(row2, text="Modalidad:").pack(side="left")
        self.mod_cb = ttk.Combobox(row2, textvariable=self.mod_var, values=first_modalities, state="readonly", width=25)
        self.mod_cb.pack(side="left", padx=5)
        self.tooltip_register(self.mod_cb, "Indica la modalidad concreta del fraude.")

        # Fila 3: Canal, Proceso, Tipo de producto
        row3 = ttk.Frame(self.frame)
        row3.pack(fill="x", pady=1)
        ttk.Label(row3, text="Canal:").pack(side="left")
        canal_cb = ttk.Combobox(row3, textvariable=self.canal_var, values=CANAL_LIST, state="readonly", width=20)
        canal_cb.pack(side="left", padx=5)
        self.tooltip_register(canal_cb, "Canal por donde ocurrió el evento.")
        ttk.Label(row3, text="Proceso:").pack(side="left")
        proc_cb = ttk.Combobox(row3, textvariable=self.proceso_var, values=PROCESO_LIST, state="readonly", width=25)
        proc_cb.pack(side="left", padx=5)
        self.tooltip_register(proc_cb, "Proceso impactado por el incidente.")
        ttk.Label(row3, text="Tipo de producto:").pack(side="left")
        tipo_prod_cb = ttk.Combobox(row3, textvariable=self.tipo_prod_var, values=TIPO_PRODUCTO_LIST, state="readonly", width=25)
        tipo_prod_cb.pack(side="left", padx=5)
        self.tooltip_register(tipo_prod_cb, "Clasificación comercial del producto.")

        # Fila 4: Fechas
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

        # Fila 5: Montos y moneda
        row5 = ttk.Frame(self.frame)
        row5.pack(fill="x", pady=1)
        ttk.Label(row5, text="Monto investigado:").pack(side="left")
        m_inv_entry = ttk.Entry(row5, textvariable=self.monto_inv_var, width=15)
        m_inv_entry.pack(side="left", padx=5)
        self.tooltip_register(m_inv_entry, "Monto total analizado.")
        ttk.Label(row5, text="Moneda:").pack(side="left")
        moneda_cb = ttk.Combobox(row5, textvariable=self.moneda_var, values=TIPO_MONEDA_LIST, state="readonly", width=10)
        moneda_cb.pack(side="left", padx=5)
        self.tooltip_register(moneda_cb, "Moneda en la que se expresan los montos.")
        ttk.Label(row5, text="Pérdida de fraude:").pack(side="left")
        m_perdida_entry = ttk.Entry(row5, textvariable=self.monto_perdida_var, width=10)
        m_perdida_entry.pack(side="left", padx=5)
        self.tooltip_register(m_perdida_entry, "Pérdida confirmada.")
        ttk.Label(row5, text="Falla de procesos:").pack(side="left")
        m_falla_entry = ttk.Entry(row5, textvariable=self.monto_falla_var, width=10)
        m_falla_entry.pack(side="left", padx=5)
        self.tooltip_register(m_falla_entry, "Valor asociado a errores de proceso.")
        ttk.Label(row5, text="Contingencia:").pack(side="left")
        m_cont_entry = ttk.Entry(row5, textvariable=self.monto_cont_var, width=10)
        m_cont_entry.pack(side="left", padx=5)
        self.tooltip_register(m_cont_entry, "Fondos provisionados por contingencia.")
        ttk.Label(row5, text="Recuperado:").pack(side="left")
        m_rec_entry = ttk.Entry(row5, textvariable=self.monto_rec_var, width=10)
        m_rec_entry.pack(side="left", padx=5)
        self.tooltip_register(m_rec_entry, "Monto recuperado.")
        ttk.Label(row5, text="Pago deuda:").pack(side="left")
        m_pago_entry = ttk.Entry(row5, textvariable=self.monto_pago_var, width=10)
        m_pago_entry.pack(side="left", padx=5)
        self.tooltip_register(m_pago_entry, "Pagos realizados a terceros por la deuda.")

        # Fila 6: Reclamo y analítica
        row6 = ttk.Frame(self.frame)
        row6.pack(fill="x", pady=1)
        ttk.Label(row6, text="ID reclamo (CXXXXXXXX):").pack(side="left")
        idrec_entry = ttk.Entry(row6, textvariable=self.id_reclamo_var, width=15)
        idrec_entry.pack(side="left", padx=5)
        self.tooltip_register(idrec_entry, "Número del reclamo asociado (C + 8 dígitos).")
        ttk.Label(row6, text="Analítica nombre:").pack(side="left")
        anal_nom_entry = ttk.Entry(row6, textvariable=self.nombre_analitica_var, width=20)
        anal_nom_entry.pack(side="left", padx=5)
        self.tooltip_register(anal_nom_entry, "Nombre descriptivo de la analítica.")
        ttk.Label(row6, text="Analítica código:").pack(side="left")
        anal_cod_entry = ttk.Entry(row6, textvariable=self.codigo_analitica_var, width=12)
        anal_cod_entry.pack(side="left", padx=5)
        self.tooltip_register(anal_cod_entry, "Código numérico de 10 dígitos para la analítica.")

        # Fila 7: Asignaciones de colaboradores (involucramiento)
        row7 = ttk.Frame(self.frame)
        row7.pack(fill="x", pady=1)
        ttk.Label(row7, text="Asignaciones a colaboradores:").pack(side="left")
        self.invol_frame = ttk.Frame(self.frame)
        self.invol_frame.pack(fill="x", pady=1)
        add_inv_btn = ttk.Button(row7, text="Agregar asignación", command=self.add_involvement)
        add_inv_btn.pack(side="right")
        self.tooltip_register(add_inv_btn, "Crea otra relación producto-colaborador.")

        # Inicialmente sin asignaciones
        self.add_involvement()

        # Botón eliminar producto
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=2)
        remove_btn = ttk.Button(btn_frame, text="Eliminar producto", command=self.remove)
        remove_btn.pack(side="right")
        self.tooltip_register(remove_btn, "Quita el producto y sus datos del caso.")

        # Validaciones en tiempo real
        self.validators.append(
            FieldValidator(
                id_entry,
                lambda: validate_required_text(self.id_var.get(), "el ID del producto"),
                self.logs,
                f"Producto {self.idx+1} - ID",
                variables=[self.id_var],
            )
        )
        self.validators.append(
            FieldValidator(
                self.client_cb,
                lambda: validate_required_text(self.client_var.get(), "el cliente del producto"),
                self.logs,
                f"Producto {self.idx+1} - Cliente",
                variables=[self.client_var],
            )
        )
        self.validators.append(
            FieldValidator(
                cat1_cb,
                lambda: validate_required_text(self.cat1_var.get(), "la categoría 1"),
                self.logs,
                f"Producto {self.idx+1} - Categoría 1",
                variables=[self.cat1_var],
            )
        )
        self.validators.append(
            FieldValidator(
                self.cat2_cb,
                lambda: validate_required_text(self.cat2_var.get(), "la categoría 2"),
                self.logs,
                f"Producto {self.idx+1} - Categoría 2",
                variables=[self.cat2_var],
            )
        )
        self.validators.append(
            FieldValidator(
                self.mod_cb,
                lambda: validate_required_text(self.mod_var.get(), "la modalidad"),
                self.logs,
                f"Producto {self.idx+1} - Modalidad",
                variables=[self.mod_var],
            )
        )
        self.validators.append(
            FieldValidator(
                focc_entry,
                lambda: validate_date_text(self.fecha_oc_var.get(), "la fecha de ocurrencia", allow_blank=False),
                self.logs,
                f"Producto {self.idx+1} - Fecha de ocurrencia",
                variables=[self.fecha_oc_var],
            )
        )
        self.validators.append(
            FieldValidator(
                fdesc_entry,
                self._validate_fecha_descubrimiento,
                self.logs,
                f"Producto {self.idx+1} - Fechas",
                variables=[self.fecha_desc_var, self.fecha_oc_var],
            )
        )
        amount_vars = [
            self.monto_inv_var,
            self.monto_perdida_var,
            self.monto_falla_var,
            self.monto_cont_var,
            self.monto_rec_var,
            self.monto_pago_var,
        ]
        self.validators.append(
            FieldValidator(
                m_inv_entry,
                lambda: validate_amount_text(self.monto_inv_var.get(), "el monto investigado", allow_blank=False),
                self.logs,
                f"Producto {self.idx+1} - Monto investigado",
                variables=[self.monto_inv_var],
            )
        )
        for entry, var, label in [
            (m_perdida_entry, self.monto_perdida_var, "la pérdida de fraude"),
            (m_falla_entry, self.monto_falla_var, "la falla de procesos"),
            (m_cont_entry, self.monto_cont_var, "la contingencia"),
            (m_rec_entry, self.monto_rec_var, "el recupero"),
            (m_pago_entry, self.monto_pago_var, "el pago de deuda"),
        ]:
            self.validators.append(
                FieldValidator(
                    entry,
                    lambda var=var, label=label: validate_amount_text(var.get(), label, allow_blank=True),
                    self.logs,
                    f"Producto {self.idx+1} - {label}",
                    variables=[var],
                )
            )
        self.validators.append(
            FieldValidator(
                m_perdida_entry,
                self._validate_montos_consistentes,
                self.logs,
                f"Producto {self.idx+1} - Consistencia de montos",
                variables=amount_vars,
            )
        )
        self.validators.append(
            FieldValidator(
                idrec_entry,
                lambda: validate_reclamo_id(self.id_reclamo_var.get()),
                self.logs,
                f"Producto {self.idx+1} - ID reclamo",
                variables=[self.id_reclamo_var],
            )
        )
        self.validators.append(
            FieldValidator(
                anal_cod_entry,
                lambda: validate_codigo_analitica(self.codigo_analitica_var.get()),
                self.logs,
                f"Producto {self.idx+1} - Código analítica",
                variables=[self.codigo_analitica_var],
            )
        )

    def on_cat1_change(self):
        """Actualiza las opciones de categoría 2 y modalidad cuando cambia categoría 1."""
        cat1 = self.cat1_var.get()
        subcats = list(TAXONOMIA.get(cat1, {}).keys())
        if not subcats:
            subcats = [""]
        self.cat2_cb['values'] = subcats
        self.cat2_var.set('')
        self.cat2_cb.set('')
        self.mod_cb['values'] = []
        self.mod_var.set('')
        log_event("navegacion", f"Producto {self.idx+1}: cambió categoría 1", self.logs)

    def on_cat2_change(self):
        """Actualiza las opciones de modalidad cuando cambia categoría 2."""
        cat1 = self.cat1_var.get()
        cat2 = self.cat2_var.get()
        modalities = TAXONOMIA.get(cat1, {}).get(cat2, [])
        if not modalities:
            modalities = [""]
        self.mod_cb['values'] = modalities
        self.mod_var.set('')
        self.mod_cb.set('')
        log_event("navegacion", f"Producto {self.idx+1}: cambió categoría 2", self.logs)

    def add_involvement(self):
        """Añade una fila de asignación de colaborador a este producto."""
        idx = len(self.involvements)
        row = InvolvementRow(self.invol_frame, self, idx, self.get_team_options, self.remove_involvement, self.logs, self.tooltip_register)
        self.involvements.append(row)

    def remove_involvement(self, row):
        self.involvements.remove(row)

    def update_client_options(self):
        """Actualiza la lista de clientes en el desplegable."""
        current = self.client_var.get()
        self.client_cb['values'] = self.get_client_options()
        if current in self.client_cb['values']:
            self.client_var.set(current)
        elif self.client_cb['values']:
            self.client_var.set(self.client_cb['values'][0])

    def update_team_options(self):
        """Actualiza las listas de colaboradores en las asignaciones."""
        for inv in self.involvements:
            inv.update_team_options()

    def on_id_change(self):
        """Autocompleta el producto cuando se escribe un ID reconocido."""
        pid = self.id_var.get().strip()
        log_event("navegacion", f"Producto {self.idx+1}: modificó ID a {pid}", self.logs)
        if not pid:
            return
        data = self.product_lookup.get(pid)
        if not data:
            return

        def set_if_present(var, key):
            value = data.get(key)
            if value not in (None, ""):
                var.set(str(value).strip())

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
        set_if_present(self.id_reclamo_var, 'id_reclamo')
        set_if_present(self.nombre_analitica_var, 'nombre_analitica')
        set_if_present(self.codigo_analitica_var, 'codigo_analitica')
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
        log_event("navegacion", f"Producto {self.idx+1}: autopoblado desde catálogo", self.logs)

    def _validate_fecha_descubrimiento(self):
        """Valida la fecha de descubrimiento y su relación con la de ocurrencia."""
        msg = validate_date_text(self.fecha_desc_var.get(), "la fecha de descubrimiento", allow_blank=False)
        if msg:
            return msg
        try:
            occ = datetime.strptime(self.fecha_oc_var.get(), "%Y-%m-%d")
            desc = datetime.strptime(self.fecha_desc_var.get(), "%Y-%m-%d")
        except ValueError:
            return None
        if occ > desc:
            return "La fecha de ocurrencia no puede ser posterior a la de descubrimiento."
        if desc > datetime.now():
            return "La fecha de descubrimiento no puede ser futura."
        return None

    def _validate_montos_consistentes(self):
        """Valida que la distribución de montos sea coherente con la investigación."""
        m_inv = parse_decimal_amount(self.monto_inv_var.get())
        m_perd = parse_decimal_amount(self.monto_perdida_var.get())
        m_falla = parse_decimal_amount(self.monto_falla_var.get())
        m_cont = parse_decimal_amount(self.monto_cont_var.get())
        m_rec = parse_decimal_amount(self.monto_rec_var.get())
        m_pago = parse_decimal_amount(self.monto_pago_var.get())
        if None in (m_inv, m_perd, m_falla, m_cont, m_rec, m_pago):
            return None
        if abs((m_perd + m_falla + m_cont + m_rec) - m_inv) > Decimal("0.01"):
            return "Los montos de pérdida, falla, contingencia y recupero deben sumar el monto investigado."
        if m_pago > m_inv:
            return "El pago de deuda no puede ser mayor al monto investigado."
        tipo_prod = self.tipo_prod_var.get().lower()
        if any(word in tipo_prod for word in ['crédito', 'tarjeta']) and abs(m_cont - m_inv) > Decimal("0.01"):
            return "En productos de crédito o tarjeta, el monto de contingencia debe igualar al investigado."
        return None

    def get_data(self):
        """Devuelve los datos del producto como un diccionario y lista de asignaciones."""
        return {
            "producto": {
                "id_producto": self.id_var.get().strip(),
                "id_caso": "",  # se completará al guardar
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
            },
            "reclamo": {
                "id_reclamo": self.id_reclamo_var.get().strip(),
                "nombre_analitica": self.nombre_analitica_var.get().strip(),
                "codigo_analitica": self.codigo_analitica_var.get().strip(),
            },
            "asignaciones": [inv.get_data() for inv in self.involvements],
        }

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el producto {self.idx+1}?"):
            log_event("navegacion", f"Se eliminó producto {self.idx+1}", self.logs)
            self.frame.destroy()
            self.remove_callback(self)


class RiskFrame:
    """Representa un riesgo identificado en la sección de riesgos."""

    def __init__(self, parent, idx, remove_callback, logs, tooltip_register):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        # Variables
        self.id_var = tk.StringVar(value=f"RSK-{idx+1:06d}")
        self.lider_var = tk.StringVar()
        self.descripcion_var = tk.StringVar()
        self.criticidad_var = tk.StringVar(value=CRITICIDAD_LIST[0])
        self.exposicion_var = tk.StringVar()
        self.planes_var = tk.StringVar()

        # Contenedor
        self.frame = ttk.LabelFrame(parent, text=f"Riesgo {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)

        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="ID riesgo:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=15)
        id_entry.pack(side="left", padx=5)
        self.tooltip_register(id_entry, "Usa el formato RSK-000000.")
        ttk.Label(row1, text="Líder:").pack(side="left")
        lider_entry = ttk.Entry(row1, textvariable=self.lider_var, width=20)
        lider_entry.pack(side="left", padx=5)
        self.tooltip_register(lider_entry, "Responsable del seguimiento del riesgo.")
        ttk.Label(row1, text="Criticidad:").pack(side="left")
        crit_cb = ttk.Combobox(row1, textvariable=self.criticidad_var, values=CRITICIDAD_LIST, state="readonly", width=12)
        crit_cb.pack(side="left", padx=5)
        self.tooltip_register(crit_cb, "Nivel de severidad del riesgo.")

        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="Descripción del riesgo:").pack(side="left")
        desc_entry = ttk.Entry(row2, textvariable=self.descripcion_var, width=60)
        desc_entry.pack(side="left", padx=5)
        self.tooltip_register(desc_entry, "Describe el riesgo de forma clara.")

        row3 = ttk.Frame(self.frame)
        row3.pack(fill="x", pady=1)
        ttk.Label(row3, text="Exposición residual (US$):").pack(side="left")
        expos_entry = ttk.Entry(row3, textvariable=self.exposicion_var, width=15)
        expos_entry.pack(side="left", padx=5)
        self.tooltip_register(expos_entry, "Monto estimado en dólares.")
        ttk.Label(row3, text="Planes de acción (IDs separados por ;):").pack(side="left")
        planes_entry = ttk.Entry(row3, textvariable=self.planes_var, width=40)
        planes_entry.pack(side="left", padx=5)
        self.tooltip_register(planes_entry, "Lista de planes registrados en OTRS o Aranda.")

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=2)
        remove_btn = ttk.Button(btn_frame, text="Eliminar riesgo", command=self.remove)
        remove_btn.pack(side="right")
        self.tooltip_register(remove_btn, "Quita este riesgo del caso.")

        self.validators.append(
            FieldValidator(
                id_entry,
                self._validate_risk_id,
                self.logs,
                f"Riesgo {self.idx+1} - ID",
                variables=[self.id_var],
            )
        )
        self.validators.append(
            FieldValidator(
                expos_entry,
                lambda: validate_amount_text(self.exposicion_var.get(), "la exposición residual", allow_blank=True),
                self.logs,
                f"Riesgo {self.idx+1} - Exposición",
                variables=[self.exposicion_var],
            )
        )

    def get_data(self):
        return {
            "id_riesgo": self.id_var.get().strip(),
            "lider": self.lider_var.get().strip(),
            "descripcion": self.descripcion_var.get().strip(),
            "criticidad": self.criticidad_var.get(),
            "exposicion_residual": self.exposicion_var.get().strip(),
            "planes_accion": self.planes_var.get().strip(),
        }

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar el riesgo {self.idx+1}?"):
            log_event("navegacion", f"Se eliminó riesgo {self.idx+1}", self.logs)
            self.frame.destroy()
            self.remove_callback(self)

    def _validate_risk_id(self):
        """Valida el formato del identificador de riesgo."""
        value = self.id_var.get().strip()
        if not re.match(r"^RSK-\d{6,10}$", value):
            return "El ID de riesgo debe seguir el formato RSK-XXXXXX (6 a 10 dígitos)."
        return None


class NormFrame:
    """Representa una norma transgredida en la sección de normas."""

    def __init__(self, parent, idx, remove_callback, logs, tooltip_register):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []

        self.id_var = tk.StringVar()
        self.descripcion_var = tk.StringVar()
        self.fecha_var = tk.StringVar()

        self.frame = ttk.LabelFrame(parent, text=f"Norma {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)
        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="ID de norma:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=5)
        self.tooltip_register(id_entry, "Formato sugerido: 0000.000.00.00")
        ttk.Label(row1, text="Fecha de vigencia (YYYY-MM-DD):").pack(side="left")
        fecha_entry = ttk.Entry(row1, textvariable=self.fecha_var, width=15)
        fecha_entry.pack(side="left", padx=5)
        self.tooltip_register(fecha_entry, "Fecha de publicación o vigencia de la norma.")

        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="Descripción de la norma:").pack(side="left")
        desc_entry = ttk.Entry(row2, textvariable=self.descripcion_var, width=70)
        desc_entry.pack(side="left", padx=5)
        self.tooltip_register(desc_entry, "Detalla el artículo o sección vulnerada.")

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=2)
        remove_btn = ttk.Button(btn_frame, text="Eliminar norma", command=self.remove)
        remove_btn.pack(side="right")
        self.tooltip_register(remove_btn, "Quita esta norma del caso.")

        self.validators.append(
            FieldValidator(
                id_entry,
                lambda: validate_norm_id(self.id_var.get()),
                self.logs,
                f"Norma {self.idx+1} - ID",
                variables=[self.id_var],
            )
        )
        self.validators.append(
            FieldValidator(
                fecha_entry,
                lambda: validate_date_text(self.fecha_var.get(), "la fecha de vigencia"),
                self.logs,
                f"Norma {self.idx+1} - Fecha",
                variables=[self.fecha_var],
            )
        )
        self.validators.append(
            FieldValidator(
                desc_entry,
                lambda: validate_required_text(self.descripcion_var.get(), "la descripción de la norma"),
                self.logs,
                f"Norma {self.idx+1} - Descripción",
                variables=[self.descripcion_var],
            )
        )

    def get_data(self):
        norm_id = self.id_var.get().strip()
        if not norm_id:
            norm_id = f"{random.randint(1000, 9999)}.{random.randint(100, 999):03d}.{random.randint(10, 99):02d}.{random.randint(10, 99):02d}"
            self.id_var.set(norm_id)
            log_event("navegacion", f"Norma {self.idx+1} sin ID: se asignó correlativo {norm_id}", self.logs)
        return {
            "id_norma": norm_id,
            "descripcion": self.descripcion_var.get().strip(),
            "fecha_vigencia": self.fecha_var.get().strip(),
        }

    def remove(self):
        if messagebox.askyesno("Confirmar", f"¿Desea eliminar la norma {self.idx+1}?"):
            log_event("navegacion", f"Se eliminó norma {self.idx+1}", self.logs)
            self.frame.destroy()
            self.remove_callback(self)


# ---------------------------------------------------------------------------
# Clase principal de la aplicación

class FraudCaseApp:
    """Clase que encapsula la aplicación de gestión de casos de fraude."""

    def __init__(self, root):
        self.root = root
        self.root.title("Gestión de Casos de Fraude (App de escritorio)")
        # Lista para logs de navegación y validación
        self.logs = []
        self._hover_tooltips = []
        self.validators = []

        def register_tooltip(widget, text):
            if widget is None or not text:
                return None
            tip = HoverTooltip(widget, text)
            self._hover_tooltips.append(tip)
            return tip

        self.register_tooltip = register_tooltip
        # Cargar catálogos para autopoblado
        self.team_lookup = load_team_details()
        # Cargar client details para autopoblar clientes. Si no existe el
        # fichero ``client_details.csv`` se obtiene un diccionario vacío. Este
        # diccionario se usa en ClientFrame.on_id_change() para rellenar
        # automáticamente campos del cliente cuando se reconoce su ID.
        self.client_lookup = load_client_details()
        self.product_lookup = load_product_details()
        # Datos en memoria: listas de frames
        self.client_frames = []
        self.team_frames = []
        self.product_frames = []
        self.risk_frames = []
        self.norm_frames = []

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

        # Variables de análisis
        self.antecedentes_var = tk.StringVar()
        self.modus_var = tk.StringVar()
        self.hallazgos_var = tk.StringVar()
        self.descargos_var = tk.StringVar()
        self.conclusiones_var = tk.StringVar()
        self.recomendaciones_var = tk.StringVar()

        # Construir interfaz
        self.build_ui()
        # Registrar la función de guardado temporal en el callback global. De
        # este modo, ``log_event`` invocará ``self.save_temp_version`` cada
        # vez que se registre un evento de navegación.
        global SAVE_TEMP_CALLBACK
        SAVE_TEMP_CALLBACK = self.save_temp_version
        # Cargar autosave si existe
        self.load_autosave()

    # ---------------------------------------------------------------------
    # Construcción de la interfaz

    def build_ui(self):
        """Construye la interfaz del usuario en diferentes pestañas."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

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

        case_section = ttk.LabelFrame(parent, text="1. Datos generales del caso")
        case_section.pack(fill="x", expand=False, padx=5, pady=5)
        self.build_case_tab(case_section)

        clients_section = ttk.LabelFrame(parent, text="2. Clientes implicados")
        clients_section.pack(fill="x", expand=True, padx=5, pady=5)
        self.build_clients_tab(clients_section)

        products_section = ttk.LabelFrame(parent, text="3. Productos investigados")
        products_section.pack(fill="x", expand=True, padx=5, pady=5)
        self.build_products_tab(products_section)

        team_section = ttk.LabelFrame(parent, text="4. Colaboradores involucrados")
        team_section.pack(fill="x", expand=True, padx=5, pady=5)
        self.build_team_tab(team_section)

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

    def sync_main_form_after_import(self, section_name):
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
        self.focus_main_tab()
        log_event(
            "navegacion",
            f"Sincronizó la pestaña principal tras importar {section_name}",
            self.logs,
        )

    def build_case_tab(self, parent):
        """Construye la pestaña de detalles del caso."""
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        # Case ID y tipo de informe
        row1 = ttk.Frame(frame)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="Número de caso (AAAA-NNNN):").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_caso_var, width=20)
        id_entry.pack(side="left", padx=5)
        id_entry.bind("<FocusOut>", lambda e: log_event("navegacion", "Modificó número de caso", self.logs))
        self.register_tooltip(id_entry, "Identificador del expediente con formato AAAA-NNNN.")
        ttk.Label(row1, text="Tipo de informe:").pack(side="left")
        tipo_cb = ttk.Combobox(row1, textvariable=self.tipo_informe_var, values=TIPO_INFORME_LIST, state="readonly", width=15)
        tipo_cb.pack(side="left", padx=5)
        self.register_tooltip(tipo_cb, "Selecciona si el reporte es interno o regulatorio.")

        # Categorías y modalidad
        row2 = ttk.Frame(frame)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="Categoría nivel 1:").pack(side="left")
        cat1_cb = ttk.Combobox(row2, textvariable=self.cat_caso1_var, values=list(TAXONOMIA.keys()), state="readonly", width=20)
        cat1_cb.pack(side="left", padx=5)
        cat1_cb.bind("<<ComboboxSelected>>", lambda e: self.on_case_cat1_change())
        self.register_tooltip(cat1_cb, "Nivel superior de la taxonomía de fraude.")
        ttk.Label(row2, text="Categoría nivel 2:").pack(side="left")
        self.case_cat2_cb = ttk.Combobox(row2, textvariable=self.cat_caso2_var, values=list(TAXONOMIA[self.cat_caso1_var.get()].keys()), state="readonly", width=20)
        self.case_cat2_cb.pack(side="left", padx=5)
        self.case_cat2_cb.bind("<<ComboboxSelected>>", lambda e: self.on_case_cat2_change())
        self.register_tooltip(self.case_cat2_cb, "Subcategoría que precisa el evento.")
        ttk.Label(row2, text="Modalidad:").pack(side="left")
        self.case_mod_cb = ttk.Combobox(row2, textvariable=self.mod_caso_var, values=TAXONOMIA[self.cat_caso1_var.get()][self.cat_caso2_var.get()], state="readonly", width=25)
        self.case_mod_cb.pack(side="left", padx=5)
        self.register_tooltip(self.case_mod_cb, "Modalidad específica dentro de la taxonomía.")

        # Canal y proceso
        row3 = ttk.Frame(frame)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="Canal:").pack(side="left")
        canal_cb = ttk.Combobox(row3, textvariable=self.canal_caso_var, values=CANAL_LIST, state="readonly", width=25)
        canal_cb.pack(side="left", padx=5)
        self.register_tooltip(canal_cb, "Canal donde se originó el evento.")
        ttk.Label(row3, text="Proceso impactado:").pack(side="left")
        proc_cb = ttk.Combobox(row3, textvariable=self.proceso_caso_var, values=PROCESO_LIST, state="readonly", width=25)
        proc_cb.pack(side="left", padx=5)
        self.register_tooltip(proc_cb, "Proceso que sufrió la desviación.")

        # Validaciones del caso
        self.validators.append(
            FieldValidator(
                id_entry,
                lambda: validate_case_id(self.id_caso_var.get()),
                self.logs,
                "Caso - ID",
                variables=[self.id_caso_var],
            )
        )
        self.validators.append(
            FieldValidator(
                tipo_cb,
                lambda: validate_required_text(self.tipo_informe_var.get(), "el tipo de informe"),
                self.logs,
                "Caso - Tipo de informe",
                variables=[self.tipo_informe_var],
            )
        )
        self.validators.append(
            FieldValidator(
                cat1_cb,
                lambda: validate_required_text(self.cat_caso1_var.get(), "la categoría nivel 1"),
                self.logs,
                "Caso - Categoría 1",
                variables=[self.cat_caso1_var],
            )
        )
        self.validators.append(
            FieldValidator(
                self.case_cat2_cb,
                lambda: validate_required_text(self.cat_caso2_var.get(), "la categoría nivel 2"),
                self.logs,
                "Caso - Categoría 2",
                variables=[self.cat_caso2_var],
            )
        )
        self.validators.append(
            FieldValidator(
                self.case_mod_cb,
                lambda: validate_required_text(self.mod_caso_var.get(), "la modalidad del caso"),
                self.logs,
                "Caso - Modalidad",
                variables=[self.mod_caso_var],
            )
        )
        self.validators.append(
            FieldValidator(
                canal_cb,
                lambda: validate_required_text(self.canal_caso_var.get(), "el canal del caso"),
                self.logs,
                "Caso - Canal",
                variables=[self.canal_caso_var],
            )
        )
        self.validators.append(
            FieldValidator(
                proc_cb,
                lambda: validate_required_text(self.proceso_caso_var.get(), "el proceso impactado"),
                self.logs,
                "Caso - Proceso",
                variables=[self.proceso_caso_var],
            )
        )

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
        log_event("navegacion", "Modificó categoría 1 del caso", self.logs)

    def on_case_cat2_change(self):
        cat1 = self.cat_caso1_var.get()
        cat2 = self.cat_caso2_var.get()
        mods = TAXONOMIA.get(cat1, {}).get(cat2, [])
        if not mods:
            mods = [""]
        self.case_mod_cb['values'] = mods
        self.mod_caso_var.set('')
        self.case_mod_cb.set('')
        log_event("navegacion", "Modificó categoría 2 del caso", self.logs)
        if self.cat_caso2_var.get() == 'Fraude Externo':
            messagebox.showwarning(
                "Analítica de fraude externo",
                "Recuerda coordinar con el equipo de reclamos para registrar la analítica correcta en casos de Fraude Externo.",
            )

    def build_clients_tab(self, parent):
        """Construye la pestaña de clientes con lista dinámica."""
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        # Contenedor para los clientes
        self.clients_container = ttk.Frame(frame)
        self.clients_container.pack(fill="x", pady=5)
        # Botón añadir cliente
        add_btn = ttk.Button(frame, text="Agregar cliente", command=self.add_client)
        add_btn.pack(side="left", padx=5)
        self.register_tooltip(add_btn, "Añade un nuevo cliente implicado en el caso.")
        # Inicialmente un cliente en blanco
        self.add_client()

    def add_client(self):
        """Crea y añade un nuevo marco de cliente a la interfaz.

        Se utiliza ``self.client_lookup`` para proporcionar datos de autopoblado
        al nuevo cliente, en caso de que exista un registro previo en
        ``client_details.csv``. Luego se actualizan las opciones de clientes
        disponibles para los productos.
        """
        idx = len(self.client_frames)
        client = ClientFrame(self.clients_container, idx, self.remove_client,
                             self.update_client_options_global, self.logs,
                             self.register_tooltip, client_lookup=self.client_lookup)
        self.client_frames.append(client)
        self.update_client_options_global()

    def remove_client(self, client_frame):
        self.client_frames.remove(client_frame)
        # Renombrar las etiquetas
        for i, cl in enumerate(self.client_frames):
            cl.idx = i
            cl.frame.config(text=f"Cliente {i+1}")
        self.update_client_options_global()

    def update_client_options_global(self):
        """Actualiza la lista de clientes en todos los productos y envolvimientos."""
        options = [c.id_var.get().strip() for c in self.client_frames if c.id_var.get().strip()]
        # Actualizar combobox de clientes en cada producto
        for prod in self.product_frames:
            prod.update_client_options()
        log_event("navegacion", "Actualizó opciones de cliente", self.logs)

    def build_team_tab(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        self.team_container = ttk.Frame(frame)
        self.team_container.pack(fill="x", pady=5)
        add_btn = ttk.Button(frame, text="Agregar colaborador", command=self.add_team)
        add_btn.pack(side="left", padx=5)
        self.register_tooltip(add_btn, "Crea un registro para otro colaborador investigado.")
        self.add_team()

    def add_team(self):
        idx = len(self.team_frames)
        team = TeamMemberFrame(self.team_container, idx, self.remove_team, self.update_team_options_global, self.team_lookup, self.logs, self.register_tooltip)
        self.team_frames.append(team)
        self.update_team_options_global()

    def remove_team(self, team_frame):
        self.team_frames.remove(team_frame)
        # Renombrar
        for i, tm in enumerate(self.team_frames):
            tm.idx = i
            tm.frame.config(text=f"Colaborador {i+1}")
        self.update_team_options_global()

    def update_team_options_global(self):
        """Actualiza listas de colaboradores en productos e involucra."""
        options = [t.id_var.get().strip() for t in self.team_frames if t.id_var.get().strip()]
        for prod in self.product_frames:
            prod.update_team_options()
        log_event("navegacion", "Actualizó opciones de colaborador", self.logs)

    def build_products_tab(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        self.product_container = ttk.Frame(frame)
        self.product_container.pack(fill="x", pady=5)
        add_btn = ttk.Button(frame, text="Agregar producto", command=self.add_product)
        add_btn.pack(side="left", padx=5)
        self.register_tooltip(add_btn, "Registra un nuevo producto investigado.")
        # No añadimos automáticamente un producto porque los productos están asociados a clientes

    def _apply_case_taxonomy_defaults(self, product_frame):
        """Configura un producto nuevo con la taxonomía seleccionada en el caso."""

        cat1 = self.cat_caso1_var.get()
        cat2 = self.cat_caso2_var.get()
        modalidad = self.mod_caso_var.get()
        if cat1 in TAXONOMIA:
            product_frame.cat1_var.set(cat1)
            product_frame.on_cat1_change()
            if cat2 in TAXONOMIA[cat1]:
                product_frame.cat2_var.set(cat2)
                product_frame.on_cat2_change()
                if modalidad in TAXONOMIA[cat1][cat2]:
                    product_frame.mod_var.set(modalidad)
                    product_frame.mod_cb.set(modalidad)

    def add_product(self):
        idx = len(self.product_frames)
        prod = ProductFrame(self.product_container, idx, self.remove_product, self.get_client_ids, self.get_team_ids, self.logs, self.product_lookup, self.register_tooltip)
        self._apply_case_taxonomy_defaults(prod)
        self.product_frames.append(prod)
        # Renombrar
        for i, p in enumerate(self.product_frames):
            p.idx = i
            p.frame.config(text=f"Producto {i+1}")

    def remove_product(self, prod_frame):
        self.product_frames.remove(prod_frame)
        for i, p in enumerate(self.product_frames):
            p.idx = i
            p.frame.config(text=f"Producto {i+1}")

    def get_client_ids(self):
        return [c.id_var.get().strip() for c in self.client_frames if c.id_var.get().strip()]

    def get_team_ids(self):
        return [t.id_var.get().strip() for t in self.team_frames if t.id_var.get().strip()]

    def build_risk_tab(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        self.risk_container = ttk.Frame(frame)
        self.risk_container.pack(fill="x", pady=5)
        add_btn = ttk.Button(frame, text="Agregar riesgo", command=self.add_risk)
        add_btn.pack(side="left", padx=5)
        self.register_tooltip(add_btn, "Registra un nuevo riesgo identificado.")
        self.add_risk()

    def add_risk(self):
        idx = len(self.risk_frames)
        risk = RiskFrame(self.risk_container, idx, self.remove_risk, self.logs, self.register_tooltip)
        self.risk_frames.append(risk)
        for i, r in enumerate(self.risk_frames):
            r.idx = i
            r.frame.config(text=f"Riesgo {i+1}")

    def remove_risk(self, risk_frame):
        self.risk_frames.remove(risk_frame)
        for i, r in enumerate(self.risk_frames):
            r.idx = i
            r.frame.config(text=f"Riesgo {i+1}")

    def build_norm_tab(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        self.norm_container = ttk.Frame(frame)
        self.norm_container.pack(fill="x", pady=5)
        add_btn = ttk.Button(frame, text="Agregar norma", command=self.add_norm)
        add_btn.pack(side="left", padx=5)
        self.register_tooltip(add_btn, "Agrega otra norma transgredida.")
        self.add_norm()

    def add_norm(self):
        idx = len(self.norm_frames)
        norm = NormFrame(self.norm_container, idx, self.remove_norm, self.logs, self.register_tooltip)
        self.norm_frames.append(norm)
        for i, n in enumerate(self.norm_frames):
            n.idx = i
            n.frame.config(text=f"Norma {i+1}")

    def remove_norm(self, norm_frame):
        self.norm_frames.remove(norm_frame)
        for i, n in enumerate(self.norm_frames):
            n.idx = i
            n.frame.config(text=f"Norma {i+1}")

    def build_analysis_tab(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        # Campos de análisis
        row1 = ttk.Frame(frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="Antecedentes:").pack(side="left")
        antecedentes_entry = ttk.Entry(row1, textvariable=self.antecedentes_var, width=80)
        antecedentes_entry.pack(side="left", padx=5)
        antecedentes_entry.bind("<FocusOut>", lambda e: log_event("navegacion", "Modificó antecedentes", self.logs))
        self.register_tooltip(antecedentes_entry, "Resume los hechos previos y contexto del caso.")
        row2 = ttk.Frame(frame)
        row2.pack(fill="x", pady=1)
        ttk.Label(row2, text="Modus operandi:").pack(side="left")
        modus_entry = ttk.Entry(row2, textvariable=self.modus_var, width=80)
        modus_entry.pack(side="left", padx=5)
        modus_entry.bind("<FocusOut>", lambda e: log_event("navegacion", "Modificó modus operandi", self.logs))
        self.register_tooltip(modus_entry, "Describe la forma en que se ejecutó el fraude.")
        row3 = ttk.Frame(frame)
        row3.pack(fill="x", pady=1)
        ttk.Label(row3, text="Hallazgos principales:").pack(side="left")
        hall_entry = ttk.Entry(row3, textvariable=self.hallazgos_var, width=80)
        hall_entry.pack(side="left", padx=5)
        hall_entry.bind("<FocusOut>", lambda e: log_event("navegacion", "Modificó hallazgos", self.logs))
        self.register_tooltip(hall_entry, "Menciona los hallazgos clave de la investigación.")
        row4 = ttk.Frame(frame)
        row4.pack(fill="x", pady=1)
        ttk.Label(row4, text="Descargos del colaborador:").pack(side="left")
        desc_entry = ttk.Entry(row4, textvariable=self.descargos_var, width=80)
        desc_entry.pack(side="left", padx=5)
        desc_entry.bind("<FocusOut>", lambda e: log_event("navegacion", "Modificó descargos", self.logs))
        self.register_tooltip(desc_entry, "Registra los descargos formales del colaborador.")
        row5 = ttk.Frame(frame)
        row5.pack(fill="x", pady=1)
        ttk.Label(row5, text="Conclusiones:").pack(side="left")
        concl_entry = ttk.Entry(row5, textvariable=self.conclusiones_var, width=80)
        concl_entry.pack(side="left", padx=5)
        concl_entry.bind("<FocusOut>", lambda e: log_event("navegacion", "Modificó conclusiones", self.logs))
        self.register_tooltip(concl_entry, "Escribe las conclusiones generales del informe.")
        row6 = ttk.Frame(frame)
        row6.pack(fill="x", pady=1)
        ttk.Label(row6, text="Recomendaciones y mejoras:").pack(side="left")
        reco_entry = ttk.Entry(row6, textvariable=self.recomendaciones_var, width=80)
        reco_entry.pack(side="left", padx=5)
        reco_entry.bind("<FocusOut>", lambda e: log_event("navegacion", "Modificó recomendaciones", self.logs))
        self.register_tooltip(reco_entry, "Propón acciones correctivas y preventivas.")

    def build_actions_tab(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        # Botones de importación
        ttk.Label(frame, text="Importar datos masivos (CSV)").pack(anchor="w")
        import_buttons = ttk.Frame(frame)
        import_buttons.pack(anchor="w", pady=2)
        btn_clientes = ttk.Button(import_buttons, text="Cargar clientes", command=self.import_clients)
        btn_clientes.pack(side="left", padx=2)
        self.register_tooltip(btn_clientes, "Importa clientes desde un CSV masivo.")
        btn_colabs = ttk.Button(import_buttons, text="Cargar colaboradores", command=self.import_team_members)
        btn_colabs.pack(side="left", padx=2)
        self.register_tooltip(btn_colabs, "Importa colaboradores y sus datos laborales.")
        btn_productos = ttk.Button(import_buttons, text="Cargar productos", command=self.import_products)
        btn_productos.pack(side="left", padx=2)
        self.register_tooltip(btn_productos, "Carga productos investigados desde un CSV.")
        btn_combo = ttk.Button(import_buttons, text="Cargar combinado", command=self.import_combined)
        btn_combo.pack(side="left", padx=2)
        self.register_tooltip(btn_combo, "Importa en un solo archivo clientes, productos y colaboradores.")
        # Nuevos botones para riesgos, normas y reclamos
        btn_riesgos = ttk.Button(import_buttons, text="Cargar riesgos", command=self.import_risks)
        btn_riesgos.pack(side="left", padx=2)
        self.register_tooltip(btn_riesgos, "Carga la matriz de riesgos desde CSV.")
        btn_normas = ttk.Button(import_buttons, text="Cargar normas", command=self.import_norms)
        btn_normas.pack(side="left", padx=2)
        self.register_tooltip(btn_normas, "Importa las normas vulneradas.")
        btn_reclamos = ttk.Button(import_buttons, text="Cargar reclamos", command=self.import_claims)
        btn_reclamos.pack(side="left", padx=2)
        self.register_tooltip(btn_reclamos, "Vincula reclamos con los productos.")

        # Botones de guardado y carga
        ttk.Label(frame, text="Guardar y cargar versiones").pack(anchor="w", pady=(10,2))
        version_buttons = ttk.Frame(frame)
        version_buttons.pack(anchor="w", pady=2)
        btn_save = ttk.Button(version_buttons, text="Guardar y enviar", command=self.save_and_send)
        btn_save.pack(side="left", padx=2)
        self.register_tooltip(btn_save, "Valida y exporta todos los archivos requeridos.")
        btn_load = ttk.Button(version_buttons, text="Cargar versión", command=self.load_version_dialog)
        btn_load.pack(side="left", padx=2)
        self.register_tooltip(btn_load, "Restaura una versión previa en formato JSON.")
        btn_clear = ttk.Button(version_buttons, text="Borrar todos los datos", command=self.clear_all)
        btn_clear.pack(side="left", padx=2)
        self.register_tooltip(btn_clear, "Limpia el formulario completo para iniciar desde cero.")

        feedback_frame = ttk.LabelFrame(frame, text="Retroalimentación del formulario")
        feedback_frame.pack(fill="x", pady=(15, 5))
        ttk.Label(feedback_frame, text="¿Esta pantalla fue útil?").pack(side="left", padx=5)
        btn_up = ttk.Button(feedback_frame, text="👍 Me gustó", command=lambda: self.request_feedback(True))
        btn_up.pack(side="left", padx=2)
        self.register_tooltip(btn_up, "Haz clic si la experiencia fue positiva.")
        btn_down = ttk.Button(feedback_frame, text="👎 Necesita mejoras", command=lambda: self.request_feedback(False))
        btn_down.pack(side="left", padx=2)
        self.register_tooltip(btn_down, "Cuéntanos qué deberíamos mejorar.")

        # Información adicional
        ttk.Label(frame, text="El auto‑guardado se realiza automáticamente en un archivo JSON").pack(anchor="w", pady=(10,2))

    # ---------------------------------------------------------------------
    # Importación desde CSV

    def request_feedback(self, was_positive):
        """Solicita un comentario breve y lo registra en los logs."""

        sentiment = "positivo" if was_positive else "negativo"
        default_prompt = "Cuéntanos qué funcionó bien." if was_positive else "Describe qué deberíamos mejorar."
        comment = simpledialog.askstring("Retroalimentación", default_prompt, parent=self.root)
        detail = (comment or "Sin comentarios adicionales").strip()
        log_event("feedback", f"Feedback {sentiment}: {detail}", self.logs)
        messagebox.showinfo("¡Gracias!", "Registramos tu opinión para seguir mejorando.")

    # ---------------------------------------------------------------------
    # Importación desde CSV

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

    def _populate_client_frame_from_row(self, frame, row):
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

        Ejemplo::

            fila = {"id_cliente": "123", "telefonos": "999"}
            self._populate_client_frame_from_row(cliente, fila)
        """

        id_cliente = (row.get('id_cliente') or row.get('IdCliente') or '').strip()
        frame.id_var.set(id_cliente)
        tipo_id = (row.get('tipo_id') or row.get('TipoID') or TIPO_ID_LIST[0]).strip()
        frame.tipo_id_var.set(tipo_id)
        flag_value = (row.get('flag') or row.get('Flag') or FLAG_CLIENTE_LIST[0]).strip()
        frame.flag_var.set(flag_value)
        telefonos = (row.get('telefonos') or row.get('Telefono') or '').strip()
        frame.telefonos_var.set(telefonos)
        correos = (row.get('correos') or row.get('Correo') or '').strip()
        frame.correos_var.set(correos)
        direcciones = (row.get('direcciones') or row.get('Direccion') or '').strip()
        frame.direcciones_var.set(direcciones)
        accionado_val = (row.get('accionado') or row.get('Accionado') or '').strip()
        frame.set_accionado_from_text(accionado_val)
        self.client_lookup[id_cliente] = {
            'tipo_id': frame.tipo_id_var.get(),
            'flag': frame.flag_var.get(),
            'telefonos': frame.telefonos_var.get(),
            'correos': frame.correos_var.get(),
            'direcciones': frame.direcciones_var.get(),
            'accionado': accionado_val,
        }

    def import_clients(self):
        """Importa clientes desde un archivo CSV y los añade a la lista."""
        filename = filedialog.askopenfilename(title="Seleccionar CSV de clientes", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
        try:
            with open(filename, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                imported = 0
                for row in reader:
                    # Extraer datos esperados
                    id_cliente = row.get('id_cliente', '').strip()
                    if not id_cliente:
                        continue
                    # Verificar duplicado
                    existing = next((c for c in self.client_frames if c.id_var.get().strip() == id_cliente), None)
                    target_frame = existing or self._obtain_client_slot_for_import()
                    if existing:
                        log_event("navegacion", f"Actualizó cliente {id_cliente} desde importación", self.logs)
                    self._populate_client_frame_from_row(target_frame, row)
                    imported += 1
            self.update_client_options_global()
            # Guardar autosave y registrar evento
            self.save_auto()
            log_event("navegacion", f"Clientes importados desde CSV: {imported}", self.logs)
            if imported:
                self.sync_main_form_after_import("clientes")
                messagebox.showinfo("Importación completa", f"Se cargaron {imported} clientes.")
            else:
                messagebox.showwarning("Sin cambios", "El archivo no aportó clientes nuevos.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar clientes: {ex}")

    def import_team_members(self):
        """Importa colaboradores desde un archivo CSV y los añade a la lista.

        Esta función abre un diálogo para seleccionar un archivo CSV que debe
        contener al menos una columna ``id_colaborador``.  Cada fila del
        archivo se convierte en una nueva entrada de colaborador dentro del
        formulario, rellenando los campos con la información encontrada.  Los
        IDs duplicados se omiten para evitar crear dos registros con el mismo
        identificador.  Tras la importación se actualizan las listas
        desplegables que dependen de los colaboradores y se guarda un
        autosave.

        Ejemplo de uso:

            >>> # El usuario hace clic en "Cargar colaboradores" y selecciona un CSV
            # con columnas id_colaborador, flag, division, area, servicio, puesto,
            # nombre_agencia, codigo_agencia, tipo_falta, tipo_sancion
            app.import_team_members()

        """
        filename = filedialog.askopenfilename(title="Seleccionar CSV de colaboradores", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
        try:
            with open(filename, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                imported = 0
                for row in reader:
                    id_col = row.get('id_colaborador', '').strip()
                    if not id_col:
                        continue
                    if id_col in [t.id_var.get().strip() for t in self.team_frames]:
                        log_event("validacion", f"Colaborador duplicado {id_col} en importación", self.logs)
                        continue
                    self.add_team()
                    tm = self.team_frames[-1]
                    tm.id_var.set(id_col)
                    tm.flag_var.set(row.get('flag', 'No aplica').strip())
                    tm.division_var.set(row.get('division', '').strip())
                    tm.area_var.set(row.get('area', '').strip())
                    tm.servicio_var.set(row.get('servicio', '').strip())
                    tm.puesto_var.set(row.get('puesto', '').strip())
                    tm.nombre_agencia_var.set(row.get('nombre_agencia', '').strip())
                    tm.codigo_agencia_var.set(row.get('codigo_agencia', '').strip())
                    tm.tipo_falta_var.set(row.get('tipo_falta', 'No aplica').strip())
                    tm.tipo_sancion_var.set(row.get('tipo_sancion', 'No aplica').strip())
                    self.team_lookup[id_col] = {
                        'division': tm.division_var.get(),
                        'area': tm.area_var.get(),
                        'servicio': tm.servicio_var.get(),
                        'puesto': tm.puesto_var.get(),
                        'nombre_agencia': tm.nombre_agencia_var.get(),
                        'codigo_agencia': tm.codigo_agencia_var.get(),
                    }
                    imported += 1
            self.update_team_options_global()
            self.save_auto()
            log_event("navegacion", "Colaboradores importados desde CSV", self.logs)
            if imported:
                self.sync_main_form_after_import("colaboradores")
                messagebox.showinfo("Importación completa", "Colaboradores importados correctamente.")
            else:
                messagebox.showwarning("Sin cambios", "No se encontraron colaboradores nuevos en el archivo.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar colaboradores: {ex}")

    def import_products(self):
        """Importa productos desde un archivo CSV y los añade a la lista.

        Cada fila del CSV define un producto e incluye columnas como
        ``id_producto``, ``id_cliente``, ``categoria1``, ``categoria2``,
        ``modalidad``, ``canal``, ``proceso``, ``fecha_ocurrencia``,
        ``fecha_descubrimiento``, ``monto_investigado``, ``tipo_moneda``,
        ``monto_perdida_fraude``, ``monto_falla_procesos``,
        ``monto_contingencia``, ``monto_recuperado``, ``monto_pago_deuda``,
        ``tipo_producto``, ``id_reclamo``, ``nombre_analitica`` y
        ``codigo_analitica``.  Esta función crea una entrada por cada
        producto, asigna el cliente correcto (creándolo si no existe) y
        selecciona la taxonomía adecuada si coincide con los valores
        permitidos.  Los productos duplicados se omiten.  Las asignaciones
        de montos a colaboradores no se cargan en esta función; para ello
        utilice el importador combinado.  Después de la importación se
        actualiza el autosave y se registra un evento de navegación.

        """
        filename = filedialog.askopenfilename(title="Seleccionar CSV de productos", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
        try:
            with open(filename, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                imported = 0
                for row in reader:
                    id_prod = row.get('id_producto', '').strip()
                    if not id_prod:
                        continue
                    # Verificar duplicado
                    if id_prod in [p.id_var.get().strip() for p in self.product_frames]:
                        log_event("validacion", f"Producto duplicado {id_prod} en importación", self.logs)
                        continue
                    self.add_product()
                    pr = self.product_frames[-1]
                    pr.id_var.set(id_prod)
                    pr.client_var.set(row.get('id_cliente', '').strip())
                    # Asignar categorías con validación básica
                    cat1 = row.get('categoria1', '')
                    if cat1 in TAXONOMIA:
                        pr.cat1_var.set(cat1)
                        pr.on_cat1_change()
                        cat2 = row.get('categoria2', '')
                        if cat2 in TAXONOMIA[cat1]:
                            pr.cat2_var.set(cat2)
                            pr.on_cat2_change()
                            mod = row.get('modalidad', '')
                            if mod in TAXONOMIA[cat1][cat2]:
                                pr.mod_var.set(mod)
                            elif mod:
                                warning = f"Producto {id_prod}: la modalidad '{mod}' no corresponde a {cat1}/{cat2}."
                                log_event('validacion', warning, self.logs)
                                messagebox.showwarning('Taxonomía inválida', warning)
                        elif cat2:
                            warning = f"Producto {id_prod}: la categoría 2 '{cat2}' no existe bajo {cat1}."
                            log_event('validacion', warning, self.logs)
                            messagebox.showwarning('Taxonomía inválida', warning)
                    else:
                        if cat1:
                            warning = f"Producto {id_prod}: la categoría 1 '{cat1}' no está en la taxonomía."
                            log_event('validacion', warning, self.logs)
                            messagebox.showwarning('Taxonomía inválida', warning)
                        pr.cat1_var.set(cat1)
                    pr.canal_var.set(row.get('canal', CANAL_LIST[0]))
                    pr.proceso_var.set(row.get('proceso', PROCESO_LIST[0]))
                    pr.fecha_oc_var.set(row.get('fecha_ocurrencia', ''))
                    pr.fecha_desc_var.set(row.get('fecha_descubrimiento', ''))
                    pr.monto_inv_var.set(row.get('monto_investigado', ''))
                    pr.moneda_var.set(row.get('tipo_moneda', TIPO_MONEDA_LIST[0]))
                    pr.monto_perdida_var.set(row.get('monto_perdida_fraude', ''))
                    pr.monto_falla_var.set(row.get('monto_falla_procesos', ''))
                    pr.monto_cont_var.set(row.get('monto_contingencia', ''))
                    pr.monto_rec_var.set(row.get('monto_recuperado', ''))
                    pr.monto_pago_var.set(row.get('monto_pago_deuda', ''))
                    tipo_prod = row.get('tipo_producto', '')
                    if tipo_prod in TIPO_PRODUCTO_LIST:
                        pr.tipo_prod_var.set(tipo_prod)
                    pr.id_reclamo_var.set(row.get('id_reclamo', '').strip())
                    pr.nombre_analitica_var.set(row.get('nombre_analitica', '').strip())
                    pr.codigo_analitica_var.set(row.get('codigo_analitica', '').strip())
                    # No se cargan asignaciones desde este CSV
                    self.product_lookup[id_prod] = {
                        'id_cliente': pr.client_var.get(),
                        'tipo_producto': pr.tipo_prod_var.get(),
                        'categoria1': pr.cat1_var.get(),
                        'categoria2': pr.cat2_var.get(),
                        'modalidad': pr.mod_var.get(),
                        'canal': pr.canal_var.get(),
                        'proceso': pr.proceso_var.get(),
                        'fecha_ocurrencia': pr.fecha_oc_var.get(),
                        'fecha_descubrimiento': pr.fecha_desc_var.get(),
                        'monto_investigado': pr.monto_inv_var.get(),
                        'tipo_moneda': pr.moneda_var.get(),
                        'monto_perdida_fraude': pr.monto_perdida_var.get(),
                        'monto_falla_procesos': pr.monto_falla_var.get(),
                        'monto_contingencia': pr.monto_cont_var.get(),
                        'monto_recuperado': pr.monto_rec_var.get(),
                        'monto_pago_deuda': pr.monto_pago_var.get(),
                        'id_reclamo': pr.id_reclamo_var.get(),
                        'nombre_analitica': pr.nombre_analitica_var.get(),
                        'codigo_analitica': pr.codigo_analitica_var.get(),
                    }
                    imported += 1
            self.save_auto()
            log_event("navegacion", "Productos importados desde CSV", self.logs)
            if imported:
                self.sync_main_form_after_import("productos")
                messagebox.showinfo("Importación completa", "Productos importados correctamente.")
            else:
                messagebox.showwarning("Sin cambios", "El CSV no contenía productos nuevos.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar productos: {ex}")

    def import_combined(self):
        """Importa datos combinados de productos, clientes y colaboradores.

        Este importador permite cargar en un único CSV toda la información
        relacionada con un producto, incluyendo su cliente, colaborador(es),
        montos asignados y taxonomía.  Cada fila puede contener columnas
        ``id_cliente``, ``tipo_id``, ``flag_cliente``, ``telefonos``,
        ``correos``, ``direcciones``, ``accionado``, ``id_colaborador``,
        ``flag_colaborador``, ``division``, ``area``, ``servicio``,
        ``puesto``, ``nombre_agencia``, ``codigo_agencia``, ``tipo_falta``,
        ``tipo_sancion``, ``id_producto``, ``categoria1``, ``categoria2``,
        ``modalidad``, ``canal``, ``proceso``, ``fecha_ocurrencia``,
        ``fecha_descubrimiento``, ``monto_investigado``, ``tipo_moneda``,
        ``monto_perdida_fraude``, ``monto_falla_procesos``,
        ``monto_contingencia``, ``monto_recuperado``, ``monto_pago_deuda``,
        ``tipo_producto``, ``id_reclamo``, ``nombre_analitica``,
        ``codigo_analitica``, ``flag_colaborador``, ``monto_asignado``.

        La función crea o actualiza clientes y colaboradores según sea
        necesario y añade productos con toda su información.  Además
        procesa las columnas de asignación de montos a colaboradores
        (``monto_asignado``) creando entradas en la sección de
        involucra‑miembros.  Los valores de categoría se validan
        contra la taxonomía y se seleccionan en los desplegables
        correspondientes.  Al finalizar se registra un evento de
        navegación y se guarda un autosave.

        """
        filename = filedialog.askopenfilename(title="Seleccionar CSV combinado", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
        try:
            with open(filename, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                created_records = False
                for row in reader:
                    # Columns may include id_cliente, tipo_id, flag_cliente, id_producto, id_colaborador, monto_asignado, etc.
                    id_cliente = row.get('id_cliente', '').strip()
                    if id_cliente and id_cliente not in [c.id_var.get().strip() for c in self.client_frames]:
                        self.add_client()
                        cl = self.client_frames[-1]
                        cl.id_var.set(id_cliente)
                        cl.tipo_id_var.set(row.get('tipo_id', 'DNI'))
                        cl.flag_var.set(row.get('flag_cliente', 'No aplica'))
                        cl.telefonos_var.set(row.get('telefonos', ''))
                        cl.correos_var.set(row.get('correos', ''))
                        cl.direcciones_var.set(row.get('direcciones', ''))
                        accionado_val = row.get('accionado', '')
                        cl.set_accionado_from_text(accionado_val)
                        self.client_lookup[id_cliente] = {
                            'tipo_id': cl.tipo_id_var.get(),
                            'flag': cl.flag_var.get(),
                            'telefonos': cl.telefonos_var.get(),
                            'correos': cl.correos_var.get(),
                            'direcciones': cl.direcciones_var.get(),
                            'accionado': accionado_val,
                        }
                        created_records = True
                    # Team member
                    id_col = row.get('id_colaborador', '').strip()
                    if id_col and id_col not in [t.id_var.get().strip() for t in self.team_frames]:
                        self.add_team()
                        tm = self.team_frames[-1]
                        tm.id_var.set(id_col)
                        tm.flag_var.set(row.get('flag_colaborador', 'No aplica'))
                        tm.division_var.set(row.get('division', ''))
                        tm.area_var.set(row.get('area', ''))
                        tm.servicio_var.set(row.get('servicio', ''))
                        tm.puesto_var.set(row.get('puesto', ''))
                        tm.nombre_agencia_var.set(row.get('nombre_agencia', ''))
                        tm.codigo_agencia_var.set(row.get('codigo_agencia', ''))
                        tm.tipo_falta_var.set(row.get('tipo_falta', 'No aplica'))
                        tm.tipo_sancion_var.set(row.get('tipo_sancion', 'No aplica'))
                        self.team_lookup[id_col] = {
                            'division': tm.division_var.get(),
                            'area': tm.area_var.get(),
                            'servicio': tm.servicio_var.get(),
                            'puesto': tm.puesto_var.get(),
                            'nombre_agencia': tm.nombre_agencia_var.get(),
                            'codigo_agencia': tm.codigo_agencia_var.get(),
                        }
                        created_records = True
                    # Producto
                    id_prod = row.get('id_producto', '').strip()
                    if id_prod:
                        prod = None
                        for p in self.product_frames:
                            if p.id_var.get().strip() == id_prod:
                                prod = p
                                break
                        if not prod:
                            self.add_product()
                            prod = self.product_frames[-1]
                            prod.id_var.set(id_prod)
                            prod.client_var.set(id_cliente)
                            # Category assignments
                            cat1 = row.get('categoria1', '')
                            if cat1 in TAXONOMIA:
                                prod.cat1_var.set(cat1)
                                prod.on_cat1_change()
                                cat2 = row.get('categoria2', '')
                                if cat2 in TAXONOMIA[cat1]:
                                    prod.cat2_var.set(cat2)
                                    prod.on_cat2_change()
                                    mod = row.get('modalidad', '')
                                    if mod in TAXONOMIA[cat1][cat2]:
                                        prod.mod_var.set(mod)
                                    elif mod:
                                        warning = f"Producto {id_prod}: la modalidad '{mod}' no corresponde a {cat1}/{cat2}."
                                        log_event('validacion', warning, self.logs)
                                        messagebox.showwarning('Taxonomía inválida', warning)
                                elif cat2:
                                    warning = f"Producto {id_prod}: la categoría 2 '{cat2}' no existe bajo {cat1}."
                                    log_event('validacion', warning, self.logs)
                                    messagebox.showwarning('Taxonomía inválida', warning)
                            else:
                                if cat1:
                                    warning = f"Producto {id_prod}: la categoría 1 '{cat1}' no está en la taxonomía."
                                    log_event('validacion', warning, self.logs)
                                    messagebox.showwarning('Taxonomía inválida', warning)
                                prod.cat1_var.set(cat1)
                            prod.canal_var.set(row.get('canal', CANAL_LIST[0]))
                            prod.proceso_var.set(row.get('proceso', PROCESO_LIST[0]))
                            prod.fecha_oc_var.set(row.get('fecha_ocurrencia', ''))
                            prod.fecha_desc_var.set(row.get('fecha_descubrimiento', ''))
                            prod.monto_inv_var.set(row.get('monto_investigado', ''))
                            prod.moneda_var.set(row.get('tipo_moneda', TIPO_MONEDA_LIST[0]))
                            prod.monto_perdida_var.set(row.get('monto_perdida_fraude', ''))
                            prod.monto_falla_var.set(row.get('monto_falla_procesos', ''))
                            prod.monto_cont_var.set(row.get('monto_contingencia', ''))
                            prod.monto_rec_var.set(row.get('monto_recuperado', ''))
                            prod.monto_pago_var.set(row.get('monto_pago_deuda', ''))
                            tipo_prod = row.get('tipo_producto', '')
                            if tipo_prod in TIPO_PRODUCTO_LIST:
                                prod.tipo_prod_var.set(tipo_prod)
                            prod.id_reclamo_var.set(row.get('id_reclamo', '').strip())
                            prod.nombre_analitica_var.set(row.get('nombre_analitica', '').strip())
                            prod.codigo_analitica_var.set(row.get('codigo_analitica', '').strip())
                            self.product_lookup[id_prod] = {
                                'id_cliente': prod.client_var.get(),
                                'tipo_producto': prod.tipo_prod_var.get(),
                                'categoria1': prod.cat1_var.get(),
                                'categoria2': prod.cat2_var.get(),
                                'modalidad': prod.mod_var.get(),
                                'canal': prod.canal_var.get(),
                                'proceso': prod.proceso_var.get(),
                                'fecha_ocurrencia': prod.fecha_oc_var.get(),
                                'fecha_descubrimiento': prod.fecha_desc_var.get(),
                                'monto_investigado': prod.monto_inv_var.get(),
                                'tipo_moneda': prod.moneda_var.get(),
                                'monto_perdida_fraude': prod.monto_perdida_var.get(),
                                'monto_falla_procesos': prod.monto_falla_var.get(),
                                'monto_contingencia': prod.monto_cont_var.get(),
                                'monto_recuperado': prod.monto_rec_var.get(),
                                'monto_pago_deuda': prod.monto_pago_var.get(),
                                'id_reclamo': prod.id_reclamo_var.get(),
                                'nombre_analitica': prod.nombre_analitica_var.get(),
                                'codigo_analitica': prod.codigo_analitica_var.get(),
                            }
                            created_records = True
                        # Añadir asignación a este producto
                        monto_asignado = row.get('monto_asignado', '').strip()
                        if id_col and monto_asignado:
                            # Añadir fila de involvement
                            inv = InvolvementRow(prod.invol_frame, prod, len(prod.involvements), prod.get_team_options, prod.remove_involvement, self.logs, prod.tooltip_register)
                            prod.involvements.append(inv)
                            inv.team_var.set(id_col)
                            inv.monto_var.set(monto_asignado)
                            created_records = True
            # Actualizar opciones
            self.update_client_options_global()
            self.update_team_options_global()
            self.save_auto()
            log_event("navegacion", "Datos combinados importados desde CSV", self.logs)
            if created_records:
                self.sync_main_form_after_import("datos combinados")
                messagebox.showinfo("Importación completa", "Datos combinados importados correctamente.")
            else:
                messagebox.showwarning("Sin cambios", "No se detectaron registros nuevos en el archivo.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar el CSV combinado: {ex}")

    def import_risks(self):
        """Importa riesgos desde un archivo CSV.

        Cada fila del CSV debe contener las columnas ``id_riesgo``,
        ``id_caso``, ``lider``, ``descripcion``, ``criticidad``,
        ``exposicion_residual`` y ``planes_accion``.  La función crea
        entradas de riesgo en la sección de riesgos y valida que los
        identificadores no se repitan y que cumplan el formato
        ``RSK-`` seguido de 6 a 10 dígitos.  Al importar, los riesgos
        se vinculan al caso actual (si la columna ``id_caso`` coincide),
        se registran eventos de navegación y se guarda un autosave.  Si
        el CSV no contiene la columna ``id_caso``, todos los riesgos se
        asocian al caso actual.

        """
        """Importa detalles de riesgos desde un archivo CSV.

        El CSV debe contener columnas ``id_riesgo``, ``lider``, ``descripcion``,
        ``criticidad``, ``exposicion_residual`` y ``planes_accion``. Crea
        nuevas entradas de riesgo para cada fila. Si un ID de riesgo ya
        existe, se registra en el log y se omite.
        """
        filename = filedialog.askopenfilename(title="Seleccionar CSV de riesgos", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
        try:
            with open(filename, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rid = row.get('id_riesgo', '').strip()
                    if not rid:
                        continue
                    if any(r.id_var.get().strip() == rid for r in self.risk_frames):
                        log_event("validacion", f"Riesgo duplicado {rid} en importación", self.logs)
                        continue
                    self.add_risk()
                    rf = self.risk_frames[-1]
                    rf.id_var.set(rid)
                    rf.lider_var.set(row.get('lider', '').strip())
                    rf.descripcion_var.set(row.get('descripcion', '').strip())
                    crit = row.get('criticidad', '').strip()
                    if crit in CRITICIDAD_LIST:
                        rf.criticidad_var.set(crit)
                    rf.exposicion_var.set(row.get('exposicion_residual', '').strip())
                    rf.planes_var.set(row.get('planes_accion', '').strip())
            # Autosave y log
            self.save_auto()
            log_event("navegacion", "Riesgos importados desde CSV", self.logs)
            messagebox.showinfo("Importación completa", "Riesgos importados correctamente.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar riesgos: {ex}")

    def import_norms(self):
        """Importa normas transgredidas desde un archivo CSV.

        El archivo CSV debe tener las columnas ``id_norma``, ``id_caso``,
        ``descripcion`` y ``fecha_vigencia``.  Esta función añade
        entradas de normas a la sección correspondiente, verificando que
        cada identificador sea único y que cumpla el patrón
        ``XXXX.XXX.XX.XX`` (o se deje en blanco para generarlo
        automáticamente).  Se asocian al caso actual mediante la
        columna ``id_caso`` si existe; en caso contrario se utiliza el
        número de caso activo.  Tras la importación se registra un
        autosave.

        """
        """Importa detalles de normas desde un archivo CSV.

        El CSV debe contener columnas ``id_norma``, ``descripcion`` y
        ``fecha_vigencia``. Crea nuevas normas para cada fila. Si un ID de
        norma ya existe, se registra en el log y se omite.
        """
        filename = filedialog.askopenfilename(title="Seleccionar CSV de normas", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
        try:
            with open(filename, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    nid = row.get('id_norma', '').strip()
                    if not nid:
                        continue
                    if any(n.id_var.get().strip() == nid for n in self.norm_frames):
                        log_event("validacion", f"Norma duplicada {nid} en importación", self.logs)
                        continue
                    self.add_norm()
                    nf = self.norm_frames[-1]
                    nf.id_var.set(nid)
                    nf.descripcion_var.set(row.get('descripcion', '').strip())
                    nf.fecha_var.set(row.get('fecha_vigencia', '').strip())
            self.save_auto()
            log_event("navegacion", "Normas importadas desde CSV", self.logs)
            messagebox.showinfo("Importación completa", "Normas importadas correctamente.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar normas: {ex}")

    def import_claims(self):
        """Importa reclamos desde un archivo CSV.

        Cada fila del CSV debe incluir ``id_reclamo``, ``id_caso``,
        ``id_producto``, ``nombre_analitica`` y ``codigo_analitica``.
        Esta función crea o actualiza registros de reclamo vinculando
        cada reclamo con su producto y su caso.  El identificador de
        reclamo debe iniciar con ``C`` y estar seguido de ocho dígitos
        (``CXXXXXXXX``) o puede estar vacío si el producto no tiene
        montos de pérdida/falla/contingencia.  Los códigos de analítica
        se validan para cumplir los requisitos de 10 dígitos y prefijo
        permitido (43, 45, 46 o 56).  Al finalizar se guarda un autosave
        y se registra el evento de navegación.

        """
        """Importa reclamos desde un archivo CSV.

        El CSV debe contener columnas ``id_reclamo``, ``id_producto``,
        ``nombre_analitica`` y ``codigo_analitica``. Para cada fila se
        asignan los datos al producto correspondiente. Si el producto no
        existe en la interfaz, se registra un error y se omite.
        """
        filename = filedialog.askopenfilename(title="Seleccionar CSV de reclamos", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
        try:
            with open(filename, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rid = row.get('id_reclamo', '').strip()
                    pid = row.get('id_producto', '').strip()
                    if not pid:
                        continue
                    # buscar producto
                    prod = None
                    for p in self.product_frames:
                        if p.id_var.get().strip() == pid:
                            prod = p
                            break
                    if not prod:
                        log_event("validacion", f"Producto {pid} no encontrado para reclamo {rid}", self.logs)
                        continue
                    prod.id_reclamo_var.set(rid)
                    prod.nombre_analitica_var.set(row.get('nombre_analitica', '').strip())
                    prod.codigo_analitica_var.set(row.get('codigo_analitica', '').strip())
            self.save_auto()
            log_event("navegacion", "Reclamos importados desde CSV", self.logs)
            messagebox.showinfo("Importación completa", "Reclamos importados correctamente.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar reclamos: {ex}")

    # ---------------------------------------------------------------------
    # Autoguardado y carga

    def save_auto(self):
        """Guarda automáticamente el estado actual en un archivo JSON."""
        data = self.gather_data()
        try:
            with open(AUTOSAVE_FILE, 'w', encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as ex:
            log_event("validacion", f"Error guardando autosave: {ex}", self.logs)

    def load_autosave(self):
        """Carga el estado guardado automáticamente si el archivo existe."""
        if os.path.exists(AUTOSAVE_FILE):
            try:
                with open(AUTOSAVE_FILE, 'r', encoding="utf-8") as f:
                    data = json.load(f)
                self.populate_from_data(data)
                log_event("navegacion", "Se cargó el autosave", self.logs)
            except Exception as ex:
                log_event("validacion", f"Error cargando autosave: {ex}", self.logs)

    def load_version_dialog(self):
        """Abre un diálogo para cargar una versión previa del formulario.

        Esta función solicita al usuario que seleccione un archivo ``.json``
        previamente generado mediante la opción «Guardar y enviar» o un
        autosave temporal.  Tras seleccionar el archivo, se invoca
        ``load_version`` con la ruta escogida para restaurar el estado
        completo del formulario.  Si el usuario cancela la operación no
        se realizan cambios.

        """
        filename = filedialog.askopenfilename(title="Seleccionar versión JSON", filetypes=[("JSON Files", "*.json")])
        if not filename:
            return
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                data = json.load(f)
            self.populate_from_data(data)
            log_event("navegacion", f"Se cargó versión desde {filename}", self.logs)
            messagebox.showinfo("Versión cargada", "La versión se cargó correctamente.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo cargar la versión: {ex}")

    def clear_all(self):
        """Elimina todos los datos actuales y restablece el formulario.

        Este método solicita confirmación al usuario para borrar toda la
        información cargada: clientes, colaboradores, productos, riesgos,
        normas y narrativas.  Si el usuario confirma, todos los frames
        dinámicos se destruyen, las listas se vacían y se restablecen los
        valores por defecto de los campos del caso.  También se elimina el
        autosave y se registran eventos de navegación y validación.

        """
        if not messagebox.askyesno("Confirmar", "¿Desea borrar todos los datos? Esta acción no se puede deshacer."):
            return
        # Limpiar campos del caso
        self.id_caso_var.set("")
        self.tipo_informe_var.set(TIPO_INFORME_LIST[0])
        self.cat_caso1_var.set(list(TAXONOMIA.keys())[0])
        self.on_case_cat1_change()
        self.canal_caso_var.set(CANAL_LIST[0])
        self.proceso_caso_var.set(PROCESO_LIST[0])
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
        # Volver a crear uno por cada sección donde corresponde
        self.add_client()
        self.add_team()
        self.add_risk()
        self.add_norm()
        # Limpiar análisis
        self.antecedentes_var.set("")
        self.modus_var.set("")
        self.hallazgos_var.set("")
        self.descargos_var.set("")
        self.conclusiones_var.set("")
        self.recomendaciones_var.set("")
        # Guardar auto
        self.save_auto()
        log_event("navegacion", "Se borraron todos los datos", self.logs)
        messagebox.showinfo("Datos borrados", "Todos los datos han sido borrados.")

    # ---------------------------------------------------------------------
    # Recolección y población de datos

    def gather_data(self):
        """Reúne todos los datos del formulario en una estructura de diccionarios."""
        data = {}
        data['caso'] = {
            "id_caso": self.id_caso_var.get().strip(),
            "tipo_informe": self.tipo_informe_var.get(),
            "categoria1": self.cat_caso1_var.get(),
            "categoria2": self.cat_caso2_var.get(),
            "modalidad": self.mod_caso_var.get(),
            "canal": self.canal_caso_var.get(),
            "proceso": self.proceso_caso_var.get(),
        }
        data['clientes'] = [c.get_data() for c in self.client_frames]
        data['colaboradores'] = [t.get_data() for t in self.team_frames]
        productos = []
        reclamos = []
        involucs = []
        for p in self.product_frames:
            prod_data = p.get_data()
            productos.append(prod_data['producto'])
            # Reclamo
            reclamos.append({
                "id_reclamo": prod_data['reclamo']['id_reclamo'],
                "id_caso": "",  # se añade al exportar
                "id_producto": prod_data['producto']['id_producto'],
                "nombre_analitica": prod_data['reclamo']['nombre_analitica'],
                "codigo_analitica": prod_data['reclamo']['codigo_analitica'],
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
        data['normas'] = [n.get_data() for n in self.norm_frames]
        data['analisis'] = {
            "antecedentes": self.antecedentes_var.get().strip(),
            "modus_operandi": self.modus_var.get().strip(),
            "hallazgos": self.hallazgos_var.get().strip(),
            "descargos": self.descargos_var.get().strip(),
            "conclusiones": self.conclusiones_var.get().strip(),
            "recomendaciones": self.recomendaciones_var.get().strip(),
        }
        return data

    def populate_from_data(self, data):
        """Puebla el formulario con datos previamente guardados."""
        # Limpiar primero
        self.clear_all()
        # Datos de caso
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
        if caso.get('canal') in CANAL_LIST:
            self.canal_caso_var.set(caso.get('canal'))
        if caso.get('proceso') in PROCESO_LIST:
            self.proceso_caso_var.set(caso.get('proceso'))
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
            tm.division_var.set(col.get('division', ''))
            tm.area_var.set(col.get('area', ''))
            tm.servicio_var.set(col.get('servicio', ''))
            tm.puesto_var.set(col.get('puesto', ''))
            tm.nombre_agencia_var.set(col.get('nombre_agencia', ''))
            tm.codigo_agencia_var.set(col.get('codigo_agencia', ''))
            tm.tipo_falta_var.set(col.get('tipo_falta', ''))
            tm.tipo_sancion_var.set(col.get('tipo_sancion', ''))
        # Productos y sus reclamos e involuc
        for i, prod in enumerate(data.get('productos', [])):
            if i >= len(self.product_frames):
                self.add_product()
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
            pframe.canal_var.set(prod.get('canal', CANAL_LIST[0]))
            pframe.proceso_var.set(prod.get('proceso', PROCESO_LIST[0]))
            pframe.fecha_oc_var.set(prod.get('fecha_ocurrencia', ''))
            pframe.fecha_desc_var.set(prod.get('fecha_descubrimiento', ''))
            pframe.monto_inv_var.set(prod.get('monto_investigado', ''))
            pframe.moneda_var.set(prod.get('tipo_moneda', TIPO_MONEDA_LIST[0]))
            pframe.monto_perdida_var.set(prod.get('monto_perdida_fraude', ''))
            pframe.monto_falla_var.set(prod.get('monto_falla_procesos', ''))
            pframe.monto_cont_var.set(prod.get('monto_contingencia', ''))
            pframe.monto_rec_var.set(prod.get('monto_recuperado', ''))
            pframe.monto_pago_var.set(prod.get('monto_pago_deuda', ''))
            tipo_producto = prod.get('tipo_producto')
            if tipo_producto in TIPO_PRODUCTO_LIST:
                pframe.tipo_prod_var.set(tipo_producto)
        # Reclamos
        reclamos = data.get('reclamos', [])
        for rec in reclamos:
            for pframe in self.product_frames:
                if pframe.id_var.get().strip() == rec.get('id_producto'):
                    pframe.id_reclamo_var.set(rec.get('id_reclamo', ''))
                    pframe.nombre_analitica_var.set(rec.get('nombre_analitica', ''))
                    pframe.codigo_analitica_var.set(rec.get('codigo_analitica', ''))
        # Involucramientos
        invols = data.get('involucramientos', [])
        for inv in invols:
            for pframe in self.product_frames:
                if pframe.id_var.get().strip() == inv.get('id_producto'):
                    # agregar asignación a pframe
                    assign = InvolvementRow(pframe.invol_frame, pframe, len(pframe.involvements), pframe.get_team_options, pframe.remove_involvement, self.logs, pframe.tooltip_register)
                    pframe.involvements.append(assign)
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
        # Analisis
        analisis = data.get('analisis', {})
        self.antecedentes_var.set(analisis.get('antecedentes', ''))
        self.modus_var.set(analisis.get('modus_operandi', ''))
        self.hallazgos_var.set(analisis.get('hallazgos', ''))
        self.descargos_var.set(analisis.get('descargos', ''))
        self.conclusiones_var.set(analisis.get('conclusiones', ''))
        self.recomendaciones_var.set(analisis.get('recomendaciones', ''))

    # ---------------------------------------------------------------------
    # Validación de reglas de negocio

    def validate_data(self):
        """Valida los datos del formulario y retorna lista de errores."""
        errors = []
        # Validar número de caso
        id_caso = self.id_caso_var.get().strip()
        if not id_caso:
            errors.append("Debe ingresar el número de caso.")
        # Validar duplicidad del key técnico (caso, producto, cliente, colaborador, fecha ocurrencia, reclamo)
        key_set = set()
        product_client_map = {}
        total_investigado = Decimal('0')
        total_componentes = Decimal('0')
        for idx, tm in enumerate(self.team_frames, start=1):
            division = tm.division_var.get().strip().lower()
            area = tm.area_var.get().strip().lower()
            division_norm = division.replace('á', 'a').replace('é', 'e').replace('ó', 'o')
            area_norm = area.replace('á', 'a').replace('é', 'e').replace('ó', 'o')
            needs_agency = (
                'dca' in division_norm or 'canales de atencion' in division_norm
            ) and ('area comercial' in area_norm)
            if needs_agency:
                if not tm.nombre_agencia_var.get().strip() or not tm.codigo_agencia_var.get().strip():
                    errors.append(
                        f"El colaborador {idx} debe registrar nombre y código de agencia por pertenecer a canales comerciales."
                    )
        for p in self.product_frames:
            prod_data = p.get_data()
            pid = prod_data['producto']['id_producto']
            cid = prod_data['producto']['id_cliente']
            if pid in product_client_map:
                prev_client = product_client_map[pid]
                if prev_client != cid:
                    errors.append(
                        f"El producto {pid} está asociado a dos clientes distintos ({prev_client} y {cid})."
                    )
                else:
                    errors.append(f"El producto {pid} está duplicado en el formulario.")
            else:
                product_client_map[pid] = cid
            # For each involvement; if no assignments, use empty string for id_colaborador
            if not prod_data['asignaciones']:
                # still need to check combination with blank collaborator
                key = (id_caso, pid, cid, '', prod_data['producto']['fecha_ocurrencia'], prod_data['reclamo']['id_reclamo'])
                if key in key_set:
                    errors.append(f"Registro duplicado de clave técnica (producto {pid})")
                key_set.add(key)
            for inv in prod_data['asignaciones']:
                key = (id_caso, pid, cid, inv['id_colaborador'], prod_data['producto']['fecha_ocurrencia'], prod_data['reclamo']['id_reclamo'])
                if key in key_set:
                    errors.append(f"Registro duplicado de clave técnica (producto {pid}, colaborador {inv['id_colaborador']})")
                key_set.add(key)
        # Validar fechas y montos por producto
        for p in self.product_frames:
            data = p.get_data()
            producto = data['producto']
            # Fechas
            try:
                occ = datetime.strptime(producto['fecha_ocurrencia'], "%Y-%m-%d")
                desc = datetime.strptime(producto['fecha_descubrimiento'], "%Y-%m-%d")
                if occ > desc:
                    errors.append(f"La fecha de ocurrencia debe ser anterior a la de descubrimiento en el producto {producto['id_producto']}")
                if occ > datetime.now() or desc > datetime.now():
                    errors.append(f"Las fechas del producto {producto['id_producto']} no pueden ser futuras")
            except ValueError:
                errors.append(f"Fechas inválidas en el producto {producto['id_producto']}")
            # Montos
            m_inv = parse_decimal_amount(producto['monto_investigado'])
            m_perd = parse_decimal_amount(producto['monto_perdida_fraude'])
            m_fall = parse_decimal_amount(producto['monto_falla_procesos'])
            m_cont = parse_decimal_amount(producto['monto_contingencia'])
            m_rec = parse_decimal_amount(producto['monto_recuperado'])
            m_pago = parse_decimal_amount(producto['monto_pago_deuda'])
            if m_inv is None or m_perd is None or m_fall is None or m_cont is None or m_rec is None or m_pago is None:
                errors.append(f"Valores numéricos inválidos en el producto {producto['id_producto']}")
                continue
            if abs((m_perd + m_fall + m_cont + m_rec) - m_inv) > Decimal('0.01'):
                errors.append(
                    f"La suma de pérdida, falla, contingencia y recupero debe ser igual al monto investigado en el producto {producto['id_producto']}"
                )
            if m_pago > m_inv:
                errors.append(f"El monto pagado de deuda excede el monto investigado en el producto {producto['id_producto']}")
            total_investigado += m_inv
            total_componentes += (m_perd + m_fall + m_cont + m_rec)
            # Reclamo y analíticas
            if (m_perd > 0 or m_fall > 0 or m_cont > 0) and (not data['reclamo']['id_reclamo'] or not data['reclamo']['nombre_analitica'] or not data['reclamo']['codigo_analitica']):
                errors.append(f"Debe ingresar reclamo y analítica completa en el producto {producto['id_producto']} porque hay montos de pérdida, falla o contingencia")
            # Código analítica
            cod_anal = data['reclamo']['codigo_analitica']
            if cod_anal:
                if not (cod_anal.isdigit() and len(cod_anal) == 10 and cod_anal.startswith(('43','45','46','56'))):
                    errors.append(f"Código analítica inválido en el producto {producto['id_producto']}")
            # Longitud id_producto
            pid_len = len(producto['id_producto'])
            if not (pid_len in (13,14,16,20) or pid_len > 100):
                errors.append(f"Longitud del ID de producto {producto['id_producto']} debe ser 13,14,16,20 o mayor a 100")
            # Tipo producto vs contingencia
            tipo_prod = producto['tipo_producto'].lower()
            if any(word in tipo_prod for word in ['crédito', 'tarjeta']):
                if abs(m_cont - m_inv) > Decimal('0.01'):
                    errors.append(f"El monto de contingencia debe ser igual al monto investigado en el producto {producto['id_producto']} porque es un crédito o tarjeta")
            # Fraude externo
            if producto['categoria2'] == 'Fraude Externo':
                messagebox.showwarning("Fraude Externo", f"Producto {producto['id_producto']} con categoría 2 'Fraude Externo': verifique la analítica registrada.")
        if self.product_frames and abs(total_componentes - total_investigado) > Decimal('0.01'):
            errors.append("La suma total de pérdidas, fallas, contingencias y recuperos no coincide con el total investigado del caso.")
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
                parse_decimal_amount(p.get_data()['producto']['monto_perdida_fraude']) > Decimal('0') or
                parse_decimal_amount(p.get_data()['producto']['monto_contingencia']) > Decimal('0')
                for p in self.product_frames
            )
            any_sanction = any(
                t.tipo_sancion_var.get() not in ('No aplica', '')
                for t in self.team_frames
            )
            if any_loss or any_sanction:
                errors.append("No se puede seleccionar tipo de informe 'Interno' si hay pérdidas, contingencias o sanciones registradas.")
        # Validar riesgos
        risk_ids = set()
        plan_ids = set()
        for r in self.risk_frames:
            rd = r.get_data()
            rid = rd['id_riesgo']
            if not re.match(r"^RSK-\d{6,10}$", rid):
                errors.append(f"ID de riesgo {rid} no sigue el formato RSK-XXXXXX (6-10 dígitos)")
            if rid in risk_ids:
                errors.append(f"ID de riesgo duplicado: {rid}")
            risk_ids.add(rid)
            # Exposición
            try:
                if rd['exposicion_residual']:
                    float(rd['exposicion_residual'])
            except ValueError:
                errors.append(f"Exposición residual inválida en el riesgo {rid}")
            # Planes de acción
            for plan in [p.strip() for p in rd['planes_accion'].split(';') if p.strip()]:
                if plan in plan_ids:
                    errors.append(f"Plan de acción {plan} duplicado entre riesgos")
                plan_ids.add(plan)
        # Validar normas
        norm_ids = set()
        for n in self.norm_frames:
            nd = n.get_data()
            nid = nd['id_norma']
            if nid:
                # Debe seguir formato de números con puntos
                import re
                if not re.match(r'\d{4}\.\d{3}\.\d{2}\.\d{2}$', nid):
                    errors.append(f"ID de norma {nid} no tiene el formato XXXX.XXX.XX.XX")
                if nid in norm_ids:
                    errors.append(f"ID de norma duplicado: {nid}")
                norm_ids.add(nid)
            # Fecha vigencia
            fvig = nd['fecha_vigencia']
            if fvig:
                try:
                    fv = datetime.strptime(fvig, "%Y-%m-%d")
                    if fv > datetime.now():
                        errors.append(f"Fecha de vigencia futura en norma {nid or 'sin ID'}")
                except ValueError:
                    errors.append(f"Fecha de vigencia inválida en norma {nid or 'sin ID'}")
        return errors

    # ---------------------------------------------------------------------
    # Exportación de datos

    def build_markdown_report(self, data):
        """Genera el informe solicitado en formato Markdown."""

        case = data['caso']
        analysis = data['analisis']
        clients = data['clientes']
        team = data['colaboradores']
        products = data['productos']
        riesgos = data['riesgos']
        normas = data['normas']
        total_inv = sum((parse_decimal_amount(p.get('monto_investigado')) or Decimal('0')) for p in products)
        destinatarios = sorted({
            " - ".join(filter(None, [col.get('division', '').strip(), col.get('area', '').strip(), col.get('servicio', '').strip()]))
            for col in team
            if any([col.get('division'), col.get('area'), col.get('servicio')])
        })
        destinatarios = [d for d in destinatarios if d]
        destinatarios_text = ", ".join(destinatarios) if destinatarios else "Sin divisiones registradas"

        def md_table(headers, rows):
            if not rows:
                return ["Sin registros."]
            safe = lambda cell: str(cell or '').replace('|', '\\|')
            lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(['---'] * len(headers)) + " |"]
            for row in rows:
                lines.append("| " + " | ".join(safe(col) for col in row) + " |")
            return lines

        reclamo_por_producto = {r['id_producto']: r for r in data['reclamos']}

        lines = [
            "Banco de Crédito - BCP",
            "SEGURIDAD CORPORATIVA, INVESTIGACIONES & CRIMEN CIBERNÉTICO",
            "INVESTIGACIONES & CIBERCRIMINOLOGÍA",
            f"Informe {case['tipo_informe']} N.{case['id_caso']}",
            f"Dirigido a: {destinatarios_text}",
            (
                "Referencia: "
                f"{len(team)} colaboradores investigados, {len(products)} productos afectados, "
                f"monto investigado total {total_inv:.2f} y modalidad {case['modalidad']}."
            ),
            "",
            "## 1. Antecedentes",
            analysis.get('antecedentes') or "Pendiente",
            "",
            "## 2. Tabla de clientes",
        ]
        client_rows = [
            [
                f"Cliente {idx}",
                client.get('tipo_id', ''),
                client.get('id_cliente', ''),
                client.get('flag', ''),
                client.get('telefonos', ''),
                client.get('correos', ''),
                client.get('direcciones', ''),
                client.get('accionado', ''),
            ]
            for idx, client in enumerate(clients, start=1)
        ]
        lines.extend(md_table([
            "Cliente", "Tipo ID", "ID", "Flag", "Teléfonos", "Correos", "Direcciones", "Accionado"
        ], client_rows))
        lines.extend([
            "",
            "## 3. Tabla de team members involucrados",
        ])
        team_rows = [
            [
                f"Colaborador {idx}",
                col.get('id_colaborador', ''),
                col.get('flag', ''),
                col.get('division', ''),
                col.get('area', ''),
                col.get('servicio', ''),
                col.get('puesto', ''),
                col.get('nombre_agencia', ''),
                col.get('codigo_agencia', ''),
                col.get('tipo_falta', ''),
                col.get('tipo_sancion', ''),
            ]
            for idx, col in enumerate(team, start=1)
        ]
        lines.extend(md_table([
            "Colaborador", "ID", "Flag", "División", "Área", "Servicio", "Puesto", "Agencia", "Código", "Falta", "Sanción"
        ], team_rows))
        lines.extend([
            "",
            "## 4. Tabla de productos combinado",
        ])
        product_rows = []
        for idx, prod in enumerate(products, start=1):
            reclamo = reclamo_por_producto.get(prod['id_producto'], {})
            product_rows.append([
                f"Producto {idx}",
                prod.get('id_producto', ''),
                prod.get('id_cliente', ''),
                prod.get('tipo_producto', ''),
                prod.get('canal', ''),
                prod.get('proceso', ''),
                prod.get('categoria1', ''),
                prod.get('categoria2', ''),
                prod.get('modalidad', ''),
                f"INV:{prod.get('monto_investigado', '')} | PER:{prod.get('monto_perdida_fraude', '')} | FALLA:{prod.get('monto_falla_procesos', '')} | CONT:{prod.get('monto_contingencia', '')} | REC:{prod.get('monto_recuperado', '')} | PAGO:{prod.get('monto_pago_deuda', '')}",
                f"{reclamo.get('id_reclamo', '')} / {reclamo.get('codigo_analitica', '')}",
            ])
        lines.extend(md_table([
            "Registro", "ID", "Cliente", "Tipo", "Canal", "Proceso", "Cat.1", "Cat.2", "Modalidad", "Montos", "Reclamo/Analítica"
        ], product_rows))
        lines.extend([
            "",
            "## 5. Resumen automatizado",
            (
                f"Se documentaron {len(clients)} clientes, {len(team)} colaboradores y {len(products)} productos. "
                f"El caso está tipificado como {case['categoria1']} / {case['categoria2']} en modalidad {case['modalidad']}."
            ),
            "",
            "## 6. Modus Operandi",
            analysis.get('modus_operandi') or "Pendiente",
            "",
            "## 7. Hallazgos Principales",
            analysis.get('hallazgos') or "Pendiente",
            "",
            "## 8. Descargo de colaboradores",
            analysis.get('descargos') or "Pendiente",
            "",
            "## 9. Tabla de riesgos identificados",
        ])
        risk_rows = [
            [
                risk.get('id_riesgo', ''),
                risk.get('lider', ''),
                risk.get('criticidad', ''),
                risk.get('exposicion_residual', ''),
                risk.get('planes_accion', ''),
            ]
            for risk in riesgos
        ]
        lines.extend(md_table([
            "ID Riesgo", "Líder", "Criticidad", "Exposición US$", "Planes"
        ], risk_rows))
        lines.extend([
            "",
            "## 10. Tabla de normas transgredidas",
        ])
        norm_rows = [
            [
                norm.get('id_norma', ''),
                norm.get('descripcion', ''),
                norm.get('fecha_vigencia', ''),
            ]
            for norm in normas
        ]
        lines.extend(md_table([
            "N° de norma", "Descripción", "Fecha de vigencia"
        ], norm_rows))
        lines.extend([
            "",
            "## 11. Conclusiones",
            analysis.get('conclusiones') or "Pendiente",
            "",
            "## 12. Recomendaciones y mejoras de procesos",
            analysis.get('recomendaciones') or "Pendiente",
            "",
        ])
        return "\n".join(lines)

    def save_and_send(self):
        """Valida los datos y guarda CSVs normalizados y JSON en la carpeta elegida."""
        errors = self.validate_data()
        if errors:
            messagebox.showerror("Errores de validación", "\n".join(errors))
            log_event("validacion", f"Errores al guardar: {errors}", self.logs)
            return
        # Seleccionar carpeta de destino
        folder = filedialog.askdirectory(title="Seleccionar carpeta para guardar archivos")
        if not folder:
            return
        # Reunir datos
        data = self.gather_data()
        # Completar claves foráneas con id_caso
        for c in data['clientes']:
            c['id_caso'] = data['caso']['id_caso']
        for t in data['colaboradores']:
            t['id_caso'] = data['caso']['id_caso']
        for p in data['productos']:
            p['id_caso'] = data['caso']['id_caso']
        for r in data['reclamos']:
            r['id_caso'] = data['caso']['id_caso']
        for i in data['involucramientos']:
            i['id_caso'] = data['caso']['id_caso']
        for risk in data['riesgos']:
            risk['id_caso'] = data['caso']['id_caso']
        for norm in data['normas']:
            norm['id_caso'] = data['caso']['id_caso']
        # Guardar CSVs
        case_id = data['caso']['id_caso'] or 'caso'
        def write_csv(file_name, rows, header):
            with open(os.path.join(folder, f"{case_id}_{file_name}"), 'w', newline='', encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
        # CASOS
        write_csv('casos.csv', [data['caso']], ['id_caso', 'tipo_informe', 'categoria1', 'categoria2', 'modalidad', 'canal', 'proceso'])
        # CLIENTES
        write_csv('clientes.csv', data['clientes'], ['id_cliente', 'id_caso', 'tipo_id', 'flag', 'telefonos', 'correos', 'direcciones', 'accionado'])
        # COLABORADORES
        write_csv('colaboradores.csv', data['colaboradores'], ['id_colaborador', 'id_caso', 'flag', 'division', 'area', 'servicio', 'puesto', 'nombre_agencia', 'codigo_agencia', 'tipo_falta', 'tipo_sancion'])
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
        write_csv('analisis.csv', [dict({'id_caso': data['caso']['id_caso']}, **data['analisis'])], ['id_caso', 'antecedentes', 'modus_operandi', 'hallazgos', 'descargos', 'conclusiones', 'recomendaciones'])
        # LOGS
        write_csv('logs.csv', self.logs, ['timestamp', 'tipo', 'mensaje'])
        # Guardar JSON
        with open(os.path.join(folder, f"{case_id}_version.json"), 'w', encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Guardar informe Markdown
        report_path = os.path.join(folder, f"{case_id}_informe.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self.build_markdown_report(data))
        messagebox.showinfo(
            "Datos guardados",
            f"Los archivos se han guardado como {case_id}_*.csv, {case_id}_version.json y {case_id}_informe.md.",
        )
        log_event("navegacion", "Datos guardados y enviados", self.logs)

    def save_temp_version(self):
        """Guarda una versión temporal del estado actual del formulario.

        Este método recoge los datos actuales mediante ``gather_data`` y los
        escribe en un archivo JSON con un sufijo de marca de tiempo. El
        fichero se guarda en el mismo directorio que el script y se nombra
        ``<id_caso>_temp_<YYYYMMDD_HHMMSS>.json``. Si no se ha especificado
        un ID de caso todavía, se utiliza ``caso`` como prefijo. La función
        se invoca automáticamente desde ``log_event`` cada vez que el usuario
        edita un campo (evento de navegación).

        Examples:
            >>> app.save_temp_version()
            # Crea un archivo como ``2025-0001_temp_20251114_154501.json`` con
            # el contenido completo del formulario.
        """
        data = self.gather_data()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        case_id = data.get('caso', {}).get('id_caso', '') or 'caso'
        filename = f"{case_id}_temp_{timestamp}.json"
        try:
            path = os.path.join(os.path.dirname(__file__), filename)
            with open(path, 'w', encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as ex:
            # Registrar en el log pero no interrumpir
            log_event("validacion", f"Error guardando versión temporal: {ex}", self.logs)


# ---------------------------------------------------------------------------
# Ejecución de la aplicación

if __name__ == '__main__':
    root = tk.Tk()
    app = FraudCaseApp(root)
    root.mainloop()