import os
import tkinter as tk
from tkinter import ttk

import pytest

import app as app_module


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tkinter no disponible en el entorno de pruebas",
)
def test_import_team_button_triggers_correct_task(monkeypatch, messagebox_spy):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    app = app_module.FraudCaseApp(root)

    started_tasks = []
    selected_keys = []

    def fake_start(task_label, button, worker, ui_callback, error_prefix, ui_error_prefix=None):
        started_tasks.append((task_label, button))

    monkeypatch.setattr(app, "_start_background_import", fake_start)
    monkeypatch.setattr(
        app,
        "_select_csv_file",
        lambda key, title: selected_keys.append((key, title)) or "dummy.csv",
    )
    monkeypatch.setattr(app, "_validate_import_headers", lambda filename, key: True)

    notebook = ttk.Notebook(root)
    actions_tab = ttk.Frame(notebook)
    app.build_actions_tab(actions_tab)

    app.import_team_button.invoke()

    assert selected_keys[0][0] == "colaboradores"
    assert started_tasks[0][0] == "colaboradores"
    assert started_tasks[0][1] is app.import_team_button

    root.destroy()
