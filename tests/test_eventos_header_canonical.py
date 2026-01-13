import settings


def test_eventos_header_canonical_has_expected_column_names():
    header = settings.EVENTOS_HEADER_CANONICO_START

    assert "tipo_moneda" in header
    assert "tipo_sancion" in header
    assert "codigo_analitica" in header
    assert "fecha_ocurrencia_caso" in header
    assert "fecha_descubrimiento_caso" in header

    assert "tipo_monead" not in header
    assert "tipo_de_sanction" not in header
    assert "codino_analitica" not in header
    assert "fecha_de_ocurrencia" not in header
    assert "fecha_de_descubrimiento" not in header
