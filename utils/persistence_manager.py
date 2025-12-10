"""Persistence helpers for background JSON save/load operations."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping

from utils.background_worker import run_guarded_task


SchemaValidator = Callable[[Mapping[str, object]], Mapping[str, object]]

CURRENT_SCHEMA_VERSION = "1.0"
SUPPORTED_SCHEMA_VERSIONS = {CURRENT_SCHEMA_VERSION}


@dataclass
class PersistenceResult:
    """Resultado de una operación de persistencia."""

    path: Path
    payload: Mapping[str, object]
    failed: list[tuple[Path, BaseException]] = field(default_factory=list)


class PersistenceError(Exception):
    """Error producido al intentar cargar un archivo de respaldo."""

    def __init__(self, message: str, failures: list[tuple[Path, BaseException]]):
        super().__init__(message)
        self.failures = failures


class PersistenceManager:
    """Centraliza las operaciones de guardado y carga en segundo plano."""

    def __init__(
        self,
        root,
        schema_validator: SchemaValidator | None = None,
        *,
        task_category: str = "persistence",
    ) -> None:
        self.root = root
        self.schema_validator = schema_validator or validate_schema_payload
        self.task_category = task_category

    def save(
        self,
        path: Path,
        payload: Mapping[str, object],
        *,
        on_success: Callable[[PersistenceResult], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
    ):
        """Persiste un ``payload`` JSON usando escritura atómica."""

        def _task() -> PersistenceResult:
            return self._write_atomic(path, payload)

        return self._run_in_background(_task, on_success, on_error)

    def load(
        self,
        path: Path,
        *,
        on_success: Callable[[PersistenceResult], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
    ):
        """Carga un archivo JSON validando el esquema."""

        def _task() -> PersistenceResult:
            return self._load_payload(path)

        return self._run_in_background(_task, on_success, on_error)

    def load_first_valid(
        self,
        paths: Iterable[Path],
        *,
        on_success: Callable[[PersistenceResult], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
    ):
        """Intenta cargar la primera ruta válida del iterable en segundo plano."""

        def _task() -> PersistenceResult:
            failures: list[tuple[Path, BaseException]] = []
            for path in paths:
                normalized = Path(path)
                try:
                    result = self._load_payload(normalized)
                    result.failed = list(failures)
                    return result
                except BaseException as exc:  # pragma: no cover - defensive path
                    failures.append((normalized, exc))
                    continue
            raise PersistenceError(
                "No se pudo cargar ningún archivo de respaldo válido.", failures
            )

        return self._run_in_background(_task, on_success, on_error)

    # ------------------------------------------------------------------
    # Implementación interna

    def _run_in_background(
        self,
        task_func: Callable[[], PersistenceResult],
        on_success: Callable[[PersistenceResult], None] | None,
        on_error: Callable[[BaseException], None] | None,
    ):
        if self.root is not None:
            return run_guarded_task(
                task_func,
                on_success,
                on_error,
                self.root,
                category=self.task_category,
            )
        try:
            result = task_func()
        except BaseException as exc:  # pragma: no cover - fallback cuando no hay root
            if on_error:
                on_error(exc)
            return None
        if on_success:
            on_success(result)
        return None

    def _write_atomic(self, path: Path, payload: Mapping[str, object]) -> PersistenceResult:
        self._validate_payload(payload)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target.with_name(f"{target.name}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, target)
        return PersistenceResult(path=target, payload=payload)

    def _load_payload(self, path: Path) -> PersistenceResult:
        normalized = Path(path)
        try:
            with normalized.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except json.JSONDecodeError as exc:  # pragma: no cover - contextualiza el error
            raise ValueError(f"JSON inválido en {normalized}: {exc}") from exc
        try:
            self._validate_payload(payload)
        except Exception as exc:  # pragma: no cover - asegura rastreo del archivo
            raise ValueError(f"{normalized}: {exc}") from exc
        return PersistenceResult(path=normalized, payload=payload)

    def _validate_payload(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        if self.schema_validator:
            return self.schema_validator(payload)
        if not isinstance(payload, Mapping):
            raise ValueError("El archivo debe contener un objeto JSON válido.")
        return payload


def validate_schema_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
    """Validates the required structure and version metadata for persistence files."""

    if not isinstance(payload, Mapping):
        raise ValueError("El archivo debe contener un objeto JSON válido.")

    version = payload.get("schema_version")
    if version is None:
        raise ValueError("Falta el campo requerido 'schema_version'.")
    if str(version) not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Versión de esquema incompatible: {version}; se espera {CURRENT_SCHEMA_VERSION}."
        )

    if "dataset" not in payload:
        raise ValueError("Falta la sección obligatoria 'dataset'.")
    dataset_payload = payload.get("dataset")
    if not isinstance(dataset_payload, Mapping):
        raise ValueError("La sección 'dataset' debe ser un objeto JSON.")

    form_state = payload.get("form_state")
    if form_state is not None and not isinstance(form_state, Mapping):
        raise ValueError("La sección 'form_state' debe ser un objeto JSON.")

    return payload
