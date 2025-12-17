from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pytest

from report.carta_inmediatez import CartaInmediatezError, CartaInmediatezGenerator


def _stub_renderer(_template_path: Path, output_path: Path, placeholders: dict[str, str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(placeholders.get("NUMERO_CARTA", ""))


def _write_history(path: Path, rows: list[list[str]]) -> None:
    headers = [
        "numero_caso",
        "fecha_generacion",
        "mes",
        "investigador_principal",
        "matricula_investigador",
        "matricula_team_member",
        "Tipo",
        "codigo_agencia",
        "agencia",
        "Numero_de_Carta",
        "Tipo_entrevista",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)


def test_carta_generator_appends_history_and_files(tmp_path: Path) -> None:
    year = datetime.now().year
    exports_dir = tmp_path / "exports"
    external_dir = tmp_path / "external"
    previous_row = [
        "2024-0001",
        f"{year}-01-01",
        "01",
        "Investigador",
        "INV001",
        "TM001",
        "Sede",
        "000001",
        "Agencia Central",
        f"002-{year}",
        "Involucrado",
    ]
    _write_history(exports_dir / "h_cartas_inmediatez.csv", [previous_row])
    generator = CartaInmediatezGenerator(exports_dir, external_dir, renderer=_stub_renderer, docx_available=True)

    case_payload = {
        "caso": {
            "id_caso": f"{year}-0101",
            "investigador": {"matricula": "INV999", "nombre": "Investigador X"},
        }
    }
    members = [
        {
            "id_colaborador": "TM010",
            "nombres": "Ana",
            "apellidos": "Pérez",
            "puesto": "Analista",
            "nombre_agencia": "Agencia Central",
            "codigo_agencia": "000123",
            "flag": "Involucrado",
            "division": "Division Comercial",
        },
        {
            "id_colaborador": "TM011",
            "nombres": "Luis",
            "apellidos": "Diaz",
            "puesto": "Gestor",
            "nombre_agencia": "Agencia Central",
            "codigo_agencia": "000123",
            "flag": "Relacionado",
            "division": "Sede Norte",
        },
    ]

    result = generator.generate_cartas(case_payload, members)

    assert len(result["files"]) == 2
    main_history = exports_dir / "cartas_inmediatez.csv"
    history_rows = list(csv.DictReader(main_history.open(encoding="utf-8")))
    assert {row["Numero_de_Carta"] for row in history_rows} == {f"003-{year}", f"004-{year}"}
    external_history = external_dir / "h_cartas_inmediatez.csv"
    assert external_history.exists()
    assert all(path.exists() for path in result["files"])


def test_carta_generator_detects_duplicate(tmp_path: Path) -> None:
    year = datetime.now().year
    exports_dir = tmp_path / "exports"
    case_id = f"{year}-0101"
    duplicate_row = [
        case_id,
        f"{year}-02-02",
        "02",
        "Investigador",
        "INV001",
        "TM010",
        "Sede",
        "000001",
        "Agencia Central",
        f"001-{year}",
        "Involucrado",
    ]
    _write_history(exports_dir / "cartas_inmediatez.csv", [duplicate_row])
    generator = CartaInmediatezGenerator(exports_dir, None, renderer=_stub_renderer, docx_available=True)

    case_payload = {
        "caso": {"id_caso": case_id, "investigador": {"matricula": "INV999", "nombre": "Investigador X"}}
    }
    members = [
        {
            "id_colaborador": "TM010",
            "nombres": "Ana",
            "apellidos": "Pérez",
            "puesto": "Analista",
            "nombre_agencia": "Agencia Central",
            "codigo_agencia": "000123",
            "flag": "Involucrado",
            "division": "Division Comercial",
        }
    ]

    with pytest.raises(CartaInmediatezError):
        generator.generate_cartas(case_payload, members)
