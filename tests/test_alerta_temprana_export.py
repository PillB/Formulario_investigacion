import os
import tkinter as tk
from tkinter import ttk

import pytest

import app as app_module
from report import alerta_temprana
from report.alerta_temprana import (
    SpanishSummaryHelper,
    _synthesize_section_text,
    build_alerta_temprana_ppt,
)
from report.alerta_temprana_content import build_alerta_temprana_sections
from report_builder import CaseData


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)
def test_alerta_temprana_button_invokes_command(monkeypatch, messagebox_spy):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    app = app_module.FraudCaseApp(root)
    invoked = []

    def fake_generate():
        invoked.append(True)

    monkeypatch.setattr(app, "generate_alerta_temprana_ppt", fake_generate)

    notebook = ttk.Notebook(root)
    actions_tab = ttk.Frame(notebook)
    app.build_actions_tab(actions_tab)

    app.btn_alerta_temprana.invoke()

    assert invoked
    root.destroy()


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)
def test_generate_alerta_temprana_ppt_uses_report_helper(monkeypatch, messagebox_spy):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    app = app_module.FraudCaseApp(root)
    app.btn_alerta_temprana = ttk.Button(root)
    calls = {}

    def fake_generate_report_file(extension, builder, description, source_widget=None):
        calls["extension"] = extension
        calls["builder"] = builder
        calls["description"] = description
        calls["source_widget"] = source_widget

    monkeypatch.setattr(app, "_generate_report_file", fake_generate_report_file)

    app.generate_alerta_temprana_ppt()

    assert calls["extension"] == "pptx"
    assert calls["builder"] is build_alerta_temprana_ppt
    assert calls["source_widget"] is app.btn_alerta_temprana
    assert "Alerta temprana" in calls["description"]
    root.destroy()


@pytest.mark.skipif(not alerta_temprana.PPTX_AVAILABLE, reason="python-pptx no disponible")
def test_build_alerta_temprana_ppt_generates_presentation(tmp_path):
    class StubLLM:
        def __init__(self):
            self.prompts = []

        def summarize(self, section, prompt, *, max_new_tokens=None):
            self.prompts.append((section, prompt))
            return f"{section} sintetizado"

    data = CaseData.from_mapping(
        {
            "caso": {
                "id_caso": "2025-0001",
                "tipo_informe": "Fraude",
                "investigador_nombre": "Ana Investigadora",
                "categoria1": "Tarjeta",
                "modalidad": "Digital",
                "fecha_de_ocurrencia": "2025-01-01",
                "fecha_de_descubrimiento": "2025-01-02",
            },
            "clientes": [{"id_cliente": "CLI1"}],
            "colaboradores": [{"nombres": "Carlos", "flag": "involucrado", "area": "TI"}],
            "productos": [
                {
                    "monto_investigado": "100.00",
                    "monto_perdida_fraude": "10.00",
                    "monto_falla_procesos": "5.00",
                    "monto_contingencia": "3.00",
                    "monto_recuperado": "2.00",
                }
            ],
            "reclamos": [],
            "involucramientos": [],
            "riesgos": [{"id_riesgo": "R1"}],
            "normas": [],
            "analisis": {
                "antecedentes": {"text": "Se detectaron cargos inusuales en tarjetas digitales."},
                "recomendaciones": {"text": "Suspender temporalmente los accesos y revisar monitoreo."},
            },
            "encabezado": {},
            "operaciones": [],
            "anexos": [],
            "firmas": [],
            "recomendaciones_categorias": {},
        }
    )

    output = tmp_path / "alerta_temprana.pptx"
    stub_llm = StubLLM()
    path = build_alerta_temprana_ppt(data, output, llm_helper=stub_llm)
    assert path.exists()

    from pptx import Presentation

    deck = Presentation(path)
    all_text = " ".join(shape.text for slide in deck.slides for shape in slide.shapes if hasattr(shape, "text"))
    assert len(deck.slides) == 2
    assert "Alerta temprana" in all_text
    assert "Resumen ejecutivo" in all_text
    assert "2025-0001" in all_text
    assert "Cronología" in all_text
    assert "Riesgos identificados" in all_text
    assert "sintetizado" in all_text
    assert any("Fraude" in prompt for _section, prompt in stub_llm.prompts)


def test_synthesize_section_text_uses_fallback_when_llm_missing():
    caso = {"id_caso": "123", "tipo_informe": "Fraude", "modalidad": "Digital"}
    analisis = {"antecedentes": {"text": "Hubo transferencias sospechosas sin autorización."}}
    productos = [{"fecha_ocurrencia": "2025-01-01"}]
    riesgos = [{"id_riesgo": "R1", "descripcion": "Credenciales filtradas"}]
    operaciones = [{"accion": "Bloquear tarjeta", "estado": "Pendiente"}]
    colaboradores = [{"nombres": "Ana", "flag": "involucrado", "area": "Seguridad"}]

    class NullLLM(SpanishSummaryHelper):
        def summarize(self, section, prompt, *, max_new_tokens=None):
            return None

    sections = build_alerta_temprana_sections(
        {
            "caso": caso,
            "analisis": analisis,
            "productos": productos,
            "riesgos": riesgos,
            "operaciones": operaciones,
            "colaboradores": colaboradores,
            "encabezado": {},
            "clientes": [],
            "reclamos": [],
        }
    )
    resumen = _synthesize_section_text("Resumen", sections, caso, NullLLM())
    assert "transferencias sospechosas" in resumen


def test_cronologia_prefers_hallazgos_bullets():
    sections = build_alerta_temprana_sections(
        {
            "caso": {"id_caso": "2025-0002"},
            "analisis": {
                "hallazgos": (
                    "- Primer hallazgo relevante del caso.\n"
                    "- Segundo hallazgo con detalle adicional para cronología.\n"
                    "- Tercer hallazgo asociado a la investigación.\n"
                    "- Cuarto hallazgo operativo.\n"
                    "- Quinto hallazgo que no debe aparecer."
                )
            },
            "productos": [],
            "riesgos": [],
            "operaciones": [{"accion": "No debería usarse", "estado": "Pendiente"}],
            "colaboradores": [],
            "encabezado": {},
            "clientes": [],
            "reclamos": [],
        }
    )
    cronologia = sections["cronologia"]
    assert "Primer hallazgo relevante" in cronologia
    assert "Cuarto hallazgo operativo" in cronologia
    assert "Quinto hallazgo" not in cronologia
