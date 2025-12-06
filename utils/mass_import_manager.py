from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass
class MassImportSummary:
    """Resultado consolidado de una importación masiva."""

    import_type: str
    file_path: Path
    successes: int = 0
    updates: int = 0
    duplicates: int = 0
    errors: int = 0
    warnings: list[str] = field(default_factory=list)
    log_path: Path | None = None

    @property
    def has_changes(self) -> bool:
        return (self.successes + self.updates) > 0

    @property
    def summary_lines(self) -> list[str]:
        lines = [
            f"Importación completada de {self.import_type}:",
            f"{self.successes} registros nuevos",
            f"{self.updates} registros actualizados",
            f"{self.duplicates} duplicados omitidos",
            f"{self.errors} filas con errores",
        ]
        if self.warnings:
            lines.append("")
            lines.append("Advertencias:")
            lines.extend(f"- {warning}" for warning in self.warnings)
        if self.log_path:
            lines.append("")
            lines.append(f"Registro detallado: {self.log_path}")
        return lines

    @property
    def summary_text(self) -> str:
        return "\n".join(self.summary_lines)


class MassImportManager:
    """Gestiona el resumen y registro de importaciones masivas."""

    def __init__(self, log_directory: Path | str):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)

    def run_import(
        self,
        file_path: str | Path,
        import_type: str,
        *,
        successes: int = 0,
        updates: int = 0,
        duplicates: int = 0,
        errors: int = 0,
        warnings: Iterable[str] | None = None,
    ) -> MassImportSummary:
        """Genera el resumen consolidado y escribe el log correspondiente."""

        normalized_path = Path(file_path)
        warning_list = [w for w in (warnings or []) if w]
        summary = MassImportSummary(
            import_type=import_type,
            file_path=normalized_path,
            successes=successes,
            updates=updates,
            duplicates=duplicates,
            errors=errors,
            warnings=warning_list,
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = self.log_directory / f"{timestamp}_{import_type}.log"
        log_lines = [
            f"Fecha: {datetime.now().isoformat(timespec='seconds')}",
            f"Archivo: {normalized_path}",
            f"Tipo de importación: {import_type}",
            "", "Resumen:", *summary.summary_lines,
        ]
        log_path.write_text("\n".join(log_lines), encoding="utf-8")
        summary.log_path = log_path
        return summary
