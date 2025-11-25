import pytest

import app as app_module
from tests.app_factory import build_import_app


@pytest.mark.parametrize(
    "method_name,sample_key",
    [
        ("import_combined", "combinado"),
        ("import_risks", "riesgos"),
        ("import_norms", "normas"),
        ("import_claims", "reclamos"),
        ("import_clients", "clientes"),
        ("import_team_members", "colaboradores"),
        ("import_products", "productos"),
    ],
)

def test_import_cancelled_from_dialog(monkeypatch, messagebox_spy, method_name, sample_key):
    app = build_import_app(monkeypatch)
    app._suppress_messagebox = False
    monkeypatch.setattr(app_module.filedialog, "askopenfilename", lambda **_: "")

    started_imports = []
    app._start_background_import = lambda *args, **kwargs: started_imports.append(True)

    getattr(app, method_name)()

    assert not started_imports
    assert app.logs[-1]["tipo"] == "cancelado"
    assert sample_key in app.logs[-1]["mensaje"]
    assert not any("Inició importación" in log["mensaje"] for log in app.logs)
    assert len(messagebox_spy.infos) == 1
    assert sample_key in messagebox_spy.infos[0][1]
    assert messagebox_spy.warnings == []
    assert messagebox_spy.errors == []
