import tkinter as tk

import pytest

from settings import CRITICIDAD_LIST
from tests.app_factory import build_summary_app
from ui.frames.products import ClaimRow


def test_claim_row_set_data_triggers_autofill(monkeypatch):
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter no disponible en el entorno de pruebas")

    class _ProductStub:
        idx = 0
        logs = []
        claim_lookup = {
            "C00000001": {
                "id_reclamo": "C00000001",
                "nombre_analitica": "Autocompletado",
                "codigo_analitica": "4300000001",
            }
        }

        def log_change(self, message):
            return None

        def _register_lookup_sync(self, *_args, **_kwargs):
            return None

        def persist_lookup_snapshot(self):
            return None

    product_stub = _ProductStub()
    try:
        row = ClaimRow(root, product_stub, 0, lambda *_: None, [], lambda *_: None)

        row.set_data({"id_reclamo": "C00000001"})

        assert row.name_var.get() == "Autocompletado"
        assert row.code_var.get() == "4300000001"
    finally:
        root.destroy()


def test_ingest_summary_risks_autofills_on_import(monkeypatch, messagebox_spy):
    app = build_summary_app(monkeypatch)
    risk_row = ["RSK-000123", "Líder", CRITICIDAD_LIST[0], "100.00"]
    sanitized = app._transform_clipboard_riesgos([risk_row])

    processed = app.ingest_summary_rows("riesgos", sanitized)

    assert processed == 1
    assert app.risk_frames[0].on_id_change_calls
    call_kwargs = app.risk_frames[0].on_id_change_calls[-1]
    assert call_kwargs.get("preserve_existing") is True
