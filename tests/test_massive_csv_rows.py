from __future__ import annotations

from csv import DictWriter
from decimal import Decimal
from pathlib import Path

import pytest

import app as app_module
from models.catalogs import iter_massive_csv_rows
from tests.app_factory import build_import_app
from validators import (
    AGENCY_CODE_PATTERN,
    TEAM_MEMBER_ID_PATTERN,
    validate_case_id,
    validate_client_id,
    sum_investigation_components,
    validate_email_list,
    validate_codigo_analitica,
    validate_date_text,
    validate_money_bounds,
    validate_norm_id,
    validate_product_dates,
    validate_reclamo_id,
    validate_risk_id,
    validate_phone_list,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "filename,expected_count,required_keys",
    [
        ("clientes_masivos.csv", 15, {"id_cliente", "tipo_id", "flag", "telefonos", "correos"}),
        (
            "colaboradores_masivos.csv",
            13,
            {"id_colaborador", "division", "area", "tipo_sancion"},
        ),
        (
            "productos_masivos.csv",
            16,
            {
                "id_producto",
                "id_cliente",
                "fecha_ocurrencia",
                "fecha_descubrimiento",
                "monto_investigado",
            },
        ),
        (
            "datos_combinados_masivos.csv",
            16,
            {"id_producto", "id_cliente", "monto_investigado"},
        ),
        ("normas_masivas.csv", 4, {"id_norma", "descripcion", "fecha_vigencia"}),
        ("riesgos_masivos.csv", 4, {"id_riesgo", "descripcion", "criticidad"}),
    ],
)
def test_iter_massive_csv_rows_loads_real_datasets(filename, expected_count, required_keys):
    path = REPO_ROOT / filename
    rows = list(iter_massive_csv_rows(path))

    assert len(rows) == expected_count
    for row in rows:
        assert set(row).issuperset(required_keys)
        assert all(key == key.strip() for key in row)
        assert None not in row
        for key in required_keys:
            assert row[key] == (row.get(key) or "").strip()


def test_massive_products_hit_validation_rules():
    rows = list(iter_massive_csv_rows(REPO_ROOT / "productos_masivos.csv"))

    for row in rows:
        product_id = row.get("id_producto") or ""
        assert (
            validate_product_dates(
                product_id,
                row.get("fecha_ocurrencia", ""),
                row.get("fecha_descubrimiento", ""),
            )
            is None
        )

        error, monto_investigado, _ = validate_money_bounds(
            row.get("monto_investigado", ""),
            f"Monto investigado del producto {product_id or 'sin ID'}",
        )
        assert error is None

        money_fields = {}
        for key, label in [
            ("monto_perdida_fraude", "Monto Pérdida de Fraude"),
            ("monto_falla_procesos", "Monto Falla en Procesos"),
            ("monto_contingencia", "Monto Contingencia"),
            ("monto_recuperado", "Monto Recuperado"),
        ]:
            err, value, _ = validate_money_bounds(row.get(key, ""), f"{label} {product_id}")
            assert err is None
            money_fields[key] = value or Decimal("0")

        assert sum_investigation_components(
            perdida=money_fields["monto_perdida_fraude"],
            falla=money_fields["monto_falla_procesos"],
            contingencia=money_fields["monto_contingencia"],
            recuperado=money_fields["monto_recuperado"],
        ) == monto_investigado

        if monto_investigado and monto_investigado > 0:
            assert validate_reclamo_id(row.get("id_reclamo", "")) is None
            assert validate_codigo_analitica(row.get("codigo_analitica", "")) is None

        tipo_producto = (row.get("tipo_producto") or "").lower()
        if "credito" in tipo_producto or "tarjeta" in tipo_producto:
            assert money_fields["monto_contingencia"] == monto_investigado


def test_real_massive_clients_enforce_contacts_and_identifiers():
    rows = list(iter_massive_csv_rows(REPO_ROOT / "clientes_masivos.csv"))

    assert len(rows) == 15

    for row in rows:
        assert validate_client_id(row.get("tipo_id", ""), row.get("id_cliente", "")) is None
        assert validate_phone_list(row.get("telefonos", ""), "Teléfonos del cliente") is None
        assert validate_email_list(row.get("correos", ""), "Correos del cliente") is None
        assert (row.get("flag") or "").strip()
        assert (row.get("accionado") or "").strip()


def test_massive_collaborators_require_proper_ids_and_agency_fields():
    rows = list(iter_massive_csv_rows(REPO_ROOT / "colaboradores_masivos.csv"))

    for row in rows:
        assert TEAM_MEMBER_ID_PATTERN.fullmatch(row.get("id_colaborador", ""))
        division = (row.get("division") or "").lower()
        area = (row.get("area") or "").lower()
        if (division == "dca" or division == "canales de atención") and "area comercial" in area:
            assert row.get("nombre_agencia")
            assert AGENCY_CODE_PATTERN.fullmatch(row.get("codigo_agencia", ""))

        assert (row.get("tipo_sancion") or "").strip()


def test_import_combined_massive_dataset_hydrates_frames(monkeypatch, messagebox_spy):
    app = build_import_app(monkeypatch)
    dataset_path = REPO_ROOT / "datos_combinados_masivos.csv"
    rows = list(iter_massive_csv_rows(dataset_path))
    expected_clients = {row["id_cliente"].strip() for row in rows if row.get("id_cliente")}
    expected_products = {row["id_producto"].strip() for row in rows if row.get("id_producto")}
    expected_team = set()
    for row in rows:
        involvement = row.get("involucramiento") or ""
        for chunk in involvement.split(";"):
            if not chunk.strip():
                continue
            collaborator = chunk.split(":", 1)[0].strip()
            if collaborator:
                expected_team.add(collaborator)

    monkeypatch.setattr(app_module, "iter_massive_csv_rows", iter_massive_csv_rows)

    app.import_combined(filename=str(dataset_path))

    assert {frame.id_var.get() for frame in app.client_frames if frame.id_var.get()} == expected_clients
    assert {frame.id_var.get() for frame in app.product_frames if frame.id_var.get()} == expected_products
    assert {frame.id_var.get() for frame in app.team_frames if frame.id_var.get()} >= expected_team
    assert messagebox_spy.errors == []


def test_import_combined_flags_invalid_rows(monkeypatch, messagebox_spy, tmp_path):
    app = build_import_app(monkeypatch)
    source_rows = list(iter_massive_csv_rows(REPO_ROOT / "datos_combinados_masivos.csv"))
    headers = list(source_rows[0].keys())
    # Agregar una fila con monto de involucramiento inválido para detonar la validación
    source_rows.append(
        {
            **source_rows[0],
            "involucramiento": "T12345:10.123",
        }
    )
    invalid_path = tmp_path / "invalid_combined.csv"
    with invalid_path.open("w", encoding="utf-8", newline="") as handle:
        writer = DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(source_rows)

    monkeypatch.setattr(app_module, "iter_massive_csv_rows", iter_massive_csv_rows)

    with pytest.raises(ValueError):
        app.import_combined(filename=str(invalid_path))

    assert any("dos decimales" in msg for _title, msg in messagebox_spy.errors)


def test_combined_massive_dataset_matches_expected_entities_and_validations():
    rows = list(iter_massive_csv_rows(REPO_ROOT / "datos_combinados_masivos.csv"))

    assert len(rows) == 16

    clients = {row["id_cliente"].strip() for row in rows if row.get("id_cliente")}
    products = {row["id_producto"].strip() for row in rows if row.get("id_producto")}
    collaborators = set()
    for row in rows:
        collaborator = (row.get("id_colaborador") or "").strip()
        if collaborator:
            assert TEAM_MEMBER_ID_PATTERN.fullmatch(collaborator)
            collaborators.add(collaborator)
        involvement = row.get("involucramiento") or ""
        for chunk in involvement.split(";"):
            if not chunk.strip():
                continue
            collaborator = chunk.split(":", 1)[0].strip()
            if collaborator:
                assert TEAM_MEMBER_ID_PATTERN.fullmatch(collaborator)
                collaborators.add(collaborator)

        labels = f"{row.get('nombre_analitica', '')} {row.get('modalidad', '')}"
        if "[INVALID" in labels:
            continue

        assert validate_product_dates(
            row.get("id_producto", ""),
            row.get("fecha_ocurrencia", ""),
            row.get("fecha_descubrimiento", ""),
        ) is None

        err, monto_investigado, _ = validate_money_bounds(
            row.get("monto_investigado", ""), "Monto investigado combinado"
        )
        assert err is None
        assert monto_investigado is not None
        for field, label in [
            ("monto_perdida_fraude", "Monto Pérdida de Fraude"),
            ("monto_falla_procesos", "Monto Falla en Procesos"),
            ("monto_contingencia", "Monto Contingencia"),
            ("monto_recuperado", "Monto Recuperado"),
        ]:
            msg, value, _ = validate_money_bounds(row.get(field, ""), label)
            assert msg is None
            assert value is not None

        if monto_investigado > 0:
            assert validate_reclamo_id(row.get("id_reclamo", "")) is None
            assert validate_codigo_analitica(row.get("codigo_analitica", "")) is None

    assert len(clients) == 16
    assert len(products) == 16
    assert len(collaborators) == 20


@pytest.mark.parametrize(
    "filename,validator",
    [
        (
            REPO_ROOT / "normas_masivas.csv",
            lambda row: (
                validate_norm_id(row.get("id_norma", "")) is None
                and validate_case_id(row.get("id_caso", "")) is None
                and validate_date_text(row.get("fecha_vigencia", ""), "Fecha de vigencia", allow_blank=False)
                is None
            ),
        ),
        (
            REPO_ROOT / "riesgos_masivos.csv",
            lambda row: (
                validate_risk_id(row.get("id_riesgo", "")) is None
                and validate_case_id(row.get("id_caso", "")) is None
            ),
        ),
    ],
)
def test_norm_and_risk_massive_files_stay_in_spec(filename, validator):
    rows = list(iter_massive_csv_rows(filename))

    assert rows, f"{filename.name} no debe estar vacío"
    for row in rows:
        assert validator(row)
