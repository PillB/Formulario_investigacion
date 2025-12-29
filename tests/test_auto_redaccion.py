from report_builder import CaseData
from utils import auto_redaccion


def test_postprocess_summary_enforces_length_and_newlines():
    raw = "Linea 1\nLinea 2\n" + ("X" * 200)
    cleaned = auto_redaccion.postprocess_summary(raw, max_chars=150)
    assert "\n" not in cleaned
    assert len(cleaned) <= 150


def test_strip_pii_removes_basic_identifiers():
    raw = (
        "Caso 2025-0001 con DNI 12345678 y RUC 12345678901. "
        "Id reclamo C12345678, matricula TM-0001 y placa ABC-123."
    )
    cleaned = auto_redaccion.strip_pii(raw)
    assert "2025-0001" not in cleaned
    assert "12345678" not in cleaned
    assert "12345678901" not in cleaned
    assert "C12345678" not in cleaned
    assert "TM-0001" not in cleaned
    assert "ABC-123" not in cleaned


def test_auto_redact_returns_placeholder_when_llm_unavailable(monkeypatch):
    case_data = CaseData.from_mapping({"caso": {"id_caso": "2025-0001"}})
    monkeypatch.setattr(auto_redaccion, "TRANSFORMERS_AVAILABLE", False)
    result = auto_redaccion.auto_redact_comment(
        case_data.as_dict(),
        "Narrativa",
        target_chars=150,
        max_new_tokens=80,
        label="breve",
    )
    assert result.text == auto_redaccion.PLACEHOLDER
    assert result.error
