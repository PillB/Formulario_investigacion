from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from report_builder import CaseData
from validators import parse_decimal_amount, sanitize_rich_text

logger = logging.getLogger(__name__)

PLACEHOLDER = "N/A"
MAX_SECTION_CHARS = 600
MAX_BULLETS = 4
MAX_BULLET_CHARS = 180
MIN_TRUNCATE_WORD_BOUNDARY = 0.6


@dataclass(frozen=True)
class ExecutiveSummary:
    headline: str
    supporting_points: list[str]
    evidence: list[str]


def _safe_text(value: object, placeholder: str = PLACEHOLDER) -> str:
    text = str(value or "").strip()
    return text or placeholder


def _format_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return PLACEHOLDER
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return text
    return parsed.strftime("%Y-%m-%d")


def _parse_iso_date(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _collect_fallback_dates(
    caso: Mapping[str, object],
    productos: Sequence[Mapping[str, object]],
) -> list[datetime]:
    candidates = [
        _parse_iso_date(caso.get("fecha_de_ocurrencia")),
        _parse_iso_date(caso.get("fecha_de_descubrimiento")),
    ]
    for producto in productos:
        if not isinstance(producto, Mapping):
            continue
        candidates.append(_parse_iso_date(producto.get("fecha_ocurrencia")))
    return [candidate for candidate in candidates if candidate]


def _format_amount(value: Decimal | None) -> str:
    if value is None:
        return PLACEHOLDER
    quantized = value.quantize(Decimal("0.01"))
    return f"{quantized:,.2f}"


def _truncate(text: str, max_chars: int, *, label: str = "") -> str:
    cleaned = sanitize_rich_text(text, max_chars=None).strip()
    if max_chars and len(cleaned) > max_chars:
        truncated = cleaned[: max_chars - 1].rstrip()
        last_space = truncated.rfind(" ")
        min_space_index = int(max_chars * MIN_TRUNCATE_WORD_BOUNDARY)
        if last_space >= min_space_index:
            truncated = truncated[:last_space].rstrip()
        result = truncated + "…"
        logger.warning(
            "Se truncó el texto%s a %s caracteres.",
            f" ({label})" if label else "",
            max_chars,
        )
        return result
    return cleaned


def _extract_rich_text(entry: object) -> str:
    if isinstance(entry, Mapping):
        raw_text = entry.get("text")
    else:
        raw_text = entry
    return sanitize_rich_text(raw_text, max_chars=MAX_SECTION_CHARS).strip()


def _split_bullets(
    text: str,
    *,
    max_items: int = MAX_BULLETS,
    max_chars: int = MAX_BULLET_CHARS,
    label: str = "",
) -> list[str]:
    if not text:
        return []
    cleaned = sanitize_rich_text(text, max_chars=None).strip()
    if not cleaned:
        return []
    raw_lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    candidates: list[str] = []
    bullet_prefix = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
    for line in raw_lines:
        normalized = bullet_prefix.sub("", line).strip()
        if normalized:
            candidates.append(normalized)
    if len(candidates) <= 1:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
        candidates = [sentence.rstrip(".") for sentence in sentences]
    bullets = [_truncate(line, max_chars, label=label) for line in candidates if line]
    return bullets[:max_items]


def _bullet_text(lines: Sequence[str]) -> str:
    if not lines:
        return PLACEHOLDER
    return "\n".join(f"• {line}" for line in lines)


def _limit_bullets(
    lines: Sequence[str],
    *,
    max_items: int = MAX_BULLETS,
    max_chars: int = MAX_BULLET_CHARS,
    label: str = "",
) -> list[str]:
    if not lines:
        return []
    trimmed = [_truncate(line, max_chars, label=label) for line in lines if line]
    return trimmed[:max_items]


def _extract_primary_finding(text: str) -> str:
    bullets = _split_bullets(text, max_items=1, max_chars=180, label="hallazgo_principal")
    return bullets[0] if bullets else ""


def _extract_control_failure_sentence(analisis: Mapping[str, object]) -> str:
    pattern = re.compile(r"(fall[óo]|falla)\s+(?:de\s+)?(?:el\s+)?control", re.IGNORECASE)
    for key in (
        "hallazgos",
        "conclusiones",
        "comentario_breve",
        "comentario_amplio",
        "antecedentes",
        "modus_operandi",
    ):
        text = _extract_rich_text(analisis.get(key))
        if not text:
            continue
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        for sentence in sentences:
            if pattern.search(sentence):
                return sentence.rstrip(".")
    return ""


def _aggregate_amounts(products: Iterable[Mapping[str, object]] | None) -> dict[str, Decimal]:
    totals = {
        "investigado": Decimal("0"),
        "perdida_fraude": Decimal("0"),
        "falla_procesos": Decimal("0"),
        "contingencia": Decimal("0"),
        "recuperado": Decimal("0"),
    }
    for product in products or []:
        if not isinstance(product, Mapping):
            continue
        for key, field in (
            ("investigado", "monto_investigado"),
            ("perdida_fraude", "monto_perdida_fraude"),
            ("falla_procesos", "monto_falla_procesos"),
            ("contingencia", "monto_contingencia"),
            ("recuperado", "monto_recuperado"),
        ):
            amount = parse_decimal_amount(product.get(field))
            if amount is not None:
                totals[key] += amount
    return totals


def _case_title(caso: Mapping[str, object], encabezado: Mapping[str, object]) -> str:
    referencia = str(encabezado.get("referencia") or "").strip()
    if referencia:
        return referencia
    parts = [
        str(caso.get("categoria1") or "").strip(),
        str(caso.get("modalidad") or "").strip(),
        str(caso.get("proceso") or "").strip(),
        str(caso.get("canal") or "").strip(),
    ]
    filtered = [part for part in parts if part]
    return " · ".join(filtered) if filtered else PLACEHOLDER


def _build_resumen_section(
    caso: Mapping[str, object],
    encabezado: Mapping[str, object],
    analisis: Mapping[str, object],
    products: Sequence[Mapping[str, object]],
    clientes: Sequence[Mapping[str, object]],
) -> str:
    totals = _aggregate_amounts(products)
    comentario = _extract_rich_text(analisis.get("comentario_breve"))
    if not comentario:
        comentario = _extract_rich_text(analisis.get("hallazgos"))
    mensaje_clave = _truncate(comentario, MAX_BULLET_CHARS, label="resumen_mensaje") if comentario else PLACEHOLDER

    support_lines = [
        (
            "Montos: "
            f"Investigado {_format_amount(totals['investigado'])}; "
            f"Pérdida fraude {_format_amount(totals['perdida_fraude'])}; "
            f"Falla procesos {_format_amount(totals['falla_procesos'])}; "
            f"Contingencia {_format_amount(totals['contingencia'])}; "
            f"Recuperado {_format_amount(totals['recuperado'])}."
        ),
        f"Productos involucrados: {len(products) or 0}",
        f"Clientes vinculados: {len(clientes) or 0}",
    ]
    has_support_data = bool(products or clientes) or any(value > 0 for value in totals.values())
    support_lines = _limit_bullets(support_lines, label="resumen_soporte") if has_support_data else []
    if not support_lines:
        support_lines = [PLACEHOLDER]

    evidence_lines = []
    for label, value, tab, field in (
        ("Fecha ocurrencia", _format_date(caso.get("fecha_de_ocurrencia")), "Caso", "fecha_de_ocurrencia"),
        (
            "Fecha descubrimiento",
            _format_date(caso.get("fecha_de_descubrimiento")),
            "Caso",
            "fecha_de_descubrimiento",
        ),
        ("Dirigido a", _safe_text(encabezado.get("dirigido_a")), "Encabezado", "dirigido_a"),
        ("Área de reporte", _safe_text(encabezado.get("area_reporte")), "Encabezado", "area_reporte"),
    ):
        if value and value != PLACEHOLDER:
            evidence_lines.append(f"{label}: {value} [{tab}: {field}]")
    evidence_lines = _limit_bullets(evidence_lines, label="resumen_evidencias")
    if not evidence_lines:
        evidence_lines = [PLACEHOLDER]

    resumen = "\n".join(
        [
            f"Mensaje clave: {mensaje_clave}",
            "Puntos de soporte:",
            _bullet_text(support_lines),
            "Evidencias:",
            _bullet_text(evidence_lines),
        ]
    )
    return _truncate(resumen, MAX_SECTION_CHARS, label="resumen")


def _build_cronologia_section(
    caso: Mapping[str, object],
    analisis: Mapping[str, object],
    productos: Sequence[Mapping[str, object]],
    operaciones: Sequence[Mapping[str, object]],
) -> str:
    for key in (
        "hallazgos",
        "comentario_breve",
        "conclusiones",
        "antecedentes",
        "comentario_amplio",
        "modus_operandi",
    ):
        narrative = _extract_rich_text(analisis.get(key))
        if narrative:
            bullets = _split_bullets(narrative, label="cronologia")
            if bullets:
                return _bullet_text(bullets)
    if operaciones:
        fallback_dates = _collect_fallback_dates(caso, productos)
        fallback_date = min(fallback_dates) if fallback_dates else None
        entries: list[tuple[datetime, int, str]] = []
        for idx, op in enumerate(operaciones):
            if not isinstance(op, Mapping):
                continue
            parsed_date = _parse_iso_date(op.get("fecha"))
            resolved_date = parsed_date or fallback_date
            if not resolved_date:
                continue
            accion = _safe_text(op.get("accion"), "")
            estado = _safe_text(op.get("estado"), "")
            detail_parts = [part for part in (accion, estado) if part]
            detalle = " - ".join(detail_parts) if detail_parts else "Detalle no disponible"
            fecha = resolved_date.strftime("%Y-%m-%d")
            summary = f"{fecha} - {detalle}"
            entries.append((resolved_date, idx, summary))
        if entries:
            lines = [entry[2] for entry in sorted(entries, key=lambda item: (item[0], item[1]))]
            return _bullet_text(_limit_bullets(lines, label="cronologia"))
    ocurrencia = _format_date(caso.get("fecha_de_ocurrencia"))
    descubrimiento = _format_date(caso.get("fecha_de_descubrimiento"))
    product_dates = [
        _format_date(prod.get("fecha_ocurrencia"))
        for prod in productos
        if isinstance(prod, Mapping) and prod.get("fecha_ocurrencia")
    ]
    if ocurrencia == PLACEHOLDER and descubrimiento == PLACEHOLDER and not product_dates:
        return PLACEHOLDER
    bullets = [
        f"Ocurrencia: {ocurrencia}. Descubrimiento: {descubrimiento}.",
    ]
    if product_dates:
        bullets.append(f"Fechas en productos: {', '.join(sorted(set(product_dates)))}.")
    return _bullet_text(bullets)


def _build_analisis_section(analisis: Mapping[str, object]) -> str:
    parts = []
    hallazgos_text = _extract_rich_text(analisis.get("hallazgos"))
    hallazgo_principal = _extract_primary_finding(hallazgos_text)
    if hallazgo_principal:
        parts.append(f"Hallazgo principal: {_truncate(hallazgo_principal, 180, label='analisis')}")

    control_failure = _extract_control_failure_sentence(analisis)
    if control_failure:
        parts.append(f"Fallo de control: {_truncate(control_failure, 180, label='analisis')}")

    for key, label in (
        ("antecedentes", "Antecedentes"),
        ("modus_operandi", "Modus operandi"),
        ("conclusiones", "Conclusiones"),
    ):
        text = _extract_rich_text(analisis.get(key))
        if text:
            parts.append(f"{label}: {_truncate(text, 180, label='analisis')}")
    if not parts:
        text = _extract_rich_text(analisis.get("comentario_amplio"))
        if text:
            parts.append(text)
    if not parts:
        return PLACEHOLDER
    return _bullet_text(parts)


def _build_riesgos_section(riesgos: Sequence[Mapping[str, object]]) -> str:
    bullets = []
    for riesgo in riesgos:
        if not isinstance(riesgo, Mapping):
            continue
        risk_id = str(riesgo.get("id_riesgo") or "").strip()
        desc = str(riesgo.get("descripcion") or "").strip()
        criticidad = str(riesgo.get("criticidad") or "").strip()
        plan = str(riesgo.get("planes_accion") or "").strip()
        parts = [part for part in (risk_id, desc, criticidad) if part]
        line = " - ".join(parts)
        if plan:
            line = f"{line}. Plan: {plan}" if line else f"Plan: {plan}"
        if line:
            bullets.append(line)
    return _bullet_text(_limit_bullets(bullets, label="riesgos"))


def _build_recomendaciones_section(
    analisis: Mapping[str, object],
    operaciones: Sequence[Mapping[str, object]],
) -> str:
    recomendacion = _extract_rich_text(analisis.get("recomendaciones"))
    if not recomendacion:
        recomendacion = _extract_rich_text(analisis.get("acciones"))
    if recomendacion:
        return _bullet_text(_split_bullets(recomendacion, label="recomendaciones"))
    bullets = []
    for op in operaciones:
        if not isinstance(op, Mapping):
            continue
        accion = _safe_text(op.get("accion"), "")
        cliente = _safe_text(op.get("cliente"), "")
        estado = _safe_text(op.get("estado"), "")
        line = " - ".join(part for part in (accion, cliente, estado) if part and part != PLACEHOLDER)
        if line:
            bullets.append(line)
    return _bullet_text(_limit_bullets(bullets, label="recomendaciones"))


def _build_responsables_section(
    caso: Mapping[str, object],
    colaboradores: Sequence[Mapping[str, object]],
    responsables: Sequence[Mapping[str, object]],
) -> str:
    bullets = []
    explicit_responsables = False
    investigador = caso.get("investigador_nombre") or (caso.get("investigador") or {}).get("nombre")
    if investigador:
        bullets.append(f"Investigador: {_safe_text(investigador, 'Investigador principal')}")

    for responsable in responsables:
        if not isinstance(responsable, Mapping):
            continue
        nombre = _safe_text(responsable.get("nombre") or responsable.get("nombres"), "")
        if not nombre:
            continue
        scope = _safe_text(responsable.get("scope"), "unidad").lower()
        scope_label = "Responsable de unidad" if scope == "unidad" else "Responsable de producto"
        puesto = _safe_text(responsable.get("puesto"), "")
        division = _safe_text(responsable.get("division"), "")
        area = _safe_text(responsable.get("area"), "")
        servicio = _safe_text(responsable.get("servicio"), "")
        agencia = _safe_text(responsable.get("nombre_agencia"), "")
        producto = _safe_text(responsable.get("id_producto"), "")

        fragments = [part for part in (puesto, division, area, servicio, agencia) if part and part != PLACEHOLDER]
        suffix = f" — {' / '.join(fragments)}" if fragments else ""
        if scope == "producto" and producto and producto != PLACEHOLDER:
            suffix = f"{suffix} (Producto {producto})"
        bullets.append(f"{scope_label}: {nombre}{suffix}")
        explicit_responsables = True

    if explicit_responsables:
        return _bullet_text(_limit_bullets(bullets, label="responsables"))

    for colab in colaboradores:
        if not isinstance(colab, Mapping):
            continue
        nombre = _safe_text(colab.get("nombres") or colab.get("nombre_completo"), "")
        if not nombre:
            continue
        flag = _safe_text(colab.get("flag"), "")
        area = _safe_text(colab.get("area"), "")
        bullets.append(f"{nombre} ({flag or 'involucrado'} - {area or 'área no especificada'})")
    return _bullet_text(_limit_bullets(bullets, label="responsables"))


def build_alerta_temprana_sections(
    data: CaseData | Mapping[str, object],
) -> dict[str, str]:
    dataset = data if isinstance(data, CaseData) else CaseData.from_mapping(data or {})
    caso = dataset.get("caso", {}) if isinstance(dataset, Mapping) else {}
    encabezado = dataset.get("encabezado", {}) if isinstance(dataset, Mapping) else {}
    productos = dataset.get("productos") if isinstance(dataset, Mapping) else []
    riesgos = dataset.get("riesgos") if isinstance(dataset, Mapping) else []
    analisis = dataset.get("analisis") if isinstance(dataset, Mapping) else {}
    operaciones = dataset.get("operaciones") if isinstance(dataset, Mapping) else []
    colaboradores = dataset.get("colaboradores") if isinstance(dataset, Mapping) else []
    clientes = dataset.get("clientes") if isinstance(dataset, Mapping) else []
    responsables = dataset.get("responsables") if isinstance(dataset, Mapping) else []

    recomendaciones = _build_recomendaciones_section(analisis, operaciones)
    return {
        "titulo_reporte": "Reporte de Alertas Tempranas por Casos de Fraude",
        "codigo": _safe_text(caso.get("id_caso")),
        "caso": _case_title(caso, encabezado),
        "emitido_por": _safe_text(
            caso.get("investigador_nombre") or (caso.get("investigador") or {}).get("nombre"),
            "Equipo de investigación",
        ),
        "resumen": _build_resumen_section(caso, encabezado, analisis, productos, clientes),
        "cronologia": _build_cronologia_section(caso, analisis, productos, operaciones),
        "analisis": _build_analisis_section(analisis),
        "riesgos": _build_riesgos_section(riesgos),
        "recomendaciones": recomendaciones,
        "acciones": recomendaciones,
        "responsables": _build_responsables_section(caso, colaboradores, responsables),
    }


def build_executive_summary(data: CaseData | Mapping[str, object]) -> ExecutiveSummary:
    dataset = data if isinstance(data, CaseData) else CaseData.from_mapping(data or {})
    caso = dataset.get("caso", {}) if isinstance(dataset, Mapping) else {}
    encabezado = dataset.get("encabezado", {}) if isinstance(dataset, Mapping) else {}
    productos = dataset.get("productos") if isinstance(dataset, Mapping) else []
    riesgos = dataset.get("riesgos") if isinstance(dataset, Mapping) else []
    analisis = dataset.get("analisis") if isinstance(dataset, Mapping) else {}
    operaciones = dataset.get("operaciones") if isinstance(dataset, Mapping) else []
    colaboradores = dataset.get("colaboradores") if isinstance(dataset, Mapping) else []
    clientes = dataset.get("clientes") if isinstance(dataset, Mapping) else []
    responsables = dataset.get("responsables") if isinstance(dataset, Mapping) else []
    reclamos = dataset.get("reclamos") if isinstance(dataset, Mapping) else []

    totals = _aggregate_amounts(productos)
    headline_parts = [
        f"Caso {_safe_text(caso.get('id_caso'))}",
        _case_title(caso, encabezado),
    ]
    impact = (
        f"Monto investigado {_format_amount(totals['investigado'])}; "
        f"Pérdida fraude {_format_amount(totals['perdida_fraude'])}; "
        f"Contingencia {_format_amount(totals['contingencia'])}."
    )
    headline = _truncate(
        " - ".join(filter(None, headline_parts)) + f". {impact}",
        280,
        label="resumen_ejecutivo",
    )

    supporting = []
    hallazgos = _extract_rich_text(analisis.get("hallazgos"))
    if hallazgos:
        supporting.append(f"Hallazgos clave: {_truncate(hallazgos, 180, label='resumen_ejecutivo')}")
    riesgos_text = _build_riesgos_section(riesgos)
    if riesgos_text != PLACEHOLDER:
        supporting.append(
            f"Riesgos identificados: {_truncate(riesgos_text.replace('• ', ''), 180, label='resumen_ejecutivo')}"
        )
    recomendaciones_text = _build_recomendaciones_section(analisis, operaciones)
    if recomendaciones_text != PLACEHOLDER:
        supporting.append(
            "Recomendaciones en curso: "
            f"{_truncate(recomendaciones_text.replace('• ', ''), 180, label='resumen_ejecutivo')}"
        )
    responsables_text = _build_responsables_section(caso, colaboradores, responsables)
    if responsables_text != PLACEHOLDER:
        supporting.append(
            f"Responsables asignados: {_truncate(responsables_text.replace('• ', ''), 180, label='resumen_ejecutivo')}"
        )
    comentario = _extract_rich_text(analisis.get("comentario_breve"))
    if comentario and comentario not in supporting:
        supporting.append(f"Resumen ejecutivo: {_truncate(comentario, 180, label='resumen_ejecutivo')}")
    supporting_points = supporting[:MAX_BULLETS] or [PLACEHOLDER]

    evidence = [
        f"Productos afectados: {len(productos) or 0}",
        f"Clientes vinculados: {len(clientes) or 0}",
        f"Colaboradores vinculados: {len(colaboradores) or 0}",
        f"Riesgos registrados: {len(riesgos) or 0}",
        f"Reclamos registrados: {len(reclamos) or 0}",
        f"Categoría/Modalidad: {_safe_text(caso.get('categoria1'))} / {_safe_text(caso.get('modalidad'))}",
        f"Canal/Proceso: {_safe_text(caso.get('canal'))} / {_safe_text(caso.get('proceso'))}",
        f"Fecha ocurrencia: {_format_date(caso.get('fecha_de_ocurrencia'))}",
        f"Fecha descubrimiento: {_format_date(caso.get('fecha_de_descubrimiento'))}",
        f"Dirigido a: {_safe_text(encabezado.get('dirigido_a'))}",
        f"Área de reporte: {_safe_text(encabezado.get('area_reporte'))}",
    ]
    evidence_clean = [line for line in evidence if line]
    return ExecutiveSummary(
        headline=headline,
        supporting_points=supporting_points,
        evidence=evidence_clean[:MAX_BULLETS + 4],
    )
