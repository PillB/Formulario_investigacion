"""Genera una versión mejorada del wireframe de formularios en Excel.

Este script actualiza las hojas del archivo
``docs/formulario_investigaciones_wireframe.xlsx`` con la estructura real de la
UI, los catálogos y los exportes definidos en el código. Se apoya en los
diagramas y definiciones de ``docs/`` y ``settings.py`` para mantener las
descripciones alineadas con las reglas de negocio.

Uso:
    python tools/generate_improved_wireframe_excel.py \\
        --output docs/formulario_investigaciones_wireframe_mejorado.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from app import EXPORT_HEADERS
from settings import EVENTOS_HEADER_CANONICO, EVENTOS_HEADER_CANONICO_START
from validators import LOG_FIELDNAMES


HEADER_FONT = Font(bold=True)
WRAP = Alignment(vertical="top", wrap_text=True)


def _apply_headers(sheet, headers: Sequence[str]) -> None:
    sheet.append(list(headers))
    for cell in sheet[1]:
        cell.font = HEADER_FONT
        cell.alignment = WRAP


def _append_rows(sheet, rows: Iterable[Sequence[str | None]]) -> None:
    for row in rows:
        sheet.append(list(row))
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value is not None:
                cell.alignment = WRAP


def _section_row(title: str, *, columns: int) -> list[str | None]:
    return [title] + [""] * (columns - 1)


def _case_and_participants_rows() -> list[Sequence[str | None]]:
    headers = ("Campo", "Tipo", "Descripción", "Autocompletado / Fuente")
    rows: list[Sequence[str | None]] = []

    rows.append(_section_row("1. Datos generales del caso", columns=len(headers)))
    rows.extend(
        [
            (
                "Número de caso (AAAA-XXXX)",
                "Entry (texto)",
                "Identificador único del caso. Se valida formato AAAA-XXXX y se usa en la llave técnica.",
                "No",
            ),
            (
                "Tipo de informe",
                "Combobox",
                "Tipo de reporte a generar (Gerencia/Interno/Credicorp).",
                "settings.TIPO_INFORME_LIST",
            ),
            (
                "Categoría nivel 1",
                "Combobox",
                "Categoría principal del fraude. Controla la lista de categoría nivel 2.",
                "settings.TAXONOMIA",
            ),
            (
                "Categoría nivel 2",
                "Combobox",
                "Subcategoría dependiente de la categoría nivel 1.",
                "settings.TAXONOMIA",
            ),
            (
                "Modalidad",
                "Combobox",
                "Modalidad específica dependiente de categoría 1/2.",
                "settings.TAXONOMIA",
            ),
            (
                "Canal",
                "Combobox",
                "Canal donde ocurrió el evento. Puede autocompletarse al elegir el ID de proceso.",
                "settings.CANAL_LIST / process_details.csv",
            ),
            (
                "ID Proceso",
                "Entry (texto)",
                "Identificador del proceso impactado (BPID-XXXXXX o BPID-RNF-XXXXXX).",
                "process_details.csv (autopobla canal/proceso)",
            ),
            (
                "Botón \"Seleccionar\" (ID Proceso)",
                "Botón",
                "Abre el selector de procesos para escoger un ID válido.",
                "Catálogo de procesos",
            ),
            (
                "Proceso impactado",
                "Combobox",
                "Proceso del negocio afectado por el evento.",
                "settings.PROCESO_LIST / process_details.csv",
            ),
            (
                "Centro de costos del caso (; separados)",
                "Entry (texto)",
                "Lista de centros de costos. Cada valor debe ser numérico y >=5 dígitos.",
                "No",
            ),
            (
                "Ocurrencia (YYYY-MM-DD)",
                "Selector de fecha",
                "Fecha de ocurrencia del caso. Debe ser <= hoy y anterior al descubrimiento.",
                "No",
            ),
            (
                "Descubrimiento (YYYY-MM-DD)",
                "Selector de fecha",
                "Fecha de descubrimiento. Debe ser <= hoy y posterior a la ocurrencia.",
                "No",
            ),
            (
                "Matrícula investigador",
                "Entry (texto)",
                "ID del investigador principal (letra + 5 dígitos) para autocompletar datos.",
                "team_details.csv",
            ),
            (
                "Nombre y apellidos",
                "Entry (solo lectura)",
                "Nombre del investigador autocompletado desde catálogos.",
                "team_details.csv",
            ),
            (
                "Puesto",
                "Label (solo lectura)",
                "Cargo del investigador autocompletado.",
                "team_details.csv",
            ),
        ]
    )

    rows.append(_section_row("2. Clientes implicados", columns=len(headers)))
    rows.extend(
        [
            (
                "Tabla resumen de clientes",
                "Tabla",
                "Resumen de clientes registrados en el caso.",
                "Resumen dinámico",
            ),
            ("Botón \"Añadir cliente\"", "Botón", "Crea un nuevo cliente.", ""),
            (
                "Afectación interna",
                "Checkbutton",
                "Marca si el cliente pertenece a afectación interna.",
                "No",
            ),
            (
                "Tipo de ID",
                "Combobox",
                "Tipo de documento del cliente (DNI/RUC/Pasaporte/etc.).",
                "settings.TIPO_ID_LIST",
            ),
            (
                "ID del cliente",
                "Entry (texto)",
                "Documento del cliente. Valida longitud según tipo de ID.",
                "No",
            ),
            ("Nombres", "Entry (texto)", "Nombres del cliente.", "client_details.csv"),
            ("Apellidos", "Entry (texto)", "Apellidos del cliente.", "client_details.csv"),
            (
                "Flag",
                "Combobox",
                "Rol del cliente (Involucrado/Afectado/No aplica).",
                "settings.FLAG_CLIENTE_LIST",
            ),
            (
                "Accionado (lista múltiple)",
                "Listbox",
                "Tribus/equipos accionados. Valida selección múltiple.",
                "settings.ACCIONADO_OPTIONS",
            ),
            (
                "Teléfonos (separados por ;)",
                "Entry (texto)",
                "Teléfonos del cliente. Validación de números (+, 6-15 dígitos).",
                "client_details.csv",
            ),
            (
                "Correos (separados por ;)",
                "Entry (texto)",
                "Correos del cliente. Deben cumplir formato de email.",
                "client_details.csv",
            ),
            (
                "Direcciones (separados por ;)",
                "Entry (texto)",
                "Direcciones físicas del cliente (opcional).",
                "client_details.csv",
            ),
            ("Botón \"Eliminar cliente\"", "Botón", "Elimina el cliente del caso.", ""),
        ]
    )

    rows.append(_section_row("3. Productos investigados", columns=len(headers)))
    rows.extend(
        [
            ("Tabla resumen de productos", "Tabla", "Resumen de productos investigados.", ""),
            ("Botón \"Agregar producto\"", "Botón", "Crea un nuevo producto.", ""),
            (
                "ID del producto",
                "Entry (texto)",
                "Identificador del producto. Valida longitud según tipo de producto.",
                "No",
            ),
            (
                "Cliente",
                "Combobox",
                "Cliente titular del producto.",
                "Lista de clientes registrados",
            ),
            (
                "Categoría 1",
                "Combobox",
                "Categoría principal del riesgo (override por producto).",
                "settings.TAXONOMIA",
            ),
            (
                "Categoría 2",
                "Combobox",
                "Subcategoría del producto (override).",
                "settings.TAXONOMIA",
            ),
            (
                "Modalidad",
                "Combobox",
                "Modalidad específica (override).",
                "settings.TAXONOMIA",
            ),
            ("Canal", "Combobox", "Canal del evento (override).", "settings.CANAL_LIST"),
            ("Proceso", "Combobox", "Proceso impactado (override).", "settings.PROCESO_LIST"),
            (
                "Tipo de producto",
                "Combobox",
                "Clasificación comercial (tarjeta, crédito, etc.).",
                "settings.TIPO_PRODUCTO_LIST",
            ),
            (
                "Fecha de ocurrencia (YYYY-MM-DD)",
                "Selector de fecha",
                "Fecha del evento. Requerida; debe ser <= hoy y < descubrimiento.",
                "No",
            ),
            (
                "Fecha de descubrimiento (YYYY-MM-DD)",
                "Selector de fecha",
                "Fecha en que se detecta el evento. Requerida; <= hoy y > ocurrencia.",
                "No",
            ),
            (
                "Monto investigado",
                "Entry (número)",
                "Monto total investigado. Debe ser suma de pérdida+falla+contingencia+recuperado.",
                "No",
            ),
            ("Moneda", "Combobox", "Moneda principal.", "settings.TIPO_MONEDA_LIST"),
            (
                "Monto pérdida fraude",
                "Entry (número)",
                "Monto de pérdida por fraude. >=0, 12 dígitos, 2 decimales.",
                "No",
            ),
            (
                "Monto falla procesos",
                "Entry (número)",
                "Monto por falla de procesos. >=0, 12 dígitos, 2 decimales.",
                "No",
            ),
            (
                "Monto contingencia",
                "Entry (número)",
                "Monto de contingencia. Si tipo producto es crédito/tarjeta debe igualar al investigado.",
                "No",
            ),
            (
                "Monto recuperado",
                "Entry (número)",
                "Monto recuperado. No puede ser mayor que el monto investigado.",
                "No",
            ),
            (
                "Monto pago deuda",
                "Entry (número)",
                "Monto de pago de deuda. No puede exceder el monto investigado.",
                "No",
            ),
            (
                "Botón \"Ir al primer faltante\"",
                "Botón",
                "Navega al reclamo pendiente cuando hay montos > 0.",
                "",
            ),
            (
                "Botón \"Autocompletar analítica\"",
                "Botón",
                "Aplica una analítica preseleccionada al reclamo pendiente.",
                "Catálogo de analíticas",
            ),
        ]
    )

    rows.append(_section_row("Reclamos asociados", columns=len(headers)))
    rows.extend(
        [
            ("Botón \"Añadir reclamo\"", "Botón", "Agrega un reclamo al producto.", ""),
            (
                "ID reclamo",
                "Entry (texto)",
                "Código de reclamo (C + 8 dígitos). Obligatorio si pérdida/falla/contingencia > 0.",
                "claim_details.csv",
            ),
            (
                "Código analítica",
                "Combobox",
                "Código analítica contable de 10 dígitos (43/45/46/56...).",
                "models.analitica_catalog",
            ),
            (
                "Analítica nombre",
                "Combobox",
                "Nombre descriptivo de la analítica contable.",
                "models.analitica_catalog",
            ),
            ("Botón \"Eliminar reclamo\"", "Botón", "Elimina el reclamo del producto.", ""),
        ]
    )

    rows.append(_section_row("Involucramiento de colaboradores", columns=len(headers)))
    rows.extend(
        [
            ("Botón \"Añadir involucrado\"", "Botón", "Agrega un colaborador involucrado.", ""),
            (
                "Colaborador involucrado",
                "Combobox",
                "Selecciona colaborador relacionado con el producto.",
                "Lista de colaboradores",
            ),
            (
                "Monto asignado",
                "Entry (número)",
                "Monto asignado al colaborador (>=0, 12 dígitos, 2 decimales).",
                "No",
            ),
            ("Botón \"Eliminar involucrado\"", "Botón", "Elimina el involucrado.", ""),
        ]
    )

    rows.append(_section_row("Involucramiento de clientes", columns=len(headers)))
    rows.extend(
        [
            ("Botón \"Añadir cliente involucrado\"", "Botón", "Agrega un cliente involucrado.", ""),
            (
                "Cliente involucrado",
                "Combobox",
                "Selecciona cliente relacionado distinto del titular.",
                "Lista de clientes",
            ),
            (
                "Monto asignado",
                "Entry (número)",
                "Monto asignado al cliente involucrado.",
                "No",
            ),
            ("Botón \"Eliminar cliente involucrado\"", "Botón", "Elimina el involucrado.", ""),
            ("Botón \"Eliminar producto\"", "Botón", "Elimina el producto y sus relaciones.", ""),
        ]
    )

    rows.append(_section_row("4. Colaboradores involucrados", columns=len(headers)))
    rows.extend(
        [
            ("Tabla resumen de colaboradores", "Tabla", "Resumen de colaboradores registrados.", ""),
            ("Botón \"Añadir colaborador\"", "Botón", "Crea un colaborador.", ""),
            (
                "ID del colaborador",
                "Entry (texto)",
                "Identificador del Team Member (letra + 5 dígitos).",
                "team_details.csv",
            ),
            ("Nombres", "Entry (texto)", "Nombres del colaborador.", "team_details.csv"),
            ("Apellidos", "Entry (texto)", "Apellidos del colaborador.", "team_details.csv"),
            (
                "Flag",
                "Combobox",
                "Rol del colaborador (Involucrado/Relacionado/etc.).",
                "settings.FLAG_COLABORADOR_LIST",
            ),
            (
                "División",
                "Combobox",
                "División del colaborador (catálogo jerárquico).",
                "TEAM_HIERARCHY_CATALOG",
            ),
            (
                "Área",
                "Combobox",
                "Área dependiente de la división.",
                "TEAM_HIERARCHY_CATALOG",
            ),
            (
                "Servicio",
                "Combobox",
                "Servicio dependiente del área.",
                "TEAM_HIERARCHY_CATALOG",
            ),
            (
                "Puesto",
                "Combobox",
                "Puesto dependiente del servicio.",
                "TEAM_HIERARCHY_CATALOG",
            ),
            (
                "Fecha carta inmediatez (YYYY-MM-DD)",
                "Selector de fecha",
                "Fecha de emisión de carta de inmediatez.",
                "team_details.csv",
            ),
            (
                "Fecha carta renuncia (YYYY-MM-DD)",
                "Selector de fecha",
                "Fecha de renuncia del colaborador.",
                "team_details.csv",
            ),
            (
                "Nombre agencia",
                "Combobox",
                "Nombre de agencia (requerido si División=DCA/Canales y Área contiene 'area comercial').",
                "AGENCY_CATALOG",
            ),
            (
                "Código agencia",
                "Combobox",
                "Código de agencia (6 dígitos) requerido bajo condición de área comercial.",
                "AGENCY_CATALOG",
            ),
            (
                "Tipo de falta",
                "Combobox",
                "Clasificación de falta.",
                "settings.TIPO_FALTA_LIST",
            ),
            (
                "Tipo de sanción",
                "Combobox",
                "Clasificación de sanción.",
                "settings.TIPO_SANCION_LIST",
            ),
            ("Botón \"Eliminar colaborador\"", "Botón", "Elimina el colaborador del caso.", ""),
        ]
    )

    return [headers, *rows]


def _risk_rows() -> list[Sequence[str | None]]:
    headers = ("Campo", "Tipo", "Descripción", "Autocompletado / Fuente")
    rows: list[Sequence[str | None]] = []
    rows.append(_section_row("Riesgos identificados", columns=len(headers)))
    rows.extend(
        [
            ("Tabla resumen de riesgos", "Tabla", "Listado de riesgos registrados.", ""),
            ("Botón \"Agregar riesgo\"", "Botón", "Crea un riesgo en el caso.", ""),
            (
                "ID de riesgo",
                "Entry (texto)",
                "Identificador del riesgo (catálogo o libre).",
                "risk_details.csv",
            ),
            (
                "Agregar riesgo nuevo",
                "Checkbutton",
                "Activa el modo manual para riesgos no catalogados.",
                "No",
            ),
            (
                "Criticidad",
                "Combobox",
                "Severidad del riesgo (obligatoria en modo catálogo).",
                "settings.CRITICIDAD_LIST / risk_details.csv",
            ),
            ("Líder", "Entry (texto)", "Responsable del riesgo.", "risk_details.csv"),
            (
                "Exposición residual (US$)",
                "Entry (número)",
                "Monto estimado (>=0, 12 dígitos, 2 decimales).",
                "risk_details.csv",
            ),
            (
                "Descripción del riesgo",
                "Entry (texto)",
                "Descripción clara del riesgo.",
                "risk_details.csv",
            ),
            (
                "Planes de acción (IDs separados por ;)",
                "Entry (texto)",
                "Lista de planes asociados sin duplicados.",
                "risk_details.csv",
            ),
            ("Botón \"Eliminar riesgo\"", "Botón", "Elimina el riesgo del caso.", ""),
        ]
    )
    return [headers, *rows]


def _norm_rows() -> list[Sequence[str | None]]:
    headers = ("Campo", "Tipo", "Descripción", "Autocompletado / Fuente")
    rows: list[Sequence[str | None]] = []
    rows.append(_section_row("Registro de Normas", columns=len(headers)))
    rows.extend(
        [
            ("Tabla resumen de normas", "Tabla", "Listado de normas transgredidas.", ""),
            ("Botón \"Agregar norma\"", "Botón", "Crea una norma en el caso.", ""),
            (
                "ID de norma",
                "Entry (texto)",
                "Formato XXXX.XXX.XX.XX. Permite autopoblado desde catálogo.",
                "norm_details.csv",
            ),
            (
                "Fecha de vigencia (YYYY-MM-DD)",
                "Selector de fecha",
                "Fecha de publicación/vigencia. No puede ser futura.",
                "norm_details.csv",
            ),
            (
                "Descripción de la norma",
                "Entry (texto)",
                "Descripción o título de la norma transgredida.",
                "norm_details.csv",
            ),
            (
                "Acápite/Inciso",
                "Entry (texto)",
                "Referencia del acápite o inciso aplicable.",
                "norm_details.csv",
            ),
            (
                "Detalle de norma",
                "Texto enriquecido",
                "Detalle narrativo del incumplimiento.",
                "norm_details.csv",
            ),
            ("Botón \"Eliminar norma\"", "Botón", "Elimina la norma del caso.", ""),
        ]
    )
    return [headers, *rows]


def _analysis_rows() -> list[Sequence[str | None]]:
    headers = ("Campo", "Tipo", "Descripción", "Autocompletado / Fuente")
    rows: list[Sequence[str | None]] = []
    rows.append(_section_row("Análisis narrativo", columns=len(headers)))
    rows.extend(
        [
            (
                "Mostrar secciones extendidas del informe",
                "Checkbutton",
                "Habilita el notebook interno con secciones extendidas.",
                "No",
            ),
            ("Antecedentes", "Texto enriquecido", "Contexto del caso.", ""),
            ("Modus operandi", "Texto enriquecido", "Forma de ejecución del fraude.", ""),
            ("Hallazgos principales", "Texto enriquecido", "Hallazgos clave.", ""),
            ("Descargos del colaborador", "Texto enriquecido", "Descargos formales.", ""),
            ("Conclusiones", "Texto enriquecido", "Conclusiones generales.", ""),
            ("Recomendaciones y mejoras", "Texto enriquecido", "Acciones correctivas.", ""),
            (
                "Comentario breve",
                "Texto enriquecido",
                "Resumen sin saltos de línea (máx. 150 caracteres).",
                "",
            ),
            (
                "Comentario amplio",
                "Texto enriquecido",
                "Resumen amplio sin saltos de línea (máx. 750 caracteres).",
                "",
            ),
            (
                "Botón \"Auto-redactar\" (comentarios)",
                "Botón",
                "Genera un resumen automático sin PII.",
                "Modelo LLM",
            ),
        ]
    )
    rows.append(_section_row("Secciones extendidas del informe", columns=len(headers)))
    rows.extend(
        [
            ("Dirigido a", "Entry (texto)", "Destinatario del informe.", ""),
            ("Referencia", "Entry (texto)", "Referencia interna del caso.", ""),
            ("Área de reporte", "Entry (texto)", "Área que emite el informe.", ""),
            (
                "Fecha de reporte (YYYY-MM-DD)",
                "Entry (texto)",
                "Fecha del reporte. Debe ser <= hoy.",
                "",
            ),
            ("Tipología de evento", "Entry (texto)", "Tipología del evento.", ""),
            (
                "Centro de costos (; separados)",
                "Entry (texto)",
                "Centros de costos (numéricos, >=5 dígitos).",
                "",
            ),
            (
                "Procesos impactados",
                "Entry (texto)",
                "Lista de procesos impactados.",
                "",
            ),
            (
                "N° de reclamos",
                "Entry (texto)",
                "Cantidad total de reclamos (numérico).",
                "",
            ),
            (
                "Analítica contable",
                "Combobox",
                "Código/Nombre de analítica contable del catálogo.",
                "models.analitica_catalog",
            ),
            ("Producto (texto opcional)", "Entry (texto)", "Producto objetivo en texto libre.", ""),
            ("Recomendaciones categorizadas - Laboral", "Texto enriquecido", "Lista por ámbito laboral.", ""),
            ("Recomendaciones categorizadas - Operativo", "Texto enriquecido", "Lista por ámbito operativo.", ""),
            ("Recomendaciones categorizadas - Legal", "Texto enriquecido", "Lista por ámbito legal.", ""),
            (
                "Investigador principal - Matrícula/ID",
                "Entry (solo lectura)",
                "Se sincroniza desde Datos generales del caso.",
                "team_details.csv",
            ),
            (
                "Investigador principal - Nombre",
                "Entry (solo lectura)",
                "Autocompletado desde catálogos.",
                "team_details.csv",
            ),
            (
                "Investigador principal - Cargo",
                "Entry (solo lectura)",
                "Autocompletado desde catálogos.",
                "team_details.csv",
            ),
            ("Tabla de operaciones", "Tabla", "Registra operaciones vinculadas.", ""),
            (
                "Operación - Fecha aprobación",
                "Entry (texto)",
                "Fecha de aprobación (YYYY-MM-DD).",
                "",
            ),
            (
                "Operación - Importe desembolsado",
                "Entry (número)",
                "Monto con validación de 2 decimales.",
                "",
            ),
            (
                "Operación - Saldo deudor",
                "Entry (número)",
                "Monto con validación de 2 decimales.",
                "",
            ),
            ("Botón \"Agregar/Actualizar operación\"", "Botón", "Guarda o actualiza la operación.", ""),
            ("Botón \"Eliminar operación\"", "Botón", "Elimina la operación seleccionada.", ""),
            ("Botón \"Limpiar formulario\"", "Botón", "Limpia los campos de operación.", ""),
            ("Anexos y respaldos", "Tabla", "Control de anexos adjuntos.", ""),
            ("Anexo - Título", "Entry (texto)", "Título del anexo.", ""),
            ("Anexo - Descripción", "Entry (texto)", "Descripción del anexo.", ""),
            ("Botón \"Agregar/Actualizar anexo\"", "Botón", "Guarda el anexo en la tabla.", ""),
            ("Botón \"Eliminar anexo\"", "Botón", "Elimina el anexo seleccionado.", ""),
            ("Botón \"Limpiar\" (anexo)", "Botón", "Limpia el formulario de anexos.", ""),
        ]
    )
    return [headers, *rows]


def _actions_rows() -> list[Sequence[str | None]]:
    headers = ("Campo", "Tipo", "Descripción", "Autocompletado / Fuente")
    rows: list[Sequence[str | None]] = []
    rows.append(_section_row("Acciones", columns=len(headers)))
    rows.extend(
        [
            (
                "Sonido de confirmación",
                "Checkbutton",
                "Activa/desactiva sonido tras validaciones y exportes.",
                "Preferencias usuario",
            ),
            (
                "Botón conmutar tema",
                "Botón",
                "Cambia el tema oscuro/claro.",
                "ThemeManager",
            ),
            ("Catálogos de detalle", "Sección", "Controles para carga de catálogos.", ""),
            ("Estado/ayuda de catálogos", "Label", "Estado de carga de catálogos.", ""),
            ("Botón \"Cargar catálogos\"", "Botón", "Carga catálogos desde CSV.", ""),
            ("Botón \"Iniciar sin catálogos\"", "Botón", "Continúa sin catálogos.", ""),
            ("Barra de progreso de catálogos", "Progressbar", "Indicador de carga.", ""),
            ("Importar datos masivos (CSV)", "Sección", "Carga de archivos masivos.", ""),
            ("Botón \"Cargar clientes\"", "Botón", "Importa clientes masivos.", "clientes_masivos.csv"),
            ("Botón \"Cargar colaboradores\"", "Botón", "Importa colaboradores masivos.", "colaboradores_masivos.csv"),
            ("Botón \"Cargar productos\"", "Botón", "Importa productos masivos.", "productos_masivos.csv"),
            ("Botón \"Cargar combinado\"", "Botón", "Importa clientes/productos/colaboradores.", "datos_combinados_masivos.csv"),
            ("Botón \"Cargar riesgos\"", "Botón", "Importa riesgos masivos.", "riesgos_masivos.csv"),
            ("Botón \"Cargar normas\"", "Botón", "Importa normas masivas.", "normas_masivas.csv"),
            ("Botón \"Cargar reclamos\"", "Botón", "Importa reclamos masivos.", "reclamos_masivos.csv"),
            ("Estado de importación", "Label", "Estado de la importación masiva.", ""),
            ("Barra de progreso de importación", "Progressbar", "Indicador de importación.", ""),
            ("Guardar, cargar y reportes", "Sección", "Acciones de guardado y reportes.", ""),
            ("Botón \"Guardar ahora\"", "Botón", "Valida y guarda exportes.", ""),
            ("Botón \"Cargar archivo…\"", "Botón", "Carga un respaldo JSON.", ""),
            ("Botón \"Recuperar último autosave\"", "Botón", "Recupera último autosave.", ""),
            ("Botón \"Historial de recuperación\"", "Botón", "Abre historial de versiones.", ""),
            ("Botón \"Generar informe (.md)\"", "Botón", "Genera informe Markdown.", ""),
            ("Botón \"Generar Word (.docx)\"", "Botón", "Genera informe Word.", ""),
            ("Botón \"Generar alerta temprana (.pptx)\"", "Botón", "Genera alerta temprana PPT.", ""),
            ("Botón \"Generar carta de inmediatez\"", "Botón", "Genera carta de inmediatez.", ""),
            ("Botón \"Borrar todos los datos\"", "Botón", "Limpia el formulario.", ""),
            (
                "Codificación de exportación",
                "Combobox",
                "Selecciona codificación para CSV (UTF-8 recomendado).",
                "Preferencias usuario",
            ),
        ]
    )
    return [headers, *rows]


def _summary_rows() -> list[Sequence[str | None]]:
    headers = ("Sección/Tabla", "Tipo", "Descripción", "Autocompletado / Fuente")
    rows: list[Sequence[str | None]] = []
    rows.extend(
        [
            (
                "Label introductorio",
                "Label",
                "Introduce la sección de resumen con actualización automática.",
                "",
            ),
            (
                "Clientes registrados",
                "Tabla",
                "Columnas: ID Cliente, Nombres, Apellidos, Tipo ID, Flag, Teléfonos, Correos, Direcciones, Accionado.",
                "",
            ),
            (
                "Colaboradores involucrados",
                "Tabla",
                "Columnas: ID, Nombres, Apellidos, Flag, División, Área, Servicio, Puesto, Fechas, Agencia, Falta, Sanción.",
                "",
            ),
            (
                "Asignaciones de involucrados",
                "Tabla",
                "Columnas: Producto, Tipo, Colaborador/Cliente involucrado, Monto asignado.",
                "",
            ),
            (
                "Productos investigados",
                "Tabla",
                "Columnas: ID Producto, Cliente, Tipo, Taxonomía, Fechas, Montos, Reclamos.",
                "",
            ),
            (
                "Riesgos registrados",
                "Tabla",
                "Columnas: ID Riesgo, Líder, Descripción, Criticidad, Exposición, Planes.",
                "",
            ),
            (
                "Reclamos asociados",
                "Tabla",
                "Columnas: ID Reclamo, ID Caso, ID Producto, Analítica, Código analítica.",
                "",
            ),
            (
                "Normas transgredidas",
                "Tabla",
                "Columnas: ID Norma, ID Caso, Descripción, Vigencia, Acápite/Inciso, Detalle.",
                "",
            ),
        ]
    )
    return [headers, *rows]


def _export_structure_rows() -> list[Sequence[str | None]]:
    headers = ("Archivo", "Columna", "Tipo", "Descripción/Notas")
    rows: list[Sequence[str | None]] = []
    for file_name, fields in EXPORT_HEADERS.items():
        rows.append(_section_row(file_name, columns=len(headers)))
        for field in fields:
            if field.startswith("fecha"):
                field_type = "date"
            elif field.startswith("monto") or field in {"exposicion_residual"}:
                field_type = "decimal"
            else:
                field_type = "string"
            rows.append((file_name, field, field_type, ""))
    rows.append(_section_row("eventos.csv", columns=len(headers)))
    rows.append(("eventos.csv", "(ver hoja Eventos_CSV)", "string", "El esquema canónico se detalla aparte."))
    rows.append(_section_row("eventos_lhcl.csv", columns=len(headers)))
    rows.append(("eventos_lhcl.csv", "(igual que eventos.csv)", "string", "Export adicional con el mismo header canónico."))
    rows.append(_section_row("llave_tecnica.csv", columns=len(headers)))
    rows.append(("llave_tecnica.csv", "(ver build_llave_tecnica_rows)", "string", "Combina caso + producto + involucrados + reclamo."))
    rows.append(_section_row("logs.csv", columns=len(headers)))
    for field in LOG_FIELDNAMES:
        rows.append(("logs.csv", field, "string", "Bitácora de eventos y validaciones."))
    return [headers, *rows]


def _mapping_export_rows() -> list[Sequence[str | None]]:
    headers = ("Archivo", "Columna", "Origen (pestaña/campo)", "Transformación / Notas")
    rows: list[Sequence[str | None]] = []

    case_map = {
        "id_caso": "Caso y participantes > Número de caso",
        "tipo_informe": "Caso y participantes > Tipo de informe",
        "categoria1": "Caso y participantes > Categoría nivel 1",
        "categoria2": "Caso y participantes > Categoría nivel 2",
        "modalidad": "Caso y participantes > Modalidad",
        "canal": "Caso y participantes > Canal",
        "proceso": "Caso y participantes > Proceso impactado",
        "fecha_de_ocurrencia": "Caso y participantes > Ocurrencia",
        "fecha_de_descubrimiento": "Caso y participantes > Descubrimiento",
        "centro_costos": "Caso y participantes > Centro de costos",
        "matricula_investigador": "Caso y participantes > Matrícula investigador",
        "investigador_nombre": "Caso y participantes > Nombre y apellidos",
        "investigador_cargo": "Caso y participantes > Puesto",
    }
    for field in EXPORT_HEADERS["casos.csv"]:
        rows.append(("casos.csv", field, case_map.get(field, ""), ""))

    client_map = {
        "id_cliente": "Clientes > ID del cliente",
        "id_caso": "Caso y participantes > Número de caso",
        "nombres": "Clientes > Nombres",
        "apellidos": "Clientes > Apellidos",
        "tipo_id": "Clientes > Tipo de ID",
        "flag": "Clientes > Flag",
        "telefonos": "Clientes > Teléfonos",
        "correos": "Clientes > Correos",
        "direcciones": "Clientes > Direcciones",
        "accionado": "Clientes > Accionado",
    }
    for field in EXPORT_HEADERS["clientes.csv"]:
        rows.append(("clientes.csv", field, client_map.get(field, ""), ""))

    team_map = {
        "id_colaborador": "Colaboradores > ID del colaborador",
        "id_caso": "Caso y participantes > Número de caso",
        "flag": "Colaboradores > Flag",
        "nombres": "Colaboradores > Nombres",
        "apellidos": "Colaboradores > Apellidos",
        "division": "Colaboradores > División",
        "area": "Colaboradores > Área",
        "servicio": "Colaboradores > Servicio",
        "puesto": "Colaboradores > Puesto",
        "fecha_carta_inmediatez": "Colaboradores > Fecha carta inmediatez",
        "fecha_carta_renuncia": "Colaboradores > Fecha carta renuncia",
        "nombre_agencia": "Colaboradores > Nombre agencia",
        "codigo_agencia": "Colaboradores > Código agencia",
        "tipo_falta": "Colaboradores > Tipo de falta",
        "tipo_sancion": "Colaboradores > Tipo de sanción",
    }
    for field in EXPORT_HEADERS["colaboradores.csv"]:
        rows.append(("colaboradores.csv", field, team_map.get(field, ""), ""))

    product_map = {
        "id_producto": "Productos > ID del producto",
        "id_caso": "Caso y participantes > Número de caso",
        "id_cliente": "Productos > Cliente",
        "categoria1": "Productos > Categoría 1",
        "categoria2": "Productos > Categoría 2",
        "modalidad": "Productos > Modalidad",
        "canal": "Productos > Canal",
        "proceso": "Productos > Proceso",
        "fecha_ocurrencia": "Productos > Fecha de ocurrencia",
        "fecha_descubrimiento": "Productos > Fecha de descubrimiento",
        "monto_investigado": "Productos > Monto investigado",
        "tipo_moneda": "Productos > Moneda",
        "monto_perdida_fraude": "Productos > Monto pérdida fraude",
        "monto_falla_procesos": "Productos > Monto falla procesos",
        "monto_contingencia": "Productos > Monto contingencia",
        "monto_recuperado": "Productos > Monto recuperado",
        "monto_pago_deuda": "Productos > Monto pago deuda",
        "tipo_producto": "Productos > Tipo de producto",
    }
    for field in EXPORT_HEADERS["productos.csv"]:
        rows.append(("productos.csv", field, product_map.get(field, ""), ""))

    claim_map = {
        "id_reclamo": "Productos > Reclamos asociados > ID reclamo",
        "id_caso": "Caso y participantes > Número de caso",
        "id_producto": "Productos > ID del producto",
        "nombre_analitica": "Productos > Reclamos asociados > Analítica nombre",
        "codigo_analitica": "Productos > Reclamos asociados > Código analítica",
    }
    for field in EXPORT_HEADERS["producto_reclamo.csv"]:
        rows.append(("producto_reclamo.csv", field, claim_map.get(field, ""), ""))

    inv_map = {
        "id_producto": "Productos > ID del producto",
        "id_caso": "Caso y participantes > Número de caso",
        "tipo_involucrado": "Productos > Involucramientos",
        "id_colaborador": "Productos > Involucramiento colaboradores",
        "id_cliente_involucrado": "Productos > Involucramiento clientes",
        "monto_asignado": "Productos > Monto asignado",
    }
    for field in EXPORT_HEADERS["involucramiento.csv"]:
        rows.append(("involucramiento.csv", field, inv_map.get(field, ""), ""))

    risk_map = {
        "id_riesgo": "Riesgos > ID de riesgo",
        "id_caso": "Caso y participantes > Número de caso",
        "lider": "Riesgos > Líder",
        "descripcion": "Riesgos > Descripción",
        "criticidad": "Riesgos > Criticidad",
        "exposicion_residual": "Riesgos > Exposición residual",
        "planes_accion": "Riesgos > Planes de acción",
    }
    for field in EXPORT_HEADERS["detalles_riesgo.csv"]:
        rows.append(("detalles_riesgo.csv", field, risk_map.get(field, ""), ""))

    norm_map = {
        "id_norma": "Normas > ID de norma",
        "id_caso": "Caso y participantes > Número de caso",
        "descripcion": "Normas > Descripción",
        "fecha_vigencia": "Normas > Fecha vigencia",
        "acapite_inciso": "Normas > Acápite/Inciso",
        "detalle_norma": "Normas > Detalle de norma",
    }
    for field in EXPORT_HEADERS["detalles_norma.csv"]:
        rows.append(("detalles_norma.csv", field, norm_map.get(field, ""), ""))

    analysis_map = {
        "id_caso": "Caso y participantes > Número de caso",
        "antecedentes": "Análisis > Antecedentes",
        "modus_operandi": "Análisis > Modus operandi",
        "hallazgos": "Análisis > Hallazgos principales",
        "descargos": "Análisis > Descargos",
        "conclusiones": "Análisis > Conclusiones",
        "recomendaciones": "Análisis > Recomendaciones",
        "comentario_breve": "Análisis > Comentario breve",
        "comentario_amplio": "Análisis > Comentario amplio",
    }
    for field in EXPORT_HEADERS["analisis.csv"]:
        rows.append(("analisis.csv", field, analysis_map.get(field, ""), ""))

    return [headers, *rows]


def _eventos_rows() -> list[Sequence[str | None]]:
    headers = ("Columna", "Descripción", "Origen (pestaña/campo)", "Transformación / Notas")
    rows: list[Sequence[str | None]] = []
    alias_map = {
        "case_id": "id_caso",
        "id_caso": "case_id",
        "product_id": "id_producto",
        "id_producto": "product_id",
        "client_id_involucrado": "id_cliente_involucrado",
        "id_cliente_involucrado": "client_id_involucrado",
        "matricula_colaborador_involucrado": "id_colaborador",
        "id_colaborador": "matricula_colaborador_involucrado",
        "fecha_ocurrencia_caso": "fecha_ocurrencia",
        "fecha_descubrimiento_caso": "fecha_descubrimiento",
    }
    canonical_fields = set(EVENTOS_HEADER_CANONICO_START)
    for field in EVENTOS_HEADER_CANONICO:
        if field in canonical_fields:
            description = "Campo canónico de eventos."
        else:
            description = "Campo legado incluido por compatibilidad histórica."
        origin = ""
        notes = ""
        if field in {"case_id", "id_caso"}:
            origin = "Caso > Número de caso"
        elif field in {"tipo_informe"}:
            origin = "Caso > Tipo de informe"
        elif field in {"categoria_1", "categoria_2", "modalidad", "categoria1", "categoria2"}:
            origin = "Caso/Producto > Taxonomía"
        elif field in {"canal"}:
            origin = "Caso/Producto > Canal"
        elif field in {"proceso_impactado", "proceso"}:
            origin = "Caso/Producto > Proceso"
        elif field in {"product_id", "id_producto"}:
            origin = "Productos > ID del producto"
        elif field in {"tipo_de_producto", "tipo_producto"}:
            origin = "Productos > Tipo de producto"
        elif field.startswith("monto_"):
            origin = "Productos > Montos"
        elif field in {"tipo_moneda"}:
            origin = "Productos > Moneda"
        elif field in {"id_reclamo", "nombre_analitica", "codigo_analitica"}:
            origin = "Productos > Reclamos asociados"
        elif field in {"telefonos_cliente_relacionado", "correos_cliente_relacionado", "direcciones_cliente_relacionado", "accionado_cliente_relacionado"}:
            origin = "Clientes > Contacto"
        elif field in {"matricula_colaborador_involucrado", "id_colaborador"}:
            origin = "Productos > Involucramiento colaboradores"
        elif field in {"id_cliente_involucrado", "client_id_involucrado"}:
            origin = "Productos > Involucramiento clientes"
        elif field in {"comentario_breve", "comentario_amplio"}:
            origin = "Análisis > Comentarios"
        elif field in {"fecha_ocurrencia", "fecha_descubrimiento"}:
            origin = "Productos > Fechas"
        elif field in {"fecha_ocurrencia_caso", "fecha_descubrimiento_caso"}:
            origin = "Caso > Fechas"

        if field == "cod_operation":
            notes = "Se exporta como <SIN_DATO> (placeholder)."
        if field.endswith("_dolares"):
            notes = "Actualmente se llena con <SIN_DATO>."
        if field in alias_map:
            notes = f"{notes} Alias/compatibilidad con {alias_map[field]}.".strip()
        rows.append((field, description, origin, notes))
    return [headers, *rows]


def _logs_rows() -> list[Sequence[str | None]]:
    headers = ("Campo", "Descripción", "Origen / Uso")
    rows = [
        ("timestamp", "Fecha y hora del evento registrado.", "Generado automáticamente."),
        ("tipo", "Tipo general del evento (validacion, navegacion, etc.).", "log_event"),
        ("subtipo", "Subtipo o etiqueta específica.", "log_event"),
        ("widget_id", "Identificador del widget asociado.", "Widget registry"),
        ("coords", "Coordenadas del cursor.", "log_event"),
        ("mensaje", "Mensaje descriptivo del evento.", "Validadores/UI"),
        ("old_value", "Valor previo en validaciones.", "FieldValidator"),
        ("new_value", "Valor nuevo en validaciones.", "FieldValidator"),
        ("action_result", "Resultado de la acción (ok/error).", "FieldValidator"),
    ]
    return [headers, *rows]


def _carta_rows() -> list[Sequence[str | None]]:
    headers = ("Campo CSV/Placeholder", "Descripción", "Origen (pestaña/campo)", "Transformación / Notas")
    rows = [
        ("numero_caso", "ID del caso.", "Caso > Número de caso", "Valor directo"),
        ("fecha_generacion", "Fecha de generación de carta.", "Sistema", "YYYY-MM-DD"),
        ("mes", "Mes de generación.", "Sistema", "Formato MMMM"),
        ("investigador_principal", "Nombre investigador principal.", "Caso > Nombre investigador", ""),
        ("matricula_investigador", "Matrícula del investigador.", "Caso > Matrícula investigador", ""),
        ("matricula_team_member", "ID del colaborador.", "Colaboradores > ID", "Normalizado a mayúsculas"),
        ("Tipo", "Tipo de sede (Agencia/Sede).", "Colaboradores > División", "Agencia si división contiene 'comercial' o 'DCC'"),
        ("codigo_agencia", "Código de agencia.", "Colaboradores > Código agencia", ""),
        ("agencia", "Nombre de agencia.", "Colaboradores > Nombre agencia", ""),
        ("Numero_de_Carta", "Número correlativo de carta.", "Sistema", "Formato 000-AAAA"),
        ("Tipo_entrevista", "Tipo de entrevista.", "Colaboradores > Flag", "Involucrado/Relacionado"),
        ("FECHA_LARGA", "Fecha larga en plantilla DOCX.", "Sistema", "Formato largo (e.g. 12 de marzo de 2025)"),
        ("NOMBRE_COMPLETO", "Nombre del colaborador.", "Colaboradores > Nombres/Apellidos", "Usa matrícula si falta nombre"),
        ("MATRICULA", "Matrícula del colaborador.", "Colaboradores > ID", ""),
        ("APELLIDOS", "Apellidos del colaborador.", "Colaboradores > Apellidos", ""),
        ("AREA", "Área del colaborador.", "Colaboradores > Área", ""),
        ("NUMERO_CARTA", "Número de carta.", "Sistema", "Alias de Numero_de_Carta"),
        ("NUMERO_CASO", "Número de caso.", "Caso > Número de caso", ""),
        ("COLABORADOR", "Nombre visible del colaborador.", "Colaboradores > Nombres/Apellidos", ""),
        ("PUESTO", "Puesto del colaborador.", "Colaboradores > Puesto", ""),
        ("AGENCIA", "Agencia del colaborador.", "Colaboradores > Nombre agencia", ""),
        ("INVESTIGADOR", "Investigador principal.", "Caso > Nombre investigador", ""),
    ]
    return [headers, *rows]


def _gerencia_rows() -> list[Sequence[str | None]]:
    headers = ("Sección", "Descripción", "Campos y Transformaciones")
    rows = [
        (
            "Cabecera",
            "Datos generales del caso.",
            "Tipo de informe, número de caso, categoría, canal, proceso, fechas.",
        ),
        (
            "Antecedentes",
            "Narrativa principal.",
            "Texto de Antecedentes.",
        ),
        (
            "Colaboradores involucrados",
            "Resumen de colaboradores.",
            "Datos de pestaña Colaboradores + fechas de cartas.",
        ),
        (
            "Clientes involucrados",
            "Resumen de clientes.",
            "Datos de pestaña Clientes (tipo ID, nombres, flag, contacto).",
        ),
        (
            "Productos",
            "Resumen de productos investigados.",
            "Montos, fechas y reclamos asociados.",
        ),
        (
            "Riesgos Potenciales",
            "Riesgos registrados.",
            "ID riesgo, líder, descripción, criticidad, exposición.",
        ),
        (
            "Normas",
            "Normas transgredidas.",
            "ID norma, descripción, vigencia, acápite, detalle.",
        ),
        (
            "Análisis y Hallazgos",
            "Narrativa consolidada.",
            "Modus operandi + Hallazgos principales.",
        ),
        (
            "Descargos y Testimonios",
            "Sección de descargos.",
            "Descargos del colaborador.",
        ),
        (
            "Conclusiones y Recomendaciones",
            "Cierre del informe.",
            "Conclusiones + Recomendaciones.",
        ),
    ]
    return [headers, *rows]


def _alerta_rows() -> list[Sequence[str | None]]:
    headers = ("Sección de PPT", "Descripción", "Campos / Datos requeridos")
    rows = [
        (
            "Masthead",
            "Carátula del caso.",
            "ID caso, investigador, categoría, canal.",
        ),
        (
            "Resumen",
            "Resumen numérico.",
            "Suma de montos investigado, pérdida, falla, contingencia, recuperado.",
        ),
        (
            "Cronología",
            "Fechas clave del caso.",
            "Fechas de ocurrencia/descubrimiento (caso y productos).",
        ),
        (
            "Análisis",
            "Narrativa resumida.",
            "Texto consolidado de análisis y hallazgos.",
        ),
        (
            "Riesgos",
            "Listado de riesgos.",
            "ID riesgo, descripción, criticidad.",
        ),
        (
            "Acciones",
            "Acciones/recomendaciones.",
            "Recomendaciones + operaciones vinculadas.",
        ),
        (
            "Responsables",
            "Investigador y responsables.",
            "Investigador principal + colaboradores con flag y área.",
        ),
    ]
    return [headers, *rows]


def _validation_panel_rows() -> list[Sequence[str | None]]:
    headers = ("Campo / Validación", "Descripción de la regla", "Mensaje de error", "Fuente")
    rows = [
        (
            "Número de caso",
            "Formato AAAA-NNNN.",
            "El número de caso debe seguir el formato AAAA-NNNN.",
            "validators.validate_case_id",
        ),
        (
            "ID Proceso",
            "Formato BPID-XXXXXX o BPID-RNF-XXXXXX.",
            "El ID de proceso debe seguir el formato BPID-XXXXXX o BPID-RNF-XXXXXX.",
            "validators.validate_process_id",
        ),
        (
            "Fechas de caso",
            "Formato YYYY-MM-DD; ocurrencia < descubrimiento; ambas <= hoy.",
            "La fecha de ocurrencia debe ser anterior a la de descubrimiento.",
            "validators.validate_date_text",
        ),
        (
            "Fechas de producto",
            "Formato YYYY-MM-DD; ocurrencia < descubrimiento; ambas <= hoy.",
            "Las fechas del producto no pueden estar en el futuro.",
            "validators.validate_product_dates",
        ),
        (
            "Montos",
            ">=0, 12 dígitos, 2 decimales. Investigado = pérdida+falla+contingencia+recuperado.",
            "La suma de las cuatro partidas debe ser igual al monto investigado.",
            "ui/frames/products.py",
        ),
        (
            "Monto pago deuda",
            "Debe ser <= monto investigado.",
            "El pago de deuda no puede ser mayor al monto investigado.",
            "ui/frames/products.py",
        ),
        (
            "Monto contingencia (crédito/tarjeta)",
            "Debe igualar monto investigado si tipo producto es crédito o tarjeta.",
            "El monto de contingencia debe ser igual al monto investigado para créditos o tarjetas.",
            "ui/frames/products.py",
        ),
        (
            "Correo electrónico",
            "Formato válido para cada correo separado por ';'.",
            "El campo contiene un correo inválido: <correo>.",
            "validators.validate_email_list",
        ),
        (
            "Teléfono",
            "Formato +? y 6-15 dígitos, separados por ';'.",
            "El campo contiene un teléfono inválido: <tel>.",
            "validators.validate_phone_list",
        ),
        (
            "ID de reclamo",
            "Formato C########.",
            "El ID de reclamo debe tener el formato CXXXXXXXX.",
            "validators.validate_reclamo_id",
        ),
        (
            "Código de analítica",
            "10 dígitos, inicia 43/45/46/56.",
            "El código de analítica debe tener 10 dígitos y comenzar con 43/45/46/56.",
            "validators.validate_codigo_analitica",
        ),
        (
            "ID de norma",
            "Formato XXXX.XXX.XX.XX.",
            "El ID de norma debe seguir el formato XXXX.XXX.XX.XX.",
            "validators.validate_norm_id",
        ),
        (
            "ID de riesgo",
            "Hasta 60 caracteres; catálogo si aplica.",
            "El ID de riesgo no puede tener más de 60 caracteres.",
            "validators.validate_risk_id",
        ),
        (
            "ID de cliente",
            "Valida longitud según tipo de documento.",
            "Mensaje específico según tipo de documento.",
            "validators.validate_client_id",
        ),
        (
            "ID de colaborador",
            "Formato letra + 5 dígitos.",
            "El ID del colaborador debe iniciar con una letra seguida de 5 dígitos.",
            "validators.validate_team_member_id",
        ),
        (
            "Código de agencia",
            "6 dígitos numéricos.",
            "El código de agencia debe tener exactamente 6 dígitos.",
            "validators.validate_agency_code",
        ),
        (
            "Reclamos obligatorios",
            "Si pérdida/falla/contingencia > 0, se exige reclamo completo.",
            "Debe ingresar al menos un reclamo completo porque hay montos de pérdida/falla/contingencia.",
            "ui/frames/products.py",
        ),
        (
            "Agencia obligatoria",
            "Si división es DCA/Canales y área contiene 'area comercial', agencia es obligatoria.",
            "Debe ingresar nombre y código de agencia.",
            "ui/frames/team.py",
        ),
        (
            "Llave técnica",
            "No permite duplicados con combinación caso+producto+cliente+colaborador+fecha+reclamo.",
            "Ya existe un registro con la misma llave técnica.",
            "utils/technical_key.py",
        ),
    ]
    return [headers, *rows]


def _catalog_rows() -> list[Sequence[str | None]]:
    headers = ("Archivo de Catálogo/Detalle", "Columna en CSV", "Campo en la UI (Pestaña - Campo)", "Autocompletado", "Notas")
    rows = [
        ("client_details.csv", "id_cliente", "Clientes - ID del cliente", "Clave de búsqueda", ""),
        ("client_details.csv", "nombres", "Clientes - Nombres", "Sí", ""),
        ("client_details.csv", "apellidos", "Clientes - Apellidos", "Sí", ""),
        ("client_details.csv", "tipo_id", "Clientes - Tipo de ID", "Sí", ""),
        ("client_details.csv", "flag", "Clientes - Flag", "Sí", ""),
        ("client_details.csv", "telefonos", "Clientes - Teléfonos", "Sí", ""),
        ("client_details.csv", "correos", "Clientes - Correos", "Sí", ""),
        ("client_details.csv", "direcciones", "Clientes - Direcciones", "Sí", ""),
        ("client_details.csv", "accionado", "Clientes - Accionado", "Sí", ""),
        ("team_details.csv", "id_colaborador", "Colaboradores - ID del colaborador", "Clave de búsqueda", ""),
        ("team_details.csv", "nombres", "Colaboradores - Nombres", "Sí", ""),
        ("team_details.csv", "apellidos", "Colaboradores - Apellidos", "Sí", ""),
        ("team_details.csv", "flag", "Colaboradores - Flag", "Sí", ""),
        ("team_details.csv", "division", "Colaboradores - División", "Sí", ""),
        ("team_details.csv", "area", "Colaboradores - Área", "Sí", ""),
        ("team_details.csv", "servicio", "Colaboradores - Servicio", "Sí", ""),
        ("team_details.csv", "puesto", "Colaboradores - Puesto", "Sí", ""),
        ("team_details.csv", "fecha_carta_inmediatez", "Colaboradores - Fecha carta inmediatez", "Sí", ""),
        ("team_details.csv", "fecha_carta_renuncia", "Colaboradores - Fecha carta renuncia", "Sí", ""),
        ("team_details.csv", "nombre_agencia", "Colaboradores - Nombre agencia", "Sí", ""),
        ("team_details.csv", "codigo_agencia", "Colaboradores - Código agencia", "Sí", ""),
        ("team_details.csv", "tipo_falta", "Colaboradores - Tipo de falta", "Sí", ""),
        ("team_details.csv", "tipo_sancion", "Colaboradores - Tipo de sanción", "Sí", ""),
        ("team_details.csv", "fecha_actualizacion", "No visible en UI", "No", "Campo técnico del catálogo."),
        ("risk_details.csv", "id_riesgo", "Riesgos - ID de riesgo", "Clave de búsqueda", ""),
        ("risk_details.csv", "lider", "Riesgos - Líder", "Sí", ""),
        ("risk_details.csv", "descripcion", "Riesgos - Descripción", "Sí", ""),
        ("risk_details.csv", "criticidad", "Riesgos - Criticidad", "Sí", ""),
        ("risk_details.csv", "exposicion_residual", "Riesgos - Exposición residual", "Sí", ""),
        ("risk_details.csv", "planes_accion", "Riesgos - Planes de acción", "Sí", ""),
        ("risk_details.csv", "pda", "No visible en UI", "No", "Dato auxiliar del catálogo."),
        ("norm_details.csv", "id_norma", "Normas - ID de norma", "Clave de búsqueda", ""),
        ("norm_details.csv", "fecha_vigencia", "Normas - Fecha de vigencia", "Sí", ""),
        ("norm_details.csv", "descripcion", "Normas - Descripción", "Sí", ""),
        ("norm_details.csv", "acapite_inciso", "Normas - Acápite/Inciso", "Sí", ""),
        ("norm_details.csv", "detalle_norma", "Normas - Detalle de norma", "Sí", ""),
        ("process_details.csv", "id_proceso", "Caso/Productos - ID Proceso", "Clave de búsqueda", ""),
        ("process_details.csv", "proceso", "Caso/Productos - Proceso impactado", "Sí", ""),
        ("process_details.csv", "canal", "Caso/Productos - Canal", "Sí", ""),
        ("process_details.csv", "descripcion", "Selector de procesos", "Sí", "Se muestra en selector."),
        ("claim_details.csv", "id_reclamo", "Productos - ID reclamo", "Clave de búsqueda", ""),
        ("claim_details.csv", "nombre_analitica", "Productos - Analítica nombre", "Sí", ""),
        ("claim_details.csv", "codigo_analitica", "Productos - Código analítica", "Sí", ""),
        ("settings.TAXONOMIA", "-", "Caso/Productos - Taxonomía", "Catálogo interno", "Jerarquía categoría1 > categoría2 > modalidad."),
        ("settings.CANAL_LIST", "-", "Caso/Productos - Canal", "Catálogo interno", ""),
        ("settings.PROCESO_LIST", "-", "Caso/Productos - Proceso", "Catálogo interno", ""),
        ("settings.TIPO_PRODUCTO_LIST", "-", "Productos - Tipo de producto", "Catálogo interno", ""),
        ("settings.TIPO_MONEDA_LIST", "-", "Productos - Moneda", "Catálogo interno", ""),
        ("settings.TIPO_ID_LIST", "-", "Clientes - Tipo de ID", "Catálogo interno", ""),
        ("settings.FLAG_CLIENTE_LIST", "-", "Clientes - Flag", "Catálogo interno", ""),
        ("settings.ACCIONADO_OPTIONS", "-", "Clientes - Accionado", "Catálogo interno", ""),
        ("settings.FLAG_COLABORADOR_LIST", "-", "Colaboradores - Flag", "Catálogo interno", ""),
        ("settings.TIPO_FALTA_LIST", "-", "Colaboradores - Tipo de falta", "Catálogo interno", ""),
        ("settings.TIPO_SANCION_LIST", "-", "Colaboradores - Tipo de sanción", "Catálogo interno", ""),
        ("settings.CRITICIDAD_LIST", "-", "Riesgos - Criticidad", "Catálogo interno", ""),
        ("TEAM_HIERARCHY_CATALOG", "-", "Colaboradores - División/Área/Servicio/Puesto", "Catálogo interno", ""),
        ("AGENCY_CATALOG", "-", "Colaboradores - Agencia", "Catálogo interno", ""),
        ("models.analitica_catalog", "-", "Productos/Análisis - Analítica contable", "Catálogo interno", ""),
    ]
    return [headers, *rows]


def build_workbook() -> Workbook:
    workbook = Workbook()
    workbook.remove(workbook.active)

    sheets = {
        "Caso y Participantes": _case_and_participants_rows(),
        "Riesgos": _risk_rows(),
        "Normas": _norm_rows(),
        "Análisis y Narrativas": _analysis_rows(),
        "Acciones": _actions_rows(),
        "Resumen": _summary_rows(),
        "Reportes y CSV": _export_structure_rows(),
        "Mapeo Exportes": _mapping_export_rows(),
        "Eventos_CSV": _eventos_rows(),
        "Logs": _logs_rows(),
        "Carta_inmediatez": _carta_rows(),
        "Informe_Gerencia": _gerencia_rows(),
        "Alerta_Temprana": _alerta_rows(),
        "Panel_Validacion": _validation_panel_rows(),
        "Mapeo Catalogos": _catalog_rows(),
    }

    for name, data in sheets.items():
        sheet = workbook.create_sheet(title=name)
        headers, *rows = data
        _apply_headers(sheet, headers)
        _append_rows(sheet, rows)
        for column_cells in sheet.columns:
            max_len = max((len(str(cell.value)) if cell.value is not None else 0) for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = min(80, max(16, max_len + 2))
    return workbook


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el wireframe de Excel mejorado.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/formulario_investigaciones_wireframe_mejorado.xlsx"),
        help="Ruta de salida del Excel mejorado.",
    )
    args = parser.parse_args()

    workbook = build_workbook()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(args.output)
    print(f"Archivo generado en {args.output}")


if __name__ == "__main__":
    main()
