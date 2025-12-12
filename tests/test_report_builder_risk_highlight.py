from pathlib import Path

import pytest

import report_builder
from docx.oxml.ns import qn
from tests.test_report_builder import sample_case_data as base_sample_case_data


@pytest.fixture
def sample_case_data():
    return base_sample_case_data.__wrapped__()


@pytest.mark.skipif(not report_builder.DOCX_AVAILABLE, reason="python-docx is required")
def test_risk_rows_with_nuevo_riesgo_are_highlighted(tmp_path: Path, sample_case_data):
    docx = pytest.importorskip("docx")

    def _cell_fill(cell) -> str | None:
        tc_pr = getattr(cell._element, "tcPr", None)
        if tc_pr is None:
            return None
        shading = tc_pr.find(qn("w:shd"))
        return shading.get(qn("w:fill")) if shading is not None else None

    sample_case_data.riesgos[0]["criticidad"] = "Nuevo Riesgo"
    sample_case_data.riesgos.append(
        {
            "id_riesgo": "R-2",
            "lider": "Lead 2",
            "criticidad": "Alta",
            "exposicion_residual": "2000",
            "planes_accion": "Mitigar",
        }
    )

    output = tmp_path / "nuevo_riesgo.docx"
    report_builder.build_docx(sample_case_data, output)

    document = docx.Document(output)
    risk_table = document.tables[3]

    highlighted_row = risk_table.rows[1]
    highlighted_fills = {_cell_fill(cell) for cell in highlighted_row.cells}
    assert "FFEBEE" in {fill.upper() for fill in highlighted_fills if fill}

    zebra_row = risk_table.rows[2]
    zebra_fills = {_cell_fill(cell) for cell in zebra_row.cells}
    assert "F5F5F5" in {fill.upper() for fill in zebra_fills if fill}
