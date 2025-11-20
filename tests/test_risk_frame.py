import pytest

from tests.test_clients_frame import DummyVar, DummyWidget, RecordingValidator
from ui.frames import risk


@pytest.fixture(autouse=True)
def patch_risk_widgets(monkeypatch):
    class _TkStub:
        StringVar = DummyVar

    class _TtkStub:
        LabelFrame = DummyWidget
        Frame = DummyWidget
        Label = DummyWidget
        Entry = DummyWidget
        Button = DummyWidget
        Combobox = DummyWidget

    monkeypatch.setattr(risk, "tk", _TkStub())
    monkeypatch.setattr(risk, "ttk", _TtkStub())
    RecordingValidator.instances.clear()
    monkeypatch.setattr(risk, "FieldValidator", RecordingValidator)
    yield
    RecordingValidator.instances.clear()


def _build_risk_frame():
    return risk.RiskFrame(
        parent=DummyWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
        change_notifier=None,
    )


def test_risk_frame_autofills_from_lookup():
    frame = _build_risk_frame()
    frame.set_lookup(
        {
            "RSK-000001": {
                "lider": "Owner",
                "descripcion": "Desde catálogo",
                "criticidad": "Alto",
                "exposicion_residual": "1200",
                "planes_accion": "Plan A",
            }
        }
    )

    frame.id_var.set("RSK-000001")
    frame.on_id_change(from_focus=True)

    assert frame.lider_var.get() == "Owner"
    assert frame.descripcion_var.get() == "Desde catálogo"
    assert frame.criticidad_var.get() == "Alto"
    assert frame.exposicion_var.get() == "1200"
    assert frame.planes_var.get() == "Plan A"


def test_risk_frame_preserves_manual_fields(monkeypatch):
    frame = _build_risk_frame()
    frame.set_lookup(
        {
            "RSK-000002": {
                "lider": "Catálogo",
                "descripcion": "Desc",
                "criticidad": "Moderado",
            }
        }
    )
    frame.id_var.set("RSK-000002")
    frame.lider_var.set("Manual")

    frame.on_id_change(preserve_existing=True)

    assert frame.lider_var.get() == "Manual"
    assert frame.descripcion_var.get() == "Desc"


def test_risk_frame_shows_message_for_missing_lookup(monkeypatch):
    frame = _build_risk_frame()
    captured = []
    monkeypatch.setattr(risk.messagebox, "showerror", lambda *args: captured.append(args))

    frame.id_var.set("RSK-999999")
    frame.on_id_change(from_focus=True)
    assert captured == []

    frame.set_lookup({"RSK-000003": {"descripcion": "X"}})
    frame.id_var.set("RSK-999999")
    frame.on_id_change(from_focus=True)
    assert captured and "Riesgo no encontrado" in captured[0][0]
