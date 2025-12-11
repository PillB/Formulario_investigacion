"""Tests for the wireframe generation utility."""

from pathlib import Path

import csv
import re

import pytest

from wireframes.generate_wireframes import _mermaid_cli_renderer, generate_assets


@pytest.fixture()
def sample_mermaid_files(tmp_path: Path) -> list[str]:
    files = []
    for idx in range(2):
        filename = f"tab0{idx + 1}_sample.mmd"
        path = tmp_path / filename
        path.write_text(
            "graph TD\n" f"  A{idx}[Sample node {idx}] --> B{idx}[Child {idx}]\n", encoding="utf-8"
        )
        files.append(filename)
    return files


@pytest.fixture()
def sample_sketch_layouts(sample_mermaid_files: list[str]) -> dict[str, dict[str, list[str]]]:
    layouts = {}
    for name in sample_mermaid_files:
        stem = Path(name).stem
        layouts[stem] = {
            "__title__": f"Sketch for {stem}",
            "Bloques": ["Elemento A", "Elemento B"],
        }
    return layouts


@pytest.fixture()
def pillow_renderer():
    def _render(source: Path, target: Path) -> None:
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (400, 120), color="white")
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), source.read_text(encoding="utf-8"), fill="black")
        image.save(target, format="PNG")

    return _render


def test_generate_assets_creates_png_pdf_and_manifest(
    tmp_path: Path,
    sample_mermaid_files: list[str],
    pillow_renderer,
    sample_sketch_layouts: dict[str, dict[str, list[str]]],
) -> None:
    generate_assets(
        base_dir=tmp_path,
        mmd_files=sample_mermaid_files,
        renderer=pillow_renderer,
        sketch_layouts=sample_sketch_layouts,
    )

    for filename in sample_mermaid_files:
        png_path = (tmp_path / filename).with_suffix(".png")
        assert png_path.exists(), f"PNG not created for {filename}"

        sketch_path = (tmp_path / Path(filename).with_suffix(".png").name).with_stem(
            f"{Path(filename).stem}_sketch"
        )
        assert sketch_path.exists(), "Sketch wireframe not created"

    pdf_path = tmp_path / "wireframes.pdf"
    assert pdf_path.exists(), "PDF was not created"

    manifest_path = tmp_path / "wireframes_manifest.csv"
    assert manifest_path.exists(), "Manifest CSV was not created"

    rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    assert len(rows) == (len(sample_mermaid_files) * 2) + 1  # png + sketch per file + pdf
    assert {row["asset_type"] for row in rows} == {"png", "pdf", "sketch"}


def test_generate_assets_logs_and_architecture_table(
    tmp_path: Path,
    sample_mermaid_files: list[str],
    pillow_renderer,
    sample_sketch_layouts: dict[str, dict[str, list[str]]],
) -> None:
    generate_assets(
        base_dir=tmp_path,
        mmd_files=sample_mermaid_files,
        renderer=pillow_renderer,
        sketch_layouts=sample_sketch_layouts,
    )

    log_path = tmp_path / "wireframes_generation.log"
    assert log_path.exists(), "Log file not created"
    log_text = log_path.read_text(encoding="utf-8")
    for name in sample_mermaid_files:
        assert name.replace(".mmd", ".png") in log_text
        assert f"{Path(name).stem}_sketch.png" in log_text
    assert "wireframes.pdf" in log_text

    architecture_path = tmp_path / "wireframe_architecture.csv"
    assert architecture_path.exists(), "Architecture CSV not created"
    table_rows = list(csv.DictReader(architecture_path.open(encoding="utf-8")))
    assert [row["mermaid_file"] for row in table_rows] == sample_mermaid_files
    iso8601_log_line = re.compile(r"^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    assert iso8601_log_line.search(log_text)


def test_generate_assets_falls_back_to_placeholder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", "")
    source = tmp_path / "example.mmd"
    source.write_text("graph TD; A-->B;", encoding="utf-8")

    generate_assets(base_dir=tmp_path, mmd_files=[source.name], renderer=None)

    placeholder = source.with_suffix(".png")
    assert placeholder.exists(), "Placeholder PNG should be generated when mmdc is missing"

    log_text = (tmp_path / "wireframes_generation.log").read_text(encoding="utf-8")
    assert "WARNING" in log_text


def test_mermaid_renderer_uses_scale(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    monkeypatch.setattr("wireframes.generate_wireframes.shutil.which", lambda _: "/usr/bin/mmdc")

    def fake_run(cmd, check):
        commands.append(cmd)
        class _Result:
            pass

        return _Result()

    renderer = _mermaid_cli_renderer(scale=3.0, run_process=fake_run)
    renderer(tmp_path / "example.mmd", tmp_path / "example.png")

    assert commands, "Renderer did not invoke CLI"
    assert "-s" in commands[0] and "3.0" in commands[0], "CLI did not receive scale flag"
