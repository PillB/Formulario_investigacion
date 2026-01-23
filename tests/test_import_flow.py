import types

from tests.app_factory import build_import_app


def test_empty_import_payload_warns_and_skips_callbacks(monkeypatch, messagebox_spy):
    app = build_import_app(monkeypatch)
    app._suppress_messagebox = False

    status = {}
    app.import_status_var = types.SimpleNamespace(
        set=lambda value: status.__setitem__("value", value)
    )

    class ButtonStub:
        def __init__(self):
            self.states = []

        def state(self, args):
            self.states.append(tuple(args))

    button = ButtonStub()
    calls = []

    app._start_background_import(
        "clientes",
        button,
        worker=lambda: [],
        ui_callback=lambda payload: calls.append(payload),
        error_prefix="No se pudo importar clientes",
    )

    assert calls == []
    assert status.get("value", "").startswith(
        "Importación de clientes cancelada: no se encontraron datos."
    )
    assert ("disabled",) in button.states
    assert ("!disabled",) in button.states
    assert messagebox_spy.warnings
    assert any("no se encontraron" in message.lower() for _title, message in messagebox_spy.warnings)
    assert messagebox_spy.errors == []
    assert messagebox_spy.infos == []
    assert app._active_import_jobs == 0
