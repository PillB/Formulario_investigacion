"""Generate wireframe PNGs and a combined PDF from Mermaid source files.

This script renders Mermaid diagrams to PNG via the Mermaid CLI (``mmdc``)
so the resulting images reflect the actual diagrams rather than raw
markdown. Generated assets are placed alongside the sources together with
CSV manifests and logs.
"""
from __future__ import annotations

from pathlib import Path
import csv
import datetime as dt
import shutil
import subprocess
from typing import Callable, List, Sequence

from PIL import Image

DEFAULT_MERMAID_CLI = "mmdc"

# Tab order must match the ttk.Notebook ordering in app.py
MMD_FILES = [
    "layout_hierarchy.mmd",
    "tab01_caso_participantes.mmd",
    "tab02_riesgos.mmd",
    "tab03_normas.mmd",
    "tab04_analisis.mmd",
    "tab05_acciones.mmd",
    "tab06_resumen.mmd",
]


def _resolve_mermaid_cli(executable: str | None = None) -> str:
    """Return an absolute path to the Mermaid CLI executable or raise an error."""

    candidate = executable or DEFAULT_MERMAID_CLI
    resolved = shutil.which(candidate)
    if resolved is None:
        raise RuntimeError(
            "Mermaid CLI (mmdc) not found. Install '@mermaid-js/mermaid-cli' and ensure 'mmdc' is on your PATH."
        )
    return resolved


def _mermaid_cli_renderer(executable: str | None = None) -> Callable[[Path, Path], None]:
    """Return a callable that renders Mermaid files to PNG via the Mermaid CLI."""

    cli = _resolve_mermaid_cli(executable)

    def render(source: Path, target: Path) -> None:
        command = [cli, "-i", str(source), "-o", str(target), "-b", "transparent"]
        subprocess.run(command, check=True)

    return render


def _build_pdf(image_paths: List[Path], target: Path) -> None:
    images = [Image.open(path).convert("RGB") for path in image_paths]
    if not images:
        raise ValueError("No images provided to assemble the PDF")

    first, *rest = images
    first.save(target, save_all=True, append_images=rest)


def _write_manifest(manifest_path: Path, rows: List[dict]) -> None:
    fieldnames = ["source", "asset_type", "output_path", "line_count"]
    with manifest_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_architecture_table(base: Path, mmd_files: Sequence[str]) -> Path:
    target = base / "wireframe_architecture.csv"
    with target.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["order", "mermaid_file"])
        for idx, filename in enumerate(mmd_files, start=1):
            writer.writerow([idx, filename])
    return target


def _write_log(log_path: Path, lines: List[str]) -> None:
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write("\n".join(lines))


def generate_assets(
    base_dir: Path | None = None,
    mmd_files: Sequence[str] | None = None,
    renderer: Callable[[Path, Path], None] | None = None,
) -> None:
    """Render PNGs, manifest CSVs, logs, and a combined PDF for Mermaid sources."""

    base = base_dir or Path(__file__).resolve().parent
    mmd_sequence = list(mmd_files) if mmd_files is not None else MMD_FILES
    image_paths: List[Path] = []
    manifest_rows: List[dict] = []
    log_lines: List[str] = []

    render_png = renderer or _mermaid_cli_renderer()

    architecture_table = _write_architecture_table(base, mmd_sequence)
    log_lines.append(f"[{dt.datetime.utcnow().isoformat()}Z] INFO: Created {architecture_table.name}")

    for filename in mmd_sequence:
        source = base / filename
        if not source.exists():
            raise FileNotFoundError(f"Mermaid source not found: {source}")

        png_path = source.with_suffix(".png")
        render_png(source, png_path)
        image_paths.append(png_path)
        manifest_rows.append(
            {
                "source": filename,
                "asset_type": "png",
                "output_path": png_path.name,
                "line_count": len(source.read_text(encoding="utf-8").splitlines()),
            }
        )
        log_lines.append(f"[{dt.datetime.utcnow().isoformat()}Z] INFO: Created {png_path.name}")

    pdf_path = base / "wireframes.pdf"
    _build_pdf(image_paths, pdf_path)
    manifest_rows.append(
        {
            "source": "multiple",
            "asset_type": "pdf",
            "output_path": pdf_path.name,
            "line_count": len(image_paths),
        }
    )
    log_lines.append(f"[{dt.datetime.utcnow().isoformat()}Z] INFO: Created {pdf_path.name}")

    manifest_path = base / "wireframes_manifest.csv"
    _write_manifest(manifest_path, manifest_rows)
    log_lines.append(f"[{dt.datetime.utcnow().isoformat()}Z] INFO: Created {manifest_path.name}")

    log_path = base / "wireframes_generation.log"
    _write_log(log_path, log_lines)

    print(f"Created {architecture_table.relative_to(base)}")
    for row in manifest_rows:
        print(f"Created {row['output_path']}")
    print(f"Created {manifest_path.relative_to(base)}")
    print(f"Created {log_path.relative_to(base)}")


if __name__ == "__main__":
    generate_assets()
