from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import importlib.util
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from validators import parse_decimal_amount, sanitize_rich_text
from report_builder import CaseData

pptx_spec = importlib.util.find_spec("pptx")
if pptx_spec:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt
else:  # pragma: no cover - dependencia opcional
    Presentation = None
    RGBColor = None
    MSO_SHAPE = None
    PP_ALIGN = None
    Inches = None
    Pt = None

PPTX_AVAILABLE = Presentation is not None
PPTX_MISSING_MESSAGE = (
    "La dependencia opcional 'python-pptx' no está instalada. "
    "Ejecuta 'pip install python-pptx' para habilitar la alerta temprana en PPT."
)
PLACEHOLDER = "No aplica / Sin información registrada."
DEFAULT_MODEL = "PlanTL-GOB-ES/flan-t5-base-spanish"
MAX_SECTION_CHARS = 600

TRANSFORMERS_AVAILABLE = importlib.util.find_spec("transformers") is not None

SLIDE_WIDTH_16_9 = Inches(13.33) if Inches else 0
SLIDE_HEIGHT_16_9 = Inches(7.5) if Inches else 0
MARGIN = Inches(0.4) if Inches else 0
COLUMN_GAP = Inches(0.3) if Inches else 0
MASTHEAD_HEIGHT = Inches(1.1) if Inches else 0


def _safe_text(value: str | None, placeholder: str = PLACEHOLDER) -> str:
    return (value or "").strip() or placeholder


def _format_date(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return PLACEHOLDER
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        return text


def _format_amount(value: Decimal | None) -> str:
    if value is None:
        return PLACEHOLDER
    quantized = value.quantize(Decimal("0.01"))
    return f"{quantized:,.2f}"


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
            amount = parse_decimal_amount(product.get(field) if isinstance(product, Mapping) else None)
            if amount is not None:
                totals[key] += amount
    return totals


def _extract_rich_text(entry: object) -> str:
    if isinstance(entry, Mapping):
        raw_text = entry.get("text")
    else:
        raw_text = entry
    return sanitize_rich_text(raw_text, max_chars=MAX_SECTION_CHARS)


def _join_sentences(lines: Iterable[str], *, max_chars: int = MAX_SECTION_CHARS) -> str:
    text = " ".join(part for part in (line.strip() for line in lines) if part)
    return sanitize_rich_text(text, max_chars=max_chars)


def _collect_narrative(analysis: Mapping[str, object]) -> str:
    ordered_keys = (
        ("antecedentes", "Antecedentes"),
        ("modus_operandi", "Modus operandi"),
        ("hallazgos", "Hallazgos"),
        ("descargos", "Descargos"),
        ("conclusiones", "Conclusiones"),
        ("recomendaciones", "Recomendaciones"),
    )
    sections: list[str] = []
    for key, label in ordered_keys:
        text = _extract_rich_text(analysis.get(key))
        if text:
            sections.append(f"{label}: {text}")
    return _join_sentences(sections)


def _timeline_summary(caso: Mapping[str, object], productos: Sequence[Mapping[str, object]]) -> str:
    fases: list[str] = []
    ocurrencia = _format_date(caso.get("fecha_de_ocurrencia"))
    descubrimiento = _format_date(caso.get("fecha_de_descubrimiento"))
    if ocurrencia != PLACEHOLDER or descubrimiento != PLACEHOLDER:
        fases.append(f"Ocurrencia: {ocurrencia}; Descubrimiento: {descubrimiento}")
    product_dates = [
        _format_date(prod.get("fecha_ocurrencia"))
        for prod in productos
        if isinstance(prod, Mapping) and prod.get("fecha_ocurrencia")
    ]
    if product_dates:
        fases.append(f"Productos registrados en: {', '.join(sorted(set(product_dates)))}")
    return _join_sentences(fases, max_chars=280) or PLACEHOLDER


def _risk_summary(risks: Iterable[Mapping[str, object]]) -> str:
    parts: list[str] = []
    for risk in risks or []:
        if not isinstance(risk, Mapping):
            continue
        risk_id = (risk.get("id_riesgo") or "").strip()
        desc = (risk.get("descripcion") or "").strip()
        criticidad = (risk.get("criticidad") or "").strip()
        snippet = "; ".join(part for part in (risk_id, desc, criticidad) if part)
        if snippet:
            parts.append(snippet)
    return _join_sentences(parts, max_chars=360)


def _acciones_summary(analysis: Mapping[str, object], operaciones: Sequence[Mapping[str, object]]) -> str:
    recomendacion = _extract_rich_text(analysis.get("recomendaciones"))
    if recomendacion:
        return recomendacion
    lines: list[str] = []
    for op in operaciones or []:
        if not isinstance(op, Mapping):
            continue
        cliente = _safe_text(op.get("cliente"), "")
        estado = _safe_text(op.get("estado"), "")
        accion = _safe_text(op.get("accion"), "")
        resumen = " ".join(part for part in (accion, cliente, estado) if part)
        if resumen:
            lines.append(resumen)
    return _join_sentences(lines, max_chars=280)


def _responsables_summary(caso: Mapping[str, object], colaboradores: Sequence[Mapping[str, object]]) -> str:
    responsables: list[str] = []
    investigador = caso.get("investigador_nombre") or (caso.get("investigador") or {}).get("nombre")
    if investigador:
        responsables.append(f"Investigador: {_safe_text(investigador, 'Investigador principal')}")
    for colab in colaboradores or []:
        if not isinstance(colab, Mapping):
            continue
        nombre = _safe_text(colab.get("nombres") or colab.get("nombre_completo"), "")
        if not nombre:
            continue
        flag = _safe_text(colab.get("flag"), "")
        area = _safe_text(colab.get("area"), "")
        responsables.append(f"{nombre} ({flag or 'involucrado'} - {area or 'área no especificada'})")
    return _join_sentences(responsables, max_chars=280) or PLACEHOLDER


def _default_case_title(caso: Mapping[str, object]) -> str:
    codigo = _safe_text(caso.get("id_caso"), "Caso sin código")
    emisor = _safe_text(caso.get("investigador_nombre") or (caso.get("investigador") or {}).get("nombre"), "Equipo de investigación")
    return f"{codigo} · Emitido por {emisor}"


def _build_prompt(section: str, contexto: str, caso: Mapping[str, object]) -> str:
    categoria = _safe_text(caso.get("categoria1"), "Categoría no especificada")
    modalidad = _safe_text(caso.get("modalidad"), "Modalidad no especificada")
    canal = _safe_text(caso.get("canal"), "Canal no especificado")
    tipo = _safe_text(caso.get("tipo_informe"), "Tipo no especificado")
    return (
        "Eres un analista de riesgos que redacta resúmenes ejecutivos en español. "
        "Redacta respuestas de 2 a 4 frases, tono conciso, en voz activa, sin viñetas. "
        "Mantén un máximo de 120 palabras y evita repetir datos ya mencionados. "
        f"Sección objetivo: {section}. "
        f"Tipo de informe: {tipo}; Categoría: {categoria}; Modalidad: {modalidad}; Canal: {canal}. "
        "Usa los datos factuales del caso y la cronología incluida. "
        f"Contexto completo:\n{contexto}"
    )


@dataclass
class SpanishSummaryHelper:
    model_name: str = DEFAULT_MODEL
    max_new_tokens: int = 144
    _pipeline: object = field(default=None, init=False, repr=False)
    _load_error: Exception | None = field(default=None, init=False, repr=False)
    _cache: dict[tuple[str, str, int], str] = field(default_factory=dict, init=False, repr=False)

    def _load_pipeline(self):
        if self._pipeline or self._load_error:
            return
        if not TRANSFORMERS_AVAILABLE:
            self._load_error = RuntimeError("transformers no disponible")
            return
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            self._pipeline = pipeline(
                task="text2text-generation",
                model=model,
                tokenizer=tokenizer,
            )
        except Exception as exc:  # pragma: no cover - defensivo frente a entornos sin pesos locales
            self._load_error = exc

    def summarize(self, section: str, prompt: str, *, max_new_tokens: int | None = None) -> str | None:
        key = (section, prompt, max_new_tokens or self.max_new_tokens)
        if key in self._cache:
            return self._cache[key]

        self._load_pipeline()
        if not self._pipeline:
            return None

        from transformers import set_seed

        try:
            set_seed(0)
            outputs = self._pipeline(
                prompt,
                max_new_tokens=max_new_tokens or self.max_new_tokens,
                num_beams=4,
                do_sample=False,
            )
        except Exception as exc:  # pragma: no cover - defensivo frente a errores del modelo
            self._load_error = exc
            return None

        if not outputs:
            return None
        text = sanitize_rich_text(outputs[0].get("generated_text"), max_chars=MAX_SECTION_CHARS).strip()
        if not text:
            return None
        self._cache[key] = text
        return text


def _synthesize_section_text(
    section: str,
    caso: Mapping[str, object],
    analisis: Mapping[str, object],
    productos: Sequence[Mapping[str, object]],
    riesgos: Sequence[Mapping[str, object]],
    operaciones: Sequence[Mapping[str, object]],
    colaboradores: Sequence[Mapping[str, object]],
    llm_helper: SpanishSummaryHelper | None,
) -> str:
    narrative = _collect_narrative(analisis)
    timeline = _timeline_summary(caso, productos)
    riesgos_text = _risk_summary(riesgos)
    acciones_text = _acciones_summary(analisis, operaciones)
    responsables_text = _responsables_summary(caso, colaboradores)

    context_lines = [
        f"Caso: {_safe_text(caso.get('id_caso'), 'sin ID')} | "
        f"Tipo: {_safe_text(caso.get('tipo_informe'), 'sin tipo')} | "
        f"Modalidad: {_safe_text(caso.get('modalidad'), 'sin modalidad')}",
        f"Cronología: {timeline}",
        f"Narrativa: {narrative or PLACEHOLDER}",
        f"Riesgos: {riesgos_text or PLACEHOLDER}",
        f"Acciones: {acciones_text or PLACEHOLDER}",
        f"Responsables: {responsables_text or PLACEHOLDER}",
    ]
    prompt = _build_prompt(section, "\n".join(context_lines), caso)

    llm_summary = llm_helper.summarize(section, prompt) if llm_helper else None
    if llm_summary:
        return llm_summary

    if section == "Resumen":
        fallback_source = narrative or acciones_text or riesgos_text
    elif section == "Cronología":
        fallback_source = timeline
    elif section == "Análisis":
        fallback_source = narrative
    elif section == "Riesgos":
        fallback_source = riesgos_text
    elif section == "Acciones":
        fallback_source = acciones_text
    else:  # Responsables
        fallback_source = responsables_text
    return fallback_source or PLACEHOLDER


def _add_section_box(slide, left, top, width, height, title: str, body: str):
    if not PPTX_AVAILABLE:
        return None
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(235, 239, 249)
    shape.line.color.rgb = RGBColor(51, 73, 123)
    text_frame = shape.text_frame
    text_frame.clear()

    title_para = text_frame.paragraphs[0]
    title_para.text = title
    title_para.font.size = Pt(16)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(36, 64, 112)

    body_para = text_frame.add_paragraph()
    body_para.text = body
    body_para.font.size = Pt(12)
    body_para.space_before = Pt(4)
    body_para.space_after = Pt(0)
    body_para.alignment = PP_ALIGN.LEFT
    return shape


def _add_masthead(slide, slide_width, title_text: str, subtitle: str):
    if not PPTX_AVAILABLE:
        return None
    masthead = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, slide_width, MASTHEAD_HEIGHT)
    masthead.fill.solid()
    masthead.fill.fore_color.rgb = RGBColor(21, 43, 77)
    masthead.line.fill.background()
    text_frame = masthead.text_frame
    text_frame.clear()

    title = text_frame.paragraphs[0]
    title.text = title_text
    title.font.size = Pt(24)
    title.font.bold = True
    title.font.color.rgb = RGBColor(255, 255, 255)

    subtitle_para = text_frame.add_paragraph()
    subtitle_para.text = subtitle
    subtitle_para.font.size = Pt(14)
    subtitle_para.font.color.rgb = RGBColor(214, 225, 240)
    return masthead


def _add_header_cards(slide, left, top, width, height, caso: Mapping[str, object], totals: Mapping[str, Decimal]):
    if not PPTX_AVAILABLE:
        return None
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(246, 248, 252)
    shape.line.color.rgb = RGBColor(179, 191, 214)
    frame = shape.text_frame
    frame.clear()

    entries = [
        ("Código", _safe_text(caso.get("id_caso"), "Caso sin código")),
        ("Tipo", _safe_text(caso.get("tipo_informe"))),
        ("Categoría", _safe_text(caso.get("categoria1"))),
        ("Modalidad", _safe_text(caso.get("modalidad"))),
        ("Proceso", _safe_text(caso.get("proceso"))),
        (
            "Fechas",
            f"{_format_date(caso.get('fecha_de_ocurrencia'))} / {_format_date(caso.get('fecha_de_descubrimiento'))}",
        ),
        ("Investigador", _safe_text(caso.get("investigador_nombre") or (caso.get("investigador") or {}).get("nombre"))),
        ("Monto investigado", _format_amount(totals.get("investigado"))),
        ("Contingencia", _format_amount(totals.get("contingencia"))),
    ]
    for label, value in entries:
        para = frame.add_paragraph()
        para.text = f"{label}: {value}"
        para.font.size = Pt(12)
        if para.runs:
            para.runs[0].font.bold = True
    return shape


def build_alerta_temprana_ppt(
    data: CaseData | Mapping[str, object],
    output_path: Path,
    llm_helper: SpanishSummaryHelper | None = None,
) -> Path:
    """Genera una presentación PPTX con la alerta temprana."""

    if not PPTX_AVAILABLE:
        raise RuntimeError("python-pptx no está disponible para generar la alerta temprana.")

    dataset = data if isinstance(data, CaseData) else CaseData.from_mapping(data or {})
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    caso = dataset.get("caso", {}) if isinstance(dataset, Mapping) else {}
    productos = dataset.get("productos") if isinstance(dataset, Mapping) else []
    riesgos = dataset.get("riesgos") if isinstance(dataset, Mapping) else []
    analisis = dataset.get("analisis") if isinstance(dataset, Mapping) else {}
    operaciones = dataset.get("operaciones") if isinstance(dataset, Mapping) else []
    colaboradores = dataset.get("colaboradores") if isinstance(dataset, Mapping) else []

    llm = llm_helper or SpanishSummaryHelper()

    presentation = Presentation()
    presentation.slide_width = SLIDE_WIDTH_16_9
    presentation.slide_height = SLIDE_HEIGHT_16_9
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])

    totals = _aggregate_amounts(productos if isinstance(productos, list) else [])
    _add_masthead(
        slide,
        presentation.slide_width,
        title_text="Alerta temprana | " + _safe_text(caso.get("titulo") or caso.get("id_caso"), "Caso sin título"),
        subtitle=_default_case_title(caso),
    )

    body_top = MARGIN + MASTHEAD_HEIGHT
    column_width = (presentation.slide_width - (2 * MARGIN) - COLUMN_GAP) // 2

    left_x = MARGIN
    right_x = MARGIN + column_width + COLUMN_GAP

    header_height = Inches(2.25)
    summary_height = Inches(1.5)
    responsables_height = Inches(1.2)
    cronologia_height = Inches(1.2)
    analisis_height = Inches(1.8)
    riesgos_height = Inches(1.1)
    acciones_height = Inches(0.9)

    _add_header_cards(slide, left_x, body_top, column_width, header_height, caso, totals)

    resumen_text = _synthesize_section_text(
        "Resumen", caso, analisis, productos, riesgos, operaciones, colaboradores, llm
    )
    _add_section_box(slide, left_x, body_top + header_height + Inches(0.1), column_width, summary_height, "Resumen", resumen_text)

    responsables_text = _synthesize_section_text(
        "Responsables", caso, analisis, productos, riesgos, operaciones, colaboradores, llm
    )
    _add_section_box(
        slide,
        left_x,
        body_top + header_height + summary_height + Inches(0.2),
        column_width,
        responsables_height,
        "Responsables",
        responsables_text,
    )

    cronologia_text = _synthesize_section_text(
        "Cronología", caso, analisis, productos, riesgos, operaciones, colaboradores, llm
    )
    _add_section_box(
        slide,
        right_x,
        body_top,
        column_width,
        cronologia_height,
        "Cronología",
        cronologia_text,
    )

    analisis_text = _synthesize_section_text(
        "Análisis", caso, analisis, productos, riesgos, operaciones, colaboradores, llm
    )
    _add_section_box(
        slide,
        right_x,
        body_top + cronologia_height + Inches(0.1),
        column_width,
        analisis_height,
        "Análisis",
        analisis_text,
    )

    riesgos_text = _synthesize_section_text(
        "Riesgos", caso, analisis, productos, riesgos, operaciones, colaboradores, llm
    )
    _add_section_box(
        slide,
        right_x,
        body_top + cronologia_height + analisis_height + Inches(0.2),
        column_width,
        riesgos_height,
        "Riesgos",
        riesgos_text,
    )

    acciones_text = _synthesize_section_text(
        "Acciones", caso, analisis, productos, riesgos, operaciones, colaboradores, llm
    )
    _add_section_box(
        slide,
        right_x,
        body_top + cronologia_height + analisis_height + riesgos_height + Inches(0.3),
        column_width,
        acciones_height,
        "Acciones",
        acciones_text,
    )

    presentation.save(output_path)
    return output_path


__all__ = [
    "build_alerta_temprana_ppt",
    "SpanishSummaryHelper",
    "PPTX_AVAILABLE",
    "PPTX_MISSING_MESSAGE",
]
