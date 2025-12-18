import pytest

from settings import (ACCIONADO_OPTIONS, CRITICIDAD_LIST, FLAG_CLIENTE_LIST,
                      FLAG_COLABORADOR_LIST, TIPO_FALTA_LIST, TIPO_ID_LIST,
                      TIPO_SANCION_LIST)
from tests.app_factory import SummaryTableStub, build_summary_app
from tests.stubs import NormFrameStub, RiskFrameStub
from tests.summary_cases import SUMMARY_CASES, build_columns


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


def test_handle_summary_paste_requires_client_contact_info(monkeypatch, messagebox_spy):
    app = build_summary_app(monkeypatch)
    app.summary_tables["clientes"] = SummaryTableStub()
    app.summary_config["clientes"] = build_columns(7)
    empty_contact_row = [
        "12345678",
        TIPO_ID_LIST[0],
        FLAG_CLIENTE_LIST[0],
        "",
        "",
        "Av. Principal 123",
        ACCIONADO_OPTIONS[0],
    ]
    app.clipboard_get = lambda row=empty_contact_row: "\t".join(row)

    result = app._handle_summary_paste("clientes")

    assert result == "break"
    assert not app.client_frames
    assert messagebox_spy.errors
    assert any(
        "Debe ingresar los teléfonos del cliente." in (message or "")
        for _title, message in messagebox_spy.errors
    )


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

    team_row = [
        "T67890",
        "Ana",
        "López",
        FLAG_COLABORADOR_LIST[0],
        "Division B",
        "Área Comercial",
        "Servicio A",
        "Puesto B",
        "2023-01-01",
        "2023-02-01",
        "Agencia Sur",
        "123456",
        TIPO_FALTA_LIST[0],
        TIPO_SANCION_LIST[0],
    ]
    team_rows = app._transform_clipboard_colaboradores([team_row])
    assert app.ingest_summary_rows("colaboradores", team_rows) == 1
    assert [frame.id_var.get() for frame in app.team_frames] == ["T67890"]
    assert app.team_frames[0].flag_var.get() == FLAG_COLABORADOR_LIST[0]
    assert app.team_frames[0].tipo_falta_var.get() == TIPO_FALTA_LIST[0]

    product_row = ["1234567890123", "12345678", "credito personal", "2500.50"]
    product_rows = app._transform_clipboard_productos([product_row])
    assert len(product_rows[0]) == len(app.IMPORT_CONFIG["productos"]["expected_headers"])
    assert product_rows[0][2] == "Crédito personal"
    assert product_rows[0][10] == "2500.50"
    assert app.ingest_summary_rows("productos", product_rows) == 1
    assert [frame.id_var.get() for frame in app.product_frames] == ["1234567890123"]
    assert app.product_frames[0].populated_rows[-1]["tipo_producto"] == "Crédito personal"

    risk_row = ["rsk-000001", "2024-0001", "Líder", "Descripción", CRITICIDAD_LIST[1], "100.00", "Plan"]
    risk_rows = app._transform_clipboard_riesgos([risk_row])
    assert risk_rows[0][0] == "RSK-000001"
    assert app.ingest_summary_rows("riesgos", risk_rows) == 1
    assert [frame.id_var.get() for frame in app.risk_frames] == ["RSK-000001"]
    assert app.risk_frames[0].criticidad_var.get() == CRITICIDAD_LIST[1]
    assert app.risk_frames[0].exposicion_var.get() == "100.00"
    assert getattr(app.risk_frames[0], "case_id_var", None).get() == "2024-0001"

    norm_row = ["2024.001.01.01", "2024-0001", "Nueva norma", "2024-01-01", "Art. 2", "Detalle"]
    norm_rows = app._transform_clipboard_normas([norm_row])
    assert app.ingest_summary_rows("normas", norm_rows) == 1
    assert [frame.id_var.get() for frame in app.norm_frames] == ["2024.001.01.01"]
    assert app.norm_frames[0].descripcion_var.get() == "Nueva norma"
    assert app.norm_frames[0].acapite_var.get() == "Art. 2"
    assert app.norm_frames[0]._get_detalle_text() == "Detalle"
    assert getattr(app.norm_frames[0], "case_id_var", None).get() == "2024-0001"


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
            ["RSK-000010", "2024-0001", "Líder", "Descripción", CRITICIDAD_LIST[0], "50.00", "Plan"],
            "Riesgos duplicados",
            "Riesgo duplicado RSK-000010",
        ),
        (
            "normas",
            "norm_frames",
            ["2024.001.02.01", "2024-0001", "Descripción", "2024-01-01", "Art. 1", "Detalle"],
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
