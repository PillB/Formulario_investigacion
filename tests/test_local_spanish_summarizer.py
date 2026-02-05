"""Pruebas unitarias para el resumidor local en español."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import local_spanish_summarizer as summarizer_module


class DummyPipeline:
    """Pipeline simulado para validar parámetros de inferencia."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, text: str, **kwargs: object) -> list[dict[str, str]]:
        self.calls.append({"text": text, **kwargs})
        return [{"summary_text": "  Resumen generado  "}]


def test_resolve_external_drive_model_path_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Debe lanzar FileNotFoundError cuando no existe external drive."""

    fake_script = tmp_path / "tools" / "local_spanish_summarizer.py"
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text("", encoding="utf-8")
    monkeypatch.setattr(summarizer_module, "__file__", str(fake_script))

    with pytest.raises(FileNotFoundError):
        summarizer_module.resolve_external_drive_model_path()


def test_summarize_spanish_text_validates_and_calls_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valida limpieza, prompt robusto y parámetros de generación."""
    dummy = DummyPipeline()

    monkeypatch.setattr(
        summarizer_module.AutoTokenizer,
        "from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        summarizer_module.AutoModelForSeq2SeqLM,
        "from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(summarizer_module, "pipeline", lambda *args, **kwargs: dummy)
    monkeypatch.setattr(summarizer_module.torch.cuda, "is_available", lambda: False)

    summarizer = summarizer_module.LocalSpanishSummarizer(Path("/tmp/model"))
    result = summarizer.summarize_spanish_text(" Texto largo para resumir. ", 120, 40)

    assert result == "Resumen generado"
    assert len(dummy.calls) == 1
    call = dummy.calls[0]
    assert "Resume el siguiente texto" in str(call["text"])
    assert call["truncation"] is True
    assert call["clean_up_tokenization_spaces"] is True
    assert call["max_length"] == 120
    assert call["min_length"] == 40


@pytest.mark.parametrize(
    ("text", "max_len", "min_len"),
    [
        ("   ", 150, 50),
        ("texto", 0, 1),
        ("texto", 10, 20),
    ],
)
def test_summarize_spanish_text_rejects_invalid_inputs(
    monkeypatch: pytest.MonkeyPatch,
    text: str,
    max_len: int,
    min_len: int,
) -> None:
    """Rechaza entradas inválidas antes de invocar el modelo."""
    dummy = DummyPipeline()

    monkeypatch.setattr(
        summarizer_module.AutoTokenizer,
        "from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        summarizer_module.AutoModelForSeq2SeqLM,
        "from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(summarizer_module, "pipeline", lambda *args, **kwargs: dummy)
    monkeypatch.setattr(summarizer_module.torch.cuda, "is_available", lambda: False)

    summarizer = summarizer_module.LocalSpanishSummarizer(Path("/tmp/model"))

    with pytest.raises(ValueError):
        summarizer.summarize_spanish_text(text, max_len, min_len)


@pytest.mark.parametrize("exc_type", [RuntimeError, ValueError])
def test_summarize_spanish_text_wraps_inference_errors(
    monkeypatch: pytest.MonkeyPatch,
    exc_type: type[Exception],
) -> None:
    """Propaga RuntimeError/ValueError de inferencia con mensaje contextual."""

    class FailingPipeline:
        def __call__(self, *_args: object, **_kwargs: object) -> list[dict[str, str]]:
            raise exc_type("fallo interno")

    monkeypatch.setattr(
        summarizer_module.AutoTokenizer,
        "from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        summarizer_module.AutoModelForSeq2SeqLM,
        "from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        summarizer_module,
        "pipeline",
        lambda *args, **kwargs: FailingPipeline(),
    )
    monkeypatch.setattr(summarizer_module.torch.cuda, "is_available", lambda: False)

    summarizer = summarizer_module.LocalSpanishSummarizer(Path("/tmp/model"))

    with pytest.raises(exc_type, match="Error durante la generación del resumen"):
        summarizer.summarize_spanish_text("texto válido")


def test_summarize_spanish_text_retries_when_output_is_degenerate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reintenta cuando la salida tiene patrones repetitivos no útiles."""

    class DegenerateThenGoodPipeline:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, _text: str, **_kwargs: object) -> list[dict[str, str]]:
            self.calls += 1
            if self.calls == 1:
                return [{"summary_text": "fraude fraude fraude fraude fraude fraude"}]
            return [{"summary_text": "Resumen útil con hallazgo y recomendación concreta."}]

    pipe = DegenerateThenGoodPipeline()

    monkeypatch.setattr(
        summarizer_module.AutoTokenizer,
        "from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        summarizer_module.AutoModelForSeq2SeqLM,
        "from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(summarizer_module, "pipeline", lambda *args, **kwargs: pipe)
    monkeypatch.setattr(summarizer_module.torch.cuda, "is_available", lambda: False)

    summarizer = summarizer_module.LocalSpanishSummarizer(Path("/tmp/model"))
    result = summarizer.summarize_spanish_text("Texto base")

    assert "Resumen útil" in result
    assert pipe.calls >= 2
