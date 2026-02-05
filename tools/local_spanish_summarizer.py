"""Utilidad CLI para resumir texto en español con un modelo local de Hugging Face.

Este script carga el modelo ``mrm8488/bert2bert_shared-spanish-finetuned-summarization``
desde el directorio local ``external drive`` sin descargas de Internet.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

MODEL_FOLDER_NAME = "mrm8488/bert2bert_shared-spanish-finetuned-summarization"
SUMMARY_PROMPT_PREFIX = (
    "Resume el siguiente texto en español con precisión factual, "
    "sin inventar datos y con lenguaje claro:\n\n"
)


class LocalSpanishSummarizer:
    """Resumen en español usando un modelo local Seq2Seq.

    Attributes:
        model_path: Ruta absoluta al directorio del modelo local.
        summarizer: Pipeline de Hugging Face para tareas de resumen.
    """

    def __init__(self, model_path: Path) -> None:
        """Inicializa el tokenizador, modelo y pipeline de resumen.

        Args:
            model_path: Ruta al directorio local del modelo.
        """
        self.model_path = model_path
        tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path), local_files_only=True)
        device = 0 if torch.cuda.is_available() else -1
        self.summarizer = pipeline(
            task="summarization",
            model=model,
            tokenizer=tokenizer,
            device=device,
        )

    def summarize_spanish_text(
        self,
        text: str,
        max_length: int = 150,
        min_length: int = 50,
    ) -> str:
        """Genera un resumen robusto para un texto en español.

        Args:
            text: Texto de entrada a resumir.
            max_length: Longitud máxima del resumen generado.
            min_length: Longitud mínima del resumen generado.

        Returns:
            Resumen generado por el modelo.

        Raises:
            ValueError: Si el texto está vacío o si longitudes son inválidas.
            RuntimeError: Si falla la inferencia por problemas de ejecución.
        """
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("El texto de entrada no puede estar vacío.")
        if min_length < 1 or max_length < 1:
            raise ValueError("max_length y min_length deben ser mayores a cero.")
        if min_length > max_length:
            raise ValueError("min_length no puede ser mayor que max_length.")

        prompt_text = f"{SUMMARY_PROMPT_PREFIX}{normalized_text}"

        try:
            result: list[dict[str, Any]] = self.summarizer(
                prompt_text,
                max_length=max_length,
                min_length=min_length,
                truncation=True,
                clean_up_tokenization_spaces=True,
                do_sample=False,
                num_beams=4,
            )
            return str(result[0]["summary_text"]).strip()
        except (RuntimeError, ValueError) as error:
            raise type(error)(f"Error durante la generación del resumen: {error}") from error


def resolve_external_drive_model_path() -> Path:
    """Resuelve y valida la ruta absoluta al modelo en ``external drive``.

    Returns:
        Ruta absoluta al modelo local.

    Raises:
        FileNotFoundError: Si no existe la carpeta ``external drive`` o el modelo.
    """
    repo_root = Path(__file__).resolve().parents[1]
    external_drive_path = (repo_root / "external drive").resolve()

    if not external_drive_path.exists() or not external_drive_path.is_dir():
        raise FileNotFoundError(
            "No se encontró la carpeta local 'external drive' en: "
            f"{external_drive_path}"
        )

    candidate_paths = [
        (external_drive_path / MODEL_FOLDER_NAME).resolve(),
        external_drive_path.resolve(),
    ]

    for candidate in candidate_paths:
        if candidate.exists() and candidate.is_dir():
            return candidate

    raise FileNotFoundError(
        "No se encontró el directorio del modelo en 'external drive'. "
        f"Se intentó con: {[str(path) for path in candidate_paths]}"
    )


def parse_args() -> argparse.Namespace:
    """Construye argumentos de línea de comandos para el resumidor."""
    parser = argparse.ArgumentParser(
        description="Resumen local en español con modelo Hugging Face sin descargas."
    )
    parser.add_argument(
        "--input_file",
        required=True,
        type=Path,
        help="Ruta al archivo de texto UTF-8 a resumir.",
    )
    parser.add_argument(
        "--max_len",
        type=int,
        default=150,
        help="Longitud máxima del resumen.",
    )
    parser.add_argument(
        "--min_len",
        type=int,
        default=50,
        help="Longitud mínima del resumen.",
    )
    return parser.parse_args()


def main() -> None:
    """Punto de entrada CLI del resumidor local."""
    args = parse_args()
    input_path: Path = args.input_file.resolve()
    text = input_path.read_text(encoding="utf-8")

    model_path = resolve_external_drive_model_path()
    summarizer = LocalSpanishSummarizer(model_path)
    summary = summarizer.summarize_spanish_text(
        text=text,
        max_length=args.max_len,
        min_length=args.min_len,
    )
    print(summary)


if __name__ == "__main__":
    main()
