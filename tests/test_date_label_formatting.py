"""Ensure date labels present format hints on separate lines."""

import inspect

from ui.frames import case, norm, products, team


def _module_source(module) -> str:
    return inspect.getsource(module)


def test_case_frame_date_labels_use_multiline_text():
    source = _module_source(case)
    assert "Ocurrencia:\\n(YYYY-MM-DD)" in source
    assert "Descubrimiento:\\n(YYYY-MM-DD)" in source


def test_product_frame_date_labels_use_multiline_text():
    source = _module_source(products)
    assert "Fecha de ocurrencia:\\n(YYYY-MM-DD)" in source
    assert "Fecha de descubrimiento:\\n(YYYY-MM-DD)" in source


def test_norm_frame_date_labels_use_multiline_text():
    source = _module_source(norm)
    assert "Fecha de vigencia:\\n(YYYY-MM-DD)" in source


def test_team_frame_date_labels_use_multiline_text():
    source = _module_source(team)
    assert "Fecha carta inmediatez:\\n(YYYY-MM-DD)" in source
    assert "Fecha carta renuncia:\\n(YYYY-MM-DD)" in source
