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
            "clientes": [{"id_cliente": "CLI1"}],
            "colaboradores": [],
            "productos": [{"monto_investigado": "100.00"}],
            "reclamos": [],
            "involucramientos": [],
            "riesgos": [{"id_riesgo": "R1", "descripcion": "Riesgo operativo"}],
            "normas": [],
            "analisis": {"hallazgos": {"text": "Se identificaron patrones anómalos."}},
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
    assert "Puntos de soporte" in content
    assert "Evidencia" in content


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
