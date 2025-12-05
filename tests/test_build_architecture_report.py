from pathlib import Path

import pytest

import build_architecture_report as arch_report
from reportlab.platypus import Spacer


def test_build_stylesheet_reuses_existing_heading_styles():
    first = arch_report._build_stylesheet()
    assert first["Heading1"].fontSize == 18
    assert first["Heading2"].fontSize == 14

    second = arch_report._build_stylesheet()
    assert second["Heading1"].fontSize == 18
    assert second["Heading2"].fontSize == 14


def test_flowable_image_preserves_aspect_ratio(monkeypatch, tmp_path):
    image_path = tmp_path / "diagram.png"
    image_path.touch()

    def fake_reader(path: str):
        assert path == str(image_path)

        class Reader:
            def getSize(self):
                return (800, 400)

        return Reader()

    captured: dict[str, float] = {}

    def fake_image(path: str, width: float | None = None, height: float | None = None):
        captured["path"] = path
        captured["width"] = width
        captured["height"] = height
        return f"image:{path}"

    monkeypatch.setattr(arch_report, "ImageReader", fake_reader)
    monkeypatch.setattr(arch_report, "Image", fake_image)

    flowable = arch_report._flowable_image(image_path, target_width=6.5 * arch_report.inch)

    assert flowable == f"image:{image_path}"
    assert captured["path"] == str(image_path)
    assert captured["width"] == 6.5 * arch_report.inch
    assert captured["height"] == (6.5 * arch_report.inch) * 0.5


def test_build_report_avoids_duplicate_styles(monkeypatch, tmp_path):
    def fake_render(source: Path, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
        return target

    monkeypatch.setattr(arch_report, "render_mermaid", fake_render)
    monkeypatch.setattr(arch_report, "_flowable_image", lambda *args, **kwargs: Spacer(1, 1))

    output = tmp_path / "architecture.pdf"
    generated = arch_report.build_report(output)

    assert generated == output
    assert output.exists()


def test_build_report_expands_diagram_pages(monkeypatch, tmp_path):
    def fake_render(source: Path, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
        return target

    image_calls: list[tuple[Path, float]] = []

    def fake_flowable(image_path: Path, target_width: float):
        image_calls.append((image_path, target_width))
        return Spacer(1, 1)

    monkeypatch.setattr(arch_report, "render_mermaid", fake_render)
    monkeypatch.setattr(arch_report, "_flowable_image", fake_flowable)

    output = tmp_path / "architecture.pdf"
    arch_report.build_report(output)

    assert [call[0] for call in image_calls] == [arch_report.ARCH_PNG, arch_report.SEQ_PNG]

    arch_page_size = arch_report.landscape(arch_report.A3)
    expected_arch_width = arch_page_size[0] - (0.7 * arch_report.inch * 2)
    seq_page_size = arch_report.A3
    expected_seq_width = seq_page_size[0] - (0.7 * arch_report.inch * 2)

    assert image_calls[0][1] == pytest.approx(expected_arch_width)
    assert image_calls[1][1] == pytest.approx(expected_seq_width)
