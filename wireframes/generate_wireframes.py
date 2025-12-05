"""Generate wireframe PNGs and a combined PDF from Mermaid source files.

This script stays offline-friendly by rendering the Mermaid source as
monospaced text on a white canvas. The intent is to mirror the structure
and labels defined in the `.mmd` files without requiring external CLI
tools. Generated assets are placed alongside the sources.
"""
from __future__ import annotations

from pathlib import Path
import textwrap
from typing import Iterable, List

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


def _render_png(text_lines: List[str], target: Path) -> None:
    font = ImageFont.load_default(size=FONT_SIZE)
    draw_dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    _, line_height = draw_dummy.textsize("Ag", font=font)

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


def generate_assets(base_dir: Path | None = None) -> None:
    """Render PNGs and a combined PDF for all Mermaid sources."""
    base = base_dir or Path(__file__).resolve().parent
    image_paths: List[Path] = []

    for filename in MMD_FILES:
        source = base / filename
        if not source.exists():
            raise FileNotFoundError(f"Mermaid source not found: {source}")

        wrapped_lines = _wrap_mermaid_lines(source.read_text(encoding="utf-8").splitlines())
        png_path = source.with_suffix(".png")
        _render_png(wrapped_lines, png_path)
        image_paths.append(png_path)
        print(f"Created {png_path.relative_to(base)}")

    pdf_path = base / "wireframes.pdf"
    _build_pdf(image_paths, pdf_path)
    print(f"Created {pdf_path.relative_to(base)}")


if __name__ == "__main__":
    generate_assets()
