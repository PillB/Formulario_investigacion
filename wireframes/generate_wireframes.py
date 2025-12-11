"""Generate wireframe PNGs and a combined PDF from Mermaid source files.

This script renders Mermaid diagrams to PNG via the Mermaid CLI (``mmdc``)
so the resulting images reflect the actual diagrams rather than raw
markdown. Generated assets are placed alongside the sources together with
CSV manifests and logs.
"""
from __future__ import annotations

import csv
import datetime as dt
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Sequence

from PIL import Image, ImageDraw, ImageFont

DEFAULT_MERMAID_CLI = "mmdc"
DEFAULT_SCALE = 2.0

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

# Minimalist sketches aligned with the widgets defined in the Tkinter frames
# (see ui/frames and tab builders in app.py). These intentionally keep shapes
# simple while preserving the sectioning and control groupings present in the
# actual GUI to help compare Mermaid diagrams against an approximate layout.
SKETCH_LAYOUTS: Dict[str, Dict[str, List[str]]] = {
    "layout_hierarchy": {
        "__title__": "Notebook y secciones principales",
        "Tabs en orden": [
            "Caso y participantes",
            "Riesgos",
            "Normas",
            "Análisis y narrativas",
            "Acciones",
            "Resumen",
        ],
        "Controles globales": [
            "Barra de acciones superior",
            "Estado / progreso",
        ],
    },
    "tab01_caso_participantes": {
        "__title__": "Caso y participantes",
        "Datos generales": [
            "Número de caso, Tipo de informe",
            "Taxonomía (categorías, modalidad, canal, proceso)",
            "Investigador principal (matrícula, nombre, cargo)",
            "Fechas de ocurrencia y descubrimiento",
            "Centro de costos",
        ],
        "Clientes implicados": [
            "Tabla resumen opcional",
            "Botón Añadir cliente",
            "Acordeones de cliente con datos personales y listas",
        ],
        "Productos investigados": [
            "Botón Añadir producto",
            "Acordeones de producto con montos y reclamo",
        ],
        "Colaboradores involucrados": [
            "Botón Añadir colaborador",
            "Acordeones de colaborador con asignaciones y montos",
        ],
    },
    "tab02_riesgos": {
        "__title__": "Riesgos",
        "Resumen de riesgos": [
            "Tabla principal (ID, criticidad, líder, exposición)",
            "Botón Añadir riesgo",
        ],
        "Detalle por riesgo": [
            "Acordeones con descripción y planes",
            "Campos de mitigación y fechas",
        ],
    },
    "tab03_normas": {
        "__title__": "Normas",
        "Tabla de normas": [
            "Botón Añadir norma",
            "Columnas: ID, Vigencia, Descripción",
        ],
        "Detalle": [
            "Acordeones con notas y archivos",
        ],
    },
    "tab04_analisis": {
        "__title__": "Análisis y narrativas",
        "Narrativas principales": [
            "Antecedentes y modus operandi",
            "Hallazgos, descargos, conclusiones",
            "Recomendaciones y mejoras",
        ],
        "Secciones extendidas": [
            "Encabezado extendido",
            "Recomendaciones categorizadas",
            "Investigador principal y Operaciones",
            "Anexos",
        ],
    },
    "tab05_acciones": {
        "__title__": "Acciones",
        "Controles generales": [
            "Audio de alerta",
            "Selector de tema",
        ],
        "Catálogos de detalle": [
            "Estado de detalle",
            "Cargar catálogos / iniciar sin catálogos",
            "Barra de progreso",
        ],
        "Importar datos masivos": [
            "Botones CSV: clientes, colaboradores, productos, normas, riesgos, estado",
            "Barra de progreso de importación",
        ],
    },
    "tab06_resumen": {
        "__title__": "Resumen",
        "Tablas compactas": [
            "Clientes",
            "Colaboradores",
            "Asignaciones por colaborador",
            "Productos y riesgos",
            "Reclamos y normas",
        ],
    },
}


def _resolve_mermaid_cli(executable: str | None = None) -> str:
    """Return an absolute path to the Mermaid CLI executable or raise an error."""

    candidate = executable or DEFAULT_MERMAID_CLI
    resolved = shutil.which(candidate)
    if resolved is None:
        raise RuntimeError(
            "Mermaid CLI (mmdc) not found. Install '@mermaid-js/mermaid-cli' and ensure 'mmdc' is on your PATH."
        )
    return resolved


def _mermaid_cli_renderer(
    executable: str | None = None,
    scale: float = DEFAULT_SCALE,
    background: str = "white",
    width: int | None = None,
    height: int | None = None,
    run_process: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> Callable[[Path, Path], None]:
    """Return a callable that renders Mermaid files to PNG via the Mermaid CLI.

    The renderer increases the default scale to produce sharper PNG outputs and
    allows callers to override width/height if desired.
    """

    cli = _resolve_mermaid_cli(executable)

    def render(source: Path, target: Path) -> None:
        command = [
            cli,
            "-i",
            str(source),
            "-o",
            str(target),
            "-b",
            background,
            "-s",
            str(scale),
        ]

        if width:
            command.extend(["-w", str(width)])
        if height:
            command.extend(["-H", str(height)])

        run_process(command, check=True)

    return render


def _placeholder_renderer(message: str | None = None) -> Callable[[Path, Path], None]:
    """Return a renderer that creates a placeholder PNG using Pillow."""

    def render(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)

        text = message or "Mermaid CLI unavailable. Generated placeholder diagram."
        text = f"{source.name}\n{text}\nInstala mermaid-cli para renderizar el diagrama real"

        image = Image.new("RGB", (1000, 600), color="white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        draw.rectangle((18, 18, 982, 582), outline="black", width=3)
        draw.multiline_text((36, 36), text, fill="black", font=font, spacing=6)

        image.save(target, format="PNG")

    return render


def _render_sketch(layout: Dict[str, List[str]], target: Path, size: tuple[int, int] = (1400, 1000)) -> None:
    """Render a lightweight B&W sketch to approximate the Tkinter layout.

    Each entry in ``layout`` maps a section title to the list of items within
    that section, stacked vertically to mirror the notebook tab composition.
    """

    image = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    margin = 32
    y = margin

    draw.text((margin, y - 22), layout.get("__title__", "Wireframe"), fill="black", font=font)

    for section, items in layout.items():
        if section == "__title__":
            continue

        section_height = 36 + (len(items) * 34)
        draw.rectangle((margin, y, size[0] - margin, y + section_height), outline="black", width=3)
        draw.text((margin + 12, y + 8), section, fill="black", font=font)

        inner_y = y + 32
        for item in items:
            draw.rectangle(
                (margin + 16, inner_y, size[0] - margin - 16, inner_y + 28),
                outline="gray",
                width=2,
            )
            draw.text((margin + 24, inner_y + 8), item, fill="black", font=font)
            inner_y += 32

        y = inner_y + 16

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


def generate_assets(
    base_dir: Path | None = None,
    mmd_files: Sequence[str] | None = None,
    renderer: Callable[[Path, Path], None] | None = None,
    sketch_layouts: Dict[str, Dict[str, List[str]]] | None = None,
    mermaid_scale: float = DEFAULT_SCALE,
) -> None:
    """Render PNGs, manifest CSVs, logs, and a combined PDF for Mermaid sources."""

    base = base_dir or Path(__file__).resolve().parent
    mmd_sequence = list(mmd_files) if mmd_files is not None else MMD_FILES
    image_paths: List[Path] = []
    manifest_rows: List[dict] = []
    log_lines: List[str] = []

    fallback_reason: str | None = None
    if renderer is not None:
        render_png = renderer
    else:
        try:
            render_png = _mermaid_cli_renderer(scale=mermaid_scale)
        except RuntimeError as exc:
            fallback_reason = str(exc)
            render_png = _placeholder_renderer(message=f"{exc}")
            print(
                "WARN: Mermaid CLI not available; generating placeholder PNGs instead.",
                f"Details: {exc}",
            )
    sketch_data = sketch_layouts or SKETCH_LAYOUTS

    architecture_table = _write_architecture_table(base, mmd_sequence)
    log_lines.append(f"[{dt.datetime.utcnow().isoformat()}Z] INFO: Created {architecture_table.name}")
    if fallback_reason:
        log_lines.append(
            f"[{dt.datetime.utcnow().isoformat()}Z] WARNING: Mermaid rendering fallback in use: {fallback_reason}"
        )

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

        sketch_layout = sketch_data.get(source.stem)
        if sketch_layout:
            sketch_path = source.with_stem(f"{source.stem}_sketch").with_suffix(".png")
            _render_sketch(sketch_layout, sketch_path)
            image_paths.append(sketch_path)
            manifest_rows.append(
                {
                    "source": filename,
                    "asset_type": "sketch",
                    "output_path": sketch_path.name,
                    "line_count": len(sketch_layout) - 1,
                }
            )
            log_lines.append(f"[{dt.datetime.utcnow().isoformat()}Z] INFO: Created {sketch_path.name}")

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
