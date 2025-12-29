from __future__ import annotations

from dataclasses import dataclass
from importlib import util as importlib_util
import re
from typing import Mapping

from report.alerta_temprana import SpanishSummaryHelper

TRANSFORMERS_AVAILABLE = importlib_util.find_spec("transformers") is not None
PLACEHOLDER = "Auto-redacción no disponible."

PII_PATTERNS = [
    re.compile(r"\b\d{4}-\d{4}\b"),  # Número de caso
    re.compile(r"\bC\d{8}\b"),  # Id reclamo
    re.compile(r"\b[A-Z]\d{5}\b"),  # Id Team Member (T12345)
    re.compile(r"\b(?:43|45|46|56)\d{8}\b"),  # Código analítica contable
    re.compile(r"\b\d{8}\b"),  # DNI
    re.compile(r"\b\d{11}\b"),  # RUC
    re.compile(r"\b[A-Z]{3}-\d{3}\b"),  # Matrículas vehiculares
    re.compile(r"\b[A-Z]{1,3}-\d{4,6}\b"),  # Matrículas internas
    re.compile(r"\b\w+@\w+\.\w+\b"),  # Correo
    re.compile(r"\b\+?\d{6,12}\b"),  # Teléfonos/IDs numéricos largos
    re.compile(
        r"\b(?:Nombre|Nombres|Apellidos)\s*[:\-]\s*[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]{1,40}"
    ),
]


@dataclass
class AutoRedaccionResult:
    text: str
    error: str | None = None


_default_helper: SpanishSummaryHelper | None = None


def _get_helper() -> SpanishSummaryHelper:
    global _default_helper
    if _default_helper is None:
        _default_helper = SpanishSummaryHelper()
    return _default_helper


def _safe_case_value(case_data: Mapping[str, object], key: str) -> str:
    value = case_data.get(key, "") if isinstance(case_data, Mapping) else ""
    return str(value or "").strip()


def _build_case_context(case_data: Mapping[str, object]) -> str:
    case = case_data.get("caso", {}) if isinstance(case_data, Mapping) else {}
    if not isinstance(case, Mapping):
        case = {}
    parts = [
        f"Tipo de informe: {_safe_case_value(case, 'tipo_informe') or 'sin tipo'}",
        f"Categoría: {_safe_case_value(case, 'categoria1') or 'sin categoría'}",
        f"Modalidad: {_safe_case_value(case, 'modalidad') or 'sin modalidad'}",
        f"Canal: {_safe_case_value(case, 'canal') or 'sin canal'}",
        f"Proceso: {_safe_case_value(case, 'proceso') or 'sin proceso'}",
        f"Fecha ocurrencia: {_safe_case_value(case, 'fecha_de_ocurrencia') or 'sin fecha'}",
        f"Fecha descubrimiento: {_safe_case_value(case, 'fecha_de_descubrimiento') or 'sin fecha'}",
    ]
    return " | ".join(parts)


def build_auto_redaccion_prompt(
    case_data: Mapping[str, object],
    narrative: str,
    *,
    target_chars: int,
    label: str,
) -> str:
    context = _build_case_context(case_data)
    prompt = (
        "Tarea: redacta un resumen ejecutivo en español para un informe de fraude. "
        "No incluyas PII (nombres, IDs, números de caso, DNI/RUC, correos, matrículas, etc.). "
        "Sin saltos de línea, sin viñetas, solo un párrafo. "
        f"Longitud objetivo: {'≤' if label == 'breve' else '≈'}{target_chars} caracteres. "
        "Entrega solo el texto final, sin encabezados ni etiquetas. "
        "\nDatos del caso: "
        f"{context}. "
        "\nNarrativa disponible: "
        f"{narrative or 'Sin narrativa adicional.'}"
    )
    return prompt


def strip_pii(text: str) -> str:
    sanitized = text
    for pattern in PII_PATTERNS:
        sanitized = pattern.sub(" ", sanitized)
    return sanitized


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def postprocess_summary(text: str, *, max_chars: int) -> str:
    cleaned = strip_pii(text or "")
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    cleaned = collapse_whitespace(cleaned)
    if max_chars and len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip()
    return cleaned


def auto_redact_comment(
    case_data: Mapping[str, object],
    narrative: str,
    *,
    target_chars: int,
    max_new_tokens: int | None = None,
    helper: SpanishSummaryHelper | None = None,
    label: str,
) -> AutoRedaccionResult:
    if not TRANSFORMERS_AVAILABLE:
        return AutoRedaccionResult(PLACEHOLDER, "transformers no está disponible.")

    prompt = build_auto_redaccion_prompt(
        case_data,
        narrative,
        target_chars=target_chars,
        label=label,
    )
    llm_helper = helper or _get_helper()
    summary = llm_helper.summarize(
        f"auto_redaccion_{label}",
        prompt,
        max_new_tokens=max_new_tokens,
    )
    if not summary:
        return AutoRedaccionResult(PLACEHOLDER, "No fue posible generar la auto-redacción.")

    cleaned = postprocess_summary(summary, max_chars=target_chars)
    if not cleaned:
        return AutoRedaccionResult(PLACEHOLDER, "La auto-redacción quedó vacía tras limpiar PII.")
    return AutoRedaccionResult(cleaned, None)
