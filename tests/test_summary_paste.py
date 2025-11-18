import pytest

from settings import (ACCIONADO_OPTIONS, CRITICIDAD_LIST, FLAG_CLIENTE_LIST,
                      TIPO_ID_LIST, TIPO_SANCION_LIST)
from tests.app_factory import SummaryTableStub, build_summary_app
from tests.stubs import NormFrameStub, RiskFrameStub
from tests.summary_cases import SUMMARY_CASES


@pytest.mark.parametrize("case", SUMMARY_CASES, ids=lambda case: case.key)
def test_handle_summary_paste_accepts_valid_rows(monkeypatch, messagebox_spy, case):
    app = build_summary_app(monkeypatch)
    app.summary_tables[case.key] = SummaryTableStub()
    app.summary_config[case.key] = case.columns
    app.clipboard_get = lambda row=case.valid_row: "\t".join(row)

    result = app._handle_summary_paste(case.key)

    assert result == "break"
    assert case.state_getter(app) == case.expected_state
    assert messagebox_spy.errors == []


@pytest.mark.parametrize("case", SUMMARY_CASES, ids=lambda case: f"invalid_{case.key}")
def test_handle_summary_paste_rejects_invalid_rows(monkeypatch, messagebox_spy, case):
    app = build_summary_app(monkeypatch)
    app.summary_tables[case.key] = SummaryTableStub()
    app.summary_config[case.key] = case.columns
    app.clipboard_get = lambda row=case.invalid_row: "\t".join(row)

    result = app._handle_summary_paste(case.key)

    assert result == "break"
    assert messagebox_spy.errors
    assert any(
        case.error_fragment.lower() in (message or "").lower()
        for _title, message in messagebox_spy.errors
    )
    assert case.state_getter(app) == []


def test_ingest_summary_rows_create_frames_with_normalized_values(monkeypatch, messagebox_spy):
    app = build_summary_app(monkeypatch)

    client_row = [
        "12345678",
        TIPO_ID_LIST[0],
        FLAG_CLIENTE_LIST[0],
        "+51999888777",
        "cli@example.com",
        "Av. Principal 123",
        ACCIONADO_OPTIONS[0],
    ]
    client_rows = app._transform_clipboard_clients([client_row])
    assert app.ingest_summary_rows("clientes", client_rows) == 1
    assert [frame.id_var.get() for frame in app.client_frames] == ["12345678"]

    team_row = ["T67890", "Division B", "Área Comercial", TIPO_SANCION_LIST[0]]
    team_rows = app._transform_clipboard_colaboradores([team_row])
    assert app.ingest_summary_rows("colaboradores", team_rows) == 1
    assert [frame.id_var.get() for frame in app.team_frames] == ["T67890"]

    product_row = ["1234567890123", "12345678", "credito personal", "2500.50"]
    product_rows = app._transform_clipboard_productos([product_row])
    assert product_rows[0][2] == "Crédito personal"
    assert product_rows[0][3] == "2500.50"
    assert app.ingest_summary_rows("productos", product_rows) == 1
    assert [frame.id_var.get() for frame in app.product_frames] == ["1234567890123"]
    assert app.product_frames[0].populated_rows[-1]["tipo_producto"] == "Crédito personal"

    risk_row = ["rsk-000001", "Líder", CRITICIDAD_LIST[1], "100.00"]
    risk_rows = app._transform_clipboard_riesgos([risk_row])
    assert risk_rows[0][0] == "RSK-000001"
    assert app.ingest_summary_rows("riesgos", risk_rows) == 1
    assert [frame.id_var.get() for frame in app.risk_frames] == ["RSK-000001"]
    assert app.risk_frames[0].criticidad_var.get() == CRITICIDAD_LIST[1]
    assert app.risk_frames[0].exposicion_var.get() == "100.00"

    norm_row = ["2024.001.01.01", "Nueva norma", "2024-01-01"]
    norm_rows = app._transform_clipboard_normas([norm_row])
    assert app.ingest_summary_rows("normas", norm_rows) == 1
    assert [frame.id_var.get() for frame in app.norm_frames] == ["2024.001.01.01"]
    assert app.norm_frames[0].descripcion_var.get() == "Nueva norma"


@pytest.mark.parametrize(
    "transform_name, rows, expected_message",
    [
        (
            "_transform_clipboard_clients",
            [["12345678", "INVALID", "", "", "", "", ""]],
            "Cliente fila 1: el tipo de ID 'INVALID' no está en el catálogo CM. Corrige la hoja de Excel antes de volver a intentarlo.",
        ),
        (
            "_transform_clipboard_productos",
            [["1234567890123", "12345678", "Crédito personal", "abc"]],
            "Producto fila 1: el monto investigado debe ser un número válido.",
        ),
    ],
)
def test_transform_clipboard_rows_invalid_inputs(monkeypatch, messagebox_spy, transform_name, rows, expected_message):
    app = build_summary_app(monkeypatch)
    transform = getattr(app, transform_name)
    with pytest.raises(ValueError) as excinfo:
        transform(rows)
    assert str(excinfo.value) == expected_message


@pytest.mark.parametrize(
    "section, frame_attr, row, warning_title, log_fragment",
    [
        (
            "riesgos",
            "risk_frames",
            ["RSK-000010", "Líder", CRITICIDAD_LIST[0], "50.00"],
            "Riesgos duplicados",
            "Riesgo duplicado RSK-000010",
        ),
        (
            "normas",
            "norm_frames",
            ["2024.001.02.01", "Descripción", "2024-01-01"],
            "Normas duplicadas",
            "Norma duplicada 2024.001.02.01",
        ),
    ],
)
def test_ingest_summary_rows_warn_on_duplicates(monkeypatch, messagebox_spy, section, frame_attr, row, warning_title, log_fragment):
    app = build_summary_app(monkeypatch)
    existing_frame = RiskFrameStub() if section == "riesgos" else NormFrameStub()
    existing_frame.id_var.set(row[0])
    getattr(app, frame_attr).append(existing_frame)

    transform = getattr(app, f"_transform_clipboard_{section}")
    sanitized_rows = transform([row])
    processed = app.ingest_summary_rows(section, sanitized_rows)

    assert processed == 0
    assert len(getattr(app, frame_attr)) == 1
    assert messagebox_spy.warnings
    title, message = messagebox_spy.warnings[-1]
    assert title == warning_title
    assert row[0] in message
    assert any(log_fragment in entry.get("mensaje", "") for entry in app.logs)
