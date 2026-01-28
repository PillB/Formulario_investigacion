from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from report_builder import CaseData
from validators import parse_decimal_amount, sanitize_rich_text

PLACEHOLDER = "N/A"
MAX_SECTION_CHARS = 600
MAX_BULLETS = 5


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


def _format_amount(value: Decimal | None) -> str:
    if value is None:
        return PLACEHOLDER
    quantized = value.quantize(Decimal("0.01"))
    return f"{quantized:,.2f}"


def _truncate(text: str, max_chars: int) -> str:
    cleaned = sanitize_rich_text(text, max_chars=None).strip()
    if max_chars and len(cleaned) > max_chars:
        return cleaned[: max_chars - 1].rstrip() + "…"
    return cleaned


def _extract_rich_text(entry: object) -> str:
    if isinstance(entry, Mapping):
        raw_text = entry.get("text")
    else:
        raw_text = entry
    return sanitize_rich_text(raw_text, max_chars=MAX_SECTION_CHARS).strip()


def _split_bullets(text: str, *, max_items: int = MAX_BULLETS) -> list[str]:
    if not text:
        return []
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(raw_lines) == 1:
        sentences = [part.strip() for part in raw_lines[0].split(". ") if part.strip()]
        raw_lines = [sentence.rstrip(".") for sentence in sentences]
    bullets = [_truncate(line, 180) for line in raw_lines if line]
    return bullets[:max_items]


def _bullet_text(lines: Sequence[str]) -> str:
    if not lines:
        return PLACEHOLDER
    return "\n".join(f"• {line}" for line in lines)


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
) -> str:
    totals = _aggregate_amounts(products)
    comentario = _extract_rich_text(analisis.get("comentario_breve"))
    if not comentario:
        comentario = _extract_rich_text(analisis.get("conclusiones"))
    if not comentario:
        comentario = _extract_rich_text(analisis.get("antecedentes"))
    summary_line = _truncate(comentario, 280) if comentario else PLACEHOLDER
    header = _case_title(caso, encabezado)
    amounts = (
        f"Monto investigado {_format_amount(totals['investigado'])}; "
        f"Pérdida fraude {_format_amount(totals['perdida_fraude'])}; "
        f"Contingencia {_format_amount(totals['contingencia'])}; "
        f"Recuperado {_format_amount(totals['recuperado'])}."
    )
    return _truncate(f"{header}. {summary_line}. {amounts}", MAX_SECTION_CHARS)


def _build_cronologia_section(
    caso: Mapping[str, object],
    analisis: Mapping[str, object],
    productos: Sequence[Mapping[str, object]],
    operaciones: Sequence[Mapping[str, object]],
) -> str:
    hallazgos = _extract_rich_text(analisis.get("hallazgos"))
    if hallazgos:
        bullets = _split_bullets(hallazgos)
        return _bullet_text(bullets)
    if operaciones:
        lines = []
        for op in operaciones:
            if not isinstance(op, Mapping):
                continue
            accion = _safe_text(op.get("accion"), "")
            fecha = _format_date(op.get("fecha"))
            estado = _safe_text(op.get("estado"), "")
            summary = " - ".join(part for part in (fecha, accion, estado) if part and part != PLACEHOLDER)
            if summary:
                lines.append(summary)
        return _bullet_text(lines[:MAX_BULLETS])
    ocurrencia = _format_date(caso.get("fecha_de_ocurrencia"))
    descubrimiento = _format_date(caso.get("fecha_de_descubrimiento"))
    product_dates = [
        _format_date(prod.get("fecha_ocurrencia"))
        for prod in productos
        if isinstance(prod, Mapping) and prod.get("fecha_ocurrencia")
    ]
    bullets = [
        f"Ocurrencia: {ocurrencia}. Descubrimiento: {descubrimiento}.",
    ]
    if product_dates:
        bullets.append(f"Fechas en productos: {', '.join(sorted(set(product_dates)))}.")
    return _bullet_text(bullets)


def _build_analisis_section(analisis: Mapping[str, object]) -> str:
    parts = []
    for key, label in (
        ("antecedentes", "Antecedentes"),
        ("modus_operandi", "Modus operandi"),
        ("conclusiones", "Conclusiones"),
    ):
        text = _extract_rich_text(analisis.get(key))
        if text:
            parts.append(f"{label}: {_truncate(text, 180)}")
    if not parts:
        text = _extract_rich_text(analisis.get("comentario_amplio"))
        if text:
            parts.append(text)
    return _bullet_text(parts or [PLACEHOLDER])


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
            bullets.append(_truncate(line, 200))
    return _bullet_text(bullets[:MAX_BULLETS])


def _build_acciones_section(analisis: Mapping[str, object], operaciones: Sequence[Mapping[str, object]]) -> str:
    recomendacion = _extract_rich_text(analisis.get("recomendaciones"))
    if recomendacion:
        return _bullet_text(_split_bullets(recomendacion))
    bullets = []
    for op in operaciones:
        if not isinstance(op, Mapping):
            continue
        accion = _safe_text(op.get("accion"), "")
        cliente = _safe_text(op.get("cliente"), "")
        estado = _safe_text(op.get("estado"), "")
        line = " - ".join(part for part in (accion, cliente, estado) if part and part != PLACEHOLDER)
        if line:
            bullets.append(_truncate(line, 200))
    return _bullet_text(bullets[:MAX_BULLETS])


def _build_responsables_section(
    caso: Mapping[str, object],
    colaboradores: Sequence[Mapping[str, object]],
) -> str:
    bullets = []
    investigador = caso.get("investigador_nombre") or (caso.get("investigador") or {}).get("nombre")
    if investigador:
        bullets.append(f"Investigador: {_safe_text(investigador, 'Investigador principal')}")
    for colab in colaboradores:
        if not isinstance(colab, Mapping):
            continue
        nombre = _safe_text(colab.get("nombres") or colab.get("nombre_completo"), "")
        if not nombre:
            continue
        flag = _safe_text(colab.get("flag"), "")
        area = _safe_text(colab.get("area"), "")
        bullets.append(f"{nombre} ({flag or 'involucrado'} - {area or 'área no especificada'})")
    return _bullet_text(bullets[:MAX_BULLETS])


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

    return {
        "titulo_reporte": "Reporte de Alertas Tempranas por Casos de Fraude",
        "codigo": _safe_text(caso.get("id_caso")),
        "caso": _case_title(caso, encabezado),
        "emitido_por": _safe_text(
            caso.get("investigador_nombre") or (caso.get("investigador") or {}).get("nombre"),
            "Equipo de investigación",
        ),
        "resumen": _build_resumen_section(caso, encabezado, analisis, productos),
        "cronologia": _build_cronologia_section(caso, analisis, productos, operaciones),
        "analisis": _build_analisis_section(analisis),
        "riesgos": _build_riesgos_section(riesgos),
        "acciones": _build_acciones_section(analisis, operaciones),
        "responsables": _build_responsables_section(caso, colaboradores),
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
    headline = _truncate(" - ".join(filter(None, headline_parts)) + f". {impact}", 280)

    supporting = []
    hallazgos = _extract_rich_text(analisis.get("hallazgos"))
    if hallazgos:
        supporting.append(f"Hallazgos clave: {_truncate(hallazgos, 180)}")
    riesgos_text = _build_riesgos_section(riesgos)
    if riesgos_text != PLACEHOLDER:
        supporting.append(f"Riesgos identificados: {_truncate(riesgos_text.replace('• ', ''), 180)}")
    acciones_text = _build_acciones_section(analisis, operaciones)
    if acciones_text != PLACEHOLDER:
        supporting.append(f"Acciones en curso: {_truncate(acciones_text.replace('• ', ''), 180)}")
    responsables_text = _build_responsables_section(caso, colaboradores)
    if responsables_text != PLACEHOLDER:
        supporting.append(f"Responsables asignados: {_truncate(responsables_text.replace('• ', ''), 180)}")
    comentario = _extract_rich_text(analisis.get("comentario_breve"))
    if comentario and comentario not in supporting:
        supporting.append(f"Resumen ejecutivo: {_truncate(comentario, 180)}")
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
