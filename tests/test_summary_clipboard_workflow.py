import tkinter as tk

import pytest

from tests.app_factory import SummaryTableStub, build_summary_app
from tests.summary_cases import SUMMARY_CASES


@pytest.mark.parametrize("case", SUMMARY_CASES, ids=lambda case: f"workflow_{case.key}")
def test_handle_summary_paste_routes_rows_to_ingestion(monkeypatch, messagebox_spy, case):
    app = build_summary_app(monkeypatch)
    app.summary_tables[case.key] = SummaryTableStub()
    app.summary_config[case.key] = case.columns
    app.clipboard_get = lambda row=case.valid_row: "\t".join(row)

    sanitized_rows = [tuple(case.valid_row)]
    ingested_payload = {}

    def fake_transform(key, parsed_rows):
        assert key == case.key
        assert parsed_rows == [case.valid_row]
        return sanitized_rows

    def fake_ingest(section, rows, stay_on_summary=True):
        ingested_payload['section'] = section
        ingested_payload['rows'] = rows
        ingested_payload['stay'] = stay_on_summary
        return len(rows)

    app._transform_summary_clipboard_rows = fake_transform
    app.ingest_summary_rows = fake_ingest

    result = app._handle_summary_paste(case.key)

    assert result == "break"
    assert ingested_payload['section'] == case.key
    assert ingested_payload['rows'] == sanitized_rows
    assert ingested_payload['stay'] is True
    assert messagebox_spy.errors == []


@pytest.mark.parametrize("case", SUMMARY_CASES, ids=lambda case: f"workflow_invalid_{case.key}")
def test_handle_summary_paste_invalid_rows_show_error(monkeypatch, messagebox_spy, case):
    app = build_summary_app(monkeypatch)
    app.summary_tables[case.key] = SummaryTableStub()
    app.summary_config[case.key] = case.columns
    app.clipboard_get = lambda row=case.invalid_row: "\t".join(row)

    def fake_transform(_key, _rows):
        raise ValueError("Contenido inválido")

    app._transform_summary_clipboard_rows = fake_transform

    result = app._handle_summary_paste(case.key)

    assert result == "break"
    assert messagebox_spy.errors
    assert any("Contenido inválido" in (msg or "") for _title, msg in messagebox_spy.errors)


def test_handle_summary_paste_reports_clipboard_failure(monkeypatch, messagebox_spy):
    app = build_summary_app(monkeypatch)
    app.summary_tables['clientes'] = SummaryTableStub()
    app.summary_config['clientes'] = SUMMARY_CASES[0].columns

    def boom():
        raise tk.TclError("clipboard unavailable")

    app.clipboard_get = boom

    result = app._handle_summary_paste('clientes')

    assert result == "break"
    assert messagebox_spy.errors
    assert any('portapapeles' in (msg or '').lower() for _title, msg in messagebox_spy.errors)


def test_handle_summary_paste_detects_column_mismatch(monkeypatch, messagebox_spy):
    app = build_summary_app(monkeypatch)
    case = SUMMARY_CASES[0]
    app.summary_tables[case.key] = SummaryTableStub()
    app.summary_config[case.key] = case.columns
    bad_row = case.valid_row[:-1]
    app.clipboard_get = lambda: "\t".join(bad_row)

    result = app._handle_summary_paste(case.key)

    assert result == "break"
    assert messagebox_spy.errors
    assert any('columnas' in (msg or '').lower() for _title, msg in messagebox_spy.errors)


def test_handle_summary_paste_large_payload(monkeypatch, messagebox_spy):
    app = build_summary_app(monkeypatch)
    app.summary_tables['clientes'] = SummaryTableStub()
    app.summary_config['clientes'] = SUMMARY_CASES[0].columns

    row = SUMMARY_CASES[0].valid_row
    clipboard_rows = [row for _ in range(120)]
    app.clipboard_get = lambda: "\n".join("\t".join(r) for r in clipboard_rows)

    processed = {}

    def fake_transform(key, parsed_rows):
        assert len(parsed_rows) == len(clipboard_rows)
        return clipboard_rows

    def fake_ingest(section, rows, stay_on_summary=True):
        processed['section'] = section
        processed['rows'] = rows
        processed['count'] = len(rows)
        processed['stay'] = stay_on_summary
        return len(rows)

    app._transform_summary_clipboard_rows = fake_transform
    app.ingest_summary_rows = fake_ingest

    result = app._handle_summary_paste('clientes')

    assert result == "break"
    assert processed['section'] == 'clientes'
    assert processed['count'] == len(clipboard_rows)
    assert processed['stay'] is True
    assert messagebox_spy.errors == []
