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
        }
    )


def test_md_headings_and_tables(sample_case_data):
    md = report_builder.build_md(sample_case_data)
    lines = md.splitlines()

    headings = [line for line in lines if line.startswith("## ")]
    assert headings == [
        "## 1. Antecedentes",
        "## 2. Tabla de clientes",
        "## 3. Tabla de team members involucrados",
        "## 4. Tabla de productos combinado",
        "## 5. Descripción breve automatizada",
        "## 6. Modus Operandi",
        "## 7. Hallazgos Principales",
        "## 8. Descargo de colaboradores",
        "## 9. Tabla de riesgos identificados",
        "## 10. Tabla de normas transgredidas",
        "## 11. Conclusiones",
        "## 12. Recomendaciones y mejoras de procesos",
    ]

    assert "| Cliente | Tipo ID | ID | Flag | Teléfonos | Correos | Direcciones | Accionado |" in md
    assert "| Colaborador | ID | Flag | División | Área | Servicio | Puesto | Agencia | Código | Falta | Sanción |" in md
    assert "| Registro | ID | Cliente | Tipo | Canal | Proceso | Cat.1 | Cat.2 | Modalidad | Montos | Reclamo/Analítica |" in md
    assert "| ID Riesgo | Líder | Criticidad | Exposición US$ | Planes |" in md
    assert "| N° de norma | Descripción | Fecha de vigencia |" in md

    assert "Se documentaron 1 clientes, 1 colaboradores y 1 productos" in md


def test_md_empty_tables_and_summary():
    empty_case = CaseData.from_mapping({"caso": {}, "clientes": [], "colaboradores": [], "productos": [], "reclamos": [], "involucramientos": [], "riesgos": [], "normas": [], "analisis": {}})
    md = report_builder.build_md(empty_case)
    lines = md.splitlines()

    assert lines.count("Sin registros.") >= 3
    assert "Se documentaron 0 clientes, 0 colaboradores y 0 productos." in md


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

    assert "Hallazgo con formato" in md
    assert "Nota adicional con encabezado" not in md
    assert "bold" not in md
    assert "diagrama.png" not in md


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
