from types import SimpleNamespace

from app import FraudCaseApp


class DummyVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


def _build_team_frame():
    return SimpleNamespace(
        id_var=DummyVar(""),
        flag_var=DummyVar(""),
        division_var=DummyVar(""),
        area_var=DummyVar(""),
        servicio_var=DummyVar(""),
        puesto_var=DummyVar(""),
        nombre_agencia_var=DummyVar(""),
        codigo_agencia_var=DummyVar(""),
        tipo_falta_var=DummyVar(""),
        tipo_sancion_var=DummyVar(""),
        nombres_var=DummyVar(""),
        apellidos_var=DummyVar(""),
        fecha_carta_inmediatez_var=DummyVar(""),
        fecha_carta_renuncia_var=DummyVar(""),
    )


def test_populate_team_frame_preserves_letter_dates_and_names():
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.team_lookup = {}

    frame = _build_team_frame()
    row = {
        "id_colaborador": "t9000",
        "nombres": "Ana",
        "apellidos": "Pérez",
        "division": "Operaciones",
        "area": "Procesos",
        "servicio": "Atención",
        "puesto": "Analista",
        "fecha_carta_inmediatez": "2024-01-15",
        "fecha_carta_renuncia": "2024-02-01",
        "nombre_agencia": "Agencia Sur",
        "codigo_agencia": "123456",
        "tipo_falta": "No aplica",
        "tipo_sancion": "Amonestación",
    }

    app._populate_team_frame_from_row(frame, row)

    assert frame.nombres_var.get() == "Ana"
    assert frame.apellidos_var.get() == "Pérez"
    assert frame.fecha_carta_inmediatez_var.get() == "2024-01-15"
    assert frame.fecha_carta_renuncia_var.get() == "2024-02-01"

    lookup_entry = app.team_lookup.get("T9000")
    assert lookup_entry is not None
    assert lookup_entry["fecha_carta_inmediatez"] == "2024-01-15"
    assert lookup_entry["fecha_carta_renuncia"] == "2024-02-01"
    assert lookup_entry["nombres"] == "Ana"
    assert lookup_entry["apellidos"] == "Pérez"
