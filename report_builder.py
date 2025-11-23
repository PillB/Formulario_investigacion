from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

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


PLACEHOLDER = "No aplica / Sin información registrada."


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
    encabezado: Dict[str, Any]
    operaciones: List[Dict[str, Any]]
    anexos: List[Dict[str, Any]]
    firmas: List[Dict[str, Any]]
    recomendaciones_categorias: Dict[str, Any]
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
                "encabezado": self.encabezado,
                "operaciones": self.operaciones,
                "anexos": self.anexos,
                "firmas": self.firmas,
                "recomendaciones_categorias": self.recomendaciones_categorias,
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
            encabezado=dict(payload.get("encabezado") or {}),
            operaciones=list(payload.get("operaciones") or []),
            anexos=list(payload.get("anexos") or []),
            firmas=list(payload.get("firmas") or []),
            recomendaciones_categorias=dict(payload.get("recomendaciones_categorias") or {}),
        )


def _normalize_report_segment(value: str | None, placeholder: str) -> str:
    text = (value or "").strip() or placeholder
    for ch in '\\/:*?"<>|':
        text = text.replace(ch, "_")
    return text.replace(" ", "_")


def _extract_analysis_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return str(value.get("text") or "")
    return str(value or "")


def normalize_analysis_texts(analysis: Mapping[str, Any] | None) -> Dict[str, str]:
    keys = [
        "antecedentes",
        "modus_operandi",
        "hallazgos",
        "descargos",
        "conclusiones",
        "recomendaciones",
    ]
    payload = analysis or {}
    normalized = {name: _extract_analysis_text(payload.get(name)) for name in keys}
    for name, value in payload.items():
        if name in normalized:
            continue
        normalized[name] = _extract_analysis_text(value)
    return normalized


def _safe_text(value: Any, *, placeholder: str = PLACEHOLDER) -> str:
    text = str(value or "").strip()
    return text or placeholder


def _format_decimal_value(value: Optional[Decimal]) -> str:
    if value is None:
        return PLACEHOLDER
    return f"{value.quantize(Decimal('0.01'))}"


def _sum_amounts(items: Iterable[Mapping[str, Any]], key: str) -> Decimal:
    total = Decimal("0")
    for item in items:
        amount = parse_decimal_amount(item.get(key)) if isinstance(item, Mapping) else None
        if amount is not None:
            total += amount
    return total


def _aggregate_amounts(
    products: List[Dict[str, Any]],
    encabezado: Mapping[str, Any],
) -> Dict[str, Optional[Decimal]]:
    def get_amount(key: str, fallback_key: Optional[str] = None) -> Optional[Decimal]:
        raw_value = encabezado.get(key) if isinstance(encabezado, Mapping) else None
        if raw_value not in (None, ""):
            parsed = parse_decimal_amount(raw_value)
            if parsed is not None:
                return parsed
        if fallback_key:
            return _sum_amounts(products, fallback_key)
        return None

    perdida_total = get_amount("perdida_total")
    if perdida_total is None:
        perdida_total = _sum_amounts(products, "monto_perdida_fraude")

    return {
        "investigado": get_amount("importe_investigado", "monto_investigado"),
        "contingencia": get_amount("contingencia", "monto_contingencia"),
        "perdida_total": perdida_total if perdida_total != Decimal("0") else perdida_total,
        "normal": get_amount("normal"),
        "vencido": get_amount("vencido"),
        "judicial": get_amount("judicial"),
        "castigo": get_amount("castigo"),
    }


def build_report_filename(tipo_informe: str | None, case_id: str | None, extension: str) -> str:
    safe_tipo_informe = _normalize_report_segment(tipo_informe, "Generico")
    safe_case_id = _normalize_report_segment(case_id, "caso")
    return f"Informe_{safe_tipo_informe}_{safe_case_id}.{extension}"


def _create_word_document():
    if not DOCX_AVAILABLE or DocxDocument is None:
        raise RuntimeError(DOCX_MISSING_MESSAGE)
    return DocxDocument()


def _build_report_context(case_data: CaseData):
    case = case_data.caso
    analysis = normalize_analysis_texts(case_data.analisis)
    clients = case_data.clientes
    team = case_data.colaboradores
    products = case_data.productos
    operaciones = case_data.operaciones
    riesgos = case_data.riesgos
    normas = case_data.normas
    encabezado = case_data.encabezado or {}
    reclamos = case_data.reclamos or []
    recomendaciones = case_data.recomendaciones_categorias or {}

    destinatarios = encabezado.get("dirigido_a")
    if not destinatarios:
        destinatarios_set = sorted(
            {
                " - ".join(
                    filter(
                        None,
                        [
                            str(col.get("division", "")).strip(),
                            str(col.get("area", "")).strip(),
                            str(col.get("servicio", "")).strip(),
                        ],
                    )
                )
                for col in team
                if any([col.get("division"), col.get("area"), col.get("servicio")])
            }
        )
        destinatarios = ", ".join([d for d in destinatarios_set if d])
    destinatarios_text = destinatarios or PLACEHOLDER

    amounts = _aggregate_amounts(products, encabezado)
    categoria = " / ".join(
        filter(None, [str(case.get("categoria1", "")).strip(), str(case.get("categoria2", "")).strip()])
    )
    tipologia = _safe_text(encabezado.get("tipologia_evento") or case.get("tipologia_evento") or case.get("modalidad"))
    procesos = encabezado.get("procesos_impactados") or ", ".join(
        sorted({str(prod.get("proceso", "")).strip() for prod in products if prod.get("proceso")})
    )
    analiticas = encabezado.get("analitica_contable")
    if not analiticas:
        codigos_analitica = sorted(
            {str(rec.get("codigo_analitica", "")).strip() for rec in reclamos if rec.get("codigo_analitica")}
        )
        analiticas = ", ".join(filter(None, codigos_analitica))

    productos_texto = encabezado.get("producto") or ", ".join(
        sorted({str(prod.get("tipo_producto", "")).strip() or str(prod.get("producto", "")).strip() for prod in products})
    )
    reclamos_count = encabezado.get("numero_reclamos") or len(reclamos)

    header_headers = [
        "Dirigido a",
        "Referencia",
        "Área de Reporte",
        "Fecha de reporte",
        "Categoría del evento",
        "Tipología de evento",
        "Importe investigado",
        "Contingencia",
        "Pérdida total",
        "Normal",
        "Vencido",
        "Judicial",
        "Castigo",
        "Analítica Contable",
        "Centro de Costos",
        "Producto",
        "Procesos impactados",
        "N° de Reclamos",
    ]

    referencia = _safe_text(
        encabezado.get("referencia")
        or case.get("referencia")
        or (
            f"{len(team)} colaboradores investigados, {len(products)} productos afectados, "
            f"monto investigado total {_format_decimal_value(amounts['investigado'])} y modalidad {case.get('modalidad', '')}."
        )
    )

    header_row = [
        destinatarios_text,
        referencia,
        _safe_text(encabezado.get("area_reporte") or case.get("area_reporte")),
        _safe_text(encabezado.get("fecha_reporte") or case.get("fecha_reporte")),
        _safe_text(categoria),
        tipologia,
        _format_decimal_value(amounts.get("investigado")),
        _format_decimal_value(amounts.get("contingencia")),
        _format_decimal_value(amounts.get("perdida_total")),
        _format_decimal_value(amounts.get("normal")),
        _format_decimal_value(amounts.get("vencido")),
        _format_decimal_value(amounts.get("judicial")),
        _format_decimal_value(amounts.get("castigo")),
        _safe_text(analiticas),
        _safe_text(encabezado.get("centro_costos") or case.get("centro_costos")),
        _safe_text(productos_texto),
        _safe_text(procesos),
        _safe_text(reclamos_count),
    ]

    def _collaborator_name(record: Mapping[str, Any]) -> str:
        parts = [record.get("nombres"), record.get("apellidos")]
        joined = " ".join(filter(None, parts)).strip()
        if joined:
            return joined
        return _safe_text(record.get("nombre_completo") or record.get("nombres_apellidos") or record.get("nombre"))

    collaborator_rows = [
        [
            _collaborator_name(col),
            _safe_text(col.get("id_colaborador") or col.get("matricula"), placeholder="-"),
            _safe_text(col.get("puesto") or col.get("cargo"), placeholder="-"),
            _safe_text(col.get("tipo_falta") or col.get("falta"), placeholder="-"),
            _safe_text(col.get("fecha_carta_inmediatez") or col.get("fecha_carta_inmediate"), placeholder="-"),
            _safe_text(col.get("fecha_carta_renuncia"), placeholder="-"),
        ]
        for col in team
    ]

    def _build_placeholder_operation_rows(count: int = 3) -> List[List[str]]:
        placeholder_cells = [PLACEHOLDER] * 10
        return [[str(idx)] + placeholder_cells for idx in range(1, count + 1)]

    operation_table_rows = _build_placeholder_operation_rows()
    if operaciones and not products:
        operation_table_rows = []
        total_desembolsado = Decimal("0")
        total_saldo = Decimal("0")

        for idx, operation in enumerate(operaciones, start=1):
            desembolsado = parse_decimal_amount(operation.get("importe_desembolsado"))
            saldo = parse_decimal_amount(operation.get("saldo_deudor"))

            if desembolsado is not None:
                total_desembolsado += desembolsado
            if saldo is not None:
                total_saldo += saldo

            operation_table_rows.append(
                [
                    _safe_text(operation.get("numero") or idx, placeholder=str(idx)),
                    _safe_text(operation.get("fecha_aprobacion")),
                    _safe_text(operation.get("cliente")),
                    _safe_text(operation.get("ingreso_bruto_mensual")),
                    _safe_text(operation.get("empresa_empleadora")),
                    _safe_text(operation.get("vendedor_inmueble")),
                    _safe_text(operation.get("vendedor_credito")),
                    _safe_text(operation.get("producto")),
                    _format_decimal_value(desembolsado),
                    _format_decimal_value(saldo),
                    _safe_text(operation.get("status")),
                ]
            )

        if operation_table_rows:
            operation_table_rows.append(
                [
                    "Totales",
                    PLACEHOLDER,
                    PLACEHOLDER,
                    PLACEHOLDER,
                    PLACEHOLDER,
                    PLACEHOLDER,
                    PLACEHOLDER,
                    PLACEHOLDER,
                    _format_decimal_value(total_desembolsado),
                    _format_decimal_value(total_saldo),
                    PLACEHOLDER,
                ]
            )

    risk_rows = [
        [
            _safe_text(risk.get("lider") or risk.get("lider_riesgo"), placeholder="-"),
            _safe_text(risk.get("id_riesgo") or risk.get("id_riesgo_grc"), placeholder="-"),
            _safe_text(risk.get("descripcion") or risk.get("descripcion_riesgo"), placeholder="-"),
            _safe_text(risk.get("criticidad") or risk.get("criticidad_riesgo"), placeholder="-"),
            _format_decimal_value(parse_decimal_amount(risk.get("exposicion_residual"))),
            _safe_text(risk.get("planes_accion") or risk.get("id_plan_accion"), placeholder="-"),
        ]
        for risk in riesgos
    ]

    norm_rows = [
        [
            _safe_text(norm.get("id_norma") or norm.get("norma"), placeholder="-"),
            _safe_text(norm.get("descripcion") or norm.get("detalle"), placeholder="-"),
        ]
        for norm in normas
    ]

    def _normalize_recommendation_list(value: Any) -> List[str]:
        if isinstance(value, str):
            value = [value] if value.strip() else []
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    rec_operativas = _normalize_recommendation_list(recomendaciones.get("operativo") or recomendaciones.get("operativas"))
    rec_laborales = _normalize_recommendation_list(recomendaciones.get("laboral") or recomendaciones.get("laborales"))
    rec_legales = _normalize_recommendation_list(recomendaciones.get("legal") or recomendaciones.get("legales"))

    if not (rec_operativas or rec_laborales or rec_legales):
        text = analysis.get("recomendaciones", "")
        if text and text != PLACEHOLDER:
            rec_operativas = [text]

    investigator = case.get("investigador") if isinstance(case, Mapping) else {}
    firmas: List[Dict[str, Any]] = []
    if isinstance(investigator, Mapping):
        nombre_investigador = investigator.get("nombre") or ""
        cargo_investigador = investigator.get("cargo") or "Investigador Principal"
        if nombre_investigador or investigator.get("matricula"):
            firmas.append({"nombre": nombre_investigador, "cargo": cargo_investigador})
    matricula_investigador = case.get("matricula_investigador") if isinstance(case, Mapping) else None
    if matricula_investigador and not firmas:
        firmas.append({"nombre": "", "cargo": "Investigador Principal"})

    return {
        "case": case,
        "analysis": analysis,
        "header_headers": header_headers,
        "header_row": header_row,
        "collaborator_rows": collaborator_rows,
        "operation_rows": operation_table_rows,
        "risk_rows": risk_rows,
        "norm_rows": norm_rows,
        "recomendaciones": {
            "laboral": rec_laborales,
            "operativo": rec_operativas,
            "legal": rec_legales,
        },
        "anexos": case_data.anexos or [],
        "firmas": firmas,
    }


def _md_table(headers: Iterable[str], rows: List[List[Any]], *, placeholder: str = PLACEHOLDER) -> List[str]:
    if not rows:
        return [placeholder]
    safe = lambda cell: str(cell or '').replace('|', '\\|')
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(['---'] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(safe(col) for col in row) + " |")
    return lines


def _md_list(items: List[str]) -> List[str]:
    if not items:
        return [PLACEHOLDER]
    return [f"- {item}" for item in items]


def _format_anexos(anexos: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for idx, anexo in enumerate(anexos, start=1):
        if isinstance(anexo, Mapping):
            titulo = anexo.get("titulo") or anexo.get("title") or anexo.get("nombre")
            descripcion = anexo.get("descripcion") or anexo.get("detalle") or ""
            label = titulo or f"Anexo {idx}"
            text = f"{label}" + (f" - {descripcion}" if descripcion else "")
            if text.strip():
                lines.append(text.strip())
        elif str(anexo).strip():
            lines.append(str(anexo).strip())
    return lines


def _format_firmas(firmas: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for firma in firmas:
        if isinstance(firma, Mapping):
            nombre = firma.get("nombre") or firma.get("responsable") or ""
            cargo = firma.get("cargo") or firma.get("puesto") or ""
            if nombre or cargo:
                parts = [part for part in [nombre, cargo] if part]
                lines.append(" – ".join(parts))
        elif str(firma).strip():
            lines.append(str(firma).strip())
    return lines


def _section_state(has_data: bool) -> str:
    return "Con información" if has_data else PLACEHOLDER


def _build_sections_summary(context: Mapping[str, Any], analysis: Mapping[str, Any]) -> List[List[str]]:
    recommendations = context["recomendaciones"]
    return [
        ["Encabezado Institucional", "Tabla", _section_state(any(val != PLACEHOLDER for val in context["header_row"]))],
        ["Antecedentes", "Narrativa", _section_state(bool(analysis.get("antecedentes")))],
        ["Colaboradores", "Tabla", _section_state(bool(context["collaborator_rows"]))],
        ["Modus operandi", "Narrativa", _section_state(bool(analysis.get("modus_operandi")))],
        ["Principales Hallazgos", "Tabla + texto", _section_state(bool(context["operation_rows"]))],
        ["Descargos", "Narrativa", _section_state(bool(analysis.get("descargos")))],
        [
            "Riesgos identificados y debilidades de los controles",
            "Tabla",
            _section_state(bool(context["risk_rows"])),
        ],
        ["Normas transgredidas", "Tabla", _section_state(bool(context["norm_rows"]))],
        ["Conclusiones", "Narrativa", _section_state(bool(analysis.get("conclusiones")))],
        [
            "Recomendaciones y Mejoras de Procesos",
            "Listas",
            _section_state(
                bool(recommendations["laboral"] or recommendations["operativo"] or recommendations["legal"])
            ),
        ],
        ["Anexos", "Lista", _section_state(bool(context["anexos"]))],
        ["Firma", "Lista", _section_state(bool(context["firmas"]))],
    ]


def build_md(case_data: CaseData) -> str:
    context = _build_report_context(case_data)
    case = context["case"]
    analysis = context["analysis"]

    header_lines = [
        "**BANCO DE CRÉDITO – BCP**",
        "**SEGURIDAD CORPORATIVA, INTELIGENCIA & CRIMEN CIBERNÉTICO**",
        "**INVESTIGACIONES & CIBERCRIMINOLOGÍA**",
        f"**Informe de Gerencia** {case.get('tipo_informe', '')} N° {case.get('id_caso', '')}",
        f"{_safe_text(case.get('lugar'))}, {_safe_text(case.get('fecha_informe'))}",
        "",
        "## Encabezado Institucional",
    ]

    lines = list(header_lines)
    lines.extend(_md_table(context["header_headers"], [context["header_row"]]))
    lines.extend(
        [
            "",
            "## Antecedentes",
            analysis.get("antecedentes") or PLACEHOLDER,
            "",
            "## Detalle de los Colaboradores Involucrados",
        ]
    )
    lines.extend(
        _md_table(
            [
                "Nombres y Apellidos",
                "Matrícula",
                "Cargo",
                "Falta cometida",
                "Fecha Carta de Inmediatez",
                "Fecha Carta de Renuncia",
            ],
            context["collaborator_rows"],
        )
    )
    lines.extend(
        [
            "",
            "## Modus operandi",
            analysis.get("modus_operandi") or PLACEHOLDER,
            "",
            "## Principales Hallazgos",
        ]
    )
    lines.extend(
        _md_table(
            [
                "N°",
                "Fecha de aprobación",
                "Cliente / DNI",
                "Ingreso Bruto Mensual",
                "Empresa Empleadora",
                "Vendedor del Inmueble",
                "Vendedor del Crédito",
                "Producto",
                "Importe Desembolsado",
                "Saldo Deudor",
                "Status (BCP/SBS)",
            ],
            context["operation_rows"],
        )
    )
    lines.extend(
        [
            "",
            analysis.get("hallazgos") or PLACEHOLDER,
            "",
            "## Descargos",
            analysis.get("descargos") or PLACEHOLDER,
            "",
            "## Riesgos identificados y debilidades de los controles",
        ]
    )
    lines.extend(
        _md_table(
            [
                "Líder del riesgo",
                "ID Riesgo (GRC)",
                "Descripción del riesgo de fraude",
                "Criticidad del riesgo",
                "Exposición residual (USD)",
                "ID Plan de Acción",
            ],
            context["risk_rows"],
        )
    )
    lines.extend(
        [
            "",
            "## Normas transgredidas",
        ]
    )
    lines.extend(_md_table(["Norma/Política", "Descripción de la transgresión"], context["norm_rows"]))
    lines.extend(
        [
            "",
            "## Conclusiones",
            analysis.get("conclusiones") or PLACEHOLDER,
            "",
            "## Recomendaciones y Mejoras de Procesos",
            "### De carácter laboral",
        ]
    )
    lines.extend(_md_list(context["recomendaciones"]["laboral"]))
    lines.extend(["", "### De carácter operativo"])
    lines.extend(_md_list(context["recomendaciones"]["operativo"]))
    lines.extend(["", "### De carácter legal"])
    lines.extend(_md_list(context["recomendaciones"]["legal"]))
    lines.extend(["", "## Anexos"])
    lines.extend(_md_list(_format_anexos(context["anexos"])))
    lines.extend(["", "## Firma"])
    lines.extend(_md_list(_format_firmas(context["firmas"])))
    lines.extend(["", "## Resumen de Secciones y Tablas del Informe"])
    lines.extend(
        _md_table(
            ["Sección", "Tipo", "Estado"],
            _build_sections_summary(context, analysis),
        )
    )
    return "\n".join(lines)


def build_docx(case_data: CaseData, path: Path | str) -> Path:
    document = _create_word_document()
    context = _build_report_context(case_data)
    case = context["case"]
    analysis = context["analysis"]

    def add_paragraphs(lines: List[str]) -> None:
        for line in lines:
            document.add_paragraph(line)

    def append_table(headers: List[str], rows: List[List[Any]]) -> None:
        if not rows:
            document.add_paragraph(PLACEHOLDER)
            return
        table = document.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        for idx, header in enumerate(headers):
            table.rows[0].cells[idx].text = header
        for row in rows:
            docx_row = table.add_row()
            for idx, value in enumerate(row):
                docx_row.cells[idx].text = str(value or "")

    def add_list(items: List[str]) -> None:
        if not items:
            document.add_paragraph(PLACEHOLDER)
            return
        for item in items:
            document.add_paragraph(item, style="List Bullet")

    header_lines = [
        "BANCO DE CRÉDITO – BCP",
        "SEGURIDAD CORPORATIVA, INTELIGENCIA & CRIMEN CIBERNÉTICO",
        "INVESTIGACIONES & CIBERCRIMINOLOGÍA",
        f"Informe de Gerencia {case.get('tipo_informe', '')} N° {case.get('id_caso', '')}",
        f"{_safe_text(case.get('lugar'))}, {_safe_text(case.get('fecha_informe'))}",
    ]

    add_paragraphs(header_lines)
    document.add_heading("Encabezado Institucional", level=2)
    append_table(context["header_headers"], [context["header_row"]])
    document.add_heading("Antecedentes", level=2)
    add_paragraphs([analysis.get("antecedentes") or PLACEHOLDER])
    document.add_heading("Detalle de los Colaboradores Involucrados", level=2)
    append_table(
        [
            "Nombres y Apellidos",
            "Matrícula",
            "Cargo",
            "Falta cometida",
            "Fecha Carta de Inmediatez",
            "Fecha Carta de Renuncia",
        ],
        context["collaborator_rows"],
    )
    document.add_heading("Modus operandi", level=2)
    add_paragraphs([analysis.get("modus_operandi") or PLACEHOLDER])
    document.add_heading("Principales Hallazgos", level=2)
    append_table(
        [
            "N°",
            "Fecha de aprobación",
            "Cliente / DNI",
            "Ingreso Bruto Mensual",
            "Empresa Empleadora",
            "Vendedor del Inmueble",
            "Vendedor del Crédito",
            "Producto",
            "Importe Desembolsado",
            "Saldo Deudor",
            "Status (BCP/SBS)",
        ],
        context["operation_rows"],
    )
    add_paragraphs([analysis.get("hallazgos") or PLACEHOLDER])
    document.add_heading("Descargos", level=2)
    add_paragraphs([analysis.get("descargos") or PLACEHOLDER])
    document.add_heading("Riesgos identificados y debilidades de los controles", level=2)
    append_table(
        [
            "Líder del riesgo",
            "ID Riesgo (GRC)",
            "Descripción del riesgo de fraude",
            "Criticidad del riesgo",
            "Exposición residual (USD)",
            "ID Plan de Acción",
        ],
        context["risk_rows"],
    )
    document.add_heading("Normas transgredidas", level=2)
    append_table(["Norma/Política", "Descripción de la transgresión"], context["norm_rows"])
    document.add_heading("Conclusiones", level=2)
    add_paragraphs([analysis.get("conclusiones") or PLACEHOLDER])
    document.add_heading("Recomendaciones y Mejoras de Procesos", level=2)
    document.add_heading("De carácter laboral", level=3)
    add_list(context["recomendaciones"]["laboral"])
    document.add_heading("De carácter operativo", level=3)
    add_list(context["recomendaciones"]["operativo"])
    document.add_heading("De carácter legal", level=3)
    add_list(context["recomendaciones"]["legal"])
    document.add_heading("Anexos", level=2)
    add_list(_format_anexos(context["anexos"]))
    document.add_heading("Firma", level=2)
    add_list(_format_firmas(context["firmas"]))
    document.add_heading("Resumen de Secciones y Tablas del Informe", level=2)
    append_table(["Sección", "Tipo", "Estado"], _build_sections_summary(context, analysis))
    document.save(path)
    return Path(path)


def save_md(case_data: CaseData, path: Path | str) -> Path:
    output_path = Path(path)
    output_path.write_text(build_md(case_data), encoding='utf-8')
    return output_path
