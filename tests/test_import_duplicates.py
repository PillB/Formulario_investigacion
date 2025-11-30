import app as app_module
from tests.app_factory import build_import_app


def test_product_import_skips_existing_and_duplicate_rows(monkeypatch, messagebox_spy):
    app = build_import_app(monkeypatch)
    existing = app._obtain_product_slot_for_import()
    existing.id_var.set("PR-1")

    rows = [
        {"id_producto": "PR-1", "id_cliente": "C-1"},
        {"id_producto": "PR-2", "id_cliente": "C-1"},
        {"id_producto": "PR-2", "id_cliente": "C-1"},
    ]
    monkeypatch.setattr(app_module, "iter_massive_csv_rows", lambda _filename: iter(rows))

    app.import_products(filename="dummy.csv")

    product_ids = {frame.id_var.get() for frame in app.product_frames}
    assert product_ids == {"PR-1", "PR-2"}
    assert len(app.product_frames) == 2
    assert any("duplicados=2" in log["mensaje"] for log in app.logs)

    summary_message = messagebox_spy.infos[-1][1]
    assert "1 registros nuevos" in summary_message
    assert "2 duplicados omitidos" in summary_message
    assert "0 filas con errores" in summary_message
