import csv

from models import AutofillService, CatalogService
from settings import BASE_DIR


def _write_team_details(tmp_path, rows):
    path = tmp_path / "team_details.csv"
    headers = [
        "id_colaborador",
        "nombres",
        "apellidos",
        "flag",
        "division",
        "area",
        "servicio",
        "puesto",
        "fecha_carta_inmediatez",
        "fecha_carta_renuncia",
        "fecha_cese",
        "motivo_cese",
        "nombre_agencia",
        "codigo_agencia",
        "tipo_falta",
        "tipo_sancion",
        "fecha_actualizacion",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            if isinstance(row, dict):
                writer.writerow([row.get(header, "") for header in headers])
            else:
                padded = list(row) + [""] * (len(headers) - len(row))
                writer.writerow(padded[: len(headers)])
    return path


def _build_services(tmp_path):
    service = CatalogService(tmp_path)
    service.refresh()
    warnings: list[str] = []
    autofill = AutofillService(service, warning_handler=warnings.append)
    return service, autofill, warnings


def test_lookup_team_member_skips_malformed_dates():
    service = CatalogService(BASE_DIR)
    service.refresh()

    data, meta = service.lookup_team_member("T12345", "2024-06-01")

    assert data["fecha_actualizacion"] == "2024-05-15"
    assert meta["fallback_used"] is False
    assert meta["reason"] is None


def test_lookup_team_member_records_future_fallback_reason():
    service = CatalogService(BASE_DIR)
    service.refresh()

    data, meta = service.lookup_team_member("T54321", "2010-01-01")

    assert data["fecha_actualizacion"] == "2020-11-20"
    assert meta["fallback_used"] is True
    assert meta["reason"] == "no_past_snapshot"


def test_lookup_team_member_defaults_to_latest_with_invalid_case_date():
    service = CatalogService(BASE_DIR)
    service.refresh()

    data, meta = service.lookup_team_member("Z99999", "not-a-date")

    assert data["fecha_actualizacion"] == "2024-06-18"
    assert meta["fallback_used"] is True
    assert meta["reason"] == "case_date_missing_or_invalid"


def test_autofill_selects_latest_snapshot_before_case_date(tmp_path):
    _write_team_details(
        tmp_path,
        [
            {
                "id_colaborador": "T1",
                "nombres": "Nombre 2023",
                "apellidos": "Apellido 2023",
                "flag": "Involucrado",
                "division": "Division 2023",
                "codigo_agencia": "000111",
                "fecha_actualizacion": "2023-02-01",
            },
            {
                "id_colaborador": "T1",
                "nombres": "Nombre 2024",
                "apellidos": "Apellido 2024",
                "flag": "Involucrado",
                "division": "Division 2024",
                "codigo_agencia": "000222",
                "fecha_actualizacion": "2024-06-15",
            },
        ],
    )
    service, autofill, _ = _build_services(tmp_path)

    result = autofill.lookup_team_autofill(
        "T1",
        current_values={
            "division": "",
            "area": "",
            "servicio": "",
            "puesto": "",
            "nombre_agencia": "",
            "codigo_agencia": "",
        },
        dirty_fields={},
        preserve_existing=False,
        case_date="2024-06-20",
    )

    assert result.found is True
    assert result.applied["division"] == "Division 2024"
    assert service.team_snapshots["T1"][0]["data"]["codigo_agencia"] == "000111"


def test_team_details_preserves_new_columns(tmp_path):
    _write_team_details(
        tmp_path,
        [
            {
                "id_colaborador": "T9",
                "nombres": "Nombre 2024",
                "apellidos": "Apellido 2024",
                "flag": "Involucrado",
                "division": "Division 2024",
                "fecha_cese": "2024-12-31",
                "motivo_cese": "Renuncia",
                "codigo_agencia": "000999",
                "fecha_actualizacion": "2024-06-15",
            }
        ],
    )
    service, _, _ = _build_services(tmp_path)

    snapshot = service.team_snapshots["T9"][0]["data"]
    assert snapshot["fecha_cese"] == "2024-12-31"
    assert snapshot["motivo_cese"] == "Renuncia"


def test_autofill_respects_dirty_fields(tmp_path):
    _write_team_details(
        tmp_path,
        [
            {
                "id_colaborador": "T2",
                "nombres": "Nombre A",
                "apellidos": "Apellido A",
                "flag": "Relacionado",
                "division": "Division A",
                "area": "Area A",
                "codigo_agencia": "001000",
                "fecha_actualizacion": "2023-01-01",
            },
        ],
    )
    _, autofill, _ = _build_services(tmp_path)

    result = autofill.lookup_team_autofill(
        "T2",
        current_values={
            "division": "Manual",
            "area": "Area manual",
            "servicio": "",
            "puesto": "",
            "nombre_agencia": "",
            "codigo_agencia": "",
        },
        dirty_fields={"division": True, "area": True},
        preserve_existing=False,
        case_date="2023-02-01",
    )

    assert "division" not in result.applied
    assert "area" not in result.applied
    assert result.applied["codigo_agencia"] == "001000"


def test_autofill_applies_name_fields(tmp_path):
    _write_team_details(
        tmp_path,
        [
            {
                "id_colaborador": "T2A",
                "nombres": "Lucía",
                "apellidos": "Herrera",
                "flag": "Involucrado",
                "division": "Division Z",
                "area": "Area Z",
                "codigo_agencia": "009999",
                "fecha_actualizacion": "2024-03-03",
            },
        ],
    )
    _, autofill, _ = _build_services(tmp_path)

    result = autofill.lookup_team_autofill(
        "T2A",
        current_values={"nombres": "", "apellidos": "", "division": ""},
        dirty_fields={},
        preserve_existing=False,
        case_date="2024-04-01",
    )

    assert result.applied["nombres"] == "Lucía"
    assert result.applied["apellidos"] == "Herrera"
    assert result.applied["division"] == "Division Z"


def test_autofill_handles_invalid_case_date_with_latest_snapshot(tmp_path):
    _write_team_details(
        tmp_path,
        [
            {
                "id_colaborador": "T3",
                "nombres": "Nombre Pasado",
                "apellidos": "Apellido Pasado",
                "flag": "Relacionado",
                "division": "Division pasada",
                "fecha_actualizacion": "2020-01-01",
            },
            {
                "id_colaborador": "T3",
                "nombres": "Nombre Vigente",
                "apellidos": "Apellido Vigente",
                "flag": "Relacionado",
                "division": "Division vigente",
                "fecha_actualizacion": "2024-05-05",
            },
        ],
    )
    _, autofill, warnings = _build_services(tmp_path)

    result = autofill.lookup_team_autofill(
        "T3",
        current_values={
            "division": "",
            "area": "",
            "servicio": "",
            "puesto": "",
            "nombre_agencia": "",
            "codigo_agencia": "",
        },
        dirty_fields={},
        preserve_existing=False,
        case_date="not-a-date",
    )

    assert result.applied["division"] == "Division vigente"
    assert result.used_future_snapshot is False
    assert result.meta["fallback_used"] is True
    assert result.meta["reason"] == "case_date_missing_or_invalid"
    assert warnings == [
        "No se pudo interpretar la fecha de ocurrencia; se usará el registro más reciente disponible del colaborador."
    ]


def test_autofill_warns_when_using_future_snapshot(tmp_path):
    _write_team_details(
        tmp_path,
        [
            {
                "id_colaborador": "T4",
                "nombres": "Nombre Futuro",
                "apellidos": "Apellido Futuro",
                "flag": "Involucrado",
                "division": "Division futura",
                "fecha_actualizacion": "2025-01-01",
            },
        ],
    )
    _, autofill, warnings = _build_services(tmp_path)

    result = autofill.lookup_team_autofill(
        "T4",
        current_values={
            "division": "",
            "area": "",
            "servicio": "",
            "puesto": "",
            "nombre_agencia": "",
            "codigo_agencia": "",
        },
        dirty_fields={},
        preserve_existing=False,
        case_date="2020-01-01",
    )

    assert result.used_future_snapshot is True
    assert result.meta["reason"] == "no_past_snapshot"
    assert warnings, "Expected a non-blocking warning"
    assert result.applied["division"] == "Division futura"


def test_autofill_returns_not_found_for_unknown_identifier(tmp_path):
    _write_team_details(
        tmp_path,
        [
            {
                "id_colaborador": "T5",
                "nombres": "Nombre",
                "apellidos": "Apellido",
                "flag": "Relacionado",
                "division": "Division",
                "fecha_actualizacion": "2024-01-01",
            },
        ],
    )
    _, autofill, warnings = _build_services(tmp_path)

    result = autofill.lookup_team_autofill(
        "",
        current_values={"division": ""},
        dirty_fields={},
        preserve_existing=False,
        case_date="2024-01-02",
    )

    assert result.found is False
    assert result.applied == {}
    assert warnings == []


def test_autofill_picks_nearest_future_snapshot(tmp_path):
    _write_team_details(
        tmp_path,
        [
            {
                "id_colaborador": "T6",
                "nombres": "Nombre Lejano",
                "apellidos": "Apellido Lejano",
                "flag": "Involucrado",
                "division": "Futuro lejano",
                "fecha_actualizacion": "2030-01-01",
            },
            {
                "id_colaborador": "T6",
                "nombres": "Nombre Cercano",
                "apellidos": "Apellido Cercano",
                "flag": "Involucrado",
                "division": "Futuro cercano",
                "fecha_actualizacion": "2025-05-05",
            },
        ],
    )
    _, autofill, warnings = _build_services(tmp_path)

    result = autofill.lookup_team_autofill(
        "T6",
        current_values={"division": ""},
        dirty_fields={},
        preserve_existing=False,
        case_date="2024-12-12",
    )

    assert result.used_future_snapshot is True
    assert result.applied["division"] == "Futuro cercano"
    assert warnings, "Future snapshot should trigger warnings"


def test_autofill_uses_latest_when_case_date_missing(tmp_path):
    _write_team_details(
        tmp_path,
        [
            {
                "id_colaborador": "T7",
                "nombres": "Nombre Antiguo",
                "apellidos": "Apellido Antiguo",
                "flag": "Relacionado",
                "division": "Antiguo",
                "fecha_actualizacion": "2020-02-02",
            },
            {
                "id_colaborador": "T7",
                "nombres": "Nombre Reciente",
                "apellidos": "Apellido Reciente",
                "flag": "Relacionado",
                "division": "Reciente",
                "fecha_actualizacion": "2024-04-04",
            },
        ],
    )
    _, autofill, warnings = _build_services(tmp_path)

    result = autofill.lookup_team_autofill(
        "T7",
        current_values={"division": ""},
        dirty_fields={},
        preserve_existing=False,
        case_date=None,
    )

    assert result.applied["division"] == "Reciente"
    assert result.used_future_snapshot is False
    assert result.meta["fallback_used"] is True
    assert result.meta["reason"] == "case_date_missing_or_invalid"
    assert warnings == [
        "No se pudo interpretar la fecha de ocurrencia; se usará el registro más reciente disponible del colaborador."
    ]


def test_autofill_meta_includes_selected_date_and_reason(tmp_path):
    _write_team_details(
        tmp_path,
        [
            {
                "id_colaborador": "T8",
                "nombres": "Nombre Antiguo",
                "apellidos": "Apellido Antiguo",
                "flag": "Involucrado",
                "division": "Antiguo",
                "fecha_actualizacion": "2020-02-02",
            },
            {
                "id_colaborador": "T8",
                "nombres": "Nombre Reciente",
                "apellidos": "Apellido Reciente",
                "flag": "Involucrado",
                "division": "Reciente",
                "fecha_actualizacion": "2024-04-04",
            },
        ],
    )
    _, autofill, warnings = _build_services(tmp_path)

    result = autofill.lookup_team_autofill(
        "T8",
        current_values={"division": ""},
        dirty_fields={},
        preserve_existing=False,
        case_date="2019-12-31",
    )

    assert result.meta["fallback_used"] is True
    assert result.meta["reason"] == "no_past_snapshot"
    assert str(result.meta["selected_date"]) == "2020-02-02"
    assert warnings, "Fallback should log a warning"
