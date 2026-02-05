import os
import tkinter as tk
from tkinter import ttk

import pytest

import app as app_module
from report.resumen_ejecutivo import build_resumen_ejecutivo_md
from report_builder import CaseData


def test_build_resumen_ejecutivo_md(tmp_path):
    data = CaseData.from_mapping(
        {
            "caso": {"id_caso": "2025-0002", "tipo_informe": "Gerencia"},
            "clientes": [{"id_cliente": "CLI1", "nombres": "Ana", "apellidos": "Perez"}],
            "colaboradores": [{"id_colaborador": "T12345", "nombres": "Juan", "apellidos": "Soto"}],
            "productos": [{"id_producto": "P001", "monto_investigado": "100.00"}],
            "reclamos": [],
            "involucramientos": [],
            "riesgos": [{"id_riesgo": "R1", "descripcion": "Riesgo operativo"}],
            "normas": [],
            "analisis": {
                "hallazgos": {"text": "Se identificaron patrones anómalos."},
                "conclusiones": {"text": "El caso requiere seguimiento inmediato."},
            },
            "encabezado": {"dirigido_a": "Gerencia de Riesgos"},
            "operaciones": [],
            "anexos": [],
            "firmas": [],
            "recomendaciones_categorias": {},
        }
    )
    output = tmp_path / "Resumen_Ejecutivo_Gerencia_2025-0002.md"
    path = build_resumen_ejecutivo_md(data, output)
    content = path.read_text(encoding="utf-8")
    assert "# Resumen Ejecutivo" in content
    assert "**Caso:** 2025-0002" in content
    assert "Mensaje clave" in content
    assert "Contexto del caso" in content
    assert "Hallazgos y análisis" in content
    assert "Evidencia y trazabilidad" in content
    assert "Monto investigado 100.00" in content


def test_resumen_ejecutivo_fallbacks(tmp_path):
    data = CaseData.from_mapping(
        {
            "caso": {},
            "clientes": [],
            "colaboradores": [],
            "productos": [],
            "reclamos": [],
            "involucramientos": [],
            "riesgos": [],
            "normas": [],
            "analisis": {},
            "encabezado": {},
            "operaciones": [],
            "anexos": [],
            "firmas": [],
            "recomendaciones_categorias": {},
        }
    )
    output = tmp_path / "Resumen_Ejecutivo_Gerencia_0000.md"
    path = build_resumen_ejecutivo_md(data, output)
    content = path.read_text(encoding="utf-8")
    assert "N/A" in content


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)
def test_resumen_ejecutivo_button_invokes_command(monkeypatch, messagebox_spy):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    app = app_module.FraudCaseApp(root)
    invoked = []

    def fake_generate():
        invoked.append(True)

    monkeypatch.setattr(app, "generate_resumen_ejecutivo", fake_generate)

    notebook = ttk.Notebook(root)
    actions_tab = ttk.Frame(notebook)
    app.build_actions_tab(actions_tab)

    app.btn_resumen_ejecutivo.invoke()

    assert invoked
    root.destroy()


def test_build_resumen_ejecutivo_md_uses_llm_helper(tmp_path):
    class StubLLM:
        def __init__(self):
            self.calls = []

        def summarize(self, section, prompt, *, max_new_tokens=None):
            self.calls.append((section, prompt, max_new_tokens))
            return f"Sección refinada {section}"

    data = CaseData.from_mapping(
        {
            "caso": {"id_caso": "2025-0100", "tipo_informe": "Fraude"},
            "clientes": [],
            "colaboradores": [],
            "productos": [{"id_producto": "P001", "monto_investigado": "120.00"}],
            "reclamos": [],
            "involucramientos": [],
            "riesgos": [],
            "normas": [],
            "analisis": {"hallazgos": {"text": "Hallazgo base."}},
            "encabezado": {},
            "operaciones": [],
            "anexos": [],
            "firmas": [],
            "recomendaciones_categorias": {},
        }
    )

    stub_llm = StubLLM()
    output = tmp_path / "Resumen_Ejecutivo_Gerencia_2025-0100.md"
    path = build_resumen_ejecutivo_md(data, output, llm_helper=stub_llm)
    content = path.read_text(encoding="utf-8")

    assert "Sección refinada" in content
    assert stub_llm.calls
