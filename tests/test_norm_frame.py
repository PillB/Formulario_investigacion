import pytest

from ui.frames import norm
from tests.test_clients_frame import DummyVar, DummyWidget, RecordingValidator
from ui.frames import norm


@pytest.fixture(autouse=True)
def patch_norm_widgets(monkeypatch):
    class _TkStub:
        StringVar = DummyVar

    class _TtkStub:
        LabelFrame = DummyWidget
        Frame = DummyWidget
        Label = DummyWidget
        Entry = DummyWidget
        Button = DummyWidget

    monkeypatch.setattr(norm, "tk", _TkStub())
    monkeypatch.setattr(norm, "ttk", _TtkStub())
    RecordingValidator.instances.clear()
    monkeypatch.setattr(norm, "FieldValidator", RecordingValidator)
    yield
    RecordingValidator.instances.clear()


def _build_norm_frame():
    return norm.NormFrame(
        parent=DummyWidget(),
        idx=0,
        remove_callback=lambda _frame: None,
        logs=[],
        tooltip_register=lambda *_args, **_kwargs: None,
        change_notifier=None,
    )


def _find_validator(label_fragment):
    for validator in RecordingValidator.instances:
        if label_fragment in validator.field_name:
            return validator
    return None


def test_norm_frame_fecha_validator_requires_value():
    frame = _build_norm_frame()

    fecha_validator = _find_validator("Fecha")
    assert fecha_validator is not None

    frame.fecha_var.set("")
    error = fecha_validator.validate_callback()
    assert error is not None
    assert "fecha de vigencia" in error.lower()

    frame.fecha_var.set("2023-01-01")
    assert fecha_validator.validate_callback() is None


def test_norm_frame_autofills_from_lookup(monkeypatch):
    frame = _build_norm_frame()
    frame.set_lookup({"123": {"descripcion": "Desde catálogo", "fecha_vigencia": "2024-03-01"}})

    frame.id_var.set("123")
    frame.on_id_change(from_focus=True)

    assert frame.descripcion_var.get() == "Desde catálogo"
    assert frame.fecha_var.get() == "2024-03-01"


def test_norm_frame_preserves_manual_fields_with_preserve_flag():
    frame = _build_norm_frame()
    frame.set_lookup({"321": {"descripcion": "Catálogo", "fecha_vigencia": "2024-05-05"}})
    frame.descripcion_var.set("Manual")
    frame.id_var.set("321")

    frame.on_id_change(preserve_existing=True)

    assert frame.descripcion_var.get() == "Manual"
    assert frame.fecha_var.get() == "2024-05-05"


def test_norm_frame_shows_message_for_missing_lookup(monkeypatch):
    frame = _build_norm_frame()
    captured = []
    monkeypatch.setattr(norm.messagebox, "showerror", lambda *args: captured.append(args))

    frame.id_var.set("999")
    frame.on_id_change(from_focus=True)
    assert captured == []

    frame.set_lookup({"111": {"descripcion": "x"}})
    frame.id_var.set("999")
    frame.on_id_change(from_focus=True)
    assert captured and "Norma no encontrada" in captured[0][0]
