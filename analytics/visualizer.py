"""Utilidades para visualizar mapas de calor y generar análisis automáticos.

Este módulo es independiente de la aplicación principal y se puede ejecutar de
forma offline contra un archivo de logs CSV generado por ``log_event``. Produce
figuras que muestran, lado a lado, cada pantalla de la app con un mapa de calor
superpuesto y genera interpretaciones automáticas basadas en los patrones de
uso y validación.
"""
from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np

from validators import LOG_FIELDNAMES


@dataclass(frozen=True)
class ScreenLayout:
    """Metadatos de cada pantalla disponibles para el visualizador."""

    name: str
    width: int
    height: int
    background_path: Optional[Path] = None


@dataclass
class VisualizerResult:
    """Resultado con la figura generada y los hallazgos automáticos."""

    figure: plt.Figure
    output_path: Optional[Path]
    interpretations: List[str]
    stats: Dict[str, object]


def load_log_rows(log_path: Path | str) -> List[MutableMapping[str, str]]:
    """Carga el CSV de logs y normaliza los campos conocidos."""

    rows: List[MutableMapping[str, str]] = []
    with open(log_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            normalized = {field: row.get(field, "") for field in LOG_FIELDNAMES}
            rows.append(normalized)
    return rows


def _parse_coords(value: str) -> Optional[Tuple[float, float]]:
    if not value:
        return None
    if "," in value:
        try:
            x_str, y_str = value.split(",", 1)
            return float(x_str), float(y_str)
        except ValueError:
            return None
    try:
        number = float(value)
        return number, number
    except ValueError:
        return None


def _assign_screen(
    row: MutableMapping[str, str],
    widget_to_screen: Optional[Dict[str, str]],
) -> Optional[str]:
    widget_id = (row.get("widget_id") or "").strip()
    if widget_to_screen and widget_id in widget_to_screen:
        return widget_to_screen[widget_id]
    subtipo = (row.get("subtipo") or "").strip()
    if subtipo:
        return subtipo
    if widget_id and ":" in widget_id:
        return widget_id.split(":", 1)[0]
    return None


def _prepare_heatmap_data(
    rows: Iterable[MutableMapping[str, str]],
    screen_layouts: Sequence[ScreenLayout],
    widget_to_screen: Optional[Dict[str, str]],
) -> Dict[str, List[Tuple[float, float]]]:
    coords_by_screen: Dict[str, List[Tuple[float, float]]] = {layout.name: [] for layout in screen_layouts}
    for row in rows:
        screen = _assign_screen(row, widget_to_screen)
        coords = _parse_coords(row.get("coords", ""))
        if screen in coords_by_screen and coords:
            coords_by_screen[screen].append(coords)
    return coords_by_screen


def _draw_heatmap(ax: plt.Axes, layout: ScreenLayout, points: List[Tuple[float, float]], bins: int = 50) -> None:
    ax.set_title(layout.name)
    if layout.background_path and Path(layout.background_path).exists():
        image = plt.imread(layout.background_path)
        ax.imshow(image, extent=(0, layout.width, layout.height, 0))
    if points:
        xs, ys = zip(*points)
        heatmap, xedges, yedges = np.histogram2d(xs, ys, bins=bins, range=[[0, layout.width], [0, layout.height]])
        ax.imshow(
            heatmap.T,
            extent=(0, layout.width, 0, layout.height),
            origin="lower",
            cmap="inferno",
            alpha=0.65,
        )
    ax.set_xlim(0, layout.width)
    ax.set_ylim(0, layout.height)
    ax.invert_yaxis()
    ax.axis("off")


def _summarize_usage(rows: Sequence[MutableMapping[str, str]]) -> Dict[str, object]:
    total = len(rows)
    tipo_counter: Counter[str] = Counter()
    widget_counter: Counter[str] = Counter()
    screen_counter: Counter[str] = Counter()
    hourly_counter: Counter[int] = Counter()
    timeline: List[datetime] = []

    for row in rows:
        tipo_counter[(row.get("tipo") or "").strip()] += 1
        widget_counter[(row.get("widget_id") or "").strip() or "(sin id)"] += 1
        screen_name = (row.get("subtipo") or "").strip() or "(sin pantalla)"
        screen_counter[screen_name] += 1
        timestamp = (row.get("timestamp") or "").strip()
        if timestamp:
            try:
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                timeline.append(dt)
                hourly_counter[dt.hour] += 1
            except ValueError:
                pass

    timeline.sort()
    durations: List[float] = []
    for prev, curr in zip(timeline, timeline[1:]):
        durations.append((curr - prev).total_seconds())
    avg_gap = sum(durations) / len(durations) if durations else 0

    return {
        "total_events": total,
        "tipo": tipo_counter,
        "widget": widget_counter,
        "screen": screen_counter,
        "hourly": hourly_counter,
        "avg_gap_seconds": avg_gap,
    }


def _interpret(stats: Dict[str, object], coords_by_screen: Dict[str, List[Tuple[float, float]]]) -> List[str]:
    interpretations: List[str] = []
    screen_counts: Counter[str] = stats.get("screen", Counter())  # type: ignore[arg-type]
    if screen_counts:
        top_screen, top_count = screen_counts.most_common(1)[0]
        interpretations.append(
            f"La pantalla con mayor actividad fue '{top_screen}' con {top_count} interacciones registradas."
        )
        bottom_screen, bottom_count = screen_counts.most_common()[-1]
        interpretations.append(
            f"La pantalla con menor actividad fue '{bottom_screen}' con {bottom_count} eventos; conviene revisar su descubribilidad."
        )
    tipo_counts: Counter[str] = stats.get("tipo", Counter())  # type: ignore[arg-type]
    total_events = stats.get("total_events", 0) or 0
    validation = tipo_counts.get("validacion", 0)
    if total_events:
        error_rate = validation / total_events * 100
        interpretations.append(
            f"La tasa de validaciones/errores es {error_rate:.1f}% ({validation}/{total_events}); conviene priorizar mejoras en los campos más conflictivos."
        )
    widget_counts: Counter[str] = stats.get("widget", Counter())  # type: ignore[arg-type]
    if widget_counts:
        top_widget, top_widget_count = widget_counts.most_common(1)[0]
        interpretations.append(
            f"El control con más interacciones fue '{top_widget}' con {top_widget_count} eventos; es candidato para pruebas de usabilidad y simplificación."
        )
    avg_gap = stats.get("avg_gap_seconds", 0) or 0
    if avg_gap:
        interpretations.append(
            f"El intervalo medio entre eventos consecutivos es de {avg_gap:.1f} segundos, lo que ayuda a dimensionar la cadencia de uso y tiempos de espera aceptables."
        )
    dense_screens = [name for name, points in coords_by_screen.items() if len(points) >= 20]
    if dense_screens:
        interpretations.append(
            "Las pantallas con mapas de calor densos (>=20 clics) permiten construir heatmaps accionables: "
            + ", ".join(sorted(dense_screens))
        )
    return interpretations


def generate_usage_visuals(
    *,
    log_path: Path | str,
    screen_layouts: Sequence[ScreenLayout],
    widget_to_screen: Optional[Dict[str, str]] = None,
    output_path: Optional[Path | str] = None,
    heatmap_bins: int = 50,
) -> VisualizerResult:
    """Genera la figura de mapas de calor lado a lado y devuelve hallazgos.

    Args:
        log_path: Ruta al archivo CSV con logs.
        screen_layouts: Metadatos de cada pantalla a mostrar. El nombre se usa
            para agrupar eventos y titular cada subplot.
        widget_to_screen: Mapeo opcional de widget_id a pantalla para mejorar
            la asignación cuando los logs no incluyen subtipo.
        output_path: Ruta donde guardar la imagen. Si es ``None`` no se escribe
            a disco, pero se devuelve la figura construida.
        heatmap_bins: Cantidad de divisiones para la grilla del mapa de calor.

    Returns:
        VisualizerResult con la figura, la ruta de salida (si aplica) y una
        lista de interpretaciones automáticas.
    """

    rows = load_log_rows(log_path)
    coords_by_screen = _prepare_heatmap_data(rows, screen_layouts, widget_to_screen)
    stats = _summarize_usage(rows)

    fig, axes = plt.subplots(1, len(screen_layouts), figsize=(6 * len(screen_layouts), 6))
    if len(screen_layouts) == 1:
        axes = [axes]  # type: ignore[list-item]
    for layout, ax in zip(screen_layouts, axes):
        _draw_heatmap(ax, layout, coords_by_screen.get(layout.name, []), bins=heatmap_bins)

    plt.tight_layout()

    save_path: Optional[Path] = None
    if output_path:
        save_path = Path(output_path)
        fig.savefig(save_path, dpi=200)

    interpretations = _interpret(stats, coords_by_screen)

    return VisualizerResult(
        figure=fig,
        output_path=save_path,
        interpretations=interpretations,
        stats=stats,
    )


__all__ = [
    "ScreenLayout",
    "VisualizerResult",
    "generate_usage_visuals",
    "load_log_rows",
]
