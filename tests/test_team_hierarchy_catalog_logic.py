import pytest

from models import TeamHierarchyCatalog
from models.static_team_catalog import build_team_catalog_rows
from tests.test_validation import _UIStubWidget, _patch_team_module


CUSTOM_HIERARCHY = {
    "D1": {
        "nbr": "División Uno",
        "areas": {
            "A1": {
                "abr": "Área Uno",
                "services": {
                    "S1": {
                        "nbr": "Servicio Uno",
                        "positions": {
                            "P1": "Puesto Uno",
                        },
                    }
                },
            }
        },
    }
}

AGENCY_MAP = {"Agencia Central": "C001"}


def _build_catalog():
    rows = build_team_catalog_rows(CUSTOM_HIERARCHY, AGENCY_MAP)
    return TeamHierarchyCatalog(rows, CUSTOM_HIERARCHY)


def _build_frame(monkeypatch, catalog=None):
    team_module, _ = _patch_team_module(monkeypatch)
    frame = team_module.TeamMemberFrame(
        parent=_UIStubWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        update_team_options=lambda: None,
        team_lookup={},
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
        team_catalog=catalog or _build_catalog(),
    )
    return frame


def test_hierarchy_exposes_dictionary_data_and_global_agencies():
    catalog = _build_catalog()

    divisions = catalog.list_hierarchy_divisions()
    assert divisions == [("D1", "División Uno")]

    areas = catalog.list_hierarchy_areas("División Uno")
    assert areas == [("A1", "Área Uno")]

    services = catalog.list_hierarchy_services("División Uno", "Área Uno")
    assert services == [("S1", "Servicio Uno")]

    roles = catalog.list_hierarchy_roles("División Uno", "Área Uno", "Servicio Uno")
    assert roles == [("P1", "Puesto Uno")]

    agency_names = catalog.list_agency_names("División Uno", "Área Uno")
    agency_codes = catalog.list_agency_codes("División Uno", "Área Uno")
    assert agency_names == ["Agencia Central"]
    assert agency_codes == ["C001"]

    agency_by_name = catalog.match_agency_by_name("División Uno", "Área Uno", "Agencia Central")
    agency_by_code = catalog.match_agency_by_code("División Uno", "Área Uno", "C001")
    assert agency_by_name == {"nombre": "Agencia Central", "codigo": "C001", "area": "Área Uno"}
    assert agency_by_code == {"nombre": "Agencia Central", "codigo": "C001", "area": "Área Uno"}


def test_division_and_area_selection_populates_children(monkeypatch):
    frame = _build_frame(monkeypatch)

    frame.division_var.set("División Uno")
    frame._on_division_change()

    assert "Área Uno" in frame._area_combo["values"]
    assert frame._area_combo._config.get("state") == "readonly"

    frame.area_var.set("Área Uno")
    frame._on_area_change()

    assert "Servicio Uno" in frame._servicio_combo["values"]

    frame.servicio_var.set("Servicio Uno")
    frame._on_service_change()

    assert "Puesto Uno" in frame._puesto_combo["values"]


def test_agency_fields_and_sync_logic(monkeypatch):
    frame = _build_frame(monkeypatch)

    # Agency fields stay enabled even without division/area
    assert frame._agencia_nombre_combo._config.get("state") == "normal"
    assert frame._agencia_codigo_combo._config.get("state") == "normal"

    # Cover recursion guard explicitly
    frame._agency_sync_in_progress = True
    frame.nombre_agencia_var.set("Agencia Central")
    frame.codigo_agencia_var.set("")
    frame._sync_agency_pair(source="nombre")
    assert frame.codigo_agencia_var.get() == ""
    frame._agency_sync_in_progress = False

    # Sync from name to code and back without bouncing
    frame.nombre_agencia_var.set("Agencia Central")
    frame._on_agency_name_change()
    assert frame.codigo_agencia_var.get() == "C001"

    frame.codigo_agencia_var.set("C001")
    frame._on_agency_code_change()
    assert frame.nombre_agencia_var.get() == "Agencia Central"

    # Changing code again should not flip the name back and forth
    frame.codigo_agencia_var.set("C001")
    frame._on_agency_code_change()
    assert frame.nombre_agencia_var.get() == "Agencia Central"
