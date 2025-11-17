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
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from functools import partial
import random

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

BASE_DIR = os.path.dirname(__file__)

# Archivo con detalles de colaboradores para autopoblado
TEAM_DETAILS_FILE = os.path.join(BASE_DIR, "team_details.csv")
# Archivo con detalles de clientes para autopoblado
CLIENT_DETAILS_FILE = os.path.join(BASE_DIR, "client_details.csv")
# Archivo con detalles de productos para autopoblado
PRODUCT_DETAILS_FILE = os.path.join(BASE_DIR, "productos_masivos.csv")

# Ruta de autosave
AUTOSAVE_FILE = os.path.join(BASE_DIR, "autosave.json")

# Ruta de logs si se desea guardar de forma permanente
LOGS_FILE = os.path.join(BASE_DIR, "logs.csv")

# Archivos de carga masiva disponibles en el repositorio
MASSIVE_SAMPLE_FILES = {
    "clientes": os.path.join(BASE_DIR, "clientes_masivos.csv"),
    "colaboradores": os.path.join(BASE_DIR, "colaboradores_masivos.csv"),
    "productos": os.path.join(BASE_DIR, "productos_masivos.csv"),
    "riesgos": os.path.join(BASE_DIR, "riesgos_masivos.csv"),
    "normas": os.path.join(BASE_DIR, "normas_masivas.csv"),
    "reclamos": os.path.join(BASE_DIR, "reclamos_masivos.csv"),
    "combinado": os.path.join(BASE_DIR, "datos_combinados_masivos.csv"),
}

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

# Encabezados alternos utilizados durante la hidratación de filas masivas
CLIENT_ID_ALIASES = ("IdCliente", "IDCliente")
TEAM_ID_ALIASES = ("IdColaborador", "IdTeamMember", "IDColaborador", "Id")
PRODUCT_ID_ALIASES = ("IdProducto", "IDProducto")
RISK_ID_ALIASES = ("IdRiesgo", "IDRiesgo")
NORM_ID_ALIASES = ("IdNorma", "IDNorma")
CLAIM_ID_ALIASES = ("IdReclamo", "IDReclamo")

# Catálogos auxiliares: permiten mapear alias provenientes de archivos
# ``*_details.csv`` con la clave canónica utilizada en el formulario.
DETAIL_LOOKUP_ALIASES = {
    "id_cliente": ("clientes", "cliente", "clients", "client"),
    "id_colaborador": ("colaboradores", "colaborador", "team", "teams"),
    "id_producto": ("productos", "producto", "product", "products"),
    "id_riesgo": ("riesgos", "riesgo", "risk", "risks"),
    "id_norma": ("normas", "norma", "rule", "rules"),
}


def normalize_detail_catalog_key(key):
    """Normaliza una clave de catálogo de detalle a minúsculas sin espacios."""

    return (key or "").strip().lower()


# ---------------------------------------------------------------------------
# Funciones de utilidad

def load_detail_catalogs():
    """Lee todos los archivos ``*_details.csv`` disponibles en la carpeta base.

    Devuelve un diccionario con la forma ``{nombre_archivo: {id: fila}}``.
    Cada fila conserva todos los campos del CSV para poder reutilizarlos como
    autopoblado o enriquecimiento posterior.
    """

    catalogs = {}
    try:
        filenames = [
            name
            for name in os.listdir(BASE_DIR)
            if name.lower().endswith("details.csv")
        ]
    except OSError:
        return catalogs

    for filename in filenames:
        path = os.path.join(BASE_DIR, filename)
        entity_name = filename[:-len("_details.csv")].lower()
        try:
            with open(path, newline='', encoding="utf-8-sig") as f:
                reader = csv.DictReader(line for line in f if line.strip())
                fieldnames = reader.fieldnames or []
                key_field = next(
                    (field for field in fieldnames if field and field.lower().startswith("id_")),
                    None,
                )
                if not key_field:
                    continue
                for row in reader:
                    key = (row.get(key_field) or "").strip()
                    if not key:
                        continue
                    catalogs.setdefault(entity_name, {})[key] = {
                        (k or ""): (v or "").strip() for k, v in row.items()
                    }
        except FileNotFoundError:
            continue
        except OSError:
            continue
    return catalogs

def load_team_details():
    """Carga los datos de colaboradores desde team_details.csv si existe.

    Devuelve un diccionario donde la clave es el ID del colaborador y el
    valor es un diccionario con las claves: division, area, servicio,
    puesto, nombre_agencia, codigo_agencia.
    """
    lookup = {}
    try:
        with open(TEAM_DETAILS_FILE, newline='', encoding="utf-8-sig") as f:
            reader = csv.DictReader(line for line in f if line.strip())
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
        with open(CLIENT_DETAILS_FILE, newline='', encoding="utf-8-sig") as f:
            reader = csv.DictReader(line for line in f if line.strip())
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
        with open(PRODUCT_DETAILS_FILE, newline='', encoding="utf-8-sig") as f:
            reader = csv.DictReader(line for line in f if line.strip())
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
                    "reclamos": [],
                }
                claim_payload = {
                    "id_reclamo": lookup[key]["id_reclamo"],
                    "nombre_analitica": lookup[key]["nombre_analitica"],
                    "codigo_analitica": lookup[key]["codigo_analitica"],
                }
                if any(value for value in claim_payload.values()):
                    lookup[key]["reclamos"] = [claim_payload]
    except FileNotFoundError:
        pass
    return lookup


def iter_massive_csv_rows(filename):
    """Yield rows from a CSV file used for carga masiva.

    The helper normalizes the reading of the repository-provided
    ``*_masivos.csv`` files by:

    * Opening the file with ``utf-8-sig`` so BOM markers are ignored.
    * Skipping empty lines that some samples use for spacing.
    * Stripping whitespace from headers and values to prevent subtle
      mismatches (e.g., ``" id_cliente"`` vs ``"id_cliente"``).

    Args:
        filename (str): Absolute path to the CSV file.

    Yields:
        dict[str, str]: Normalized row ready to consumir.
    """

    with open(filename, newline='', encoding="utf-8-sig") as handle:
        reader = csv.DictReader(line for line in handle if line.strip())
        for row in reader:
            cleaned = {}
            for key, value in row.items():
                if key is None:
                    continue
                key = key.strip()
                if isinstance(value, str):
                    value = value.strip()
                cleaned[key] = value
            if cleaned:
                yield cleaned


def parse_involvement_entries(raw_value):
    """Parse the ``involucramiento`` column from the combinado CSV."""

    if not raw_value:
        return []
    entries = []
    if isinstance(raw_value, (list, tuple)):
        raw_value = ";".join(raw_value)
    for chunk in str(raw_value).split(';'):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ':' in chunk:
            collaborator, amount = chunk.split(':', 1)
        else:
            collaborator, amount = chunk, ''
        collaborator = collaborator.strip()
        amount = amount.strip()
        if collaborator:
            entries.append((collaborator, amount))
    return entries


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


def validate_product_dates(producto_id, fecha_ocurrencia, fecha_descubrimiento):
    """Valida coherencia entre fechas y evita registros futuros."""

    label = (producto_id or "sin ID").strip() or "sin ID"
    occ_text = (fecha_ocurrencia or "").strip()
    desc_text = (fecha_descubrimiento or "").strip()
    if not occ_text or not desc_text:
        return f"Fechas inválidas en el producto {label}"
    try:
        occ = datetime.strptime(occ_text, "%Y-%m-%d")
        desc = datetime.strptime(desc_text, "%Y-%m-%d")
    except ValueError:
        return f"Fechas inválidas en el producto {label}"
    if occ >= desc:
        message = (
            f"La fecha de ocurrencia debe ser anterior a la de descubrimiento en el producto {label}"
        )
        if occ == desc:
            try:
                messagebox.showerror(
                    "Fechas del producto",
                    (
                        f"Producto {label}: la fecha de ocurrencia debe ser "
                        "estrictamente previa a la de descubrimiento."
                    ),
                )
            except tk.TclError:
                pass
        return message
    now = datetime.now()
    if occ > now or desc > now:
        return f"Las fechas del producto {label} no pueden ser futuras"
    return None


MONEY_PATTERN = re.compile(r"^(?P<int>\d{1,12})([\.,](?P<dec>\d{1,2}))?$")
TWO_DECIMALS = Decimal("0.01")


def validate_money_bounds(value, label, allow_blank=True):
    """Valida montos monetarios y retorna ``(mensaje_error, Decimal|None)``.

    Se restringen a valores positivos o cero, con hasta 12 dígitos enteros y
    dos decimales como máximo. Si el campo se deja vacío y ``allow_blank`` es
    ``True`` se considera válido y se devuelve ``None`` para el valor
    normalizado. La cuantización usa un ``localcontext`` con precisión mínima
    de 16 dígitos y redondeo ``ROUND_HALF_UP`` para evitar ``InvalidOperation``
    al normalizar montos de hasta 12 enteros y dos decimales.
    """

    text = (value or "").strip()
    if not text:
        return (None, None) if allow_blank else (f"Debe ingresar {label}.", None)

    normalized = text.replace(",", ".")
    match = MONEY_PATTERN.match(normalized)
    if not match:
        return (
            f"{label} debe ser ≥ 0 y tener dos decimales (máximo 12 dígitos enteros).",
            None,
        )

    decimal_part = match.group("dec") or ""
    if len(decimal_part) > 2:
        return (
            f"{label} debe ser ≥ 0 y tener dos decimales (máximo 12 dígitos enteros).",
            None,
        )

    try:
        with localcontext() as ctx:
            ctx.prec = max(ctx.prec, 16)
            ctx.rounding = ROUND_HALF_UP
            decimal_value = Decimal(normalized).quantize(
                TWO_DECIMALS, rounding=ROUND_HALF_UP
            )
    except InvalidOperation:
        return (
            f"{label} debe ser ≥ 0 y tener dos decimales (máximo 12 dígitos enteros).",
            None,
        )

    return None, decimal_value


def validate_amount_text(value, label, allow_blank=True):
    """Valida que los montos sean numéricos en formato monetario estándar."""

    message, _ = validate_money_bounds(value, label, allow_blank=allow_blank)
    return message


def sum_investigation_components(*, perdida, falla, contingencia, recuperado):
    """Devuelve la suma de las cuatro partidas monetarias del producto/caso."""

    return perdida + falla + contingencia + recuperado


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


def validate_risk_id(value):
    """Valida el identificador de riesgo ``RSK-XXXXXX``."""

    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID de riesgo."
    if not re.fullmatch(r"RSK-\d{6}", text):
        return "El ID de riesgo debe seguir el formato RSK-XXXXXX."
    return None


def validate_multi_selection(value, label):
    """Valida que exista al menos una selección en campos multiselección."""
    if not value.strip():
        return f"Debe seleccionar al menos una opción en {label}."
    return None


CLIENT_ID_PATTERNS = {
    "dni": (re.compile(r"^\d{8}$"), "El DNI debe tener exactamente 8 dígitos."),
    "ruc": (re.compile(r"^\d{11}$"), "El RUC debe tener exactamente 11 dígitos."),
    "pasaporte": (
        re.compile(r"^[A-Za-z0-9]{9,12}$"),
        "El pasaporte debe ser alfanumérico y tener entre 9 y 12 caracteres.",
    ),
    "carné de extranjería": (
        re.compile(r"^[A-Za-z0-9]{9,12}$"),
        "El carné de extranjería debe ser alfanumérico y tener entre 9 y 12 caracteres.",
    ),
}

TEAM_MEMBER_ID_PATTERN = re.compile(r"^[A-Za-z][0-9]{5}$")
AGENCY_CODE_PATTERN = re.compile(r"^\d{6}$")
PRODUCT_CREDIT_LENGTHS = {13, 14, 16, 20}


def normalize_without_accents(value):
    """Devuelve el texto sin tildes para facilitar las comparaciones lógicas."""

    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


# Conjunto/diccionario normalizado para validar tipos de producto sin importar tildes o mayúsculas
TIPO_PRODUCTO_CATALOG = {
    normalize_without_accents(item).lower(): item
    for item in TIPO_PRODUCTO_LIST
}
TIPO_PRODUCTO_NORMALIZED = set(TIPO_PRODUCTO_CATALOG.keys())


def validate_client_id(tipo_id, value):
    """Valida el ID del cliente de acuerdo con el tipo de documento (Diseño CM)."""

    tipo = (tipo_id or "").strip().lower()
    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID del cliente."
    pattern_data = CLIENT_ID_PATTERNS.get(tipo)
    if pattern_data and not pattern_data[0].fullmatch(text):
        return pattern_data[1]
    if not pattern_data and len(text) < 4:
        return "El ID del cliente debe tener al menos 4 caracteres."
    return None


def validate_team_member_id(value):
    """Valida el código de colaborador (letra + 5 dígitos)."""

    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID del colaborador."
    if not TEAM_MEMBER_ID_PATTERN.fullmatch(text):
        return "El ID del colaborador debe iniciar con una letra seguida de 5 dígitos."
    return None


def validate_agency_code(value, allow_blank=True):
    """Valida que el código de agencia tenga exactamente 6 dígitos."""

    text = (value or "").strip()
    if not text:
        return None if allow_blank else "Debe ingresar el código de agencia."
    if not AGENCY_CODE_PATTERN.fullmatch(text):
        return "El código de agencia debe tener exactamente 6 dígitos."
    return None


def resolve_catalog_product_type(value):
    """Devuelve el nombre oficial del catálogo para ``value`` o ``None`` si no existe."""

    normalized = normalize_without_accents((value or "").strip()).lower()
    if not normalized:
        return None
    return TIPO_PRODUCTO_CATALOG.get(normalized)


def validate_product_id(tipo_producto, value):
    """Valida el ID del producto según el tipo comercial indicado."""

    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID del producto."
    tipo_normalized = normalize_without_accents((tipo_producto or "").strip()).lower()
    if "tarjeta" in tipo_normalized:
        if not (text.isdigit() and len(text) == 16):
            return "Para tarjetas el ID debe ser numérico de 16 dígitos."
        return None
    if "credito" in tipo_normalized:
        if not (text.isdigit() and len(text) in PRODUCT_CREDIT_LENGTHS):
            return "Para créditos el ID debe ser numérico de 13, 14, 16 o 20 dígitos."
        return None
    if len(text) not in PRODUCT_CREDIT_LENGTHS and len(text) <= 100:
        return "El ID del producto debe tener 13, 14, 16, 20 o más de 100 caracteres."
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
        self._suspend_count = 0
        # La validación sólo debe activarse tras una interacción del usuario.
        # Hasta entonces se ignoran los callbacks de ``trace_add`` generados
        # por el auto‑poblamiento inicial para evitar mensajes al arrancar.
        self._validation_armed = False
        for var in self.variables:
            self._traces.append(var.trace_add("write", self._on_change))
        widget.bind("<FocusOut>", self._on_change)
        widget.bind("<KeyRelease>", self._on_change)
        if isinstance(widget, ttk.Combobox):
            widget.bind("<<ComboboxSelected>>", self._on_change)

    def _on_change(self, *_args):
        """Ejecuta la validación y actualiza el tooltip sólo si cambió el estado."""
        if self._suspend_count > 0:
            return
        event = _args[0] if _args else None
        is_user_event = hasattr(event, "widget")
        if is_user_event:
            self._validation_armed = True
        elif not self._validation_armed:
            # Se trata de un ``trace_add`` disparado antes de cualquier edición
            # del usuario, por lo que se ignora para no mostrar alertas.
            return
        error = self.validate_callback()
        self._display_error(error)

    def _display_error(self, error):
        """Muestra u oculta el mensaje si cambió."""
        if error == self.last_error:
            return
        if error:
            self.tooltip.show(error)
            log_event("validacion", f"{self.field_name}: {error}", self.logs)
        else:
            self.tooltip.hide()
        self.last_error = error

    def show_custom_error(self, message):
        """Permite forzar un mensaje específico tras una actualización programática."""
        self._validation_armed = True
        self._display_error(message)

    def suppress_during(self, callback):
        """Ejecuta ``callback`` evitando que se dispare la validación automática."""
        self._suspend_count += 1
        try:
            return callback()
        finally:
            self._suspend_count -= 1



def parse_decimal_amount(amount_string):
    """Convierte cadenas monetarias a ``Decimal`` usando ``validate_money_bounds``."""

    message, value = validate_money_bounds(amount_string or "", "monto", allow_blank=True)
    if message:
        return None
    return value or Decimal('0')


def should_autofill_field(current_value, preserve_existing):
    """Determina si se debe sobrescribir un campo durante el autopoblado.

    Args:
        current_value: Valor actual del campo (por lo general un ``str``).
        preserve_existing (bool): Cuando es ``True`` sólo se permite escribir si
            el campo está vacío o contiene únicamente espacios en blanco. Si es
            ``False`` se mantiene el comportamiento tradicional y siempre se
            sobrescribe.

    Returns:
        bool: ``True`` si corresponde autopoblar el campo, ``False`` en caso
        contrario.
    """

    if not preserve_existing:
        return True
    if current_value is None:
        return True
    if isinstance(current_value, str):
        return not current_value.strip()
    return False
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
    ):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.update_client_options = update_client_options
        self.logs = logs
        self.tooltip_register = tooltip_register
        # Diccionario con datos de clientes para autopoblado
        self.client_lookup = client_lookup or {}
        self.validators = []
        self._last_missing_lookup_id = None
        self.schedule_summary_refresh = summary_refresh_callback or (lambda: None)

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
        id_entry.bind("<FocusOut>", lambda e: self.on_id_change(from_focus=True))
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
                lambda: validate_client_id(self.tipo_id_var.get(), self.id_var.get()),
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
                self.accionado_listbox,
                lambda: validate_multi_selection(self.accionado_var.get(), "Accionado"),
                self.logs,
                f"Cliente {self.idx+1} - Accionado",
                variables=[self.accionado_var],
            )
        )

    def on_id_change(self, from_focus=False, preserve_existing=False):
        """Cuando cambia el ID, actualiza las listas dependientes."""
        # Registrar evento
        log_event("navegacion", f"Cliente {self.idx+1}: cambió ID a {self.id_var.get()}", self.logs)
        # Actualizar los desplegables de clientes en productos
        self.update_client_options()
        # Autopoblar datos si el ID existe en client_lookup
        cid = self.id_var.get().strip()
        if not cid:
            self._last_missing_lookup_id = None
            self.schedule_summary_refresh()
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
            log_event("navegacion", f"Autopoblado datos del cliente {cid}", self.logs)
        elif from_focus and self.client_lookup:
            if self._last_missing_lookup_id != cid:
                messagebox.showerror(
                    "Cliente no encontrado",
                    (
                        f"El ID {cid} no existe en los catálogos de detalle. "
                        "Verifica el documento o actualiza client_details.csv."
                    ),
                )
                self._last_missing_lookup_id = cid
        self.schedule_summary_refresh()

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

    def __init__(
        self,
        parent,
        idx,
        remove_callback,
        update_team_options,
        team_lookup,
        logs,
        tooltip_register,
        summary_refresh_callback=None,
    ):
        self.parent = parent
        self.idx = idx
        self.remove_callback = remove_callback
        self.update_team_options = update_team_options
        self.team_lookup = team_lookup
        self.logs = logs
        self.tooltip_register = tooltip_register
        self.validators = []
        self._last_missing_lookup_id = None
        self.schedule_summary_refresh = summary_refresh_callback or (lambda: None)

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
        id_entry.bind("<FocusOut>", lambda e: self.on_id_change(from_focus=True))
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
                lambda: validate_agency_code(self.codigo_agencia_var.get(), allow_blank=True),
                self.logs,
                f"Colaborador {self.idx+1} - Código agencia",
                variables=[self.codigo_agencia_var],
            )
        )

    def on_id_change(self, from_focus=False, preserve_existing=False):
        """Se ejecuta al salir del campo ID: autopuebla y actualiza listas."""
        cid = self.id_var.get().strip()
        if cid:
            # Autopoblado si existe en lookup
            data = self.team_lookup.get(cid)
            if data:
                def set_if_present(var, key):
                    value = data.get(key, "").strip()
                    if value and should_autofill_field(var.get(), preserve_existing):
                        var.set(value)

                set_if_present(self.division_var, "division")
                set_if_present(self.area_var, "area")
                set_if_present(self.servicio_var, "servicio")
                set_if_present(self.puesto_var, "puesto")
                set_if_present(self.nombre_agencia_var, "nombre_agencia")
                set_if_present(self.codigo_agencia_var, "codigo_agencia")
                self._last_missing_lookup_id = None
                log_event("navegacion", f"Autopoblado colaborador {self.idx+1} desde team_details.csv", self.logs)
            elif from_focus and self.team_lookup:
                log_event("validacion", f"ID de colaborador {cid} no encontrado en team_details.csv", self.logs)
                if self._last_missing_lookup_id != cid:
                    messagebox.showerror(
                        "Colaborador no encontrado",
                        (
                            f"El ID {cid} no existe en el catálogo team_details.csv. "
                            "Verifica el código o actualiza el archivo maestro."
                        ),
                    )
                    self._last_missing_lookup_id = cid
        else:
            self._last_missing_lookup_id = None
        # Actualizar desplegables de colaboradores
        self.update_team_options()
        self.schedule_summary_refresh()

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
            log_event(
                "navegacion",
                f"Se eliminó reclamo del producto {self.product_frame.idx+1}",
                self.logs,
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
        self.schedule_summary_refresh = summary_refresh_callback or (lambda: None)

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
        # Contenedor
        self.frame = ttk.LabelFrame(parent, text=f"Producto {self.idx+1}")
        self.frame.pack(fill="x", padx=5, pady=2)

        # Fila 1: ID, Cliente
        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", pady=1)
        ttk.Label(row1, text="ID del producto:").pack(side="left")
        id_entry = ttk.Entry(row1, textvariable=self.id_var, width=20)
        id_entry.pack(side="left", padx=5)
        id_entry.bind("<FocusOut>", lambda e: self.on_id_change(from_focus=True))
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
        cat1_cb.bind("<FocusOut>", lambda e: self.on_cat1_change())
        cat1_cb.bind("<<ComboboxSelected>>", lambda e: self.on_cat1_change())
        self.tooltip_register(cat1_cb, "Define la categoría principal del riesgo de producto.")
        ttk.Label(row2, text="Categoría 2:").pack(side="left")
        self.cat2_cb = ttk.Combobox(row2, textvariable=self.cat2_var, values=first_subcats, state="readonly", width=20)
        self.cat2_cb.pack(side="left", padx=5)
        self.cat2_cb.bind("<FocusOut>", lambda e: self.on_cat2_change())
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

        # Fila 6: Reclamos
        row6 = ttk.Frame(self.frame)
        row6.pack(fill="x", pady=1)
        ttk.Label(row6, text="Reclamos asociados:").pack(side="left")
        add_claim_btn = ttk.Button(row6, text="Agregar reclamo", command=self.add_claim)
        add_claim_btn.pack(side="right")
        self.tooltip_register(add_claim_btn, "Añade otro reclamo vinculado a este producto.")
        self.claims_frame = ttk.Frame(self.frame)
        self.claims_frame.pack(fill="x", pady=1)

        critical_widgets = [
            id_entry,
            self.client_cb,
            cat1_cb,
            self.cat2_cb,
            self.mod_cb,
            canal_cb,
            proc_cb,
            tipo_prod_cb,
            focc_entry,
            fdesc_entry,
            m_inv_entry,
            moneda_cb,
            m_perdida_entry,
            m_falla_entry,
            m_cont_entry,
            m_rec_entry,
            m_pago_entry,
        ]
        for widget in critical_widgets:
            self._register_lookup_sync(widget)

        # Fila 7: Asignaciones de colaboradores (involucramiento)
        row7 = ttk.Frame(self.frame)
        row7.pack(fill="x", pady=1)
        ttk.Label(row7, text="Asignaciones a colaboradores:").pack(side="left")
        self.invol_frame = ttk.Frame(self.frame)
        self.invol_frame.pack(fill="x", pady=1)
        add_inv_btn = ttk.Button(row7, text="Agregar asignación", command=self.add_involvement)
        add_inv_btn.pack(side="right")
        self.tooltip_register(add_inv_btn, "Crea otra relación producto-colaborador.")

        # Inicialmente sin reclamos ni asignaciones
        self.add_claim()
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
        self.validators.append(self.client_validator)
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
                tipo_prod_cb,
                lambda: validate_required_text(self.tipo_prod_var.get(), "el tipo de producto"),
                self.logs,
                f"Producto {self.idx+1} - Tipo de producto",
                variables=[self.tipo_prod_var],
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

    def add_claim(self):
        """Crea una nueva fila de reclamo para el producto."""
        idx = len(self.claims)
        row = ClaimRow(self.claims_frame, self, idx, self.remove_claim, self.logs, self.tooltip_register)
        self.claims.append(row)
        self.schedule_summary_refresh()
        self.persist_lookup_snapshot()
        return row

    def remove_claim(self, row):
        if row in self.claims:
            self.claims.remove(row)
        if not self.claims:
            self.add_claim()
        self.schedule_summary_refresh()
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
        self.schedule_summary_refresh()
        self.persist_lookup_snapshot()

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
        """Añade una fila de asignación de colaborador a este producto."""
        idx = len(self.involvements)
        row = InvolvementRow(self.invol_frame, self, idx, self.get_team_options, self.remove_involvement, self.logs, self.tooltip_register)
        self.involvements.append(row)

    def remove_involvement(self, row):
        self.involvements.remove(row)

    def update_client_options(self):
        """Actualiza la lista de clientes en el desplegable."""
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
        """Actualiza las listas de colaboradores en las asignaciones."""
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
        """Guarda en ``product_lookup`` los datos visibles para futuras hidrataciones."""

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

    def on_id_change(self, from_focus=False, preserve_existing=False):
        """Autocompleta el producto cuando se escribe un ID reconocido."""
        pid = self.id_var.get().strip()
        log_event("navegacion", f"Producto {self.idx+1}: modificó ID a {pid}", self.logs)
        if not pid:
            self._last_missing_lookup_id = None
            self.schedule_summary_refresh()
            return
        data = self.product_lookup.get(pid)
        if not data:
            if from_focus and self.product_lookup and self._last_missing_lookup_id != pid:
                messagebox.showerror(
                    "Producto no encontrado",
                    (
                        f"El ID {pid} no existe en los catálogos de detalle. "
                        "Verifica el código o actualiza product_details.csv."
                    ),
                )
                self._last_missing_lookup_id = pid
            self.schedule_summary_refresh()
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
        log_event("navegacion", f"Producto {self.idx+1}: autopoblado desde catálogo", self.logs)
        self.schedule_summary_refresh()
        self.persist_lookup_snapshot()

    def _validate_fecha_descubrimiento(self):
        """Valida la fecha de descubrimiento y su relación con la de ocurrencia."""
        msg = validate_date_text(self.fecha_desc_var.get(), "la fecha de descubrimiento", allow_blank=False)
        if msg:
            return msg
        producto_label = self.id_var.get().strip() or f"Producto {self.idx+1}"
        return validate_product_dates(
            producto_label,
            self.fecha_oc_var.get(),
            self.fecha_desc_var.get(),
        )

    def _validate_montos_consistentes(self):
        """Valida que la distribución de montos sea coherente con la investigación."""
        values = {}
        for _, var_attr, label, allow_blank, key in PRODUCT_MONEY_SPECS:
            raw_value = getattr(self, var_attr).get()
            message, decimal_value = validate_money_bounds(raw_value, label, allow_blank=allow_blank)
            if message:
                return message
            values[key] = decimal_value if decimal_value is not None else Decimal('0')

        componentes = sum_investigation_components(
            perdida=values['perdida'],
            falla=values['falla'],
            contingencia=values['contingencia'],
            recuperado=values['recuperado'],
        )
        if abs(componentes - values['inv']) > Decimal('0.01'):
            return (
                "La suma de las cuatro partidas (pérdida, falla, contingencia y recuperación) "
                "debe ser igual al monto investigado."
            )
        if values['recuperado'] > values['inv']:
            return "El monto recuperado no puede superar el monto investigado."
        if values['pago'] > values['inv']:
            return "El pago de deuda no puede ser mayor al monto investigado."
        tipo_prod = normalize_without_accents(self.tipo_prod_var.get()).lower()
        if any(word in tipo_prod for word in ('credito', 'tarjeta')):
            if abs(values['contingencia'] - values['inv']) > Decimal('0.01'):
                return "El monto de contingencia debe ser igual al monto investigado para créditos o tarjetas."
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
            "reclamos": [claim.get_data() for claim in self.claims],
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
        self._last_exposicion_decimal = None
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
        def _validate_exposure_amount():
            message, decimal_value = validate_money_bounds(
                self.exposicion_var.get(),
                "la exposición residual",
                allow_blank=True,
            )
            self._last_exposicion_decimal = decimal_value
            return message

        self.validators.append(
            FieldValidator(
                expos_entry,
                _validate_exposure_amount,
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
        return validate_risk_id(self.id_var.get())


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
        self._last_validated_risk_exposure_total = Decimal('0')

        def register_tooltip(widget, text):
            if widget is None or not text:
                return None
            tip = HoverTooltip(widget, text)
            self._hover_tooltips.append(tip)
            return tip

        self.register_tooltip = register_tooltip
        # Cargar catálogos para autopoblado conservando los valores originales
        raw_detail_catalogs = load_detail_catalogs()
        self.detail_catalogs = {
            normalize_detail_catalog_key(key): (value or {})
            for key, value in raw_detail_catalogs.items()
        }

        def _sync_catalog_aliases(canonical_key):
            canonical_key = normalize_detail_catalog_key(canonical_key)
            lookup = self.detail_catalogs.get(canonical_key)
            if not lookup:
                return
            for alias in DETAIL_LOOKUP_ALIASES.get(canonical_key, ()): 
                alias_key = normalize_detail_catalog_key(alias)
                if not alias_key:
                    continue
                self.detail_catalogs[alias_key] = lookup

        def _ensure_canonical_catalog(canonical_key):
            canonical_key = normalize_detail_catalog_key(canonical_key)
            if canonical_key in self.detail_catalogs:
                _sync_catalog_aliases(canonical_key)
                return
            for alias in DETAIL_LOOKUP_ALIASES.get(canonical_key, ()): 
                alias_key = normalize_detail_catalog_key(alias)
                lookup = self.detail_catalogs.get(alias_key)
                if lookup:
                    self.detail_catalogs[canonical_key] = lookup
                    _sync_catalog_aliases(canonical_key)
                    return

        for canonical in DETAIL_LOOKUP_ALIASES:
            _ensure_canonical_catalog(canonical)

        def _merge_with_detail_catalog(base_lookup, aliases):
            merged = {}
            for alias in aliases:
                alias_key = normalize_detail_catalog_key(alias)
                merged.update(self.detail_catalogs.get(alias_key, {}))
            merged.update(base_lookup or {})
            return merged

        self.team_lookup = _merge_with_detail_catalog(
            load_team_details(),
            ("team", "teams", "colaboradores", "colaborador", "id_colaborador"),
        )
        # Cargar client details para autopoblar clientes. Si no existe el
        # fichero ``client_details.csv`` se obtiene un diccionario vacío. Este
        # diccionario se usa en ClientFrame.on_id_change() para rellenar
        # automáticamente campos del cliente cuando se reconoce su ID.
        self.client_lookup = load_client_details()
        self.product_lookup = load_product_details()

        def _register_normalized_catalog(canonical_key, lookup):
            canonical_key = normalize_detail_catalog_key(canonical_key)
            if not lookup:
                return
            combined = dict(self.detail_catalogs.get(canonical_key, {}))
            combined.update(lookup)
            self.detail_catalogs[canonical_key] = combined
            _sync_catalog_aliases(canonical_key)

        _register_normalized_catalog("id_cliente", self.client_lookup)
        _register_normalized_catalog("id_colaborador", self.team_lookup)
        _register_normalized_catalog("id_producto", self.product_lookup)
        # Datos en memoria: listas de frames
        self.client_frames = []
        self.team_frames = []
        self.product_frames = []
        self.risk_frames = []
        self.norm_frames = []
        self.summary_tables = {}
        self.summary_config = {}
        self.summary_context_menus = {}
        self._summary_refresh_after_id = None

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

    def import_combined(self, filename=None):
        """Importa datos combinados de productos, clientes y colaboradores."""

        filename = filename or self._select_csv_file("combinado", "Seleccionar CSV combinado")
        if not filename:
            messagebox.showwarning("Sin archivo", "No hay CSV combinado disponible para importar.")
            return
        created_records = False
        missing_clients = []
        missing_team = []
        missing_products = []
        try:
            for row in iter_massive_csv_rows(filename):
                client_row, client_found = self._hydrate_row_from_details(row, 'id_cliente', CLIENT_ID_ALIASES)
                client_id = (client_row.get('id_cliente') or '').strip()
                if client_id:
                    if not client_row.get('flag') and row.get('flag_cliente'):
                        client_row['flag'] = row.get('flag_cliente')
                    for key in ('telefonos', 'correos', 'direcciones', 'accionado', 'tipo_id'):
                        if not client_row.get(key) and row.get(key):
                            client_row[key] = row.get(key)
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
                team_row, team_found = self._hydrate_row_from_details(row, 'id_colaborador', TEAM_ID_ALIASES)
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
                product_row, product_found = self._hydrate_row_from_details(row, 'id_producto', PRODUCT_ID_ALIASES)
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
                involvement_pairs = parse_involvement_entries(row.get('involucramiento', ''))
                if not involvement_pairs and collaborator_id and row.get('monto_asignado'):
                    involvement_pairs = [(collaborator_id, (row.get('monto_asignado') or '').strip())]
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
                        inv_row.monto_var.set(amount)
                        created_records = True
            self.save_auto()
            log_event("navegacion", "Datos combinados importados desde CSV", self.logs)
            if created_records:
                self.sync_main_form_after_import("datos combinados")
                messagebox.showinfo("Importación completa", "Datos combinados importados correctamente.")
            else:
                messagebox.showwarning("Sin cambios", "No se detectaron registros nuevos en el archivo.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar el CSV combinado: {ex}")
            return
        self._report_missing_detail_ids("clientes", missing_clients)
        self._report_missing_detail_ids("colaboradores", missing_team)
        self._report_missing_detail_ids("productos", missing_products)

    def import_risks(self, filename=None):
        """Importa riesgos desde un archivo CSV."""

        filename = filename or self._select_csv_file("riesgos", "Seleccionar CSV de riesgos")
        if not filename:
            messagebox.showwarning("Sin archivo", "No se encontró CSV de riesgos para importar.")
            return
        imported = 0
        try:
            for row in iter_massive_csv_rows(filename):
                hydrated, _ = self._hydrate_row_from_details(row, 'id_riesgo', RISK_ID_ALIASES)
                rid = (hydrated.get('id_riesgo') or '').strip()
                if not rid:
                    continue
                if any(r.id_var.get().strip() == rid for r in self.risk_frames):
                    log_event("validacion", f"Riesgo duplicado {rid} en importación", self.logs)
                    continue
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
                imported += 1
            self.save_auto()
            log_event("navegacion", "Riesgos importados desde CSV", self.logs)
            if imported:
                messagebox.showinfo("Importación completa", "Riesgos importados correctamente.")
            else:
                messagebox.showwarning("Sin cambios", "No se añadieron riesgos nuevos.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar riesgos: {ex}")
            return

    def import_norms(self, filename=None):
        """Importa normas transgredidas desde un archivo CSV."""

        filename = filename or self._select_csv_file("normas", "Seleccionar CSV de normas")
        if not filename:
            messagebox.showwarning("Sin archivo", "No se encontró CSV de normas.")
            return
        imported = 0
        try:
            for row in iter_massive_csv_rows(filename):
                hydrated, _ = self._hydrate_row_from_details(row, 'id_norma', NORM_ID_ALIASES)
                nid = (hydrated.get('id_norma') or '').strip()
                if not nid:
                    continue
                if any(n.id_var.get().strip() == nid for n in self.norm_frames):
                    log_event("validacion", f"Norma duplicada {nid} en importación", self.logs)
                    continue
                self.add_norm()
                nf = self.norm_frames[-1]
                nf.id_var.set(nid)
                nf.descripcion_var.set((hydrated.get('descripcion') or '').strip())
                nf.fecha_var.set((hydrated.get('fecha_vigencia') or '').strip())
                imported += 1
            self.save_auto()
            log_event("navegacion", "Normas importadas desde CSV", self.logs)
            if imported:
                messagebox.showinfo("Importación completa", "Normas importadas correctamente.")
            else:
                messagebox.showwarning("Sin cambios", "No se añadieron normas nuevas.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar normas: {ex}")
            return

    def import_claims(self, filename=None):
        """Importa reclamos desde un archivo CSV."""

        filename = filename or self._select_csv_file("reclamos", "Seleccionar CSV de reclamos")
        if not filename:
            messagebox.showwarning("Sin archivo", "No se encontró CSV de reclamos.")
            return
        imported = 0
        missing_products = []
        try:
            for row in iter_massive_csv_rows(filename):
                hydrated, found = self._hydrate_row_from_details(row, 'id_producto', PRODUCT_ID_ALIASES)
                product_id = (hydrated.get('id_producto') or '').strip()
                if not product_id:
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
                    'id_reclamo': (hydrated.get('id_reclamo') or row.get('id_reclamo') or '').strip(),
                    'nombre_analitica': (hydrated.get('nombre_analitica') or row.get('nombre_analitica') or '').strip(),
                    'codigo_analitica': (hydrated.get('codigo_analitica') or row.get('codigo_analitica') or '').strip(),
                }
                if not any(claim_payload.values()):
                    continue
                target = product_frame.find_claim_by_id(claim_payload['id_reclamo'])
                if not target:
                    target = product_frame.obtain_claim_slot()
                target.set_data(claim_payload)
                self._sync_product_lookup_claim_fields(product_frame, product_id)
                product_frame.persist_lookup_snapshot()
                imported += 1
                if not found and 'id_producto' in self.detail_catalogs:
                    missing_products.append(product_id)
            self.save_auto()
            log_event("navegacion", "Reclamos importados desde CSV", self.logs)
            if imported:
                self.sync_main_form_after_import("reclamos")
                messagebox.showinfo("Importación completa", "Reclamos importados correctamente.")
            else:
                messagebox.showwarning("Sin cambios", "Ningún reclamo se pudo vincular a productos existentes.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar reclamos: {ex}")
            return
        self._report_missing_detail_ids("productos", missing_products)

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

        # --- Pestaña Resumen ---
        summary_tab = ttk.Frame(self.notebook)
        self.notebook.add(summary_tab, text="Resumen")
        self.build_summary_tab(summary_tab)

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

        scroll_container = ttk.Frame(parent)
        scroll_container.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroll_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._main_scrollable_frame = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=self._main_scrollable_frame, anchor="nw")

        def _configure_canvas(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _resize_inner(event):
            canvas.itemconfigure(window_id, width=event.width)

        self._main_scrollable_frame.bind("<Configure>", _configure_canvas)
        canvas.bind("<Configure>", _resize_inner)

        case_section = ttk.LabelFrame(self._main_scrollable_frame, text="1. Datos generales del caso")
        case_section.pack(fill="x", expand=False, padx=5, pady=5)
        self.build_case_tab(case_section)

        clients_section = ttk.LabelFrame(self._main_scrollable_frame, text="2. Clientes implicados")
        clients_section.pack(fill="x", expand=True, padx=5, pady=5)
        self.build_clients_tab(clients_section)

        products_section = ttk.LabelFrame(self._main_scrollable_frame, text="3. Productos investigados")
        products_section.pack(fill="x", expand=True, padx=5, pady=5)
        self.build_products_tab(products_section)

        team_section = ttk.LabelFrame(self._main_scrollable_frame, text="4. Colaboradores involucrados")
        team_section.pack(fill="x", expand=True, padx=5, pady=5)
        self.build_team_tab(team_section)

    def _safe_update_idletasks(self):
        """Intenta refrescar la UI sin propagar errores cuando la ventana no existe."""

        try:
            self.root.update_idletasks()
        except tk.TclError:
            pass

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
        self.refresh_summary_tables()
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
        cat1_cb.bind("<FocusOut>", lambda e: self.on_case_cat1_change())
        cat1_cb.bind("<<ComboboxSelected>>", lambda e: self.on_case_cat1_change())
        self.register_tooltip(cat1_cb, "Nivel superior de la taxonomía de fraude.")
        ttk.Label(row2, text="Categoría nivel 2:").pack(side="left")
        self.case_cat2_cb = ttk.Combobox(row2, textvariable=self.cat_caso2_var, values=list(TAXONOMIA[self.cat_caso1_var.get()].keys()), state="readonly", width=20)
        self.case_cat2_cb.pack(side="left", padx=5)
        self.case_cat2_cb.bind("<FocusOut>", lambda e: self.on_case_cat2_change())
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
        client = ClientFrame(
            self.clients_container,
            idx,
            self.remove_client,
            self.update_client_options_global,
            self.logs,
            self.register_tooltip,
            client_lookup=self.client_lookup,
            summary_refresh_callback=self._schedule_summary_refresh,
        )
        self.client_frames.append(client)
        self.update_client_options_global()
        self._schedule_summary_refresh()

    def remove_client(self, client_frame):
        self.client_frames.remove(client_frame)
        # Renombrar las etiquetas
        for i, cl in enumerate(self.client_frames):
            cl.idx = i
            cl.frame.config(text=f"Cliente {i+1}")
        self.update_client_options_global()
        self._schedule_summary_refresh()

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
        team = TeamMemberFrame(
            self.team_container,
            idx,
            self.remove_team,
            self.update_team_options_global,
            self.team_lookup,
            self.logs,
            self.register_tooltip,
            summary_refresh_callback=self._schedule_summary_refresh,
        )
        self.team_frames.append(team)
        self.update_team_options_global()
        self._schedule_summary_refresh()

    def remove_team(self, team_frame):
        self.team_frames.remove(team_frame)
        # Renombrar
        for i, tm in enumerate(self.team_frames):
            tm.idx = i
            tm.frame.config(text=f"Colaborador {i+1}")
        self.update_team_options_global()
        self._schedule_summary_refresh()

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
                if hasattr(product_frame, 'cat2_cb'):
                    product_frame.cat2_cb.set(cat2)
                product_frame.on_cat2_change()
                if modalidad in TAXONOMIA[cat1][cat2]:
                    product_frame.mod_var.set(modalidad)
                    if hasattr(product_frame, 'mod_cb'):
                        product_frame.mod_cb.set(modalidad)

    def add_product(self):
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
            summary_refresh_callback=self._schedule_summary_refresh,
        )
        self._apply_case_taxonomy_defaults(prod)
        self.product_frames.append(prod)
        # Renombrar
        for i, p in enumerate(self.product_frames):
            p.idx = i
            p.frame.config(text=f"Producto {i+1}")
        self._schedule_summary_refresh()

    def remove_product(self, prod_frame):
        self.product_frames.remove(prod_frame)
        for i, p in enumerate(self.product_frames):
            p.idx = i
            p.frame.config(text=f"Producto {i+1}")
        self._schedule_summary_refresh()

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
        self._schedule_summary_refresh()

    def remove_risk(self, risk_frame):
        self.risk_frames.remove(risk_frame)
        for i, r in enumerate(self.risk_frames):
            r.idx = i
            r.frame.config(text=f"Riesgo {i+1}")
        self._schedule_summary_refresh()

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
        self._schedule_summary_refresh()

    def remove_norm(self, norm_frame):
        self.norm_frames.remove(norm_frame)
        for i, n in enumerate(self.norm_frames):
            n.idx = i
            n.frame.config(text=f"Norma {i+1}")
        self._schedule_summary_refresh()

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

        # Información adicional
        ttk.Label(frame, text="El auto‑guardado se realiza automáticamente en un archivo JSON").pack(anchor="w", pady=(10,2))

    def build_summary_tab(self, parent):
        """Construye la pestaña de resumen con tablas compactas."""

        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Label(
            container,
            text="Resumen compacto de los datos capturados. Las tablas se actualizan tras cada guardado o importación.",
        ).pack(anchor="w", pady=(0, 5))

        config = [
            (
                "clientes",
                "Clientes registrados",
                [
                    ("id", "ID"),
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
                    ("division", "División"),
                    ("area", "Área"),
                    ("sancion", "Sanción"),
                ],
            ),
            (
                "productos",
                "Productos investigados",
                [
                    ("id", "ID Producto"),
                    ("cliente", "Cliente"),
                    ("tipo", "Tipo"),
                    ("monto", "Monto investigado"),
                ],
            ),
            (
                "riesgos",
                "Riesgos registrados",
                [
                    ("id", "ID Riesgo"),
                    ("lider", "Líder"),
                    ("criticidad", "Criticidad"),
                    ("exposicion", "Exposición"),
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
        for key, title, columns in config:
            section = ttk.LabelFrame(container, text=title)
            section.pack(fill="both", expand=True, pady=5)
            frame = ttk.Frame(section)
            frame.pack(fill="both", expand=True)
            tree = ttk.Treeview(frame, columns=[col for col, _ in columns], show="headings", height=5)
            scrollbar = ttk.Scrollbar(frame, orient="vertical")
            for col_id, heading in columns:
                tree.heading(col_id, text=heading)
                tree.column(col_id, width=150, stretch=True)
            tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.configure(command=tree.yview)
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            self.summary_tables[key] = tree
            self._register_summary_tree_bindings(tree, key)

        self.refresh_summary_tables()

    def _register_summary_tree_bindings(self, tree, key):
        """Configura atajos de pegado y el menú contextual para una tabla."""

        tree.bind("<Control-v>", lambda event, target=key: self._handle_summary_paste(target))
        tree.bind("<Control-V>", lambda event, target=key: self._handle_summary_paste(target))
        menu = tk.Menu(tree, tearoff=False)
        menu.add_command(
            label="Pegar desde portapapeles",
            command=lambda target=key: self._handle_summary_paste(target),
        )
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
        try:
            parsed_rows = self._parse_clipboard_rows(clipboard_text, len(columns))
            sanitized_rows = self._transform_summary_clipboard_rows(key, parsed_rows)
        except ValueError as exc:
            messagebox.showerror("Pegado no válido", str(exc))
            return "break"
        ingestible_sections = {"clientes", "colaboradores", "productos", "reclamos", "riesgos", "normas"}
        if key in ingestible_sections:
            try:
                self.ingest_summary_rows(key, sanitized_rows, stay_on_summary=True)
            except ValueError as exc:
                messagebox.showerror("Pegado no válido", str(exc))
            return "break"
        tree.delete(*tree.get_children())
        for row in sanitized_rows:
            tree.insert("", "end", values=row)
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
            phone_message = validate_phone_list(client_data["telefonos"], "los teléfonos del cliente")
            if phone_message:
                raise ValueError(f"Cliente fila {idx}: {phone_message}")
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
                "division": values[1].strip(),
                "area": values[2].strip(),
                "tipo_sancion": values[3].strip(),
            }
            if collaborator["tipo_sancion"] not in TIPO_SANCION_LIST:
                raise ValueError(
                    f"Colaborador fila {idx}: debe seleccionar un tipo de sanción válido."
                )
            message = validate_team_member_id(collaborator["id_colaborador"])
            if message:
                raise ValueError(f"Colaborador fila {idx}: {message}")
            sanitized.append(
                (
                    collaborator["id_colaborador"],
                    collaborator["division"],
                    collaborator["area"],
                    collaborator["tipo_sancion"],
                )
            )
        return sanitized

    def _transform_clipboard_productos(self, rows):
        sanitized = []
        for idx, values in enumerate(rows, start=1):
            product = {
                "id_producto": values[0].strip(),
                "id_cliente": values[1].strip(),
                "tipo_producto": values[2].strip(),
                "monto_investigado": values[3].strip(),
            }
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
            amount_message, decimal_value = validate_money_bounds(
                product["monto_investigado"],
                "el monto investigado",
                allow_blank=False,
            )
            if amount_message:
                raise ValueError(f"Producto fila {idx}: {amount_message}")
            sanitized.append(
                (
                    product["id_producto"],
                    product["id_cliente"],
                    product["tipo_producto"],
                    f"{decimal_value:.2f}",
                )
            )
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
            risk = {
                "id_riesgo": values[0].strip().upper(),
                "lider": values[1].strip(),
                "criticidad": values[2].strip() or CRITICIDAD_LIST[0],
                "exposicion": values[3].strip(),
            }
            message = validate_risk_id(risk["id_riesgo"])
            if message:
                raise ValueError(f"Riesgo fila {idx}: {message}")
            if risk["criticidad"] not in valid_criticidades:
                raise ValueError(
                    f"Riesgo fila {idx}: la criticidad debe ser una de {valid_criticidades_text}."
                )
            exposure_message, exposure_decimal = validate_money_bounds(
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
                    risk["criticidad"],
                    exposure_text,
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
                self.save_auto()
                self.sync_main_form_after_import("clientes", stay_on_summary=stay_on_summary)
            return processed
        if section_key == "colaboradores":
            for values in rows:
                payload = {
                    "id_colaborador": (values[0] or "").strip(),
                    "division": (values[1] or "").strip(),
                    "area": (values[2] or "").strip(),
                    "tipo_sancion": (values[3] or "").strip(),
                    "flag_colaborador": "No aplica",
                    "servicio": "",
                    "puesto": "",
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
                self.save_auto()
                self.sync_main_form_after_import("colaboradores", stay_on_summary=stay_on_summary)
            return processed
        if section_key == "productos":
            for values in rows:
                payload = {
                    "id_producto": (values[0] or "").strip(),
                    "id_cliente": (values[1] or "").strip(),
                    "tipo_producto": (values[2] or "").strip(),
                    "monto_investigado": (values[3] or "").strip(),
                    "categoria1": "",
                    "categoria2": "",
                    "modalidad": "",
                    "canal": "",
                    "proceso": "",
                    "fecha_ocurrencia": "",
                    "fecha_descubrimiento": "",
                    "tipo_moneda": "",
                    "monto_perdida_fraude": "",
                    "monto_falla_procesos": "",
                    "monto_contingencia": "",
                    "monto_recuperado": "",
                    "monto_pago_deuda": "",
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
                self.save_auto()
                self.sync_main_form_after_import("productos", stay_on_summary=stay_on_summary)
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
                self.save_auto()
                self.sync_main_form_after_import("reclamos", stay_on_summary=stay_on_summary)
                log_event("navegacion", f"Reclamos pegados desde resumen: {processed}", self.logs)
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
                criticidad = (values[2] or CRITICIDAD_LIST[0]).strip()
                if criticidad in CRITICIDAD_LIST:
                    frame.criticidad_var.set(criticidad)
                frame.exposicion_var.set((values[3] or "").strip())
                processed += 1
            if duplicate_ids:
                messagebox.showwarning(
                    "Riesgos duplicados",
                    "Se ignoraron los siguientes riesgos ya existentes:\n" + ", ".join(duplicate_ids),
                )
            if processed:
                self.save_auto()
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
                self.save_auto()
                self.sync_main_form_after_import("normas", stay_on_summary=stay_on_summary)
            return processed
        raise ValueError("Esta tabla no admite pegado directo al formulario principal.")

    def _schedule_summary_refresh(self):
        """Programa la actualización del resumen en la cola ``after_idle`` de Tk."""

        if not self.summary_tables:
            return
        if self._summary_refresh_after_id:
            return
        try:
            self._summary_refresh_after_id = self.root.after_idle(self._run_scheduled_summary_refresh)
        except tk.TclError:
            self._summary_refresh_after_id = None
            self.refresh_summary_tables()

    def _run_scheduled_summary_refresh(self):
        self._summary_refresh_after_id = None
        self.refresh_summary_tables()

    def refresh_summary_tables(self, data=None):
        """Actualiza las tablas de resumen con la información actual."""

        if not self.summary_tables:
            return
        dataset = data or self.gather_data()

        def update_table(key, rows):
            tree = self.summary_tables.get(key)
            if not tree:
                return
            tree.delete(*tree.get_children())
            for row in rows:
                tree.insert("", "end", values=row)

        update_table(
            "clientes",
            [
                (
                    client.get("id_cliente", ""),
                    client.get("tipo_id", ""),
                    client.get("flag", ""),
                    client.get("telefonos", ""),
                    client.get("correos", ""),
                    client.get("direcciones", ""),
                    client.get("accionado", ""),
                )
                for client in dataset.get("clientes", [])
            ],
        )
        update_table(
            "colaboradores",
            [
                (
                    col.get("id_colaborador", ""),
                    col.get("division", ""),
                    col.get("area", ""),
                    col.get("tipo_sancion", ""),
                )
                for col in dataset.get("colaboradores", [])
            ],
        )
        update_table(
            "productos",
            [
                (
                    prod.get("id_producto", ""),
                    prod.get("id_cliente", ""),
                    prod.get("tipo_producto", ""),
                    prod.get("monto_investigado", ""),
                )
                for prod in dataset.get("productos", [])
            ],
        )
        update_table(
            "riesgos",
            [
                (
                    risk.get("id_riesgo", ""),
                    risk.get("lider", ""),
                    risk.get("criticidad", ""),
                    risk.get("exposicion_residual", ""),
                )
                for risk in dataset.get("riesgos", [])
            ],
        )
        update_table(
            "reclamos",
            [
                (
                    rec.get("id_reclamo", ""),
                    rec.get("id_producto", ""),
                    rec.get("nombre_analitica", ""),
                    rec.get("codigo_analitica", ""),
                )
                for rec in dataset.get("reclamos", [])
            ],
        )
        update_table(
            "normas",
            [
                (
                    norm.get("id_norma", ""),
                    norm.get("descripcion", ""),
                    norm.get("fecha_vigencia", ""),
                )
                for norm in dataset.get("normas", [])
            ],
        )

    # ---------------------------------------------------------------------
    # Importación desde CSV

    def _select_csv_file(self, sample_key, dialog_title):
        """Obtiene un CSV desde diálogo o usa el archivo masivo de ejemplo."""

        filename = None
        try:
            filename = filedialog.askopenfilename(title=dialog_title, filetypes=[("CSV Files", "*.csv")])
        except tk.TclError:
            filename = None
        if not filename:
            sample_path = MASSIVE_SAMPLE_FILES.get(sample_key)
            if sample_path and os.path.exists(sample_path):
                filename = sample_path
                log_event(
                    "navegacion",
                    f"Se usó el archivo masivo de ejemplo {os.path.basename(sample_path)} para {sample_key}.",
                    self.logs,
                )
        return filename

    def _get_detail_lookup(self, id_column):
        """Obtiene el diccionario de detalles considerando alias configurados."""

        normalized = normalize_detail_catalog_key(id_column)
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
                'flag_colaborador': frame.flag_var.get,
                'division': frame.division_var.get,
                'area': frame.area_var.get,
                'servicio': frame.servicio_var.get,
                'puesto': frame.puesto_var.get,
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

    def _find_client_frame(self, client_id):
        client_id = (client_id or '').strip()
        if not client_id:
            return None
        for frame in self.client_frames:
            if frame.id_var.get().strip() == client_id:
                return frame
        return None

    def _find_team_frame(self, collaborator_id):
        collaborator_id = (collaborator_id or '').strip()
        if not collaborator_id:
            return None
        for frame in self.team_frames:
            if frame.id_var.get().strip() == collaborator_id:
                return frame
        return None

    def _find_product_frame(self, product_id):
        product_id = (product_id or '').strip()
        if not product_id:
            return None
        for frame in self.product_frames:
            if frame.id_var.get().strip() == product_id:
                return frame
        return None

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
                self._apply_case_taxonomy_defaults(frame)
                return frame
        self.add_product()
        new_frame = self.product_frames[-1]
        self._apply_case_taxonomy_defaults(new_frame)
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

    def _populate_team_frame_from_row(self, frame, row):
        id_col = (
            row.get('id_colaborador')
            or row.get('IdColaborador')
            or row.get('IdTeamMember')
            or row.get('id_col')
            or ''
        ).strip()
        frame.id_var.set(id_col)
        flag_val = (
            row.get('flag_colaborador')
            or row.get('flag')
            or row.get('Flag')
            or 'No aplica'
        ).strip()
        frame.flag_var.set(flag_val or 'No aplica')
        frame.division_var.set((row.get('division') or '').strip())
        frame.area_var.set((row.get('area') or '').strip())
        frame.servicio_var.set((row.get('servicio') or '').strip())
        frame.puesto_var.set((row.get('puesto') or '').strip())
        frame.nombre_agencia_var.set((row.get('nombre_agencia') or '').strip())
        frame.codigo_agencia_var.set((row.get('codigo_agencia') or '').strip())
        frame.tipo_falta_var.set((row.get('tipo_falta') or '').strip() or 'No aplica')
        frame.tipo_sancion_var.set((row.get('tipo_sancion') or '').strip() or 'No aplica')
        self.team_lookup[id_col] = {
            'division': frame.division_var.get(),
            'area': frame.area_var.get(),
            'servicio': frame.servicio_var.get(),
            'puesto': frame.puesto_var.get(),
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

    def import_clients(self, filename=None):
        """Importa clientes desde un archivo CSV y los añade a la lista."""

        filename = filename or self._select_csv_file("clientes", "Seleccionar CSV de clientes")
        if not filename:
            messagebox.showwarning("Sin archivo", "No se seleccionó un CSV para clientes ni se encontró el ejemplo.")
            return
        imported = 0
        missing_ids = []
        try:
            for row in iter_massive_csv_rows(filename):
                hydrated, found = self._hydrate_row_from_details(row, 'id_cliente', CLIENT_ID_ALIASES)
                id_cliente = (hydrated.get('id_cliente') or '').strip()
                if not id_cliente:
                    continue
                frame = self._find_client_frame(id_cliente) or self._obtain_client_slot_for_import()
                self._populate_client_frame_from_row(frame, hydrated)
                self._trigger_import_id_refresh(
                    frame,
                    id_cliente,
                    notify_on_missing=True,
                    preserve_existing=False,
                )
                imported += 1
                if not found and 'id_cliente' in self.detail_catalogs:
                    missing_ids.append(id_cliente)
            self.save_auto()
            log_event("navegacion", f"Clientes importados desde CSV: {imported}", self.logs)
            if imported:
                self.sync_main_form_after_import("clientes")
                messagebox.showinfo("Importación completa", f"Se cargaron {imported} clientes.")
            else:
                messagebox.showwarning("Sin cambios", "El archivo no aportó clientes nuevos.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar clientes: {ex}")
            return
        self._report_missing_detail_ids("clientes", missing_ids)

    def import_team_members(self, filename=None):
        """Importa colaboradores desde un archivo CSV y los añade a la lista."""

        filename = filename or self._select_csv_file("colaboradores", "Seleccionar CSV de colaboradores")
        if not filename:
            messagebox.showwarning("Sin archivo", "No hay CSV para colaboradores disponible.")
            return
        imported = 0
        missing_ids = []
        try:
            for row in iter_massive_csv_rows(filename):
                hydrated, found = self._hydrate_row_from_details(row, 'id_colaborador', TEAM_ID_ALIASES)
                collaborator_id = (hydrated.get('id_colaborador') or '').strip()
                if not collaborator_id:
                    continue
                frame = self._find_team_frame(collaborator_id) or self._obtain_team_slot_for_import()
                self._populate_team_frame_from_row(frame, hydrated)
                self._trigger_import_id_refresh(
                    frame,
                    collaborator_id,
                    notify_on_missing=True,
                    preserve_existing=False,
                )
                imported += 1
                if not found and 'id_colaborador' in self.detail_catalogs:
                    missing_ids.append(collaborator_id)
            self.save_auto()
            log_event("navegacion", f"Colaboradores importados desde CSV: {imported}", self.logs)
            if imported:
                self.sync_main_form_after_import("colaboradores")
                messagebox.showinfo("Importación completa", "Colaboradores importados correctamente.")
            else:
                messagebox.showwarning("Sin cambios", "No se encontraron colaboradores nuevos en el archivo.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar colaboradores: {ex}")
            return
        self._report_missing_detail_ids("colaboradores", missing_ids)

    def import_products(self, filename=None):
        """Importa productos desde un archivo CSV y los añade a la lista."""

        filename = filename or self._select_csv_file("productos", "Seleccionar CSV de productos")
        if not filename:
            messagebox.showwarning("Sin archivo", "No se seleccionó CSV de productos ni se encontró el ejemplo.")
            return
        imported = 0
        missing_ids = []
        try:
            for row in iter_massive_csv_rows(filename):
                hydrated, found = self._hydrate_row_from_details(row, 'id_producto', PRODUCT_ID_ALIASES)
                product_id = (hydrated.get('id_producto') or '').strip()
                if not product_id:
                    continue
                frame = self._find_product_frame(product_id) or self._obtain_product_slot_for_import()
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
                imported += 1
                if not found and 'id_producto' in self.detail_catalogs:
                    missing_ids.append(product_id)
            self.save_auto()
            log_event("navegacion", f"Productos importados desde CSV: {imported}", self.logs)
            if imported:
                self.sync_main_form_after_import("productos")
                messagebox.showinfo("Importación completa", "Productos importados correctamente.")
            else:
                messagebox.showwarning("Sin cambios", "No se detectaron productos nuevos en el archivo.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo importar productos: {ex}")
            return
        self._report_missing_detail_ids("productos", missing_ids)

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
        self.refresh_summary_tables(data)

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
            pframe.set_claims_from_data(claims_map.get(pframe.id_var.get().strip(), []))
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
        self.refresh_summary_tables(data)

    # ---------------------------------------------------------------------
    # Validación de reglas de negocio

    def validate_data(self):
        """Valida los datos del formulario y retorna errores y advertencias."""
        errors = []
        warnings = []
        # Validar número de caso
        id_caso = self.id_caso_var.get().strip()
        case_message = validate_case_id(id_caso)
        if case_message:
            errors.append(case_message)
        # Validar campos obligatorios del caso antes de validar entidades hijas
        tipo_message = validate_required_text(self.tipo_informe_var.get(), "el tipo de informe")
        if tipo_message:
            errors.append(tipo_message)
        cat1_message = validate_required_text(self.cat_caso1_var.get(), "la categoría nivel 1")
        if cat1_message:
            errors.append(cat1_message)
        cat2_message = validate_required_text(self.cat_caso2_var.get(), "la categoría nivel 2")
        if cat2_message:
            errors.append(cat2_message)
        mod_message = validate_required_text(self.mod_caso_var.get(), "la modalidad del caso")
        if mod_message:
            errors.append(mod_message)
        canal_message = validate_required_text(self.canal_caso_var.get(), "el canal del caso")
        if canal_message:
            errors.append(canal_message)
        proceso_message = validate_required_text(self.proceso_caso_var.get(), "el proceso impactado")
        if proceso_message:
            errors.append(proceso_message)
        # Validar IDs de clientes
        for idx, cframe in enumerate(self.client_frames, start=1):
            message = validate_client_id(cframe.tipo_id_var.get(), cframe.id_var.get())
            if message:
                errors.append(f"Cliente {idx}: {message}")
        # Validar duplicidad del key técnico (caso, producto, cliente, colaborador, fecha ocurrencia, reclamo)
        key_set = set()
        product_client_map = {}
        total_investigado = Decimal('0')
        total_componentes = Decimal('0')
        normalized_amounts = []
        for idx, tm in enumerate(self.team_frames, start=1):
            tm_id_message = validate_team_member_id(tm.id_var.get())
            if tm_id_message:
                errors.append(f"Colaborador {idx}: {tm_id_message}")
            agency_message = validate_agency_code(tm.codigo_agencia_var.get(), allow_blank=True)
            if agency_message:
                errors.append(f"Colaborador {idx}: {agency_message}")
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
        for idx, p in enumerate(self.product_frames, start=1):
            prod_data = p.get_data()
            pid = prod_data['producto']['id_producto']
            pid_message = validate_product_id(p.tipo_prod_var.get(), p.id_var.get())
            if pid_message:
                errors.append(f"Producto {idx}: {pid_message}")
            cid = prod_data['producto']['id_cliente']
            if not cid:
                errors.append(
                    f"Producto {idx}: el cliente vinculado fue eliminado. Selecciona un nuevo titular antes de exportar."
                )
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
            claim_rows = prod_data['reclamos'] or [{'id_reclamo': ''}]
            if not prod_data['asignaciones']:
                for claim in claim_rows:
                    claim_id = (claim.get('id_reclamo') or '').strip()
                    key = (id_caso, pid, cid, '', prod_data['producto']['fecha_ocurrencia'], claim_id)
                    if key in key_set:
                        errors.append(f"Registro duplicado de clave técnica (producto {pid})")
                    key_set.add(key)
            for inv in prod_data['asignaciones']:
                for claim in claim_rows:
                    claim_id = (claim.get('id_reclamo') or '').strip()
                    key = (id_caso, pid, cid, inv['id_colaborador'], prod_data['producto']['fecha_ocurrencia'], claim_id)
                    if key in key_set:
                        errors.append(
                            f"Registro duplicado de clave técnica (producto {pid}, colaborador {inv['id_colaborador']})"
                        )
                    key_set.add(key)
        # Validar fechas y montos por producto
        for p in self.product_frames:
            data = p.get_data()
            producto = data['producto']
            tipo_producto = producto.get('tipo_producto', '').strip()
            if not tipo_producto:
                errors.append(f"Producto {producto['id_producto']}: Debe ingresar el tipo de producto.")
            else:
                normalized_tipo = normalize_without_accents(tipo_producto).lower()
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
                message, decimal_value = validate_money_bounds(
                    producto.get(field, ''),
                    f"{label} del producto {producto['id_producto']}",
                    allow_blank=allow_blank,
                )
                if message:
                    errors.append(message)
                    money_error = True
                money_values[field] = decimal_value if decimal_value is not None else Decimal('0')
            if money_error:
                continue
            m_inv = money_values['monto_investigado']
            m_perd = money_values['monto_perdida_fraude']
            m_fall = money_values['monto_falla_procesos']
            m_cont = money_values['monto_contingencia']
            m_rec = money_values['monto_recuperado']
            m_pago = money_values['monto_pago_deuda']
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
            if abs(componentes - m_inv) > Decimal('0.01'):
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
            # Reclamo y analíticas
            requiere_reclamo = m_perd > 0 or m_fall > 0 or m_cont > 0
            complete_claim_found = False
            seen_claim_ids = set()
            for claim in data['reclamos'] or []:
                claim_id = (claim.get('id_reclamo') or '').strip()
                claim_name = (claim.get('nombre_analitica') or '').strip()
                claim_code = (claim.get('codigo_analitica') or '').strip()
                has_any_value = any([claim_id, claim_name, claim_code])
                if claim_id:
                    if claim_id in seen_claim_ids:
                        errors.append(
                            f"Producto {producto['id_producto']}: El ID de reclamo {claim_id} está duplicado."
                        )
                    seen_claim_ids.add(claim_id)
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
            # Tipo producto vs contingencia
            tipo_prod = normalize_without_accents(producto['tipo_producto']).lower()
            if any(word in tipo_prod for word in ['credito', 'tarjeta']):
                if abs(m_cont - m_inv) > Decimal('0.01'):
                    errors.append(f"El monto de contingencia debe ser igual al monto investigado en el producto {producto['id_producto']} porque es un crédito o tarjeta")
            # Fraude externo
            if producto['categoria2'] == 'Fraude Externo':
                warnings.append(
                    f"Producto {producto['id_producto']} con categoría 2 'Fraude Externo': verifique la analítica registrada."
                )
        if self.product_frames and abs(total_componentes - total_investigado) > Decimal('0.01'):
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
            # Exposición
            message, exposure_decimal = validate_money_bounds(
                rd['exposicion_residual'],
                f"Exposición residual del riesgo {rid}",
                allow_blank=True,
            )
            if message:
                errors.append(message)
            elif exposure_decimal is not None:
                risk_exposure_total += exposure_decimal
            # Planes de acción
            for plan in [p.strip() for p in rd['planes_accion'].split(';') if p.strip()]:
                if plan in plan_ids:
                    errors.append(f"Plan de acción {plan} duplicado entre riesgos")
                plan_ids.add(plan)
        self._last_validated_risk_exposure_total = risk_exposure_total
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
        return errors, warnings

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

        reclamos_por_producto = {}
        for record in data['reclamos']:
            pid = record.get('id_producto')
            if not pid:
                continue
            reclamos_por_producto.setdefault(pid, []).append(record)

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
            claim_values = reclamos_por_producto.get(prod['id_producto'], [])
            claims_text = "; ".join(
                f"{rec.get('id_reclamo', '')} / {rec.get('codigo_analitica', '')}"
                for rec in claim_values
            )
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
                claims_text,
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
        errors, warnings = self.validate_data()
        if errors:
            messagebox.showerror("Errores de validación", "\n".join(errors))
            log_event("validacion", f"Errores al guardar: {errors}", self.logs)
        if warnings:
            messagebox.showwarning("Advertencias de validación", "\n".join(warnings))
            log_event("validacion", f"Advertencias al guardar: {warnings}", self.logs)
        if errors:
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