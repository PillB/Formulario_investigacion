import types

from app import FraudCaseApp
from settings import CANAL_LIST, PROCESO_LIST, TAXONOMIA
from tests.stubs import DummyVar


class _ComboStub:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


class _ProductStub:
    def __init__(self, idx):
        self.idx = idx
        self.cat1_var = DummyVar("")
        self.cat2_var = DummyVar("")
        self.mod_var = DummyVar("")
        self.fecha_oc_var = DummyVar("")
        self.fecha_desc_var = DummyVar("")
        self.canal_var = DummyVar("")
        self.proceso_var = DummyVar("")
        self.cat2_cb = _ComboStub()
        self.mod_cb = _ComboStub()
        self.canal_cb = _ComboStub()
        self.proc_cb = _ComboStub()
        self._suppress_change_notifications = False
        self.focus_called = False

    def on_cat1_change(self):
        return None

    def on_cat2_change(self):
        return None

    def focus_first_field(self):
        self.focus_called = True


class _ProductStubWithCallbacks(_ProductStub):
    def __init__(self, idx, *, misalign_modalidad=False):
        super().__init__(idx)
        self.misalign_modalidad = misalign_modalidad
        self.cat1_calls = []
        self.cat2_calls = []

    def on_cat1_change(self):
        self.cat1_calls.append(self.cat1_var.get())

    def on_cat2_change(self):
        self.cat2_calls.append(self.cat2_var.get())
        if self.misalign_modalidad:
            self.mod_var.set("otra modalidad")


def test_inheritance_creation_matches_manual_copy(monkeypatch):
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.logs = []
    app.product_frames = []
    app._suppress_messagebox = True
    app._schedule_summary_refresh = lambda *_args, **_kwargs: None

    cat1 = list(TAXONOMIA.keys())[0]
    cat2 = list(TAXONOMIA[cat1].keys())[0]
    modalidad = TAXONOMIA[cat1][cat2][0]
    canal = CANAL_LIST[0]
    proceso = PROCESO_LIST[0]
    app.cat_caso1_var = DummyVar(cat1)
    app.cat_caso2_var = DummyVar(cat2)
    app.mod_caso_var = DummyVar(modalidad)
    app.fecha_caso_var = DummyVar("2024-01-01")
    app.fecha_descubrimiento_caso_var = DummyVar("2024-01-02")
    app.canal_caso_var = DummyVar(canal)
    app.proceso_caso_var = DummyVar(proceso)

    def _add_product(self, initialize_rows=True):
        frame = _ProductStub(len(self.product_frames))
        self.product_frames.append(frame)
        return frame

    app.add_product = types.MethodType(_add_product, app)

    product_frame = app.add_product_inheriting_case()

    assert product_frame.cat1_var.get() == cat1
    assert product_frame.cat2_var.get() == cat2
    assert product_frame.mod_var.get() == modalidad
    assert product_frame.fecha_oc_var.get() == "2024-01-01"
    assert product_frame.fecha_desc_var.get() == "2024-01-02"
    assert product_frame.canal_var.get() == canal
    assert product_frame.proceso_var.get() == proceso
    assert product_frame.focus_called

    manual_product = _ProductStub(1)
    manual_product.cat1_var.set(cat1)
    manual_product.cat2_var.set(cat2)
    manual_product.mod_var.set(modalidad)
    manual_product.fecha_oc_var.set("2024-01-01")
    manual_product.fecha_desc_var.set("2024-01-02")
    manual_product.canal_var.set(canal)
    manual_product.proceso_var.set(proceso)

    assert manual_product.cat1_var.get() == product_frame.cat1_var.get()
    assert manual_product.fecha_desc_var.get() == product_frame.fecha_desc_var.get()


def test_inherited_modalidad_alignment_and_warning(monkeypatch):
    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr("app.messagebox.showwarning", lambda title, message: warnings.append((title, message)))

    def _build_app():
        app = FraudCaseApp.__new__(FraudCaseApp)
        app.logs = []
        app.product_frames = []
        app._suppress_messagebox = False
        app._schedule_summary_refresh = lambda *_args, **_kwargs: None
        return app

    cat1 = list(TAXONOMIA.keys())[0]
    cat2 = list(TAXONOMIA[cat1].keys())[0]
    modalidad = TAXONOMIA[cat1][cat2][0]
    canal = CANAL_LIST[0]
    proceso = PROCESO_LIST[0]

    app = _build_app()
    app.cat_caso1_var = DummyVar(cat1)
    app.cat_caso2_var = DummyVar(cat2)
    app.mod_caso_var = DummyVar(modalidad)
    app.fecha_caso_var = DummyVar("2024-01-01")
    app.fecha_descubrimiento_caso_var = DummyVar("2024-01-02")
    app.canal_caso_var = DummyVar(canal)
    app.proceso_caso_var = DummyVar(proceso)

    def _add_aligned(self, initialize_rows=True, user_initiated=False):
        frame = _ProductStubWithCallbacks(len(self.product_frames), misalign_modalidad=False)
        self.product_frames.append(frame)
        return frame

    app.add_product = types.MethodType(_add_aligned, app)
    aligned_product = app.add_product_inheriting_case()
    assert aligned_product.mod_var.get() == modalidad
    assert not warnings

    warnings.clear()
    app.logs.clear()

    def _add_misaligned(self, initialize_rows=True, user_initiated=False):
        frame = _ProductStubWithCallbacks(len(self.product_frames), misalign_modalidad=True)
        self.product_frames.append(frame)
        return frame

    app.add_product = types.MethodType(_add_misaligned, app)
    misaligned_product = app.add_product_inheriting_case()

    assert misaligned_product.mod_var.get() != modalidad
    assert warnings
    assert any(log["tipo"] == "herencia" and "desalineado" in log["mensaje"] for log in app.logs)
