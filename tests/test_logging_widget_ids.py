import types
from pathlib import Path

import app as app_module


def test_generate_report_file_records_widget_id(monkeypatch, tmp_path, messagebox_spy):
    app = app_module.FraudCaseApp.__new__(app_module.FraudCaseApp)
    app.logs = []
    app._docx_available = True
    app._pptx_available = True
    app._mirror_exports_to_external_drive = lambda *_, **__: []
    app.flush_logs_now = lambda: None
    app._play_feedback_sound = lambda: None
    app._show_success_toast = lambda *_, **__: None
    app._prepare_case_data_for_export = lambda: (
        {"caso": {"id_caso": "2024-0001", "tipo_informe": "Fraude"}},
        Path(tmp_path),
        "2024-0001",
    )

    original_log_event = app_module.log_event
    captured: list[dict] = []

    def capture(event_type, message, logs, widget_id=None, event_subtipo=None, coords=None, **kwargs):
        captured.append(
            {
                "tipo": event_type,
                "mensaje": message,
                "widget_id": widget_id,
                "action_result": kwargs.get("action_result"),
            }
        )
        return original_log_event(
            event_type,
            message,
            logs,
            widget_id=widget_id,
            event_subtipo=event_subtipo,
            coords=coords,
            **kwargs,
        )

    monkeypatch.setattr(app_module, "log_event", capture)

    def builder(_data, path: Path):
        path.write_text("ok", encoding="utf-8")
        return path

    app._generate_report_file("md", builder, "Markdown (.md)", widget_id="btn_md")

    assert any(
        entry["widget_id"] == "btn_md"
        and entry["tipo"] == "navegacion"
        and entry["action_result"] == "success"
        for entry in captured
    )


def test_load_autosave_logs_with_widget_id(monkeypatch, tmp_path, messagebox_spy):
    app = app_module.FraudCaseApp.__new__(app_module.FraudCaseApp)
    app.logs = []
    app._suppress_messagebox = True
    app._autosave_start_guard = False
    app._notify_user = lambda *_, **__: None
    app._clear_case_state = lambda *_, **__: None
    app._report_persistence_failure = lambda *_, **__: None
    app._parse_persisted_payload = lambda payload: (payload.get("dataset", {}), payload.get("form_state", {}))
    app._apply_loaded_dataset = lambda *_, **__: None
    autosave_path = tmp_path / "autosave.json"
    autosave_path.write_text("{}", encoding="utf-8")
    app._discover_autosave_candidates = lambda: [(0, autosave_path)]
    app.actions_action_bar = types.SimpleNamespace(
        buttons={"load_autosave": types.SimpleNamespace(winfo_name=lambda: "btn_load_autosave")}
    )

    original_log_event = app_module.log_event
    captured: list[dict] = []

    def capture(event_type, message, logs, widget_id=None, event_subtipo=None, coords=None, **kwargs):
        captured.append(
            {
                "tipo": event_type,
                "mensaje": message,
                "widget_id": widget_id,
                "action_result": kwargs.get("action_result"),
            }
        )
        return original_log_event(
            event_type,
            message,
            logs,
            widget_id=widget_id,
            event_subtipo=event_subtipo,
            coords=coords,
            **kwargs,
        )

    monkeypatch.setattr(app_module, "log_event", capture)

    class StubManager:
        def load_first_valid(self, paths, on_success, on_error):
            result = types.SimpleNamespace(
                payload={"dataset": {"caso": {}}},
                path=paths[0],
                failed=[(paths[0], RuntimeError("boom"))],
            )
            on_success(result)

    app._get_persistence_manager = lambda: StubManager()

    app.load_autosave()

    assert any(entry["widget_id"] == "btn_load_autosave" for entry in captured)
