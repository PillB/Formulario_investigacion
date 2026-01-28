import os
from pathlib import Path

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

EVENTOS_PLACEHOLDER = "<SIN_DATO>"
EVENTOS_HEADER_CANONICO_START = [
    "case_id",
    "tipo_informe",
    "categoria_1",
    "categoria_2",
    "modalidad",
    "tipo_de_producto",
    "canal",
    "proceso_impactado",
    "product_id",
    "cod_operation",
    "monto_investigado",
    "tipo_moneda",
    "tipo_id_cliente_involucrado",
    "client_id_involucrado",
    "flag_cliente_involucrado",
    "nombres_cliente_involucrado",
    "apellidos_cliente_involucrado",
    "matricula_colaborador_involucrado",
    "apellido_paterno_involucrado",
    "apellido_materno_involucrado",
    "nombres_involucrado",
    "division",
    "area",
    "servicio",
    "nombre_agencia",
    "codigo_agencia",
    "puesto",
    "fecha_cese",
    "tipo_de_falta",
    "tipo_sancion",
    "fecha_ocurrencia_caso",
    "fecha_descubrimiento_caso",
    "monto_fraude_interno_soles",
    "monto_fraude_interno_dolares",
    "monto_fraude_externo_soles",
    "monto_fraude_externo_dolares",
    "monto_falla_en_proceso_soles",
    "monto_falla_en_proceso_dolares",
    "monto_contingencia_soles",
    "monto_contingencia_dolares",
    "monto_recuperado_soles",
    "monto_recuperado_dolares",
    "monto_pagado_soles",
    "monto_pagado_dolares",
    "comentario_breve",
    "comentario_amplio",
    "id_reclamo",
    "nombre_analitica",
    "codigo_analitica",
    "telefonos_cliente_relacionado",
    "correos_cliente_relacionado",
    "direcciones_cliente_relacionado",
    "accionado_cliente_relacionado",
]
EVENTOS_HEADER_LEGACY = [
    "id_caso",
    "tipo_informe",
    "categoria1",
    "categoria2",
    "modalidad",
    "canal",
    "proceso",
    "fecha_de_ocurrencia",
    "fecha_de_descubrimiento",
    "centro_costos",
    "matricula_investigador",
    "investigador_nombre",
    "investigador_cargo",
    "comentario_breve",
    "comentario_amplio",
    "id_producto",
    "id_cliente",
    "id_colaborador",
    "id_cliente_involucrado",
    "tipo_involucrado",
    "id_reclamo",
    "fecha_ocurrencia",
    "fecha_descubrimiento",
    "tipo_producto",
    "tipo_moneda",
    "monto_investigado",
    "monto_perdida_fraude",
    "monto_falla_procesos",
    "monto_contingencia",
    "monto_recuperado",
    "monto_pago_deuda",
    "nombre_analitica",
    "codigo_analitica",
    "cliente_nombres",
    "cliente_apellidos",
    "cliente_tipo_id",
    "cliente_flag",
    "cliente_telefonos",
    "cliente_correos",
    "cliente_direcciones",
    "cliente_accionado",
    "colaborador_flag",
    "colaborador_nombres",
    "colaborador_apellidos",
    "colaborador_division",
    "colaborador_area",
    "colaborador_servicio",
    "colaborador_puesto",
    "colaborador_fecha_carta_inmediatez",
    "colaborador_fecha_carta_renuncia",
    "colaborador_nombre_agencia",
    "colaborador_codigo_agencia",
    "colaborador_tipo_falta",
    "colaborador_tipo_sancion",
    "monto_asignado",
]
EVENTOS_HEADER_CANONICO = list(EVENTOS_HEADER_CANONICO_START)
EVENTOS_HEADER_DUPLICATES = {
    "id_caso",
    "categoria1",
    "categoria2",
    "proceso",
    "fecha_de_ocurrencia",
    "fecha_de_descubrimiento",
    "id_producto",
    "id_colaborador",
    "id_cliente_involucrado",
    "tipo_producto",
}
EVENTOS_HEADER_EXPORT = EVENTOS_HEADER_CANONICO_START + [
    field
    for field in EVENTOS_HEADER_LEGACY
    if field not in EVENTOS_HEADER_CANONICO_START and field not in EVENTOS_HEADER_DUPLICATES
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
EXTERNAL_DRIVE_DIR = os.path.join(BASE_DIR, "external drive")
EXTERNAL_LOGS_FILE = os.path.join(EXTERNAL_DRIVE_DIR, "logs.csv")
PENDING_CONSOLIDATION_FILE = os.path.join(BASE_DIR, "pending_consolidation.txt")
REPORT_TEMPLATE_PATH = Path(
    os.getenv("REPORT_TEMPLATE_PATH", os.path.join(BASE_DIR, "templates", "report_template.dotx"))
)
STORE_LOGS_LOCALLY = True
ENABLE_EXTENDED_ANALYSIS_SECTIONS = False
TEMP_AUTOSAVE_DEBOUNCE_SECONDS = 120
TEMP_AUTOSAVE_MAX_PER_CASE = 30
TEMP_AUTOSAVE_MAX_AGE_DAYS = 7
TEMP_AUTOSAVE_COMPRESS_OLD = True
RICH_TEXT_MAX_CHARS = 5000
CONFETTI_ENABLED = False


def ensure_external_drive_dir() -> Path:
    """Crea (si no existe) la carpeta local usada como unidad externa."""

    path = Path(EXTERNAL_DRIVE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path
TEAM_DETAILS_FILE = os.path.join(BASE_DIR, "team_details.csv")
CLIENT_DETAILS_FILE = os.path.join(BASE_DIR, "client_details.csv")
PRODUCT_DETAILS_FILE = os.path.join(BASE_DIR, "productos_masivos.csv")
CLAIM_DETAILS_FILE = os.path.join(BASE_DIR, "claim_details.csv")
AUTOSAVE_FILE = os.path.join(BASE_DIR, "autosave.json")
LOGS_FILE = os.path.join(BASE_DIR, "logs.csv")
MASSIVE_SAMPLE_FILES = {
    "clientes": os.path.join(BASE_DIR, "clientes_masivos.csv"),
    "colaboradores": os.path.join(BASE_DIR, "colaboradores_masivos.csv"),
    "productos": os.path.join(BASE_DIR, "productos_masivos.csv"),
    "riesgos": os.path.join(BASE_DIR, "riesgos_masivos.csv"),
    "normas": os.path.join(BASE_DIR, "normas_masivas.csv"),
    "reclamos": os.path.join(BASE_DIR, "reclamos_masivos.csv"),
    "combinado": os.path.join(BASE_DIR, "datos_combinados_masivos.csv"),
}
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
CLIENT_ID_ALIASES = ("IdCliente", "IDCliente")
TEAM_ID_ALIASES = ("IdColaborador", "IdTeamMember", "IDColaborador", "Id")
PRODUCT_ID_ALIASES = ("IdProducto", "IDProducto")
RISK_ID_ALIASES = ("IdRiesgo", "IDRiesgo")
NORM_ID_ALIASES = ("IdNorma", "IDNorma")
CLAIM_ID_ALIASES = ("IdReclamo", "IDReclamo")
DETAIL_LOOKUP_ALIASES = {
    "id_cliente": ("clientes", "cliente", "clients", "client"),
    "id_colaborador": ("colaboradores", "colaborador", "team", "teams"),
    "id_producto": ("productos", "producto", "product", "products"),
    "id_proceso": ("procesos", "proceso", "process", "processes"),
    "id_reclamo": ("reclamos", "reclamo", "claim", "claims"),
    "id_riesgo": ("riesgos", "riesgo", "risk", "risks"),
    "id_norma": ("normas", "norma", "norm", "norms", "rule", "rules"),
}

__all__ = [
    "ACCIONADO_OPTIONS",
    "AUTOSAVE_FILE",
    "BASE_DIR",
    "CANAL_LIST",
    "CLAIM_ID_ALIASES",
    "CLAIM_DETAILS_FILE",
    "CLIENT_DETAILS_FILE",
    "CLIENT_ID_ALIASES",
    "CRITICIDAD_LIST",
    "DETAIL_LOOKUP_ALIASES",
    "EVENTOS_HEADER_CANONICO",
    "EVENTOS_HEADER_CANONICO_START",
    "EVENTOS_HEADER_DUPLICATES",
    "EVENTOS_HEADER_EXPORT",
    "EVENTOS_HEADER_LEGACY",
    "EVENTOS_PLACEHOLDER",
    "EXTERNAL_DRIVE_DIR",
    "EXTERNAL_LOGS_FILE",
    "CONFETTI_ENABLED",
    "ENABLE_EXTENDED_ANALYSIS_SECTIONS",
    "FLAG_CLIENTE_LIST",
    "FLAG_COLABORADOR_LIST",
    "LOGS_FILE",
    "STORE_LOGS_LOCALLY",
    "MASSIVE_SAMPLE_FILES",
    "NORM_ID_ALIASES",
    "PRODUCT_DETAILS_FILE",
    "PRODUCT_ID_ALIASES",
    "PROCESO_LIST",
    "RISK_ID_ALIASES",
    "TEAM_DETAILS_FILE",
    "TEAM_ID_ALIASES",
    "TAXONOMIA",
    "TIPO_FALTA_LIST",
    "TIPO_ID_LIST",
    "TIPO_INFORME_LIST",
    "TIPO_MONEDA_LIST",
    "TIPO_PRODUCTO_LIST",
    "TEMP_AUTOSAVE_COMPRESS_OLD",
    "TEMP_AUTOSAVE_DEBOUNCE_SECONDS",
    "TEMP_AUTOSAVE_MAX_AGE_DAYS",
    "TEMP_AUTOSAVE_MAX_PER_CASE",
    "ensure_external_drive_dir",
    "PENDING_CONSOLIDATION_FILE",
]
