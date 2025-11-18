"""Validadores y utilitarios compartidos entre los distintos frames."""

from __future__ import annotations

import csv
import os
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Callable, Iterable, List, Optional

from tkinter import ttk

from settings import LOGS_FILE, TIPO_PRODUCTO_LIST
from ui.tooltips import ValidationTooltip


def validate_required_text(value: str, label: str) -> Optional[str]:
    if not value.strip():
        return f"Debe ingresar {label}."
    return None


def validate_case_id(value: str) -> Optional[str]:
    text = value.strip()
    if not text:
        return "Debe ingresar el número de caso."
    if not re.match(r"^\d{4}-\d{4}$", text):
        return "El número de caso debe seguir el formato AAAA-NNNN."
    return None


def validate_date_text(value: str, label: str, allow_blank: bool = True) -> Optional[str]:
    if not value.strip():
        return None if allow_blank else f"Debe ingresar {label}."
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return f"{label} debe tener el formato YYYY-MM-DD."
    return None


def validate_product_dates(producto_id: str, fecha_ocurrencia: str, fecha_descubrimiento: str) -> Optional[str]:
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
        return message
    today = datetime.today()
    if occ > today or desc > today:
        return f"Las fechas del producto {label} no pueden estar en el futuro"
    return None


def validate_money_bounds(value: str, label: str, allow_blank: bool = True):
    text = (value or "").strip()
    if not text:
        return (None, None) if allow_blank else (f"Debe ingresar {label}.", None)
    try:
        with localcontext() as ctx:
            ctx.prec = 20
            amount = Decimal(text)
    except InvalidOperation:
        return (f"{label} debe ser un número válido.", None)
    quantized = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if quantized < 0:
        return (f"{label} no puede ser negativo.", None)
    if len(quantized.as_tuple().digits) > 12:
        return (f"{label} no puede tener más de 12 dígitos.", None)
    return (None, quantized)


def validate_amount_text(value: str, label: str, allow_blank: bool = True) -> Optional[str]:
    return validate_money_bounds(value, label, allow_blank)[0]


def sum_investigation_components(*, perdida: Decimal, falla: Decimal, contingencia: Decimal, recuperado: Decimal) -> Decimal:
    return perdida + falla + contingencia + recuperado


def validate_email_list(value: str, label: str) -> Optional[str]:
    emails = [item.strip() for item in value.split(';') if item.strip()]
    pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    for email in emails:
        if not pattern.fullmatch(email):
            return f"{label} contiene un correo inválido: {email}"
    return None


def validate_phone_list(value: str, label: str) -> Optional[str]:
    phones = [item.strip() for item in value.split(';') if item.strip()]
    for phone in phones:
        if not re.fullmatch(r"^\+?\d{6,15}$", phone):
            return f"{label} contiene un teléfono inválido: {phone}"
    return None


def validate_reclamo_id(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID de reclamo."
    if not re.fullmatch(r"^C\d{8}$", text):
        return "El ID de reclamo debe tener el formato CXXXXXXXX."
    return None


def validate_codigo_analitica(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return "Debe ingresar el código de analítica."
    if not re.fullmatch(r"^(43|45|46|56)\d{8}$", text):
        return "El código de analítica debe tener 10 dígitos y comenzar con 43, 45, 46 o 56."
    return None


def validate_norm_id(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID de norma."
    if not re.fullmatch(r"NRM-\d{5}$", text):
        return "El ID de norma debe seguir el formato NRM-XXXXX."
    return None


def validate_risk_id(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID de riesgo."
    if not re.fullmatch(r"RSK-\d{6}$", text):
        return "El ID de riesgo debe seguir el formato RSK-XXXXXX."
    return None


def validate_multi_selection(value: str, label: str) -> Optional[str]:
    if not value.strip():
        return f"Debe seleccionar al menos una opción en {label}."
    return None


def normalize_without_accents(value: str) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


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
TIPO_PRODUCTO_CATALOG = {
    normalize_without_accents(item).lower(): item
    for item in TIPO_PRODUCTO_LIST
}
TIPO_PRODUCTO_NORMALIZED = set(TIPO_PRODUCTO_CATALOG.keys())


def validate_client_id(tipo_id: str, value: str) -> Optional[str]:
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


def validate_team_member_id(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID del colaborador."
    if not TEAM_MEMBER_ID_PATTERN.fullmatch(text):
        return "El ID del colaborador debe iniciar con una letra seguida de 5 dígitos."
    return None


def validate_agency_code(value: str, allow_blank: bool = True) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return None if allow_blank else "Debe ingresar el código de agencia."
    if not AGENCY_CODE_PATTERN.fullmatch(text):
        return "El código de agencia debe tener exactamente 6 dígitos."
    return None


def resolve_catalog_product_type(value: str) -> Optional[str]:
    normalized = normalize_without_accents((value or "").strip()).lower()
    if not normalized:
        return None
    return TIPO_PRODUCTO_CATALOG.get(normalized)


def validate_product_id(tipo_producto: str, value: str) -> Optional[str]:
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


class FieldValidator:
    """Vincula un widget con una función de validación en tiempo real."""

    def __init__(
        self,
        widget,
        validate_callback: Callable[[], Optional[str]],
        logs: List[dict],
        field_name: str,
        variables: Optional[List] = None,
    ) -> None:
        self.widget = widget
        self.validate_callback = validate_callback
        self.logs = logs
        self.field_name = field_name
        self.tooltip = ValidationTooltip(widget)
        self.variables = variables or []
        self._traces: List[str] = []
        self.last_error: Optional[str] = None
        self._suspend_count = 0
        self._validation_armed = False
        for var in self.variables:
            self._traces.append(var.trace_add("write", self._on_change))
        widget.bind("<FocusOut>", self._on_change)
        widget.bind("<KeyRelease>", self._on_change)
        if isinstance(widget, ttk.Combobox):
            widget.bind("<<ComboboxSelected>>", self._on_change)

    def _on_change(self, *_args):
        if self._suspend_count > 0:
            return
        event = _args[0] if _args else None
        is_user_event = hasattr(event, "widget")
        if is_user_event:
            self._validation_armed = True
        elif not self._validation_armed:
            return
        error = self.validate_callback()
        self._display_error(error)

    def _display_error(self, error: Optional[str]) -> None:
        if error == self.last_error:
            return
        if error:
            self.tooltip.show(error)
            log_event("validacion", f"{self.field_name}: {error}", self.logs)
        else:
            self.tooltip.hide()
        self.last_error = error

    def show_custom_error(self, message: Optional[str]) -> None:
        self._validation_armed = True
        self._display_error(message)

    def suppress_during(self, callback: Callable):
        self._suspend_count += 1
        try:
            return callback()
        finally:
            self._suspend_count -= 1


def parse_decimal_amount(amount_string: str | Decimal | None) -> Optional[Decimal]:
    message, value = validate_money_bounds(amount_string or "", "monto", allow_blank=True)
    if message:
        return None
    return value or Decimal('0')


def should_autofill_field(current_value, preserve_existing: bool) -> bool:
    if not preserve_existing:
        return True
    if current_value is None:
        return True
    if isinstance(current_value, str):
        return not current_value.strip()
    return False


SAVE_TEMP_CALLBACK = None


def log_event(event_type: str, message: str, logs: List[dict]) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {"timestamp": timestamp, "tipo": event_type, "mensaje": message}
    logs.append(row)
    _append_log_to_disk(row)
    if SAVE_TEMP_CALLBACK is not None and event_type == 'navegacion':
        try:
            SAVE_TEMP_CALLBACK()
        except Exception:
            pass


def _append_log_to_disk(row: dict) -> None:
    if not LOGS_FILE:
        return
    folder = os.path.dirname(LOGS_FILE)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    file_exists = os.path.exists(LOGS_FILE)
    try:
        with open(LOGS_FILE, 'a', newline='', encoding='utf-8') as file_handle:
            writer = csv.DictWriter(file_handle, fieldnames=['timestamp', 'tipo', 'mensaje'])
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except OSError:
        pass


def escape_csv(value) -> str:
    if value is None:
        return ""
    text = str(value)
    if any(ch in text for ch in [',', '\n', '"']):
        text = text.replace('"', '""')
        text = f'"{text}"'
    return text


__all__ = [
    'FieldValidator',
    'SAVE_TEMP_CALLBACK',
    'escape_csv',
    'log_event',
    'normalize_without_accents',
    'parse_decimal_amount',
    'resolve_catalog_product_type',
    'should_autofill_field',
    'sum_investigation_components',
    'validate_agency_code',
    'validate_amount_text',
    'validate_case_id',
    'validate_client_id',
    'validate_codigo_analitica',
    'validate_date_text',
    'validate_email_list',
    'validate_money_bounds',
    'validate_multi_selection',
    'validate_norm_id',
    'validate_phone_list',
    'validate_product_dates',
    'validate_product_id',
    'validate_reclamo_id',
    'validate_required_text',
    'validate_risk_id',
    'validate_team_member_id',
]
