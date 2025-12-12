import importlib
import importlib.util
import sys

import pytest


def test_styling_helpers_fail_gracefully_without_python_docx(monkeypatch):
    if importlib.util.find_spec("docx"):
        pytest.skip("python-docx instalado: no aplica la ruta de degradación")

    # Asegurar que importamos el módulo limpio para inspeccionar la ruta sin dependencias
    monkeypatch.syspath_prepend("")
    importlib.invalidate_caches()
    sys.modules.pop("report.styling_enhancer", None)

    styling = importlib.import_module("report.styling_enhancer")

    assert styling.DOCX_STYLING_AVAILABLE is False
    assert styling.BCP_DARK_BLUE is None

    dummy_paragraph = type("Paragraph", (), {"runs": []})()
    with pytest.raises(ModuleNotFoundError):
        styling.style_title(dummy_paragraph)
