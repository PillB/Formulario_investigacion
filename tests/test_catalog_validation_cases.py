from __future__ import annotations

from csv import DictWriter
from decimal import Decimal
from pathlib import Path

import pytest

from models.catalogs import iter_massive_csv_rows, load_detail_catalogs
from validators import (
    AGENCY_CODE_PATTERN,
    TEAM_MEMBER_ID_PATTERN,
    sum_investigation_components,
    validate_agency_code,
    validate_client_id,
    validate_codigo_analitica,
    validate_date_text,
    validate_money_bounds,
    validate_product_dates,
    validate_reclamo_id,
    validate_team_member_id,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_massive_products_and_combined_samples_respect_design_rules():
    datasets = [
        REPO_ROOT / "productos_masivos.csv",
        REPO_ROOT / "datos_combinados_masivos.csv",
    ]

    for dataset in datasets:
        for row in iter_massive_csv_rows(dataset):
            labels = f"{row.get('nombre_analitica', '')} {row.get('modalidad', '')}"
            if "[INVALID" in labels:
                continue

            producto_id = row.get("id_producto", "")

            assert (
                validate_product_dates(
                    producto_id,
                    row.get("fecha_ocurrencia", ""),
                    row.get("fecha_descubrimiento", ""),
                )
                is None
            )

            money_fields = {}
            for key, label in [
                ("monto_investigado", "Monto investigado"),
                ("monto_perdida_fraude", "Monto Pérdida de Fraude"),
                ("monto_falla_procesos", "Monto Falla en Procesos"),
                ("monto_contingencia", "Monto Contingencia"),
                ("monto_recuperado", "Monto Recuperado"),
                ("monto_pago_deuda", "Monto Pago de Deuda"),
            ]:
                err, value, _ = validate_money_bounds(row.get(key, ""), f"{label} {producto_id}")
                assert err is None
                money_fields[key] = value or Decimal("0")

            assert sum_investigation_components(
                perdida=money_fields["monto_perdida_fraude"],
                falla=money_fields["monto_falla_procesos"],
                contingencia=money_fields["monto_contingencia"],
                recuperado=money_fields["monto_recuperado"],
            ) == money_fields["monto_investigado"]

            assert money_fields["monto_pago_deuda"] <= money_fields["monto_investigado"]

            if money_fields["monto_investigado"] > 0:
                assert validate_reclamo_id(row.get("id_reclamo", "")) is None
                assert (row.get("nombre_analitica") or "").strip()
                assert validate_codigo_analitica(row.get("codigo_analitica", "")) is None

            tipo_producto = (row.get("tipo_producto") or "").lower()
            if "credito" in tipo_producto or "tarjeta" in tipo_producto:
                assert money_fields["monto_contingencia"] == money_fields["monto_investigado"]


def test_detail_catalogs_enforce_identifiers_and_dates():
    catalogs = load_detail_catalogs(REPO_ROOT)

    assert "client" in catalogs
    assert "team" in catalogs

    client_errors = []
    valid_clients = []
    for client in catalogs["client"].values():
        err = validate_client_id(client.get("tipo_id", ""), client.get("id_cliente", ""))
        if err:
            client_errors.append(err)
        else:
            valid_clients.append(client["id_cliente"])

    assert valid_clients, "Debe haber clientes de muestra válidos para las pruebas manuales"
    assert any("RUC" in error or "caracteres" in error for error in client_errors)

    for member in catalogs["team"].values():
        collaborator = member.get("id_colaborador", "")
        assert validate_team_member_id(collaborator) is None
        assert TEAM_MEMBER_ID_PATTERN.fullmatch(collaborator)

        if (member.get("division") or "").lower() in {"dca", "canales de atención"}:
            if "area comercial" in (member.get("area") or "").lower():
                assert (member.get("nombre_agencia") or "").strip()
                assert AGENCY_CODE_PATTERN.fullmatch(member.get("codigo_agencia", ""))
                assert validate_agency_code(member.get("codigo_agencia", ""), allow_blank=False) is None

        if member.get("fecha_actualizacion"):
            assert (
                validate_date_text(
                    member["fecha_actualizacion"],
                    "Fecha de actualización",  # noqa: E501
                    allow_blank=False,
                )
                is None
            )


def test_invalid_massive_and_detail_rows_surface_expected_errors(tmp_path):
    invalid_massive = tmp_path / "productos_masivos.csv"
    headers = [
        "id_producto",
        "id_cliente",
        "tipo_producto",
        "fecha_ocurrencia",
        "fecha_descubrimiento",
        "monto_investigado",
        "monto_perdida_fraude",
        "monto_falla_procesos",
        "monto_contingencia",
        "monto_recuperado",
        "monto_pago_deuda",
        "id_reclamo",
        "nombre_analitica",
        "codigo_analitica",
    ]
    with invalid_massive.open("w", newline="", encoding="utf-8") as handle:
        writer = DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerow(
            {
                "id_producto": "PRDX",
                "id_cliente": "123",
                "tipo_producto": "Crédito de prueba",
                "fecha_ocurrencia": "2024-02-10",
                "fecha_descubrimiento": "2024-02-09",
                "monto_investigado": "100.00",
                "monto_perdida_fraude": "10.00",
                "monto_falla_procesos": "5.00",
                "monto_contingencia": "10.00",
                "monto_recuperado": "1.00",
                "monto_pago_deuda": "150.00",
                "id_reclamo": "C12",
                "nombre_analitica": "",
                "codigo_analitica": "123",
            }
        )

    rows = list(iter_massive_csv_rows(invalid_massive))
    assert len(rows) == 1
    invalid_row = rows[0]

    assert validate_product_dates(
        invalid_row.get("id_producto", ""),
        invalid_row.get("fecha_ocurrencia", ""),
        invalid_row.get("fecha_descubrimiento", ""),
    ) is not None

    _, monto_investigado, _ = validate_money_bounds(
        invalid_row.get("monto_investigado", ""), "Monto investigado"
    )
    assert monto_investigado == Decimal("100.00")

    money_components = [
        validate_money_bounds(invalid_row.get(field, ""), field)[1]
        for field in (
            "monto_perdida_fraude",
            "monto_falla_procesos",
            "monto_contingencia",
            "monto_recuperado",
        )
    ]
    assert sum(filter(None, money_components)) != monto_investigado

    assert validate_reclamo_id(invalid_row.get("id_reclamo", "")) is not None
    assert validate_codigo_analitica(invalid_row.get("codigo_analitica", "")) is not None

    invalid_detail_dir = tmp_path / "details"
    invalid_detail_dir.mkdir()

    with (invalid_detail_dir / "client_details.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = DictWriter(
            handle,
            fieldnames=["id_cliente", "tipo_id", "flag", "telefonos", "correos", "direcciones"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id_cliente": "111",
                "tipo_id": "dni",
                "flag": "Afectado",
                "telefonos": "123",
                "correos": "correo-invalido",
                "direcciones": "",
            }
        )

    with (invalid_detail_dir / "team_details.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = DictWriter(
            handle,
            fieldnames=[
                "id_colaborador",
                "division",
                "area",
                "servicio",
                "puesto",
                "nombre_agencia",
                "codigo_agencia",
                "fecha_actualizacion",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id_colaborador": "12345",
                "division": "DCA",
                "area": "Área Comercial",
                "servicio": "",
                "puesto": "",
                "nombre_agencia": "",
                "codigo_agencia": "12",
                "fecha_actualizacion": "2024/05/01",
            }
        )

    detail_catalogs = load_detail_catalogs(invalid_detail_dir)
    assert "client" in detail_catalogs and "team" in detail_catalogs

    client_entry = next(iter(detail_catalogs["client"].values()))
    assert validate_client_id(client_entry.get("tipo_id", ""), client_entry.get("id_cliente", "")) is not None

    team_entry = next(iter(detail_catalogs["team"].values()))
    assert validate_team_member_id(team_entry.get("id_colaborador", "")) is not None
    assert validate_agency_code(team_entry.get("codigo_agencia", ""), allow_blank=False) is not None
    assert validate_date_text(team_entry.get("fecha_actualizacion", ""), "Fecha de actualización", allow_blank=False) is not None
