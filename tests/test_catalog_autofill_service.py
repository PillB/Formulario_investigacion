import csv

import csv

from models import AutofillService, CatalogService


def _write_team_details(tmp_path, rows):
    path = tmp_path / "team_details.csv"
    headers = [
        "id_colaborador",
        "division",
        "area",
        "servicio",
        "puesto",
        "nombre_agencia",
        "codigo_agencia",
        "fecha_actualizacion",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
    return path


def _build_services(tmp_path):
    service = CatalogService(tmp_path)
    service.refresh()
    warnings: list[str] = []
    autofill = AutofillService(service, warning_handler=warnings.append)
    return service, autofill, warnings


def test_autofill_selects_latest_snapshot_before_case_date(tmp_path):
    _write_team_details(
        tmp_path,
        [
            ("T1", "Division 2023", "", "", "", "", "000111", "2023-02-01"),
            ("T1", "Division 2024", "", "", "", "", "000222", "2024-06-15"),
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


def test_autofill_respects_dirty_fields(tmp_path):
    _write_team_details(
        tmp_path,
        [
            ("T2", "Division A", "Area A", "", "", "", "001000", "2023-01-01"),
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


def test_autofill_handles_invalid_case_date_with_latest_snapshot(tmp_path):
    _write_team_details(
        tmp_path,
        [
            ("T3", "Division pasada", "", "", "", "", "", "2020-01-01"),
            ("T3", "Division vigente", "", "", "", "", "", "2024-05-05"),
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
            ("T4", "Division futura", "", "", "", "", "", "2025-01-01"),
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
            ("T5", "Division", "", "", "", "", "", "2024-01-01"),
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
            ("T6", "Futuro lejano", "", "", "", "", "", "2030-01-01"),
            ("T6", "Futuro cercano", "", "", "", "", "", "2025-05-05"),
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
            ("T7", "Antiguo", "", "", "", "", "", "2020-02-02"),
            ("T7", "Reciente", "", "", "", "", "", "2024-04-04"),
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
            ("T8", "Antiguo", "", "", "", "", "", "2020-02-02"),
            ("T8", "Reciente", "", "", "", "", "", "2024-04-04"),
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
