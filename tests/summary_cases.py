"""Casos representativos para probar el pegado del resumen."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

from settings import (ACCIONADO_OPTIONS, CRITICIDAD_LIST, FLAG_CLIENTE_LIST,
                      TIPO_ID_LIST, TIPO_SANCION_LIST)

if TYPE_CHECKING:
    from app import FraudCaseApp


def build_columns(count):
    return [(f"c{i}", f"Col {i}") for i in range(count)]


def collect_ids(frames):
    return [frame.id_var.get() for frame in frames if frame.id_var.get()]


def collect_claim_ids(app: 'FraudCaseApp'):
    claim_ids = []
    for frame in app.product_frames:
        for claim in frame.claims:
            if claim.data:
                claim_ids.append(claim.data.get('id_reclamo'))
    return claim_ids


def collect_involvements(app: 'FraudCaseApp'):
    values = []
    for frame in app.product_frames:
        product_id = frame.id_var.get()
        if not product_id:
            continue
        for inv in frame.involvements:
            team = inv.team_var.get()
            amount = inv.monto_var.get()
            if team:
                values.append((product_id, team, amount))
    return values


@dataclass
class SummaryPasteCase:
    key: str
    columns: list[tuple[str, str]]
    valid_row: list[str]
    invalid_row: list[str]
    state_getter: Callable[['FraudCaseApp'], list]
    expected_state: list
    error_fragment: str


SUMMARY_CASES = [
    SummaryPasteCase(
        key="clientes",
        columns=build_columns(7),
        valid_row=[
            "12345678",
            TIPO_ID_LIST[0],
            FLAG_CLIENTE_LIST[0],
            "999888777",
            "cli@example.com",
            "Av. Principal 123",
            ACCIONADO_OPTIONS[0],
        ],
        invalid_row=[
            "12345678",
            TIPO_ID_LIST[0],
            FLAG_CLIENTE_LIST[0],
            "999888777",
            "correo-invalido",
            "Av. Principal 123",
            ACCIONADO_OPTIONS[0],
        ],
        state_getter=lambda app: collect_ids(app.client_frames),
        expected_state=["12345678"],
        error_fragment="correo",
    ),
    SummaryPasteCase(
        key="colaboradores",
        columns=build_columns(10),
        valid_row=[
            "T67890",
            "Ana",
            "López",
            "Division B",
            "Área Comercial",
            "Servicio A",
            "Puesto B",
            TIPO_SANCION_LIST[0],
            "2023-01-01",
            "2023-02-01",
        ],
        invalid_row=[
            "bad",
            "",
            "",
            "Division B",
            "Área Comercial",
            "Servicio A",
            "Puesto B",
            "Inválida",
            "2023-01-01",
            "2023-02-01",
        ],
        state_getter=lambda app: collect_ids(app.team_frames),
        expected_state=["T67890"],
        error_fragment="colaborador",
    ),
    SummaryPasteCase(
        key="productos",
        columns=build_columns(4),
        valid_row=["1234567890123", "12345678", "Crédito personal", "1500.00"],
        invalid_row=["1234567890123", "12345678", "Crédito personal", "abc"],
        state_getter=lambda app: collect_ids(app.product_frames),
        expected_state=["1234567890123"],
        error_fragment="monto",
    ),
    SummaryPasteCase(
        key="reclamos",
        columns=build_columns(4),
        valid_row=["C12345678", "1234567890123", "Analítica", "4300000000"],
        invalid_row=["123", "", "", "000"],
        state_getter=collect_claim_ids,
        expected_state=["C12345678"],
        error_fragment="reclamo",
    ),
    SummaryPasteCase(
        key="riesgos",
        columns=build_columns(4),
        valid_row=["RSK-000001", "Líder", CRITICIDAD_LIST[0], "100.00"],
        invalid_row=["RSK-000001", "Líder", "INVÁLIDO", "abc"],
        state_getter=lambda app: collect_ids(app.risk_frames),
        expected_state=["RSK-000001"],
        error_fragment="criticidad",
    ),
    SummaryPasteCase(
        key="normas",
        columns=build_columns(3),
        valid_row=["2024.001.01.01", "Descripción", "2024-01-01"],
        invalid_row=["2024.001.01.01", "Descripción", "2024/01/01"],
        state_getter=lambda app: collect_ids(app.norm_frames),
        expected_state=["2024.001.01.01"],
        error_fragment="fecha",
    ),
    SummaryPasteCase(
        key="involucramientos",
        columns=build_columns(3),
        valid_row=["1234567890123", "T22222", "250.75"],
        invalid_row=["1234567890123", "T22222", "10.123"],
        state_getter=collect_involvements,
        expected_state=[("1234567890123", "T22222", "250.75")],
        error_fragment="dos decimales",
    ),
]
