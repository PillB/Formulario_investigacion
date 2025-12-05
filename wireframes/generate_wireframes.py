"""Generate wireframe PNGs and a combined PDF from Mermaid source files.

This script stays offline-friendly by rendering the Mermaid source as
monospaced text on a white canvas. The intent is to mirror the structure
and labels defined in the `.mmd` files without requiring external CLI
tools. Generated assets are placed alongside the sources.
"""
from __future__ import annotations

from pathlib import Path
import csv
import datetime as dt
import textwrap
from typing import Iterable, List, Sequence

from PIL import Image, ImageDraw, ImageFont

OUTPUT_WIDTH = 1400
PADDING = 24
FONT_SIZE = 14
WRAP_COLUMNS = 140

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


def _wrap_mermaid_lines(lines: Iterable[str]) -> List[str]:
    wrapped: List[str] = []
    for line in lines:
        if line.strip() == "":
            wrapped.append("")
            continue
        wrapped.extend(textwrap.wrap(line.rstrip("\n"), width=WRAP_COLUMNS, replace_whitespace=False))
    return wrapped


def _load_font() -> ImageFont.ImageFont:
    """Load a monospaced font compatible with current Pillow versions."""

    # Pillow removed the ``textsize`` helper; ``textbbox`` remains available and
    # works with the built-in bitmap font. ``load_default`` keeps the script
    # dependency-free across environments.
    return ImageFont.load_default()


def _measure_line_height(font: ImageFont.ImageFont) -> int:
    """Return the pixel height of a representative text sample."""

    # ``textbbox`` is stable across Pillow releases and avoids the deprecated
    # ``textsize`` API that is no longer exposed in newer versions.
    draw_dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    _, y0, _, y1 = draw_dummy.textbbox((0, 0), "Ag", font=font)
    return y1 - y0


def _render_png(text_lines: List[str], target: Path) -> None:
    font = _load_font()
    line_height = _measure_line_height(font)

    height = PADDING * 2 + line_height * len(text_lines)
    image = Image.new("RGB", (OUTPUT_WIDTH, height), color="white")
    draw = ImageDraw.Draw(image)
    draw.multiline_text((PADDING, PADDING), "\n".join(text_lines), fill="black", font=font, spacing=0)
    image.save(target, format="PNG")


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


def generate_assets(base_dir: Path | None = None, mmd_files: Sequence[str] | None = None) -> None:
    """Render PNGs, manifest CSVs, logs, and a combined PDF for Mermaid sources."""

    base = base_dir or Path(__file__).resolve().parent
    mmd_sequence = list(mmd_files) if mmd_files is not None else MMD_FILES
    image_paths: List[Path] = []
    manifest_rows: List[dict] = []
    log_lines: List[str] = []

    architecture_table = _write_architecture_table(base, mmd_sequence)
    log_lines.append(f"[{dt.datetime.utcnow().isoformat()}Z] INFO: Created {architecture_table.name}")

    for filename in mmd_sequence:
        source = base / filename
        if not source.exists():
            raise FileNotFoundError(f"Mermaid source not found: {source}")

        wrapped_lines = _wrap_mermaid_lines(source.read_text(encoding="utf-8").splitlines())
        png_path = source.with_suffix(".png")
        _render_png(wrapped_lines, png_path)
        image_paths.append(png_path)
        manifest_rows.append(
            {
                "source": filename,
                "asset_type": "png",
                "output_path": png_path.name,
                "line_count": len(wrapped_lines),
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
