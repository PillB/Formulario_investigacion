"""Validadores y utilitarios compartidos entre los distintos frames."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_UP
from typing import Callable, Dict, List, Optional, Tuple

from tkinter import TclError, messagebox

from settings import RICH_TEXT_MAX_CHARS, TIPO_PRODUCTO_LIST
from ui.tooltips import ValidationTooltip

_LOG_QUEUE: List[dict] = []
LOG_FIELDNAMES = ["timestamp", "tipo", "subtipo", "widget_id", "coords", "mensaje"]


def _scrub_control_characters(text: str) -> str:
    return "".join(
        ch for ch in text if ch == "\n" or unicodedata.category(ch) != "Cc"
    )


def _sanitize_log_value(
    value, *, neutralize_formulas: bool = False, collapse_newlines: bool = True
) -> str:
    normalized = "" if value is None else str(value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    sanitized = _scrub_control_characters(normalized)
    if collapse_newlines:
        sanitized = re.sub(r"\n+", " ", sanitized)
    if neutralize_formulas and sanitized.startswith(("=", "+", "-", "@")):
        sanitized = "'" + sanitized
    return sanitized


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


def _parse_date(value: str) -> Optional[datetime]:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None


def validate_date_text(
    value: str,
    label: str,
    allow_blank: bool = True,
    *,
    enforce_max_today: bool = False,
    must_be_before: Optional[Tuple[str, str]] = None,
    must_be_after: Optional[Tuple[str, str]] = None,
) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return None if allow_blank else f"Debe ingresar {label}."

    parsed_date = _parse_date(text)
    if not parsed_date:
        return f"{label} debe tener el formato YYYY-MM-DD."

    today = datetime.today().date()
    if enforce_max_today and parsed_date.date() > today:
        return f"{label} no puede estar en el futuro."

    if must_be_before:
        other_value, other_label = must_be_before
        other_date = _parse_date(other_value)
        if other_date and parsed_date >= other_date:
            compare_label = other_label or "la fecha de referencia"
            return f"{label} debe ser anterior a {compare_label}."

    if must_be_after:
        other_value, other_label = must_be_after
        other_date = _parse_date(other_value)
        if other_date and parsed_date <= other_date:
            compare_label = other_label or "la fecha de referencia"
            return f"{label} debe ser posterior a {compare_label}."

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
        return (None, None, "") if allow_blank else (f"Debe ingresar {label}.", None, "")
    try:
        with localcontext() as ctx:
            ctx.prec = 20
            amount = Decimal(text)
    except InvalidOperation:
        return (f"{label} debe ser un número válido.", None, "")
    amount_tuple = amount.as_tuple()
    if amount_tuple.exponent < -2:
        return (f"{label} solo puede tener dos decimales como máximo.", None, "")
    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quantized < 0:
        return (f"{label} no puede ser negativo.", None, "")

    normalized_text = f"{quantized:.2f}"
    integer_part = normalized_text.split(".")[0].lstrip("-")
    if len(integer_part) > 12:
        return (f"{label} no puede tener más de 12 dígitos en la parte entera.", None, "")
    return (None, quantized, normalized_text)


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


PROCESS_ID_PATTERN = re.compile(r"^BPID-(?:RNF-)?\d{6}$")


def validate_process_id(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID de proceso."
    if not PROCESS_ID_PATTERN.fullmatch(text):
        return "El ID de proceso debe seguir el formato BPID-XXXXXX o BPID-RNF-XXXXXX."
    return None


def validate_codigo_analitica(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return "Debe ingresar el código de analítica."
    if not re.fullmatch(r"^(43|45|46|56)\d{8}$", text):
        return "El código de analítica debe tener 10 dígitos y comenzar con 43, 45, 46 o 56."
    return None


NORM_ID_PATTERN = re.compile(r"^\d{4}\.\d{3}\.\d{2}\.\d{2}$")


def validate_norm_id(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID de norma."
    if not NORM_ID_PATTERN.fullmatch(text):
        return "El ID de norma debe seguir el formato XXXX.XXX.XX.XX."
    return None


RISK_ID_PATTERN = re.compile(r"^RSK-\d+$")


def validate_risk_id(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return "Debe ingresar el ID de riesgo."
    if len(text) > 60:
        return "El ID de riesgo no puede tener más de 60 caracteres."
    if not all(ch.isprintable() for ch in text):
        return "El ID de riesgo solo puede usar caracteres imprimibles."
    return None


def validate_catalog_risk_id(value: str) -> Optional[str]:
    base_error = validate_risk_id(value)
    if base_error:
        return base_error
    if not RISK_ID_PATTERN.fullmatch((value or "").strip()):
        return "El ID de riesgo de catálogo debe seguir el formato RSK-########."
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


ProductFamilyRule = Tuple[re.Pattern[str], str]

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
ACCOUNT_PRODUCT_RULE: ProductFamilyRule = (
    re.compile(r"^(?:\d{10,18}|(?=.*[A-Za-z])[A-Za-z0-9]{20})$"),
    (
        "Los productos de ahorro, cuentas y depósitos deben usar IDs numéricos de 10 a 18 dígitos "
        "(formato CM BCP) o un identificador alfanumérico de 20 caracteres que incluya al menos una letra."
    ),
)
RAW_PRODUCT_FAMILY_RULES: Dict[str, ProductFamilyRule] = {
    "cuenta de ahorro": ACCOUNT_PRODUCT_RULE,
    "cuenta corriente": ACCOUNT_PRODUCT_RULE,
    "cuenta a plazo": ACCOUNT_PRODUCT_RULE,
    "deposito a plazo": ACCOUNT_PRODUCT_RULE,
    "cts": ACCOUNT_PRODUCT_RULE,
}
ALPHANUMERIC_PRODUCT_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{4,30}$")
PRODUCT_FAMILY_VALIDATORS: Dict[str, ProductFamilyRule] = {
    normalize_without_accents(key).lower(): rule
    for key, rule in RAW_PRODUCT_FAMILY_RULES.items()
}


def _match_product_family_rule(tipo_normalized: str) -> Optional[ProductFamilyRule]:
    for keyword, rule in PRODUCT_FAMILY_VALIDATORS.items():
        if keyword and keyword in tipo_normalized:
            return rule
    return None

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


def normalize_team_member_identifier(value: str) -> str:
    """Devuelve el ID del colaborador sin espacios y en mayúsculas."""

    return (value or "").strip().upper()


def validate_team_member_id(value: str) -> Optional[str]:
    text = normalize_team_member_identifier(value)
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
        if not (text.isalnum() and len(text) == 16):
            return "Para tarjetas el ID debe tener 16 caracteres alfanuméricos."
        return None
    if "credito" in tipo_normalized:
        if not (text.isalnum() and len(text) in PRODUCT_CREDIT_LENGTHS):
            return "Para créditos el ID debe tener 13, 14, 16 o 20 caracteres alfanuméricos."
        return None
    family_rule = _match_product_family_rule(tipo_normalized)
    if family_rule:
        pattern, message = family_rule
        if not pattern.fullmatch(text):
            return message
        return None
    if not ALPHANUMERIC_PRODUCT_ID_PATTERN.fullmatch(text):
        return (
            "El ID del producto debe ser alfanumérico y tener entre 4 y 30 caracteres para productos no crediticios."
        )
    return None


class FieldValidator:
    """Vincula un widget con una función de validación en tiempo real."""

    modal_notifications_enabled = True
    status_consumer: Optional[Callable[[str, Optional[str], object], None]] = None
    # Permite que los tests o herramientas de depuración recopilen instancias
    # sin necesidad de aplicar un monkeypatch explícito. Si ``instance_registry``
    # o ``instances`` apunta a una lista, cada validador se añadirá
    # automáticamente.
    instance_registry: Optional[list] = None

    @classmethod
    def set_status_consumer(
        cls, consumer: Optional[Callable[[str, Optional[str], object], None]]
    ) -> None:
        """Permite publicar los resultados de validación en un panel externo."""

        cls.status_consumer = consumer

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
        self._debounce_job: Optional[str] = None
        self._last_validated_value = self._capture_current_value()
        for var in self.variables:
            self._traces.append(var.trace_add("write", self._on_change))
        self._bind_widget_events(widget)
        self._register_instance()

    def suspend(self) -> None:
        self._suspend_count += 1

    def resume(self) -> None:
        if self._suspend_count > 0:
            self._suspend_count -= 1

    def _register_instance(self) -> None:
        registry = getattr(self.__class__, "instance_registry", None)
        if registry is None:
            registry = getattr(self.__class__, "instances", None)
        if isinstance(registry, list):
            registry.append(self)

    def _bind_widget_events(self, widget) -> None:
        for event_name in (
            "<FocusOut>",
            "<<ComboboxSelected>>",
            "<<Paste>>",
            "<<Cut>>",
        ):
            widget.bind(
                event_name,
                lambda event, name=event_name: self._on_change(name, event),
                add="+",
            )

    def add_widget(self, widget) -> None:
        """Incluye widgets adicionales cuyos eventos deben disparar la validación."""

        self._bind_widget_events(widget)

    def _on_change(self, event_name=None, *_args):
        if self._suspend_count > 0:
            return
        if event_name is not None and not isinstance(event_name, str):
            event = event_name
            event_name = None
        else:
            event = _args[0] if _args else None
        current_value = self._capture_current_value()
        value_changed_since_validation = current_value != self._last_validated_value
        is_user_event = hasattr(event, "widget")
        is_focus_out = event_name == "<FocusOut>" or (is_user_event and self._is_focus_out(event))
        is_commit_event = event_name in {"<<ComboboxSelected>>", "<<Paste>>", "<<Cut>>"}
        is_variable_trace = (
            isinstance(event_name, str)
            and not event_name.startswith("<")
            and not event_name.startswith("<<")
            and not is_user_event
        )

        should_validate = False
        allow_modal_notifications = False

        if is_variable_trace:
            if value_changed_since_validation:
                self._validation_armed = True
                self._schedule_validation(
                    allow_modal_notifications=False,
                    transient=False,
                    is_focus_out=False,
                )
            return

        if is_focus_out and (value_changed_since_validation or self._validation_armed):
            should_validate = True
            allow_modal_notifications = True
            self._validation_armed = False
        elif is_commit_event:
            self._validation_armed = True
            should_validate = True
        elif is_user_event and not is_focus_out:
            self._validation_armed = True

        if not should_validate:
            return

        self._cancel_pending_validation()
        self._run_validation(
            allow_modal_notifications=allow_modal_notifications,
            transient=is_focus_out,
            is_focus_out=is_focus_out,
        )

    def _run_validation(
        self,
        *,
        allow_modal_notifications: bool,
        transient: bool,
        is_focus_out: bool,
    ) -> None:
        self._debounce_job = None
        error = self.validate_callback()
        self._display_error(
            error,
            allow_modal=allow_modal_notifications,
            transient=transient,
        )
        self._last_validated_value = self._capture_current_value()
        if not is_focus_out:
            self._validation_armed = False

    def _schedule_validation(
        self,
        *,
        allow_modal_notifications: bool,
        transient: bool,
        is_focus_out: bool,
        delay_ms: int = 120,
    ) -> None:
        self._cancel_pending_validation()
        after = getattr(self.widget, "after", None)
        if callable(after):
            try:
                self._debounce_job = after(
                    delay_ms,
                    lambda: self._run_validation(
                        allow_modal_notifications=allow_modal_notifications,
                        transient=transient,
                        is_focus_out=is_focus_out,
                    ),
                )
                return
            except Exception:
                self._debounce_job = None
        self._run_validation(
            allow_modal_notifications=allow_modal_notifications,
            transient=transient,
            is_focus_out=is_focus_out,
        )

    def _cancel_pending_validation(self) -> None:
        if not self._debounce_job:
            return
        after_cancel = getattr(self.widget, "after_cancel", None)
        if callable(after_cancel):
            try:
                after_cancel(self._debounce_job)
            except Exception:
                pass
        self._debounce_job = None

    def _capture_current_value(self):
        if self.variables:
            return tuple(var.get() for var in self.variables)
        getter = getattr(self.widget, "get", None)
        if getter:
            try:
                return getter()
            except Exception:
                return None
        return None

    @staticmethod
    def _is_focus_out(event) -> bool:
        event_type = getattr(event, "type", None)
        try:
            from tkinter import EventType

            if event_type == EventType.FocusOut:
                return True
        except Exception:
            pass
        return str(event_type) == "FocusOut" or event_type == "9"

    def _display_error(
        self,
        error: Optional[str],
        *,
        allow_modal: bool = True,
        transient: bool = False,
    ) -> None:
        tooltip_visible = getattr(self.tooltip, "is_visible", True)
        if callable(tooltip_visible):
            try:
                tooltip_visible = tooltip_visible()
            except Exception:
                tooltip_visible = True
        if error == self.last_error and tooltip_visible:
            return
        consumer = self.__class__.status_consumer
        if error:
            if consumer:
                consumer(self.field_name, error, self.widget)
            elif allow_modal:
                self._notify_modal_error(error)
            auto_hide_ms = 1500 if transient else None
            try:
                self.tooltip.show(error, auto_hide_ms=auto_hide_ms)
            except TypeError:
                self.tooltip.show(error)
            log_event("validacion", f"{self.field_name}: {error}", self.logs)
        else:
            if consumer:
                consumer(self.field_name, None, self.widget)
            self.tooltip.hide()
        self.last_error = error

    def _notify_modal_error(self, error: str) -> None:
        if not self.modal_notifications_enabled:
            return
        message = f"{self.field_name}: {error}"
        try:
            messagebox.showerror("Error de validación", message)
        except TclError:
            return

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
    message, value, _ = validate_money_bounds(amount_string or "", "monto", allow_blank=True)
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


def sanitize_rich_text(text: str | None, max_chars: Optional[int] = RICH_TEXT_MAX_CHARS) -> str:
    """Normaliza texto enriquecido eliminando caracteres de control y aplicando un límite.

    Args:
        text: Texto a limpiar. Se convierte a ``str`` si no lo es.
        max_chars: Máximo de caracteres permitidos tras la limpieza. Si es ``None``
            o un valor menor que 1 no se aplica truncamiento.

    Returns:
        Texto saneado sin caracteres de control no imprimibles, con saltos de línea
        normalizados y recortado al límite especificado.
    """

    normalized = "" if text is None else str(text).replace("\r\n", "\n").replace("\r", "\n")
    filtered_chars = [
        ch for ch in normalized if ch in {"\n", "\t"} or ch.isprintable()
    ]
    sanitized = "".join(filtered_chars)
    if max_chars is not None and max_chars > 0:
        return sanitized[:max_chars]
    return sanitized


def _serialize_coords(coords) -> str:
    if coords is None:
        return ""
    if isinstance(coords, (list, tuple)) and len(coords) == 2:
        return f"{coords[0]},{coords[1]}"
    return str(coords)


def normalize_log_row(row: dict) -> dict:
    return {
        "timestamp": _sanitize_log_value(row.get("timestamp", "")),
        "tipo": _sanitize_log_value(row.get("tipo", "")),
        "subtipo": _sanitize_log_value(row.get("subtipo", "")),
        "widget_id": _sanitize_log_value(
            row.get("widget_id", ""), neutralize_formulas=True
        ),
        "coords": _sanitize_log_value(_serialize_coords(row.get("coords"))),
        "mensaje": _sanitize_log_value(
            row.get("mensaje", ""), neutralize_formulas=True
        ),
    }


def log_event(
    event_type: str,
    message: str,
    logs: List[dict],
    widget_id: Optional[str] = None,
    event_subtipo: Optional[str] = None,
    coords=None,
) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = normalize_log_row(
        {
            "timestamp": timestamp,
            "tipo": event_type,
            "subtipo": event_subtipo or "",
            "widget_id": widget_id or "",
            "coords": coords,
            "mensaje": message,
        }
    )
    logs.append(row)
    _LOG_QUEUE.append(row)


def drain_log_queue() -> List[dict]:
    """Devuelve y limpia los registros pendientes de escritura en disco."""

    if not _LOG_QUEUE:
        return []
    rows = list(_LOG_QUEUE)
    _LOG_QUEUE.clear()
    return rows


__all__ = [
    'FieldValidator',
    'drain_log_queue',
    'LOG_FIELDNAMES',
    'log_event',
    'normalize_without_accents',
    'normalize_team_member_identifier',
    'normalize_log_row',
    'parse_decimal_amount',
    'sanitize_rich_text',
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
    'validate_process_id',
    'validate_phone_list',
    'validate_product_dates',
    'validate_product_id',
    'validate_reclamo_id',
    'validate_required_text',
    'validate_catalog_risk_id',
    'validate_risk_id',
    'validate_team_member_id',
]
