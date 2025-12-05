from pathlib import Path

import build_architecture_report as arch_report
from reportlab.platypus import Spacer


def test_build_stylesheet_reuses_existing_heading_styles():
    first = arch_report._build_stylesheet()
    assert first["Heading1"].fontSize == 18
    assert first["Heading2"].fontSize == 14

    second = arch_report._build_stylesheet()
    assert second["Heading1"].fontSize == 18
    assert second["Heading2"].fontSize == 14


def test_build_report_avoids_duplicate_styles(monkeypatch, tmp_path):
    def fake_render(source: Path, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
        return target

    monkeypatch.setattr(arch_report, "render_mermaid", fake_render)
    monkeypatch.setattr(arch_report, "Image", lambda *args, **kwargs: Spacer(1, 1))

    output = tmp_path / "architecture.pdf"
    generated = arch_report.build_report(output)

    assert generated == output
    assert output.exists()
