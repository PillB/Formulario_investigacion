import csv

import pytest

from settings import EVENTOS_HEADER_CANONICO
from tests.app_factory import build_import_app


def _write_csv(tmp_path, headers):
    file_path = tmp_path / "eventos.csv"
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerow(["" for _ in headers])
    return file_path


def test_validate_import_headers_accepts_legacy_with_aliases(tmp_path, monkeypatch):
    app = build_import_app(monkeypatch)
    legacy_headers = list(app._get_import_config("combinado")["expected_headers"])
    legacy_headers[legacy_headers.index("id_producto")] = "product_id"
    legacy_headers[legacy_headers.index("id_cliente_involucrado")] = "client_id_involucrado"
    legacy_headers[legacy_headers.index("id_colaborador")] = "matricula_colaborador_involucrado"
    file_path = _write_csv(tmp_path, legacy_headers)

    assert app._validate_import_headers(str(file_path), "combinado") is True


def test_validate_import_headers_accepts_canonical(tmp_path, monkeypatch):
    app = build_import_app(monkeypatch)
    file_path = _write_csv(tmp_path, EVENTOS_HEADER_CANONICO)

    assert app._validate_import_headers(str(file_path), "combinado") is True


@pytest.mark.parametrize(
    "header,expected_key",
    [
        ("case_id", "id_caso"),
        ("product_id", "id_producto"),
        ("client_id_involucrado", "id_cliente_involucrado"),
        ("matricula_colaborador_involucrado", "id_colaborador"),
    ],
)
def test_normalize_eventos_row_maps_canonical_aliases(monkeypatch, header, expected_key):
    app = build_import_app(monkeypatch)
    normalized = app._normalize_eventos_row({header: "value"}, "canonical")

    assert normalized[expected_key] == "value"


def test_normalize_eventos_row_maps_case_date_aliases(monkeypatch):
    app = build_import_app(monkeypatch)
    normalized = app._normalize_eventos_row(
        {
            "fecha_de_ocurrencia": "2024-01-01",
            "fecha_de_descubrimiento": "2024-01-02",
        },
        "legacy",
    )

    assert normalized["fecha_ocurrencia_caso"] == "2024-01-01"
    assert normalized["fecha_descubrimiento_caso"] == "2024-01-02"
