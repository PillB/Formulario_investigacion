"""Utility to render the architecture PDF for Formulario_investigacion.

The script regenerates Mermaid diagrams (PNG) using mermaid-cli and then
assembles a styled PDF with ReportLab. It keeps all logic in one place so the
repo does not need to track the binary PDF artifact.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, LETTER, landscape
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
)
from reportlab.platypus.tableofcontents import TableOfContents

PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "docs"
DEFAULT_OUTPUT = PROJECT_ROOT / "Formulario_Investigacion_Architecture_and_Data_Flow.pdf"
ARCH_MMD = DOCS_DIR / "architecture.mmd"
ARCH_PNG = DOCS_DIR / "architecture.png"
SEQ_MMD = DOCS_DIR / "sequence_diagram.mmd"
SEQ_PNG = DOCS_DIR / "sequence.png"
PUPPETEER_CONFIG = PROJECT_ROOT / "puppeteer-config.json"


class HeadingParagraph(Paragraph):
    """Paragraph that stores the heading level to feed the TOC."""

    def __init__(self, text: str, style: ParagraphStyle, level: int):
        super().__init__(text, style)
        self.toc_level = level


# ---------------------------------------------------------------------------
# Mermaid helpers
# ---------------------------------------------------------------------------


def render_mermaid(source: Path, target: Path) -> Path:
    """Render a Mermaid file to PNG using mermaid-cli.

    The function tries an installed ``mmdc`` binary first and falls back to
    ``npx -y @mermaid-js/mermaid-cli`` to avoid tracking rendered assets in git.
    """

    if not source.exists():
        raise FileNotFoundError(source)

    target.parent.mkdir(parents=True, exist_ok=True)

    cmd: list[str]
    if shutil.which("mmdc"):
        cmd = ["mmdc", "-i", str(source), "-o", str(target)]
    elif shutil.which("npx"):
        cmd = [
            "npx",
            "-y",
            "@mermaid-js/mermaid-cli",
            "-i",
            str(source),
            "-o",
            str(target),
        ]
    else:
        raise RuntimeError(
            "Se requiere mermaid-cli. Instala 'npm install -g @mermaid-js/mermaid-cli'"
        )

    if PUPPETEER_CONFIG.exists():
        cmd.extend(["-p", str(PUPPETEER_CONFIG)])

    subprocess.run(cmd, check=True)
    return target


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------


def _build_stylesheet() -> StyleSheet1:
    styles = getSampleStyleSheet()

    def _ensure_style(name: str, **attributes: object) -> ParagraphStyle:
        style = styles[name] if name in styles.byName else ParagraphStyle(name=name)
        for attr, value in attributes.items():
            setattr(style, attr, value)
        if name not in styles.byName:
            styles.add(style)
        return style

    _ensure_style(
        name="CoverTitle",
        fontSize=24,
        leading=28,
        spaceAfter=18,
        alignment=1,
    )
    _ensure_style(
        name="CoverSubtitle",
        fontSize=12,
        leading=14,
        textColor=colors.grey,
        alignment=1,
        spaceAfter=6,
    )
    _ensure_style(
        name="Meta",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#555555"),
        alignment=1,
        spaceAfter=14,
    )

    _ensure_style(name="Heading1", fontSize=18, leading=22, spaceAfter=12)
    _ensure_style(name="Heading2", fontSize=14, leading=18, spaceAfter=8)

    _ensure_style(
        name="Body",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=14,
        spaceAfter=8,
    )
    _ensure_style(
        name="Bullet",
        parent=styles["Body"],
        leftIndent=12,
        bulletIndent=0,
        spaceAfter=4,
    )
    _ensure_style(
        name="TableHeader",
        parent=styles["Body"],
        fontSize=10,
        textColor=colors.white,
        backColor=colors.HexColor("#1f3a93"),
        spaceAfter=4,
    )
    _ensure_style(
        name="TableCell",
        parent=styles["Body"],
        fontSize=9,
        leading=12,
    )
    return styles


# ---------------------------------------------------------------------------
# PDF assembly
# ---------------------------------------------------------------------------


def _after_flowable(doc: BaseDocTemplate, flowable):
    if getattr(flowable, "toc_level", None) is not None:
        text = flowable.getPlainText()
        level = flowable.toc_level
        doc.notify("TOCEntry", (level, text, doc.page))


def _page_decor(canvas, doc: BaseDocTemplate):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawRightString(
        doc.pagesize[0] - doc.rightMargin,
        doc.bottomMargin - 12,
        f"Página {doc.page}",
    )
    canvas.restoreState()


def _heading(text: str, styles: StyleSheet1, level: int) -> HeadingParagraph:
    style_name = f"Heading{level}"
    return HeadingParagraph(text, styles[style_name], level)


def _paragraph(text: str, styles: StyleSheet1) -> Paragraph:
    return Paragraph(textwrap.dedent(text).strip(), styles["Body"])


def _bullet_list(items: list[str], styles: StyleSheet1) -> ListFlowable:
    return ListFlowable(
        [ListItem(_paragraph(item, styles), leftIndent=0) for item in items],
        bulletType="bullet",
        start=None,
        leftIndent=12,
    )


def _technology_table(styles: StyleSheet1) -> Table:
    data = [
        ["Capa", "Tecnología"],
        ["UI de escritorio", "Tkinter / ttk"],
        ["Diagramas", "Mermaid (architecture.mmd, sequence_diagram.mmd)"],
        ["Persistencia temporal", "autosave.json, autosaves/<caso>/auto_<n>.json"],
        ["Validaciones", "validators.py y FieldValidator"],
        ["Importación", "utils.iter_massive_csv_rows y importadores en Acciones"],
        ["Reportes", "report_builder.py (CSV/JSON/Markdown/DOCX)"],
        ["Logs y analítica", "logs.csv + analytics/usage_visualizer.py"],
    ]

    table = Table(data, repeatRows=1)
    table.setStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a93")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )
    return table


def _flowable_image(image_path: Path, target_width: float) -> Image:
    """Scale an image to the requested width while keeping the aspect ratio."""

    reader = ImageReader(str(image_path))
    original_width, original_height = reader.getSize()
    if original_width <= 0 or original_height <= 0:
        raise ValueError("Image dimensions must be positive")

    scale = target_width / float(original_width)
    target_height = original_height * scale
    return Image(str(image_path), width=target_width, height=target_height)


def build_report(output: Path = DEFAULT_OUTPUT) -> Path:
    styles = _build_stylesheet()

    render_mermaid(ARCH_MMD, ARCH_PNG)
    render_mermaid(SEQ_MMD, SEQ_PNG)

    page_margins = {
        "left": 0.7 * inch,
        "right": 0.7 * inch,
        "top": 0.8 * inch,
        "bottom": 0.8 * inch,
    }

    doc = BaseDocTemplate(
        str(output),
        pagesize=LETTER,
        leftMargin=page_margins["left"],
        rightMargin=page_margins["right"],
        topMargin=page_margins["top"],
        bottomMargin=page_margins["bottom"],
        title="Formulario de investigación – Arquitectura",
        author="AI Architecture Assistant",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")

    arch_page_size = landscape(A3)
    arch_frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        arch_page_size[0] - doc.leftMargin - doc.rightMargin,
        arch_page_size[1] - doc.topMargin - doc.bottomMargin,
        id="arch_frame",
    )

    seq_page_size = A3
    seq_frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        seq_page_size[0] - doc.leftMargin - doc.rightMargin,
        seq_page_size[1] - doc.topMargin - doc.bottomMargin,
        id="seq_frame",
    )

    doc.addPageTemplates(
        [
            PageTemplate(id="main", frames=frame, onPage=_page_decor, pagesize=LETTER),
            PageTemplate(
                id="arch_diagram", frames=arch_frame, onPage=_page_decor, pagesize=arch_page_size
            ),
            PageTemplate(
                id="seq_diagram", frames=seq_frame, onPage=_page_decor, pagesize=seq_page_size
            ),
        ]
    )
    doc.afterFlowable = lambda flowable: _after_flowable(doc, flowable)

    today = _dt.date.today().strftime("%Y-%m-%d")

    story = [
        Spacer(1, 1.5 * inch),
        Paragraph("Formulario de Investigación", styles["CoverTitle"]),
        Paragraph("Arquitectura y flujos de datos", styles["CoverSubtitle"]),
        Paragraph(f"Versión 1.0 — {today}", styles["Meta"]),
        Paragraph("Autor: AI Architecture Assistant", styles["Meta"]),
        Spacer(1, 1.2 * inch),
        Paragraph(
            "Documento generado automáticamente. Ejecuta build_architecture_report.py para actualizarlo.",
            styles["Meta"],
        ),
        PageBreak(),
    ]

    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(name="TOCHeading1", fontSize=12, leftIndent=12, spaceAfter=4),
        ParagraphStyle(name="TOCHeading2", fontSize=10, leftIndent=24, spaceAfter=2),
    ]
    story.extend([_heading("Tabla de contenidos", styles, 1), Spacer(1, 0.2 * inch), toc, PageBreak()])

    # Section 1: Contexto
    story.append(_heading("1. Contexto del sistema y propósito", styles, 1))
    story.append(
        _paragraph(
            "Gestión asigna casos de fraude y los investigadores usan la aplicación Tkinter\n"
            "(main.py / app.py) para capturar datos de caso, clientes, colaboradores, productos,\n"
            "riesgos y normas. El objetivo es validar en línea, prevenir duplicados y producir\n"
            "un expediente exportable (CSV/JSON/Markdown/DOCX) desde report_builder.py.",
            styles,
        )
    )

    # Section 2: Flujos de captura
    story.append(_heading("2. Flujos de ingreso de datos", styles, 1))
    story.append(_heading("2.1 Ingreso manual", styles, 2))
    story.append(
        _paragraph(
            "Cada pestaña en ui/ frames utiliza ttk.Entry, Combobox y Text widgets con validación\n"
            "en blur (FieldValidator). Se verifican formatos de fechas, montos y claves para mantener\n"
            "consistencia con las reglas del Design document CM.",
            styles,
        )
    )
    story.append(_heading("2.2 Carga masiva", styles, 2))
    story.append(
        _paragraph(
            "Acciones > Importar procesa archivos .txt (pipes), .csv o .xlsx. El módulo utils.mass_load\n"
            "normaliza filas hacia el modelo interno y las pestañas de UI aplican _apply_*_import_payload\n"
            "para hidratar las tablas y disparar las mismas validaciones que el ingreso manual.",
            styles,
        )
    )
    story.append(_bullet_list(
        [
            "Formatos soportados: .txt con pipes, .csv, .xlsx",
            "Campos mapeados según utils/mass_load.py y cabeceras esperadas en cada entidad",
            "Filas inválidas se descartan con mensajes en la barra de estado y logs",
        ],
        styles,
    ))

    # Section 3: Entidades
    story.append(_heading("3. Entidades y campos", styles, 1))
    story.append(
        _paragraph(
            "Las pestañas Cliente, Equipo, Producto, Reclamo, Involucramiento, Riesgo y Norma usan\n"
            "combobox y entradas obligatorias. Los IDs siguen reglas: caso AAAA-NNNN, reclamo C########,\n"
            "team member letra+5 dígitos, analítica contable 10 dígitos (43/45/46/56) y validaciones\n"
            "de fechas y montos definidas en validators.py.",
            styles,
        )
    )

    # Section 4: Autocomplete
    story.append(_heading("4. Autocomplete y catálogos", styles, 1))
    story.append(
        _paragraph(
            "utils/autocomplete.py conecta Combobox con catálogos locales (client_details.csv,\n"
            "team_details.csv, risk_details.csv, norm_details.csv). En producción se espera consumir\n"
            "archivos descargados de Databricks para clientes/colaboradores, el registro GRC para riesgos\n"
            "y el índice maestro de normas.",
            styles,
        )
    )
    story.append(
        _bullet_list(
            [
                "Autocompletar preserva valores editados por el usuario (should_autofill_field).",
                "Búsquedas se disparan al perder foco o al confirmar el ID.",
                "Fuentes futuras: Databricks (clientes/colaboradores), GRC (riesgos), índice de normas, GDH mensual para activos y cesados.",
            ],
            styles,
        )
    )

    # Section 5: Autosave & logs
    story.append(_heading("5. Autosave y bitácora", styles, 1))
    story.append(
        _paragraph(
            "Autosave se ejecuta de forma diferida tras ediciones y en intervalos; genera autosave.json\n"
            "y autosaves/<timestamp>_<case_id>.json. Los eventos de validación, importación y navegación\n"
            "se almacenan en logs.csv para auditoría y para visualización con analytics/usage_visualizer.py.",
            styles,
        )
    )
    story.append(
        _bullet_list(
            [
                "Desencadenantes: pérdida de foco, temporizador y cambios masivos.",
                "Formato de log: timestamp, tipo, subtipo, widget_id, valor, case_id.",
                "Los respaldos también se copian a 'external drive/<case_id>/' cuando existe permiso.",
            ],
            styles,
        )
    )

    # Section 6: Generación de reportes
    story.append(_heading("6. Flujo de generación de reportes", styles, 1))
    story.append(
        _paragraph(
            "El botón 'Guardar y enviar' valida todas las pestañas (validators.py), construye el contexto con\n"
            "report_builder._build_report_context y exporta CSV, JSON, Markdown y DOCX. Si python-docx está\n"
            "instalado, se arma el informe Word usando la plantilla Plantilla_reporte.md como base.",
            styles,
        )
    )

    # Section 7: Tecnología
    story.append(_heading("7. Resumen de tecnología", styles, 1))
    story.append(_technology_table(styles))

    # Diagrams
    story.append(NextPageTemplate("arch_diagram"))
    story.append(PageBreak())
    story.append(_heading("Anexo A — Diagrama de arquitectura (Mermaid)", styles, 1))
    story.append(Spacer(1, 0.1 * inch))
    story.append(_flowable_image(ARCH_PNG, target_width=arch_frame.width))

    story.append(NextPageTemplate("seq_diagram"))
    story.append(PageBreak())
    story.append(_heading("Anexo B — Diagrama de secuencia", styles, 1))
    story.append(Spacer(1, 0.1 * inch))
    story.append(_flowable_image(SEQ_PNG, target_width=seq_frame.width))

    doc.build(story)
    return output


def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera el PDF de arquitectura y flujos.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Ruta del PDF de salida (por defecto {DEFAULT_OUTPUT.name})",
    )
    return parser.parse_args(args)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = parse_args(argv)
    try:
        output = build_report(args.output)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Error generando el PDF: {exc}\n")
        return 1
    else:
        print(f"PDF generado en {output}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
