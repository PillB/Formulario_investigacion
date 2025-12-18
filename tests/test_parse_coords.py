import importlib

import pytest

from analytics.usage_visualizer import _parse_coords as parse_usage_coords

try:
    visualizer_module = importlib.import_module("analytics.visualizer")
    parse_visualizer_coords = visualizer_module._parse_coords
except ModuleNotFoundError:
    parse_visualizer_coords = None


def test_parse_coords_accepts_serialized_strings():
    value = "120.0,340.0"
    assert parse_usage_coords(value) == (120.0, 340.0)
    if parse_visualizer_coords:
        assert parse_visualizer_coords(value) == (120.0, 340.0)


def test_parse_coords_rejects_invalid_numbers():
    assert parse_usage_coords("nan,10") is None
    if parse_visualizer_coords:
        assert parse_visualizer_coords("inf,10") is None
        assert parse_visualizer_coords("  ") is None
    assert parse_usage_coords(None) is None
