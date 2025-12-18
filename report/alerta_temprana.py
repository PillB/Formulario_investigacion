from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Mapping

try:  # python-pptx es opcional en tiempo de ejecución
    from pptx import Presentation
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt
except Exception:  # pragma: no cover - dependencia opcional
    Presentation = None
    PP_ALIGN = None
    Inches = None
    Pt = None

PPTX_AVAILABLE = Presentation is not None
PPTX_MISSING_MESSAGE = (
    "La dependencia opcional 'python-pptx' no está instalada. "
    "Ejecuta 'pip install python-pptx' para habilitar la alerta temprana en PPT."
)
PLACEHOLDER = "No aplica / Sin información registrada."

from report_builder import CaseData
from validators import parse_decimal_amount


def _safe_text(value: str | None) -> str:
    return (value or "").strip() or PLACEHOLDER


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
    try:
        return f"{value.quantize(Decimal('0.01')):,.2f}"
    except Exception:
        return str(value)


def _aggregate_amounts(products: list[Mapping[str, object]] | None) -> dict[str, Decimal]:
    totals = {
        "investigado": Decimal("0"),
        "perdida_fraude": Decimal("0"),
        "falla_procesos": Decimal("0"),
        "contingencia": Decimal("0"),
        "recuperado": Decimal("0"),
    }
    for product in products or []:
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


def _build_body_paragraph(text_frame, text: str, *, bold: bool = False) -> None:
    paragraph = text_frame.add_paragraph()
    paragraph.text = text
    paragraph.level = 1
    if paragraph.runs and bold:
        paragraph.runs[0].font.bold = True


def build_alerta_temprana_ppt(data: CaseData, output_path: Path) -> Path:
    """Genera una presentación PPTX con un resumen de alerta temprana."""

    if not PPTX_AVAILABLE:
        raise RuntimeError("python-pptx no está disponible para generar la alerta temprana.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    presentation = Presentation()
    metadata = data.get("caso", {}) if isinstance(data, Mapping) else {}
    clientes = data.get("clientes") if isinstance(data, Mapping) else []
    productos = data.get("productos") if isinstance(data, Mapping) else []
    riesgos = data.get("riesgos") if isinstance(data, Mapping) else []

    title_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    if title_slide.shapes.title:
        title_slide.shapes.title.text = f"Alerta temprana - {metadata.get('id_caso') or 'Caso sin ID'}"
    subtitle = title_slide.placeholders[1] if len(title_slide.placeholders) > 1 else None
    if subtitle is not None:
        subtitle.text = f"Tipo de informe: {_safe_text(metadata.get('tipo_informe'))}"

    details_slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    details_slide.shapes.title.text = "Resumen del caso"
    body_shape = details_slide.shapes.placeholders[1] if len(details_slide.shapes.placeholders) > 1 else None
    if body_shape is None and Inches:
        body_shape = details_slide.shapes.add_textbox(
            Inches(1), Inches(1.5), Inches(8), Inches(4)
        )
    text_frame = getattr(body_shape, "text_frame", None)
    if text_frame is None:
        raise RuntimeError("No se pudo inicializar el cuerpo de la alerta temprana.")
    text_frame.clear()

    _build_body_paragraph(text_frame, f"Número de caso: {_safe_text(metadata.get('id_caso'))}", bold=True)
    _build_body_paragraph(text_frame, f"Investigador: {_safe_text(metadata.get('investigador_nombre'))}")
    _build_body_paragraph(text_frame, f"Categoría: {_safe_text(metadata.get('categoria1'))}")
    _build_body_paragraph(text_frame, f"Modalidad: {_safe_text(metadata.get('modalidad'))}")
    _build_body_paragraph(
        text_frame,
        f"Fechas (ocurrencia/descubrimiento): {_format_date(metadata.get('fecha_de_ocurrencia'))} / "
        f"{_format_date(metadata.get('fecha_de_descubrimiento'))}",
    )
    _build_body_paragraph(text_frame, f"Clientes involucrados: {len(clientes)}")
    _build_body_paragraph(text_frame, f"Productos registrados: {len(productos)}")
    _build_body_paragraph(text_frame, f"Riesgos capturados: {len(riesgos)}")

    totals = _aggregate_amounts(productos if isinstance(productos, list) else [])
    totals_slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    totals_slide.shapes.title.text = "Montos consolidados"
    totals_shape = totals_slide.shapes.placeholders[1] if len(totals_slide.shapes.placeholders) > 1 else None
    if totals_shape is None and Inches:
        totals_shape = totals_slide.shapes.add_textbox(
            Inches(1), Inches(1.5), Inches(8), Inches(4)
        )
    totals_frame = getattr(totals_shape, "text_frame", None)
    if totals_frame is None:
        raise RuntimeError("No se pudo inicializar el resumen de montos.")
    totals_frame.clear()

    _build_body_paragraph(totals_frame, f"Monto investigado total: {_format_amount(totals['investigado'])}", bold=True)
    _build_body_paragraph(totals_frame, f"Pérdida por fraude: {_format_amount(totals['perdida_fraude'])}")
    _build_body_paragraph(totals_frame, f"Falla en procesos: {_format_amount(totals['falla_procesos'])}")
    _build_body_paragraph(totals_frame, f"Contingencia: {_format_amount(totals['contingencia'])}")
    _build_body_paragraph(totals_frame, f"Recuperado: {_format_amount(totals['recuperado'])}")

    if PP_ALIGN and totals_frame.paragraphs:
        totals_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
    for para in totals_frame.paragraphs:
        for run in para.runs:
            if Pt:
                run.font.size = Pt(14)

    presentation.save(output_path)
    return output_path
