from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

import pytest

import build_architecture_report as arch_report
from reportlab.platypus import Spacer


def _make_png(path: Path, size: tuple[int, int]) -> None:
    image = Image.new("RGB", size, color="white")
    image.save(path)


def test_render_mermaid_uses_high_resolution(monkeypatch, tmp_path):
    source = tmp_path / "diagram.mmd"
    target = tmp_path / "diagram.png"
    source.write_text("graph TD; A-->B;")

    monkeypatch.setattr(arch_report.shutil, "which", lambda name: "/usr/bin/mmdc" if name == "mmdc" else None)
    commands: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool):  # noqa: D401
        commands.append(cmd)

    monkeypatch.setattr(arch_report.subprocess, "run", fake_run)

    arch_report.render_mermaid(source, target)

    assert commands, "render_mermaid should invoke mmdc"
    cmd = commands[0]
    assert "-s" in cmd
    assert str(arch_report.MERMAID_EXPORT_SCALE) in cmd
    assert "-w" in cmd
    assert str(arch_report.MERMAID_EXPORT_WIDTH_PX) in cmd


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


def test_build_editable_deck_scales_each_diagram(monkeypatch, tmp_path):
    rendered: dict[str, Path] = {}

    def fake_render(source: Path, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        size = (1600, 800) if "architecture" in target.stem else (800, 1600)
        _make_png(target, size)
        rendered[source.name] = target
        return target

    monkeypatch.setattr(arch_report, "render_mermaid", fake_render)

    output = tmp_path / "diagrams.pptx"
    deck_path = arch_report.build_editable_deck(output)

    presentation = Presentation(deck_path)
    assert presentation.slide_width == arch_report.PPTX_SLIDE_WIDTH
    assert presentation.slide_height == arch_report.PPTX_SLIDE_HEIGHT

    assert len(presentation.slides) == 2
    arch_picture = [
        shape
        for shape in presentation.slides[0].shapes
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
    ][0]
    seq_picture = [
        shape
        for shape in presentation.slides[1].shapes
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
    ][0]

    max_width = arch_report.PPTX_SLIDE_WIDTH - 2 * arch_report.PPTX_MARGIN
    content_top = (
        arch_report.PPTX_MARGIN
        + arch_report.PPTX_TITLE_HEIGHT
        + arch_report.PPTX_SUBTITLE_HEIGHT
        + arch_report.PPTX_CONTENT_GAP
    )
    max_height = arch_report.PPTX_SLIDE_HEIGHT - content_top - arch_report.PPTX_MARGIN

    expected_arch = arch_report._scale_image_to_box(
        rendered[arch_report.ARCH_MMD.name], max_width, max_height
    )
    expected_seq = arch_report._scale_image_to_box(
        rendered[arch_report.SEQ_MMD.name], max_width, max_height
    )

    assert arch_picture.width == pytest.approx(expected_arch[0])
    assert arch_picture.height == pytest.approx(expected_arch[1])
    assert seq_picture.width == pytest.approx(expected_seq[0])
    assert seq_picture.height == pytest.approx(expected_seq[1])
