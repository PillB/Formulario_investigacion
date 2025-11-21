import pytest

from analytics.usage_visualizer import (
    DEFAULT_SCREEN_DIMENSIONS,
    DEFAULT_SCREEN_HINTS,
    AnalyticsReport,
    infer_screen,
    visualize_usage,
)


@pytest.fixture
def sample_log_file(tmp_path):
    log_path = tmp_path / "logs.csv"
    log_path.write_text(
        "timestamp,tipo,subtipo,widget_id,coords,mensaje\n"
        "2024-01-01 10:00:00,navegacion,click,tab_clientes,100,200,Abrio pestaña Clientes\n"
        "2024-01-01 10:02:00,validacion,error,entry_cliente,150,250,Error cliente duplicado\n"
        "2024-01-01 10:10:00,navegacion,click,tab_productos,300,120,Abrio pestaña Productos\n"
        "2024-01-01 10:15:00,navegacion,click,btn_resumen,220,180,Visita pestaña Resumen\n"
        "2024-01-01 10:17:00,validacion,warning,btn_guardar,,Advertencia de guardado\n"
        "2024-01-01 10:25:00,navegacion,click,tab_clientes,80,90,Volvió a Clientes\n",
        encoding="utf-8",
    )
    return log_path


def test_infer_screen_uses_hints():
    row = {"widget_id": "tab_clientes", "mensaje": "Abrió pestaña Clientes"}
    assert infer_screen(row) == "clientes"
    custom = {"panel": ["panel principal"]}
    assert infer_screen({"mensaje": "Panel principal"}, custom) == "panel"


def test_visualize_usage_builds_heatmaps(sample_log_file, tmp_path):
    matplotlib = pytest.importorskip("matplotlib")
    report = visualize_usage(
        sample_log_file,
        screen_dimensions=(400, 300),
        screen_hints=DEFAULT_SCREEN_HINTS,
        output_path=tmp_path / "heatmap.png",
    )
    assert isinstance(report, AnalyticsReport)
    assert report.screen_counts["clientes"] == 3
    assert report.screen_counts["productos"] == 1
    assert report.validation_share > 0
    assert any("más usada" in text for text in report.interpretations)
    assert (tmp_path / "heatmap.png").exists()
    matplotlib.pyplot.close(report.figure)


def test_defaults_are_exported():
    assert DEFAULT_SCREEN_DIMENSIONS[0] > 0
    assert "resumen" in DEFAULT_SCREEN_HINTS
