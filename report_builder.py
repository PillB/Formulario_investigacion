from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:  # python-docx es opcional en tiempo de ejecución
    from docx import Document as DocxDocument
except ImportError:  # pragma: no cover - se usa el respaldo integrado
    DocxDocument = None

DOCX_AVAILABLE = DocxDocument is not None
DOCX_MISSING_MESSAGE = (
    "La dependencia opcional 'python-docx' no está instalada. "
    "Instálala con 'pip install python-docx' para habilitar el informe Word."
)

from validators import parse_decimal_amount


@dataclass
class CaseData(Mapping):
    """Estructura normalizada del caso y sus entidades relacionadas."""

    caso: Dict[str, Any]
    clientes: List[Dict[str, Any]]
    colaboradores: List[Dict[str, Any]]
    productos: List[Dict[str, Any]]
    reclamos: List[Dict[str, Any]]
    involucramientos: List[Dict[str, Any]]
    riesgos: List[Dict[str, Any]]
    normas: List[Dict[str, Any]]
    analisis: Dict[str, Any]
    _dict_cache: Dict[str, Any] = field(default=None, init=False, repr=False)

    def as_dict(self) -> Dict[str, Any]:
        if self._dict_cache is None:
            self._dict_cache = {
                "caso": self.caso,
                "clientes": self.clientes,
                "colaboradores": self.colaboradores,
                "productos": self.productos,
                "reclamos": self.reclamos,
                "involucramientos": self.involucramientos,
                "riesgos": self.riesgos,
                "normas": self.normas,
                "analisis": self.analisis,
            }
        return self._dict_cache

    def __getitem__(self, key: str) -> Any:  # type: ignore[override]
        return self.as_dict()[key]

    def __iter__(self):  # type: ignore[override]
        return iter(self.as_dict())

    def __len__(self):  # type: ignore[override]
        return len(self.as_dict())

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        return self.as_dict().get(key, default)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CaseData":
        return cls(
            caso=dict(payload.get("caso") or {}),
            clientes=list(payload.get("clientes") or []),
            colaboradores=list(payload.get("colaboradores") or []),
            productos=list(payload.get("productos") or []),
            reclamos=list(payload.get("reclamos") or []),
            involucramientos=list(payload.get("involucramientos") or []),
            riesgos=list(payload.get("riesgos") or []),
            normas=list(payload.get("normas") or []),
            analisis=dict(payload.get("analisis") or {}),
        )


def _normalize_report_segment(value: str | None, placeholder: str) -> str:
    text = (value or "").strip() or placeholder
    for ch in '\\/:*?"<>|':
        text = text.replace(ch, "_")
    return text.replace(" ", "_")


def build_report_filename(tipo_informe: str | None, case_id: str | None, extension: str) -> str:
    safe_tipo_informe = _normalize_report_segment(tipo_informe, "Generico")
    safe_case_id = _normalize_report_segment(case_id, "caso")
    return f"Informe_{safe_tipo_informe}_{safe_case_id}.{extension}"


def _create_word_document():
    if DocxDocument is None:
        raise RuntimeError(DOCX_MISSING_MESSAGE)
    return DocxDocument()


def _build_summary_paragraphs(
    case: Mapping[str, Any] | Dict[str, Any],
    clients: List[Dict[str, Any]],
    team: List[Dict[str, Any]],
    products: List[Dict[str, Any]],
    total_inv: Decimal,
) -> List[str]:
    formatted_total = total_inv.quantize(Decimal('0.01'))
    data_available = bool(clients or team or products or any(case.values()))
    if data_available or total_inv:
        counts_paragraph = (
            "Resumen cuantitativo: "
            f"Se registran {len(clients)} clientes, {len(team)} colaboradores y {len(products)} productos vinculados. "
            f"Monto afectado total {formatted_total}."
        )
    else:
        counts_paragraph = "Resumen cuantitativo: Sin información registrada."

    modalities = []
    modality = (case.get('modalidad') or '').strip() if case else ''
    if modality:
        modalities.append(modality)
    for prod in products:
        prod_modalidad = (prod.get('modalidad') or '').strip()
        if prod_modalidad:
            modalities.append(prod_modalidad)
    unique_modalities = sorted(set(modalities))

    category_text = " / ".join(
        filter(None, [str(case.get('categoria1', '') or '').strip(), str(case.get('categoria2', '') or '').strip()])
    )
    if unique_modalities or category_text:
        modality_parts = []
        if unique_modalities:
            modality_parts.append(f"Modalidades destacadas: {', '.join(unique_modalities)}.")
        if category_text:
            modality_parts.append(f"Tipificación: {category_text}.")
        modalities_paragraph = "Modalidades y tipificación: " + " ".join(modality_parts)
    else:
        modalities_paragraph = "Modalidades y tipificación: Sin información registrada."

    return [counts_paragraph, modalities_paragraph]


def _build_report_context(case_data: CaseData):
    case = case_data.caso
    analysis = case_data.analisis
    clients = case_data.clientes
    team = case_data.colaboradores
    products = case_data.productos
    riesgos = case_data.riesgos
    normas = case_data.normas
    total_inv = sum(
        [parse_decimal_amount(p.get('monto_investigado')) or Decimal('0') for p in products],
        start=Decimal('0'),
    )
    destinatarios = sorted({
        " - ".join(filter(None, [col.get('division', '').strip(), col.get('area', '').strip(), col.get('servicio', '').strip()]))
        for col in team
        if any([col.get('division'), col.get('area'), col.get('servicio')])
    })
    destinatarios = [d for d in destinatarios if d]
    destinatarios_text = ", ".join(destinatarios) if destinatarios else "Sin divisiones registradas"
    reclamos_por_producto: Dict[str, List[Dict[str, Any]]] = {}
    for record in case_data.reclamos:
        pid = record.get('id_producto')
        if not pid:
            continue
        reclamos_por_producto.setdefault(pid, []).append(record)
    client_rows = [
        [
            f"Cliente {idx}",
            client.get('tipo_id', ''),
            client.get('id_cliente', ''),
            client.get('flag', ''),
            client.get('telefonos', ''),
            client.get('correos', ''),
            client.get('direcciones', ''),
            client.get('accionado', ''),
        ]
        for idx, client in enumerate(clients, start=1)
    ]
    team_rows = [
        [
            f"Colaborador {idx}",
            col.get('id_colaborador', ''),
            col.get('flag', ''),
            col.get('division', ''),
            col.get('area', ''),
            col.get('servicio', ''),
            col.get('puesto', ''),
            col.get('nombre_agencia', ''),
            col.get('codigo_agencia', ''),
            col.get('tipo_falta', ''),
            col.get('tipo_sancion', ''),
        ]
        for idx, col in enumerate(team, start=1)
    ]
    product_rows = []
    for idx, prod in enumerate(products, start=1):
        claim_values = reclamos_por_producto.get(prod.get('id_producto'), [])
        claims_text = "; ".join(
            f"{rec.get('id_reclamo', '')} / {rec.get('codigo_analitica', '')}"
            for rec in claim_values
        )
        product_rows.append([
            f"Producto {idx}",
            prod.get('id_producto', ''),
            prod.get('id_cliente', ''),
            prod.get('tipo_producto', ''),
            prod.get('canal', ''),
            prod.get('proceso', ''),
            prod.get('categoria1', ''),
            prod.get('categoria2', ''),
            prod.get('modalidad', ''),
            (
                f"INV:{prod.get('monto_investigado', '')} | PER:{prod.get('monto_perdida_fraude', '')} "
                f"| FALLA:{prod.get('monto_falla_procesos', '')} | CONT:{prod.get('monto_contingencia', '')} "
                f"| REC:{prod.get('monto_recuperado', '')} | PAGO:{prod.get('monto_pago_deuda', '')}"
            ),
            claims_text,
        ])
    risk_rows = [
        [
            risk.get('id_riesgo', ''),
            risk.get('lider', ''),
            risk.get('criticidad', ''),
            risk.get('exposicion_residual', ''),
            risk.get('planes_accion', ''),
        ]
        for risk in riesgos
    ]
    norm_rows = [
        [
            norm.get('id_norma', ''),
            norm.get('descripcion', ''),
            norm.get('fecha_vigencia', ''),
        ]
        for norm in normas
    ]
    summary_paragraphs = _build_summary_paragraphs(case, clients, team, products, total_inv)
    documented_counts = (
        f"Se documentaron {len(clients)} clientes, {len(team)} colaboradores y {len(products)} productos."
    )
    return {
        'case': case,
        'analysis': analysis,
        'total_investigado': total_inv,
        'destinatarios_text': destinatarios_text,
        'client_rows': client_rows,
        'team_rows': team_rows,
        'product_rows': product_rows,
        'risk_rows': risk_rows,
        'norm_rows': norm_rows,
        'summary_paragraphs': summary_paragraphs,
        'documented_counts': documented_counts,
    }


def _md_table(headers: Iterable[str], rows: List[List[Any]]) -> List[str]:
    if not rows:
        return ["Sin registros."]
    safe = lambda cell: str(cell or '').replace('|', '\\|')
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(['---'] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(safe(col) for col in row) + " |")
    return lines


def build_md(case_data: CaseData) -> str:
    context = _build_report_context(case_data)
    case = context['case']
    analysis = context['analysis']

    lines = [
        "Banco de Crédito - BCP",
        "SEGURIDAD CORPORATIVA, INVESTIGACIONES & CRIMEN CIBERNÉTICO",
        "INVESTIGACIONES & CIBERCRIMINOLOGÍA",
        f"Informe {case.get('tipo_informe', '')} N.{case.get('id_caso', '')}",
        f"Dirigido a: {context['destinatarios_text']}",
        (
            "Referencia: "
            f"{len(context['team_rows'])} colaboradores investigados, {len(context['product_rows'])} productos afectados, "
            f"monto investigado total {context['total_investigado']:.2f} y modalidad {case.get('modalidad', '')}."
        ),
        "",
        "## 1. Antecedentes",
        analysis.get('antecedentes') or "Pendiente",
        "",
        "## 2. Tabla de clientes",
    ]
    lines.extend(_md_table([
        "Cliente", "Tipo ID", "ID", "Flag", "Teléfonos", "Correos", "Direcciones", "Accionado"
    ], context['client_rows']))
    lines.extend([
        "",
        "## 3. Tabla de team members involucrados",
    ])
    lines.extend(_md_table([
        "Colaborador", "ID", "Flag", "División", "Área", "Servicio", "Puesto", "Agencia", "Código", "Falta", "Sanción"
    ], context['team_rows']))
    lines.extend([
        "",
        "## 4. Tabla de productos combinado",
    ])
    lines.extend(_md_table([
        "Registro", "ID", "Cliente", "Tipo", "Canal", "Proceso", "Cat.1", "Cat.2", "Modalidad", "Montos", "Reclamo/Analítica"
    ], context['product_rows']))
    lines.extend([
        "",
        "## 5. Resumen automatizado",
    ])
    lines.append(context['documented_counts'])
    lines.extend(context['summary_paragraphs'])
    lines.append("")
    lines.extend([
        "## 6. Modus Operandi",
        analysis.get('modus_operandi') or "Pendiente",
        "",
        "## 7. Hallazgos Principales",
        analysis.get('hallazgos') or "Pendiente",
        "",
        "## 8. Descargo de colaboradores",
        analysis.get('descargos') or "Pendiente",
        "",
        "## 9. Tabla de riesgos identificados",
    ])
    lines.extend(_md_table([
        "ID Riesgo", "Líder", "Criticidad", "Exposición US$", "Planes"
    ], context['risk_rows']))
    lines.extend([
        "",
        "## 10. Tabla de normas transgredidas",
    ])
    lines.extend(_md_table([
        "N° de norma", "Descripción", "Fecha de vigencia"
    ], context['norm_rows']))
    lines.extend([
        "",
        "## 11. Conclusiones",
        analysis.get('conclusiones') or "Pendiente",
        "",
        "## 12. Recomendaciones y mejoras de procesos",
        analysis.get('recomendaciones') or "Pendiente",
        "",
    ])
    return "\n".join(lines)


def build_docx(case_data: CaseData, path: Path | str) -> Path:
    document = _create_word_document()
    context = _build_report_context(case_data)
    case = context['case']
    analysis = context['analysis']

    header_lines = [
        "Banco de Crédito - BCP",
        "SEGURIDAD CORPORATIVA, INVESTIGACIONES & CRIMEN CIBERNÉTICO",
        "INVESTIGACIONES & CIBERCRIMINOLOGÍA",
        f"Informe {case.get('tipo_informe', '')} N.{case.get('id_caso', '')}",
        f"Dirigido a: {context['destinatarios_text']}",
        (
            "Referencia: "
            f"{len(context['team_rows'])} colaboradores investigados, {len(context['product_rows'])} productos afectados, "
            f"monto investigado total {context['total_investigado']:.2f} y modalidad {case.get('modalidad', '')}."
        ),
        "",
    ]
    for line in header_lines:
        document.add_paragraph(line)

    def add_heading_and_text(title, body_text):
        document.add_heading(title, level=2)
        document.add_paragraph(body_text or "Pendiente")
        document.add_paragraph("")

    def append_table_section(title, headers, rows):
        document.add_heading(title, level=2)
        if not rows:
            document.add_paragraph("Sin registros.")
            document.add_paragraph("")
            return
        table = document.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        for idx, header in enumerate(headers):
            table.rows[0].cells[idx].text = header
        for row in rows:
            docx_row = table.add_row()
            for idx, value in enumerate(row):
                docx_row.cells[idx].text = str(value or '')
        document.add_paragraph("")

    add_heading_and_text("1. Antecedentes", analysis.get('antecedentes'))
    append_table_section(
        "2. Tabla de clientes",
        ["Cliente", "Tipo ID", "ID", "Flag", "Teléfonos", "Correos", "Direcciones", "Accionado"],
        context['client_rows'],
    )
    append_table_section(
        "3. Tabla de team members involucrados",
        ["Colaborador", "ID", "Flag", "División", "Área", "Servicio", "Puesto", "Agencia", "Código", "Falta", "Sanción"],
        context['team_rows'],
    )
    append_table_section(
        "4. Tabla de productos combinado",
        ["Registro", "ID", "Cliente", "Tipo", "Canal", "Proceso", "Cat.1", "Cat.2", "Modalidad", "Montos", "Reclamo/Analítica"],
        context['product_rows'],
    )
    document.add_heading("5. Resumen automatizado", level=2)
    for paragraph in context['summary_paragraphs']:
        document.add_paragraph(paragraph)
    document.add_paragraph("")
    add_heading_and_text("6. Modus Operandi", analysis.get('modus_operandi'))
    add_heading_and_text("7. Hallazgos Principales", analysis.get('hallazgos'))
    add_heading_and_text("8. Descargo de colaboradores", analysis.get('descargos'))
    append_table_section(
        "9. Tabla de riesgos identificados",
        ["ID Riesgo", "Líder", "Criticidad", "Exposición US$", "Planes"],
        context['risk_rows'],
    )
    append_table_section(
        "10. Tabla de normas transgredidas",
        ["N° de norma", "Descripción", "Fecha de vigencia"],
        context['norm_rows'],
    )
    add_heading_and_text("11. Conclusiones", analysis.get('conclusiones'))
    add_heading_and_text("12. Recomendaciones y mejoras de procesos", analysis.get('recomendaciones'))
    document.save(path)
    return Path(path)


def save_md(case_data: CaseData, path: Path | str) -> Path:
    output_path = Path(path)
    output_path.write_text(build_md(case_data), encoding='utf-8')
    return output_path
