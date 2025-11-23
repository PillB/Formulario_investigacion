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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
EXTERNAL_DRIVE_DIR = os.path.join(BASE_DIR, "external drive")
EXTERNAL_LOGS_FILE = os.path.join(EXTERNAL_DRIVE_DIR, "logs.csv")
STORE_LOGS_LOCALLY = True
TEMP_AUTOSAVE_DEBOUNCE_SECONDS = 120
TEMP_AUTOSAVE_MAX_PER_CASE = 30
TEMP_AUTOSAVE_MAX_AGE_DAYS = 7
TEMP_AUTOSAVE_COMPRESS_OLD = True
RICH_TEXT_MAX_CHARS = 5000


def ensure_external_drive_dir() -> Path:
    """Crea (si no existe) la carpeta local usada como unidad externa."""

    path = Path(EXTERNAL_DRIVE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path
TEAM_DETAILS_FILE = os.path.join(BASE_DIR, "team_details.csv")
CLIENT_DETAILS_FILE = os.path.join(BASE_DIR, "client_details.csv")
PRODUCT_DETAILS_FILE = os.path.join(BASE_DIR, "productos_masivos.csv")
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
    "id_reclamo": ("reclamos", "reclamo", "claim", "claims"),
    "id_riesgo": ("riesgos", "riesgo", "risk", "risks"),
    "id_norma": ("normas", "norma", "rule", "rules"),
}

__all__ = [
    "ACCIONADO_OPTIONS",
    "AUTOSAVE_FILE",
    "BASE_DIR",
    "CANAL_LIST",
    "CLAIM_ID_ALIASES",
    "CLIENT_DETAILS_FILE",
    "CLIENT_ID_ALIASES",
    "CRITICIDAD_LIST",
    "DETAIL_LOOKUP_ALIASES",
    "EXTERNAL_DRIVE_DIR",
    "EXTERNAL_LOGS_FILE",
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
]
