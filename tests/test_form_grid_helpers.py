from ui.frames import utils


class _GridStub:
    def __init__(self):
        self.column_weights = []
        self.row_weights = []
        self._grid_last_kwargs = {}

    def columnconfigure(self, index, weight=0):
        self.column_weights.append((index, weight))

    def rowconfigure(self, index, weight=0):
        self.row_weights.append((index, weight))

    def winfo_manager(self):
        return "grid"


def test_build_two_column_form_sets_uniform_weights(monkeypatch):
    parent = _GridStub()
    created = {}

    def _fake_label_frame(target_parent, text=""):
        frame = _GridStub()
        frame.label_text = text
        created["frame"] = frame
        return frame

    monkeypatch.setattr(utils.ttk, "LabelFrame", _fake_label_frame)

    form = utils.build_two_column_form(parent, label_text="Demo")

    assert form is created["frame"]
    assert (0, 0) in form.column_weights
    assert (1, 1) in form.column_weights
    assert form._grid_last_kwargs["padx"] == utils.COL_PADX
    assert form._grid_last_kwargs["pady"] == utils.ROW_PADY


def test_grid_labeled_widget_sets_padding_and_stretch(monkeypatch):
    form = _GridStub()
    label = _GridStub()
    field = _GridStub()

    utils.grid_labeled_widget(form, row=5, label_widget=label, field_widget=field)

    assert label._grid_last_kwargs["row"] == 5
    assert label._grid_last_kwargs["sticky"] == "e"
    assert field._grid_last_kwargs["column"] == 1
    assert field._grid_last_kwargs["sticky"] == "we"
    assert (1, 1) in form.column_weights
