from pathlib import Path

import utils.mass_import_manager as import_manager
from utils.mass_import_manager import MassImportManager


def test_orchestrate_handles_locked_file(monkeypatch, tmp_path):
    manager = MassImportManager(tmp_path / "logs")

    locked_file = tmp_path / "locked.csv"
    locked_file.write_text("id,name\n1,blocked\n", encoding="utf-8")

    error_messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        import_manager.messagebox,
        "showerror",
        lambda title, message: error_messages.append((title, message)),
    )

    button_states: list[list[str]] = []

    class DummyButton:
        def state(self, states):
            button_states.append(list(states))
            return states

    class DummyApp:
        _catalog_loading = False

        def __init__(self):
            self.logs = []

        def _select_csv_file(self, sample_key, dialog_title):
            return str(locked_file)

        def _validate_import_headers(self, filename, key):
            return True

        def _start_background_import(self, task_label, button, worker, ui_callback, error_prefix, ui_error_prefix=None):
            button.state(['disabled'])
            raise OSError("Archivo bloqueado por otra aplicación")

    app = DummyApp()
    button = DummyButton()
    logs: list[tuple[str, str]] = []

    def worker_factory(file_path: str):
        assert Path(file_path) == locked_file
        return lambda *_, **__: None

    manager.orchestrate_csv_import(
        app=app,
        sample_key="riesgos",
        task_label="riesgos",
        button=button,
        worker_factory=worker_factory,
        ui_callback=lambda payload, file_path: None,
        error_prefix="No se pudo importar riesgos",
        filename=str(locked_file),
        dialog_title="Seleccionar CSV de riesgos",
        log_handler=lambda category, message: logs.append((category, message)),
    )

    assert error_messages, "Se debe mostrar un mensaje de error al usuario"
    title, message = error_messages[0]
    assert "locked.csv" in message
    assert "riesgos" in message
    assert any(state == ['disabled'] for state in button_states)
    assert button_states[-1] == ['!disabled'], "El botón debe reactivarse tras el error"
    assert logs and "No se pudo importar riesgos" in logs[-1][1]

