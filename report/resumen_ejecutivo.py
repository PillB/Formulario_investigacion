from __future__ import annotations

from pathlib import Path
from typing import Mapping

from report.alerta_temprana_content import ExecutiveSummary, build_executive_summary
from report_builder import CaseData, build_report_filename
from validators import sanitize_rich_text


def build_resumen_ejecutivo_filename(
    tipo_informe: str | None,
    case_id: str | None,
    extension: str = "md",
) -> str:
    safe_name = build_report_filename(tipo_informe, case_id, extension)
    return safe_name.replace("Informe_", "Resumen_Ejecutivo_")


def _render_section(title: str, body: str) -> str:
    return f"## {title}\n\n{body.strip()}\n"


def _render_bullets(lines: list[str]) -> str:
    if not lines:
        return "- N/A"
    return "\n".join(f"- {sanitize_rich_text(line, max_chars=260)}" for line in lines)


def _render_summary(summary: ExecutiveSummary, case_id: str) -> str:
    return "\n".join(
        [
            "# Resumen Ejecutivo",
            "",
            f"**Caso:** {case_id or 'N/A'}",
            "",
            _render_section("Mensaje clave", sanitize_rich_text(summary.headline, max_chars=400)),
            _render_section("Puntos de soporte (3-5)", _render_bullets(summary.supporting_points)),
            _render_section("Evidencia / trazabilidad", _render_bullets(summary.evidence)),
        ]
    ).strip() + "\n"


def build_resumen_ejecutivo_md(
    data: CaseData | Mapping[str, object],
    output_path: Path,
) -> Path:
    dataset = data if isinstance(data, CaseData) else CaseData.from_mapping(data or {})
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    case = dataset.get("caso", {}) if isinstance(dataset, Mapping) else {}
    case_id = str(case.get("id_caso") or "").strip()
    summary = build_executive_summary(dataset)
    content = _render_summary(summary, case_id)
    output_path.write_text(content, encoding="utf-8")
    return output_path


__all__ = [
    "build_resumen_ejecutivo_filename",
    "build_resumen_ejecutivo_md",
]
