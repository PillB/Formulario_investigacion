from pathlib import Path

import pytest

import report_builder
from report_builder import CaseData


@pytest.fixture
def sample_case_data():
    return CaseData.from_mapping(
        {
            "caso": {
                "id_caso": "2024-0007",
                "tipo_informe": "Inicial",
                "categoria1": "Fraude",
                "categoria2": "Digital",
                "modalidad": "Remota",
                "lugar": "Lima",
                "fecha_informe": "01 de enero de 2024",
            },
            "encabezado": {
                "area_reporte": "Seguridad",
                "fecha_reporte": "02/01/2024",
                "tipologia_evento": "Ingeniería social",
                "referencia": "Caso de referencia",
                "centro_costos": "CC-01",
                "procesos_impactados": "Onboarding",
            },
            "clientes": [
                {
                    "tipo_id": "DNI",
                    "id_cliente": "12345678",
                    "flag": "A",
                    "telefonos": "999-888-777",
                    "correos": "cliente@example.com",
                    "direcciones": "Calle Falsa 123",
                    "accionado": "Sí",
                }
            ],
            "colaboradores": [
                {
                    "id_colaborador": "T12345",
                    "flag": "B",
                    "division": "Riesgos",
                    "area": "Analítica",
                    "servicio": "Monitoreo",
                    "puesto": "Analista",
                    "nombre_agencia": "Agencia Central",
                    "codigo_agencia": "000111",
                    "tipo_falta": "Grave",
                    "tipo_sancion": "Suspensión",
                }
            ],
            "productos": [
                {
                    "id_producto": "PRD-1",
                    "id_cliente": "12345678",
                    "tipo_producto": "Tarjeta",
                    "canal": "Web",
                    "proceso": "Alta",
                    "categoria1": "Cat1",
                    "categoria2": "Cat2",
                    "modalidad": "Online",
                    "monto_investigado": "100.00",
                    "monto_perdida_fraude": "10.00",
                    "monto_falla_procesos": "20.00",
                    "monto_contingencia": "30.00",
                    "monto_recuperado": "15.00",
                    "monto_pago_deuda": "5.00",
                }
            ],
            "reclamos": [
                {
                    "id_producto": "PRD-1",
                    "id_reclamo": "C12345678",
                    "codigo_analitica": "4300000001",
                }
            ],
            "operaciones": [
                {
                    "numero": 1,
                    "fecha_aprobacion": "2024-01-10",
                    "cliente": "Cliente Uno",
                    "ingreso_bruto_mensual": "5000",
                    "empresa_empleadora": "Empresa A",
                    "vendedor_inmueble": "Vendedor 1",
                    "vendedor_credito": "Ejecutivo 1",
                    "producto": "Crédito",
                    "importe_desembolsado": "60.00",
                    "saldo_deudor": "50.00",
                    "status": "BCP",
                }
            ],
            "involucramientos": [],
            "riesgos": [
                {
                    "id_riesgo": "R-1",
                    "lider": "Lead",
                    "criticidad": "Alta",
                    "exposicion_residual": "1000",
                    "planes_accion": "Mitigar",
                }
            ],
            "normas": [
                {
                    "id_norma": "N-1",
                    "descripcion": "Norma A",
                    "fecha_vigencia": "2023-01-01",
                }
            ],
            "analisis": {
                "antecedentes": "Contexto del caso",
                "modus_operandi": "Uso de credenciales",
                "hallazgos": "Hallazgo clave",
                "descargos": "Sin descargos",
                "conclusiones": "Conclusión",
                "recomendaciones": "Recomendar",
            },
            "anexos": [{"titulo": "Anexo 1", "descripcion": "Detalle de pruebas"}],
            "firmas": [{"nombre": "Investigador", "cargo": "Analista"}],
            "recomendaciones_categorias": {
                "laboral": ["Capacitar al equipo"],
                "operativo": ["Actualizar control"],
                "legal": ["Escalar a legal"],
            },
        }
    )


def test_md_headings_and_tables(sample_case_data):
    md = report_builder.build_md(sample_case_data)
    lines = md.splitlines()

    headings = [line for line in lines if line.startswith("## ")]
    assert headings == [
        "## Encabezado Institucional",
        "## Antecedentes",
        "## Detalle de los Colaboradores Involucrados",
        "## Modus operandi",
        "## Principales Hallazgos",
        "## Descargos",
        "## Riesgos identificados y debilidades de los controles",
        "## Normas transgredidas",
        "## Conclusiones",
        "## Recomendaciones y Mejoras de Procesos",
        "## Anexos",
        "## Firma",
        "## Resumen de Secciones y Tablas del Informe",
    ]

    assert "| Dirigido a | Referencia | Área de Reporte | Fecha de reporte |" in md
    assert "| Nombres y Apellidos | Matrícula | Cargo | Falta cometida | Fecha Carta de Inmediatez | Fecha Carta de Renuncia |" in md
    assert "| N° | Fecha de aprobación | Cliente / DNI | Ingreso Bruto Mensual | Empresa Empleadora | Vendedor del Inmueble | Vendedor del Crédito | Producto | Importe Desembolsado | Saldo Deudor | Status (BCP/SBS) |" in md
    assert "| Líder del riesgo | ID Riesgo (GRC) | Descripción del riesgo de fraude | Criticidad del riesgo | Exposición residual (USD) | ID Plan de Acción |" in md
    assert "| Norma/Política | Descripción de la transgresión |" in md
    assert report_builder.PLACEHOLDER in md


def test_md_empty_tables_and_summary():
    empty_case = CaseData.from_mapping({"caso": {}, "clientes": [], "colaboradores": [], "productos": [], "reclamos": [], "involucramientos": [], "riesgos": [], "normas": [], "analisis": {}, "encabezado": {}, "operaciones": [], "anexos": [], "firmas": [], "recomendaciones_categorias": {}})
    md = report_builder.build_md(empty_case)
    lines = md.splitlines()

    assert md.count(report_builder.PLACEHOLDER) >= 3


def test_hallazgos_table_uses_placeholders_with_products(sample_case_data):
    md = report_builder.build_md(sample_case_data)

    assert "Cliente Uno" not in md
    assert "Totales" not in md
    assert "| 1 | No aplica / Sin información registrada. |" in md


def test_md_handles_rich_text_analysis_payload(sample_case_data):
    sample_case_data.analisis["hallazgos"] = {
        "text": "Hallazgo con formato",
        "tags": [{"tag": "bold", "start": "1.0", "end": "1.8"}],
        "images": [{"index": "2.0", "source": "/tmp/diagrama.png"}],
    }
    sample_case_data.analisis["nota_adicional"] = {
        "text": "Nota adicional con encabezado",
        "tags": [{"tag": "header", "start": "1.0", "end": "1.4"}],
    }

    normalized = report_builder.normalize_analysis_texts(sample_case_data.analisis)

    assert normalized["hallazgos"] == "Hallazgo con formato"
    assert normalized["nota_adicional"] == "Nota adicional con encabezado"

    md = report_builder.build_md(sample_case_data)

    assert "**Hallazgo** con formato" in md
    assert "Nota adicional con encabezado" not in md
    assert "bold" not in md
    assert "diagrama.png" not in md


def test_md_renders_analysis_tags_into_markdown():
    tagged_case = CaseData.from_mapping(
        {
            "caso": {"id_caso": "2024-0099", "tipo_informe": "Inicial"},
            "encabezado": {},
            "clientes": [],
            "colaboradores": [],
            "productos": [],
            "reclamos": [],
            "involucramientos": [],
            "riesgos": [],
            "normas": [],
            "analisis": {
                "antecedentes": {
                    "text": "Titulo\nDetalle en negrita",
                    "tags": [
                        {"tag": "header", "start": "1.0", "end": "1.6"},
                        {"tag": "bold", "start": "2.0", "end": "2.18"},
                    ],
                },
                "modus_operandi": {
                    "text": "Primer punto\nSegundo punto",
                    "tags": [
                        {"tag": "list", "start": "1.0", "end": "2.13"},
                    ],
                },
                "hallazgos": {
                    "text": "Celda A\nCelda B",
                    "tags": [
                        {"tag": "table", "start": "1.0", "end": "2.7"},
                    ],
                },
            },
            "operaciones": [],
            "anexos": [],
            "firmas": [],
            "recomendaciones_categorias": {},
        }
    )

    md = report_builder.build_md(tagged_case)

    assert "### Titulo" in md
    assert "**Detalle en negrita**" in md
    assert "- Primer punto" in md
    assert "- Segundo punto" in md
    assert "```\nCelda A\nCelda B\n```" in md


def test_report_filename_normalization():
    assert report_builder.build_report_filename("Inicial", "2024-0001", "md") == "Informe_Inicial_2024-0001.md"
    assert report_builder.build_report_filename("Cierre Especial", "2024/0002", "docx") == "Informe_Cierre_Especial_2024_0002.docx"
    assert report_builder.build_report_filename(None, None, "docx") == "Informe_Generico_caso.docx"


def test_docx_missing_dependency(monkeypatch, sample_case_data):
    monkeypatch.setattr(report_builder, "DOCX_AVAILABLE", False)
    with pytest.raises(RuntimeError) as excinfo:
        report_builder.build_docx(sample_case_data, Path("dummy.docx"))
    assert report_builder.DOCX_MISSING_MESSAGE in str(excinfo.value)


def test_docx_missing_docx_document(monkeypatch, sample_case_data):
    monkeypatch.setattr(report_builder, "DocxDocument", None)
    monkeypatch.setattr(report_builder, "DOCX_AVAILABLE", True)

    with pytest.raises(RuntimeError) as excinfo:
        report_builder.build_docx(sample_case_data, Path("dummy.docx"))

    assert report_builder.DOCX_MISSING_MESSAGE in str(excinfo.value)
