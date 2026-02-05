from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from report.alerta_temprana import SpanishSummaryHelper
from report_builder import CaseData, build_report_filename
from validators import parse_decimal_amount, sanitize_rich_text

PLACEHOLDER = "N/A"
MAX_PARAGRAPH_CHARS = 520
MAX_BULLETS = 10
MAX_LIST_ITEMS = 3


def build_resumen_ejecutivo_filename(
    tipo_informe: str | None,
    case_id: str | None,
    extension: str = "md",
) -> str:
    safe_name = build_report_filename(tipo_informe, case_id, extension)
    return safe_name.replace("Informe_", "Resumen_Ejecutivo_")


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
    return f"{value.quantize(Decimal('0.01')):,.2f}"


def _extract_text(value: object, *, max_chars: int = MAX_PARAGRAPH_CHARS) -> str:
    if isinstance(value, Mapping):
        value = value.get("text")
    cleaned = sanitize_rich_text(value, max_chars=None).strip()
    if not cleaned:
        return ""
    if max_chars and len(cleaned) > max_chars:
        return cleaned[: max_chars - 1].rstrip() + "…"
    return cleaned


def _truncate(text: str, max_chars: int = MAX_PARAGRAPH_CHARS) -> str:
    if not text:
        return ""
    cleaned = sanitize_rich_text(text, max_chars=None).strip()
    if max_chars and len(cleaned) > max_chars:
        return cleaned[: max_chars - 1].rstrip() + "…"
    return cleaned


def _aggregate_amounts(products: Iterable[Mapping[str, object]] | None) -> dict[str, Decimal]:
    totals = {
        "investigado": Decimal("0"),
        "perdida_fraude": Decimal("0"),
        "falla_procesos": Decimal("0"),
        "contingencia": Decimal("0"),
        "recuperado": Decimal("0"),
        "pago_deuda": Decimal("0"),
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
            ("pago_deuda", "monto_pago_deuda"),
        ):
            amount = parse_decimal_amount(product.get(field))
            if amount is not None:
                totals[key] += amount
    return totals


def _join_nonempty(parts: Sequence[str], *, sep: str = " / ") -> str:
    filtered = [part for part in parts if part and part != PLACEHOLDER]
    return sep.join(filtered) if filtered else PLACEHOLDER


def _summarize_names(
    items: Sequence[Mapping[str, object]],
    *,
    first_key: str,
    last_key: str,
) -> str:
    names = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        nombre = " ".join(
            filter(
                None,
                [
                    str(item.get(first_key) or "").strip(),
                    str(item.get(last_key) or "").strip(),
                ],
            )
        ).strip()
        if nombre:
            names.append(nombre)
    if not names:
        return PLACEHOLDER
    sample = names[:MAX_LIST_ITEMS]
    extra = len(names) - len(sample)
    summary = ", ".join(sample)
    if extra > 0:
        summary = f"{summary} (+{extra} más)"
    return summary


def _summarize_values(values: Iterable[str]) -> str:
    cleaned = [value for value in {value.strip() for value in values if value and value.strip()}]
    if not cleaned:
        return PLACEHOLDER
    ordered = sorted(cleaned)
    summary = ", ".join(ordered[:MAX_LIST_ITEMS])
    extra = len(cleaned) - len(ordered[:MAX_LIST_ITEMS])
    if extra > 0:
        summary = f"{summary} (+{extra} más)"
    return summary


def _render_section(title: str, body: str) -> str:
    content = body.strip() if body else PLACEHOLDER
    return f"## {title}\n\n{content}\n"


def _render_bullets(lines: Sequence[str]) -> str:
    cleaned = [line for line in (line.strip() for line in lines) if line]
    if not cleaned:
        return f"- {PLACEHOLDER}"
    return "\n".join(f"- {sanitize_rich_text(line, max_chars=240)}" for line in cleaned[:MAX_BULLETS])


def _pick_key_message(analisis: Mapping[str, object]) -> str:
    for key in (
        "conclusiones",
        "hallazgos",
        "comentario_breve",
        "antecedentes",
        "comentario_amplio",
    ):
        text = _extract_text(analisis.get(key))
        if text:
            return text
    return ""


def _build_key_message(
    caso: Mapping[str, object],
    encabezado: Mapping[str, object],
    analisis: Mapping[str, object],
    totals: Mapping[str, Decimal],
) -> str:
    case_id = _safe_text(caso.get("id_caso"))
    tipo_informe = _safe_text(caso.get("tipo_informe"))
    categoria = _join_nonempty(
        [
            str(caso.get("categoria1") or "").strip(),
            str(caso.get("categoria2") or "").strip(),
        ]
    )
    modalidad = _safe_text(caso.get("modalidad"))
    canal = _safe_text(caso.get("canal"))
    proceso = _safe_text(caso.get("proceso"))
    referencia = _safe_text(encabezado.get("referencia") or caso.get("referencia"))
    narrativa = _pick_key_message(analisis)

    sentences = [
        f"Caso {case_id} ({tipo_informe}).",
        f"Categoría {categoria}; modalidad {modalidad}; canal {canal}; proceso {proceso}.",
        f"Referencia: {referencia}.",
    ]
    if narrativa:
        sentences.insert(1, _truncate(narrativa, 240))
    impact = (
        "Impacto financiero: "
        f"Monto investigado {_format_amount(totals.get('investigado'))}; "
        f"Pérdida fraude {_format_amount(totals.get('perdida_fraude'))}; "
        f"Contingencia {_format_amount(totals.get('contingencia'))}; "
        f"Recuperado {_format_amount(totals.get('recuperado'))}."
    )
    sentences.append(impact)
    combined = " ".join(sentence for sentence in sentences if sentence and sentence != PLACEHOLDER)
    return _truncate(combined, MAX_PARAGRAPH_CHARS) or PLACEHOLDER


def _build_context_section(
    caso: Mapping[str, object],
    encabezado: Mapping[str, object],
    productos: Sequence[Mapping[str, object]],
    reclamos: Sequence[Mapping[str, object]],
) -> str:
    dirigido_a = _safe_text(encabezado.get("dirigido_a"))
    area_reporte = _safe_text(encabezado.get("area_reporte") or caso.get("area_reporte"))
    fecha_reporte = _safe_text(encabezado.get("fecha_reporte") or caso.get("fecha_reporte"))
    ocurrencia = _format_date(caso.get("fecha_de_ocurrencia"))
    descubrimiento = _format_date(caso.get("fecha_de_descubrimiento"))

    productos_texto = _summarize_values(
        [
            str(prod.get("tipo_producto") or prod.get("producto") or "").strip()
            for prod in productos
            if isinstance(prod, Mapping)
        ]
    )
    procesos = _summarize_values(
        [
            str(prod.get("proceso") or "").strip()
            for prod in productos
            if isinstance(prod, Mapping)
        ]
    )
    if procesos == PLACEHOLDER:
        procesos = _safe_text(caso.get("proceso"))

    analiticas = _summarize_values(
        [
            str(rec.get("codigo_analitica") or "").strip()
            for rec in reclamos
            if isinstance(rec, Mapping)
        ]
    )
    centro_costos = _safe_text(caso.get("centro_costos"))

    if all(
        value == PLACEHOLDER
        for value in (
            dirigido_a,
            area_reporte,
            fecha_reporte,
            ocurrencia,
            descubrimiento,
            productos_texto,
            procesos,
            analiticas,
            centro_costos,
        )
    ):
        return PLACEHOLDER

    sentences = [
        f"Dirigido a: {dirigido_a}. Área de reporte: {area_reporte}. Fecha de reporte: {fecha_reporte}.",
        f"Fechas clave: ocurrencia {ocurrencia}; descubrimiento {descubrimiento}.",
        f"Productos investigados: {productos_texto}. Procesos impactados: {procesos}.",
        f"Analítica contable: {analiticas}. Centro de costos: {centro_costos}.",
    ]
    combined = " ".join(sentence for sentence in sentences if sentence and sentence != PLACEHOLDER)
    return _truncate(combined, MAX_PARAGRAPH_CHARS) or PLACEHOLDER


def _build_scope_section(
    clientes: Sequence[Mapping[str, object]],
    colaboradores: Sequence[Mapping[str, object]],
    productos: Sequence[Mapping[str, object]],
    reclamos: Sequence[Mapping[str, object]],
) -> str:
    if not any([clientes, colaboradores, productos, reclamos]):
        return PLACEHOLDER
    clientes_names = _summarize_names(clientes, first_key="nombres", last_key="apellidos")
    colaboradores_names = _summarize_names(colaboradores, first_key="nombres", last_key="apellidos")
    products_ids = _summarize_values(
        [
            str(prod.get("id_producto") or "").strip()
            for prod in productos
            if isinstance(prod, Mapping)
        ]
    )
    sentences = [
        f"Clientes vinculados: {len(clientes)} ({clientes_names}).",
        f"Colaboradores involucrados: {len(colaboradores)} ({colaboradores_names}).",
        f"Productos investigados: {len(productos)} (IDs {products_ids}).",
        f"Reclamos asociados: {len(reclamos)}.",
    ]
    return _truncate(" ".join(sentences), MAX_PARAGRAPH_CHARS) or PLACEHOLDER


def _build_analysis_section(analisis: Mapping[str, object]) -> str:
    parts = []
    for key, label in (
        ("antecedentes", "Antecedentes"),
        ("modus_operandi", "Modus operandi"),
        ("hallazgos", "Hallazgos"),
        ("descargos", "Descargos"),
    ):
        text = _extract_text(analisis.get(key))
        if text:
            parts.append(f"{label}: {_truncate(text, 220)}")
    if not parts:
        comentario = _extract_text(analisis.get("comentario_amplio"))
        if comentario:
            parts.append(comentario)
    return _truncate(" ".join(parts), MAX_PARAGRAPH_CHARS) or PLACEHOLDER


def _build_risk_norm_section(
    riesgos: Sequence[Mapping[str, object]],
    normas: Sequence[Mapping[str, object]],
) -> str:
    risk_lines = []
    for riesgo in riesgos:
        if not isinstance(riesgo, Mapping):
            continue
        risk_id = _safe_text(riesgo.get("id_riesgo"))
        desc = _safe_text(riesgo.get("descripcion"))
        criticidad = _safe_text(riesgo.get("criticidad"))
        if all(value == PLACEHOLDER for value in (risk_id, desc, criticidad)):
            continue
        risk_lines.append(f"{risk_id} ({criticidad}) - {desc}")
    norm_lines = []
    for norma in normas:
        if not isinstance(norma, Mapping):
            continue
        norm_id = _safe_text(norma.get("id_norma"))
        desc = _safe_text(norma.get("descripcion"))
        if all(value == PLACEHOLDER for value in (norm_id, desc)):
            continue
        norm_lines.append(f"{norm_id}: {desc}")

    risk_summary = _summarize_values(risk_lines)
    norm_summary = _summarize_values(norm_lines)
    if risk_summary == PLACEHOLDER and norm_summary == PLACEHOLDER:
        return PLACEHOLDER
    return _truncate(
        f"Riesgos potenciales: {risk_summary}. Normas transgredidas: {norm_summary}.",
        MAX_PARAGRAPH_CHARS,
    )


def _build_conclusions_section(
    analisis: Mapping[str, object],
    recomendaciones: Mapping[str, object],
) -> str:
    conclusion = _extract_text(analisis.get("conclusiones"))
    recomendacion_general = _extract_text(analisis.get("recomendaciones"))
    recomendacion_detalle = []
    for key, label in (
        ("laboral", "Laboral"),
        ("operativo", "Operativo"),
        ("legal", "Legal"),
    ):
        entries = recomendaciones.get(key) or []
        if isinstance(entries, str):
            entries = [entries]
        if isinstance(entries, Sequence):
            cleaned = [sanitize_rich_text(entry, max_chars=160).strip() for entry in entries if entry]
        else:
            cleaned = []
        if cleaned:
            recomendacion_detalle.append(f"{label}: {', '.join(cleaned[:MAX_LIST_ITEMS])}")

    parts = []
    if conclusion:
        parts.append(f"Conclusiones: {_truncate(conclusion, 240)}")
    if recomendacion_general:
        parts.append(f"Recomendaciones: {_truncate(recomendacion_general, 240)}")
    if recomendacion_detalle:
        parts.append(f"Recomendaciones por categoría: {'; '.join(recomendacion_detalle)}")
    return _truncate(" ".join(parts), MAX_PARAGRAPH_CHARS) or PLACEHOLDER


def _build_evidence_section(
    caso: Mapping[str, object],
    encabezado: Mapping[str, object],
    totals: Mapping[str, Decimal],
    clientes: Sequence[Mapping[str, object]],
    colaboradores: Sequence[Mapping[str, object]],
    productos: Sequence[Mapping[str, object]],
    reclamos: Sequence[Mapping[str, object]],
    riesgos: Sequence[Mapping[str, object]],
    normas: Sequence[Mapping[str, object]],
) -> list[str]:
    lines = [
        f"Clientes vinculados: {len(clientes)}",
        f"Colaboradores involucrados: {len(colaboradores)}",
        f"Productos investigados: {len(productos)}",
        f"Reclamos asociados: {len(reclamos)}",
        f"Riesgos registrados: {len(riesgos)}",
        f"Normas registradas: {len(normas)}",
        f"Monto investigado: {_format_amount(totals.get('investigado'))}",
        f"Pérdida fraude: {_format_amount(totals.get('perdida_fraude'))}",
        f"Contingencia: {_format_amount(totals.get('contingencia'))}",
        f"Recuperado: {_format_amount(totals.get('recuperado'))}",
        f"Fecha de ocurrencia: {_format_date(caso.get('fecha_de_ocurrencia'))}",
        f"Fecha de descubrimiento: {_format_date(caso.get('fecha_de_descubrimiento'))}",
        f"Dirigido a: {_safe_text(encabezado.get('dirigido_a'))}",
        f"Área de reporte: {_safe_text(encabezado.get('area_reporte'))}",
    ]
    return lines


def _render_summary(sections: Mapping[str, str], header_lines: Sequence[str], evidence: Sequence[str]) -> str:
    blocks = [
        "# Resumen Ejecutivo",
        *header_lines,
        "",
    ]
    blocks.extend(_render_section(title, body) for title, body in sections.items())
    blocks.append("## Evidencia y trazabilidad\n")
    blocks.append(_render_bullets(evidence))
    return "\n".join(blocks).strip() + "\n"


def _build_resumen_llm_prompt(section_name: str, section_text: str, *, case_id: str, tipo_informe: str) -> str:
    return (
        "Eres un analista senior de fraude y riesgo operacional. "
        "Reescribe la sección con tono ejecutivo, precisión factual y sin inventar datos. "
        "No incluyas PII ni agregues encabezados. Entrega un solo párrafo. "
        f"Caso: {case_id or PLACEHOLDER}. Tipo de informe: {tipo_informe or PLACEHOLDER}. "
        f"Sección objetivo: {section_name}. "
        "Mantén información accionable y evita repetición. "
        f"Texto base: {section_text}"
    )


def _refine_resumen_sections_with_llm(
    sections: dict[str, str],
    *,
    case_id: str,
    tipo_informe: str,
    llm_helper: SpanishSummaryHelper | None,
) -> dict[str, str]:
    if llm_helper is None:
        return sections
    refined: dict[str, str] = {}
    for section_name, section_text in sections.items():
        if section_text == PLACEHOLDER:
            refined[section_name] = section_text
            continue
        prompt = _build_resumen_llm_prompt(
            section_name,
            section_text,
            case_id=case_id,
            tipo_informe=tipo_informe,
        )
        llm_text = llm_helper.summarize(f"resumen_ejecutivo_{section_name}", prompt, max_new_tokens=220)
        refined[section_name] = _truncate(llm_text or section_text, MAX_PARAGRAPH_CHARS)
    return refined


def build_resumen_ejecutivo_md(
    data: CaseData | Mapping[str, object],
    output_path: Path,
    llm_helper: SpanishSummaryHelper | None = None,
) -> Path:
    dataset = data if isinstance(data, CaseData) else CaseData.from_mapping(data or {})
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    case = dataset.get("caso", {}) if isinstance(dataset, Mapping) else {}
    encabezado = dataset.get("encabezado", {}) if isinstance(dataset, Mapping) else {}
    analisis = dataset.get("analisis", {}) if isinstance(dataset, Mapping) else {}
    clientes = dataset.get("clientes") if isinstance(dataset, Mapping) else []
    colaboradores = dataset.get("colaboradores") if isinstance(dataset, Mapping) else []
    productos = dataset.get("productos") if isinstance(dataset, Mapping) else []
    reclamos = dataset.get("reclamos") if isinstance(dataset, Mapping) else []
    riesgos = dataset.get("riesgos") if isinstance(dataset, Mapping) else []
    normas = dataset.get("normas") if isinstance(dataset, Mapping) else []
    recomendaciones = dataset.get("recomendaciones_categorias") if isinstance(dataset, Mapping) else {}

    totals = _aggregate_amounts(productos)
    case_id = _safe_text(case.get("id_caso"))
    header_lines = [
        f"**Caso:** {case_id}",
        f"**Tipo de informe:** {_safe_text(case.get('tipo_informe'))}",
        f"**Fecha de reporte:** {_safe_text(encabezado.get('fecha_reporte') or case.get('fecha_reporte'))}",
    ]

    sections = {
        "Mensaje clave": _build_key_message(case, encabezado, analisis, totals),
        "Contexto del caso": _build_context_section(case, encabezado, productos, reclamos),
        "Alcance y afectados": _build_scope_section(clientes, colaboradores, productos, reclamos),
        "Hallazgos y análisis": _build_analysis_section(analisis),
        "Riesgos y normas": _build_risk_norm_section(riesgos, normas),
        "Conclusiones y recomendaciones": _build_conclusions_section(analisis, recomendaciones),
    }
    sections = _refine_resumen_sections_with_llm(
        sections,
        case_id=case_id,
        tipo_informe=_safe_text(case.get("tipo_informe")),
        llm_helper=llm_helper,
    )
    evidence = _build_evidence_section(
        case,
        encabezado,
        totals,
        clientes,
        colaboradores,
        productos,
        reclamos,
        riesgos,
        normas,
    )
    content = _render_summary(sections, header_lines, evidence)
    output_path.write_text(content, encoding="utf-8")
    return output_path


__all__ = [
    "build_resumen_ejecutivo_filename",
    "build_resumen_ejecutivo_md",
]
