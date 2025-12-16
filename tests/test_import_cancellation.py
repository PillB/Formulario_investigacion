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


@pytest.mark.parametrize(
    "method_name,rows,expected_info,expected_log_fragment,expected_sync",
    [
        (
            "import_combined",
            [
                {
                    "id_cliente": "C-1",
                    "id_colaborador": "T00001",
                    "id_producto": "P-1",
                    "monto_investigado": "10.00",
                    "involucramiento": "T00001:5.00",
                }
            ],
            "Datos combinados importados correctamente.",
            "Datos combinados importados",
            "datos combinados",
        ),
        (
            "import_risks",
            [{"id_riesgo": "R-1", "descripcion": "desc"}],
            "Importación completada de riesgos:",
            "Riesgos importados desde CSV",
            None,
        ),
        (
            "import_norms",
            [
                {
                    "id_norma": "N-1",
                    "descripcion": "desc",
                    "fecha_vigencia": "2024-01-01",
                    "acapite_inciso": "Art. 1",
                    "detalle_norma": "Detalle de prueba",
                }
            ],
            "Importación completada de normas:",
            "Normas importadas desde CSV",
            None,
        ),
        (
            "import_claims",
            [
                {
                    "id_producto": "P-2",
                    "id_reclamo": "C123",
                    "nombre_analitica": "Analítica",
                    "codigo_analitica": "4300000001",
                }
            ],
            "Importación completada de reclamos:",
            "Reclamos importados desde CSV",
            "reclamos",
        ),
        (
            "import_clients",
            [{"id_cliente": "CLI-1", "tipo_id": "DNI"}],
            "Importación completada de clientes:",
            "Clientes importados desde CSV: total=1",
            "clientes",
        ),
        (
            "import_team_members",
            [{"id_colaborador": "T00001"}],
            "Importación completada de colaboradores:",
            "Colaboradores importados desde CSV: total=1",
            "colaboradores",
        ),
        (
            "import_products",
            [{"id_producto": "PR-1", "id_cliente": "CLI-1"}],
            "Importación completada de productos:",
            "Productos importados desde CSV: total=1",
            "productos",
        ),
    ],
)
def test_import_success_paths(monkeypatch, messagebox_spy, method_name, rows, expected_info, expected_log_fragment, expected_sync):
    app = build_import_app(monkeypatch)
    dialog_invoked = False

    def _dialog(**_kwargs):
        nonlocal dialog_invoked
        dialog_invoked = True
        return ""

    monkeypatch.setattr(app_module.filedialog, "askopenfilename", _dialog)
    monkeypatch.setattr(app_module, "iter_massive_csv_rows", lambda _filename: iter(rows))

    getattr(app, method_name)(filename="dummy.csv")

    assert dialog_invoked is False
    assert any(expected_info in msg for _title, msg in messagebox_spy.infos)
    assert messagebox_spy.errors == []
    assert messagebox_spy.warnings == []
    assert any(expected_log_fragment in log["mensaje"] for log in app.logs)
    if expected_sync:
        assert expected_sync in app.sync_calls
