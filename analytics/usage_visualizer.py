from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

DEFAULT_SCREEN_DIMENSIONS = (1200, 800)
DEFAULT_SCREEN_HINTS: Dict[str, Sequence[str]] = {
    "clientes": ["cliente"],
    "colaboradores": ["colaborador", "team"],
    "productos": ["producto"],
    "riesgos": ["riesgo", "risk"],
    "normas": ["norma"],
    "analisis": ["analisis", "análisis", "analysis"],
    "reportes": ["docx", "markdown", "md", "reporte", "export", "guardar y enviar"],
    "alertas": ["alerta", "ppt", "pptx", "temprana"],
    "cartas": ["carta", "inmediatez"],
    "recuperacion": ["historial", "recuperacion", "recuperación", "autosave"],
    "consolidacion": ["consolida", "h_", "manifiesto", "pendiente", "external"],
    "acciones": ["accion", "acciones", "guardar", "importar", "borrar", "cargar", "autosave", "respaldo"],
    "resumen": ["resumen", "summary"],
}


@dataclass
class AnalyticsReport:
    figure: "matplotlib.figure.Figure"
    interpretations: List[str]
    screen_counts: Counter
    widget_counts: Counter
    validation_share: float
    time_spent_seconds: Dict[str, float]


@dataclass
class HeatmapData:
    screen: str
    coords: List[Tuple[float, float]]
    grid: List[List[int]]


class MissingDependencyError(RuntimeError):
    pass


def load_log_rows(log_path: str | Path) -> List[MutableMapping[str, str]]:
    path = Path(log_path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de logs en {path}")
    with path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return [row for row in reader]


def _parse_coords(value: str | None) -> Optional[Tuple[float, float]]:
    if not value:
        return None
    if "," not in value:
        return None
    try:
        x_str, y_str = value.split(",", maxsplit=1)
        return float(x_str.strip()), float(y_str.strip())
    except (ValueError, TypeError):
        return None


def parse_timestamp(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def _tokenize(text: str) -> List[str]:
    sanitized = (text or "").lower()
    tokens = re.split(r"[\s\._\-/]+", sanitized)
    return [token for token in tokens if token]


def infer_screen(row: MutableMapping[str, str], screen_hints: Dict[str, Sequence[str]] | None = None) -> str:
    hints = screen_hints or DEFAULT_SCREEN_HINTS
    widget_tokens = _tokenize(row.get("widget_id", ""))
    content_tokens = widget_tokens + _tokenize(row.get("mensaje", ""))
    for screen, keywords in hints.items():
        for keyword in keywords:
            lowered = keyword.lower()
            if any(lowered in token or token in lowered for token in widget_tokens):
                return screen
            if any(lowered in token or token in lowered for token in content_tokens):
                return screen
    return "general"


def _build_heatmap_grid(
    coords: Iterable[Tuple[float, float]],
    width: int,
    height: int,
    bin_size: int = 80,
) -> List[List[int]]:
    cols = max(1, math.ceil(width / bin_size))
    rows = max(1, math.ceil(height / bin_size))
    grid = [[0 for _ in range(cols)] for _ in range(rows)]
    for x, y in coords:
        if x < 0 or y < 0:
            continue
        col = min(cols - 1, int(x // bin_size))
        row = min(rows - 1, int(y // bin_size))
        grid[row][col] += 1
    return grid


def _accumulate_time_by_screen(rows: List[MutableMapping[str, str]], screen_hints) -> Dict[str, float]:
    ordered = sorted(rows, key=lambda r: parse_timestamp(r.get("timestamp", "")) or datetime.min)
    current_screen: Optional[str] = None
    last_ts: Optional[datetime] = None
    last_processed_ts: Optional[datetime] = None
    time_spent: Dict[str, float] = defaultdict(float)
    for row in ordered:
        ts = parse_timestamp(row.get("timestamp", ""))
        screen = infer_screen(row, screen_hints)
        if ts is None:
            continue
        last_processed_ts = ts
        if current_screen is None:
            current_screen = screen
            last_ts = ts
            continue
        if screen != current_screen and last_ts:
            elapsed = (ts - last_ts).total_seconds()
            if elapsed >= 0:
                time_spent[current_screen] += elapsed
            current_screen = screen
            last_ts = ts
    if current_screen and last_ts:
        final_ts = last_processed_ts or last_ts
        elapsed = (final_ts - last_ts).total_seconds()
        if elapsed >= 0:
            time_spent[current_screen] += elapsed
    return dict(time_spent)


def _build_heatmap_dataset(
    rows: List[MutableMapping[str, str]],
    screen_hints: Dict[str, Sequence[str]],
    screen_dimensions: Tuple[int, int],
) -> List[HeatmapData]:
    width, height = screen_dimensions
    coords_by_screen: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    for row in rows:
        coords = _parse_coords(row.get("coords"))
        if coords is None:
            continue
        screen = infer_screen(row, screen_hints)
        coords_by_screen[screen].append(coords)
    datasets: List[HeatmapData] = []
    for screen, coords in coords_by_screen.items():
        grid = _build_heatmap_grid(coords, width, height)
        datasets.append(HeatmapData(screen=screen, coords=coords, grid=grid))
    return sorted(datasets, key=lambda d: len(d.coords), reverse=True)


def _prepare_interpretations(
    screen_counts: Counter,
    widget_counts: Counter,
    validation_share: float,
    time_spent_seconds: Dict[str, float],
) -> List[str]:
    interpretations: List[str] = []
    if screen_counts:
        most_used, top_count = screen_counts.most_common(1)[0]
        total = sum(screen_counts.values()) or 1
        interpretations.append(
            f"La pantalla más usada es '{most_used}' con {top_count} interacciones ({top_count / total:.0%} del total)."
        )
        low_activity = [s for s, c in screen_counts.items() if c <= max(3, 0.1 * total)]
        if low_activity:
            interpretations.append(
                "Pantallas con baja actividad: " + ", ".join(sorted(low_activity)) + ". Revisar usabilidad o acceso."
            )
    if widget_counts:
        top_widgets = ", ".join(f"{w} ({c})" for w, c in widget_counts.most_common(3))
        interpretations.append(f"Top widgets por interacción: {top_widgets}.")
    if validation_share > 0.25:
        interpretations.append(
            "Alta proporción de eventos de validación detectada; revisar mensajes de error y flujos de captura."
        )
    if time_spent_seconds:
        longest = max(time_spent_seconds.items(), key=lambda pair: pair[1])
        interpretations.append(
            f"Mayor tiempo invertido en '{longest[0]}' con aproximadamente {longest[1]:.0f} segundos acumulados."
        )
    if not interpretations:
        interpretations.append("No se generaron interpretaciones automáticas (conjunto de datos vacío).")
    return interpretations


def visualize_usage(
    log_path: str | Path,
    *,
    screen_dimensions: Tuple[int, int] = DEFAULT_SCREEN_DIMENSIONS,
    screen_hints: Dict[str, Sequence[str]] | None = None,
    output_path: str | Path | None = None,
) -> AnalyticsReport:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise MissingDependencyError(
            "Se requiere matplotlib para generar visualizaciones. Instale matplotlib>=3.7."
        ) from exc

    rows = load_log_rows(log_path)
    hints = screen_hints or DEFAULT_SCREEN_HINTS
    datasets = _build_heatmap_dataset(rows, hints, screen_dimensions)
    screen_counts = Counter(infer_screen(row, hints) for row in rows)
    widget_counts = Counter(
        (row.get("widget_id") or row.get("mensaje") or "desconocido").strip()
        for row in rows
    )
    validation_share = sum(1 for row in rows if row.get("tipo") == "validacion") / (len(rows) or 1)
    time_spent_seconds = _accumulate_time_by_screen(rows, hints)

    if not datasets:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.set_title("Sin coordenadas registradas en el log")
        ax.axis("off")
        interpretations = _prepare_interpretations(screen_counts, widget_counts, validation_share, time_spent_seconds)
        if output_path:
            fig.savefig(output_path, bbox_inches="tight")
        return AnalyticsReport(fig, interpretations, screen_counts, widget_counts, validation_share, time_spent_seconds)

    cols = min(3, len(datasets))
    rows_count = math.ceil(len(datasets) / cols)
    fig, axes = plt.subplots(rows_count, cols, figsize=(6 * cols, 4.5 * rows_count))
    if hasattr(axes, "flat"):
        axes_list = [ax for ax in axes.flat]
    else:
        axes_list = [axes]

    for dataset, ax in zip(datasets, axes_list):
        img = ax.imshow(
            dataset.grid,
            origin="lower",
            extent=(0, screen_dimensions[0], 0, screen_dimensions[1]),
            cmap="inferno",
            alpha=0.85,
        )
        if dataset.coords:
            xs, ys = zip(*dataset.coords)
            ax.scatter(xs, ys, s=8, color="white", alpha=0.3, edgecolors="none")
        ax.set_title(f"Mapa de calor: {dataset.screen}")
        ax.set_xlim(0, screen_dimensions[0])
        ax.set_ylim(0, screen_dimensions[1])
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        fig.colorbar(img, ax=ax, fraction=0.046, pad=0.04)

    for ax in axes_list[len(datasets):]:
        ax.axis("off")

    interpretations = _prepare_interpretations(screen_counts, widget_counts, validation_share, time_spent_seconds)

    fig.suptitle("Uso por pantalla con heatmaps y análisis automático", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    if output_path:
        fig.savefig(output_path, bbox_inches="tight")

    return AnalyticsReport(fig, interpretations, screen_counts, widget_counts, validation_share, time_spent_seconds)


__all__ = [
    "AnalyticsReport",
    "HeatmapData",
    "MissingDependencyError",
    "DEFAULT_SCREEN_DIMENSIONS",
    "DEFAULT_SCREEN_HINTS",
    "infer_screen",
    "load_log_rows",
    "parse_timestamp",
    "visualize_usage",
]
