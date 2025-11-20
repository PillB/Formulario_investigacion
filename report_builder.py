from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Iterable, List
from xml.sax.saxutils import escape
import zipfile

try:  # python-docx es opcional en tiempo de ejecución
    from docx import Document as DocxDocument
except ImportError:  # pragma: no cover - se usa el respaldo integrado
    DocxDocument = None

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


_DOCX_STATIC_PARTS = {
    '[Content_Types].xml': dedent('''
        <?xml version="1.0" encoding="UTF-8"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
            <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
            <Default Extension="xml" ContentType="application/xml"/>
            <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
            <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
            <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
            <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
        </Types>
    ''').strip().encode('utf-8'),
    '_rels/.rels': dedent('''
        <?xml version="1.0" encoding="UTF-8"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
            <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
            <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
            <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
        </Relationships>
    ''').strip().encode('utf-8'),
    'docProps/core.xml': dedent('''
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:dcterms="http://purl.org/dc/terms/"
            xmlns:dcmitype="http://purl.org/dc/dcmitype/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <dc:title>Informe de caso</dc:title>
            <cp:revision>1</cp:revision>
        </cp:coreProperties>
    ''').strip().encode('utf-8'),
    'docProps/app.xml': dedent('''
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
            <Application>Formulario Investigacion</Application>
        </Properties>
    ''').strip().encode('utf-8'),
    'word/styles.xml': dedent('''
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
                <w:name w:val="Normal"/>
            </w:style>
        </w:styles>
    ''').strip().encode('utf-8'),
}


class _FallbackDocxCell:
    __slots__ = ('text',)

    def __init__(self):
        self.text = ''

    def to_xml(self):
        if not self.text:
            return '<w:tc><w:p/></w:tc>'
        safe = escape(self.text)
        return f'<w:tc><w:p><w:r><w:t xml:space="preserve">{safe}</w:t></w:r></w:p></w:tc>'


class _FallbackDocxRow:
    __slots__ = ('cells',)

    def __init__(self, cols):
        self.cells = [_FallbackDocxCell() for _ in range(cols)]

    def to_xml(self):
        return '<w:tr>' + ''.join(cell.to_xml() for cell in self.cells) + '</w:tr>'


class _FallbackDocxTable:
    __slots__ = ('rows', '_cols', 'style')

    def __init__(self, rows, cols):
        self._cols = cols
        self.rows = [_FallbackDocxRow(cols) for _ in range(rows)]
        self.style = None

    def add_row(self):
        row = _FallbackDocxRow(self._cols)
        self.rows.append(row)
        return row

    def to_xml(self):
        grid = ''.join('<w:gridCol w:w="2400"/>' for _ in range(self._cols))
        rows_xml = ''.join(row.to_xml() for row in self.rows)
        return f'<w:tbl><w:tblPr/><w:tblGrid>{grid}</w:tblGrid>{rows_xml}</w:tbl>'


class _FallbackDocxDocument:
    def __init__(self):
        self._blocks = []

    def add_paragraph(self, text):
        self._blocks.append(('paragraph', text or ''))
        return text

    def add_heading(self, text, level=1):  # noqa: ARG002 - nivel ignorado en el respaldo
        self._blocks.append(('paragraph', text or ''))
        return text

    def add_table(self, rows, cols):
        table = _FallbackDocxTable(rows, cols)
        self._blocks.append(('table', table))
        return table

    def save(self, path):
        document_xml = self._render_document_xml()
        _write_docx_package(path, document_xml)

    def _render_document_xml(self):
        pieces = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            '<w:body>',
        ]
        for block_type, payload in self._blocks:
            if block_type == 'paragraph':
                pieces.append(_fallback_paragraph_xml(payload))
            elif block_type == 'table':
                pieces.append(payload.to_xml())
        pieces.extend([
            '<w:sectPr>',
            '<w:pgSz w:w="12240" w:h="15840"/>',
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>',
            '</w:sectPr>',
            '</w:body>',
            '</w:document>',
        ])
        return '\n'.join(pieces).encode('utf-8')


def _fallback_paragraph_xml(text):
    safe = escape(text or '')
    if not safe:
        return '<w:p/>'
    return f'<w:p><w:r><w:t xml:space="preserve">{safe}</w:t></w:r></w:p>'


def _write_docx_package(path, document_xml_bytes):
    path = Path(path)
    with zipfile.ZipFile(path, 'w') as bundle:
        for name, payload in _DOCX_STATIC_PARTS.items():
            bundle.writestr(name, payload)
        bundle.writestr('word/document.xml', document_xml_bytes)


def _create_word_document():
    if DocxDocument is not None:
        return DocxDocument()
    return _FallbackDocxDocument()


def _build_report_context(case_data: CaseData):
    case = case_data.caso
    analysis = case_data.analisis
    clients = case_data.clientes
    team = case_data.colaboradores
    products = case_data.productos
    riesgos = case_data.riesgos
    normas = case_data.normas
    total_inv = sum((parse_decimal_amount(p.get('monto_investigado')) or Decimal('0')) for p in products)
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
    summary_sentence = (
        f"Se documentaron {len(clients)} clientes, {len(team)} colaboradores y {len(products)} productos. "
        f"El caso está tipificado como {case.get('categoria1', '')} / {case.get('categoria2', '')} en modalidad {case.get('modalidad', '')}."
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
        'summary_sentence': summary_sentence,
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
        context['summary_sentence'],
        "",
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
    context = _build_report_context(case_data)
    case = context['case']
    analysis = context['analysis']
    document = _create_word_document()

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
    document.add_paragraph(context['summary_sentence'])
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
