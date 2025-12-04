from tests.test_validation import _UIStubWidget, _patch_team_module


def _build_frame(monkeypatch):
    team_module, _ = _patch_team_module(monkeypatch)
    frame = team_module.TeamMemberFrame(
        parent=_UIStubWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        update_team_options=lambda: None,
        team_lookup={},
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
    )
    return frame


def test_cascade_for_division_without_area(monkeypatch):
    frame = _build_frame(monkeypatch)

    frame.division_var.set("48532")
    frame._on_division_change()

    area_values = frame._area_combo["values"]
    assert "GERENCIA DE VENTAS TRANSACCIONALES I" in area_values
    assert frame._area_combo._config.get("state") == "readonly"

    frame.area_var.set("GERENCIA DE VENTAS TRANSACCIONALES I")
    frame._on_area_change()

    service_values = frame._servicio_combo["values"]
    assert "GERENCIA DE VENTAS TRANSACCIONALES I" in service_values

    frame.servicio_var.set("GERENCIA DE VENTAS TRANSACCIONALES I")
    frame._on_service_change()

    puesto_values = frame._puesto_combo["values"]
    assert "EJECUTIVO DE VENTAS PYME" in puesto_values


def test_cascade_preserves_valid_selections(monkeypatch):
    frame = _build_frame(monkeypatch)

    frame.division_var.set("2036")
    frame._on_division_change()

    area_choice = "AREA COMERCIAL LIMA 1"
    service_choice = "AREA LIMA 1 - REGION 62"

    frame.area_var.set(area_choice)
    frame._on_area_change()
    frame.servicio_var.set(service_choice)
    frame._on_service_change()

    assert "GERENTE DE AGENCIA" in frame._puesto_combo["values"]

    frame._on_division_change()

    assert frame.area_var.get() == area_choice
    assert frame.servicio_var.get() == service_choice
