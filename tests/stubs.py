from collections import defaultdict


class DummyVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def trace_add(self, *_args, **_kwargs):
        return "trace"

    def trace_remove(self, *_args, **_kwargs):
        return None


class RichTextWidgetStub:
    def __init__(self, text=""):
        self.text = text
        self.tags = defaultdict(list)
        self.images = []
        self.created_images = []

    def get(self, *_args, **_kwargs):
        return self.text

    def insert(self, _index, text):
        self.text = text

    def delete(self, *_args, **_kwargs):
        self.text = ""
        self.tags = defaultdict(list)
        self.images = []
        self.created_images = []

    def tag_names(self):
        return list(self.tags.keys())

    def tag_add(self, tag_name, start, end):
        self.tags[tag_name].append((start, end))

    def tag_ranges(self, tag_name):
        ranges = []
        for start, end in self.tags.get(tag_name, []):
            ranges.extend([start, end])
        return ranges

    def dump(self, *_args, image=False, **_kwargs):
        if not image:
            return []
        return [("image", name, index) for name, index in self.images]

    def image_create(self, index, image=None):
        self.created_images.append((index, image))



class BaseFrameStub:
    def __init__(self):
        self.id_var = DummyVar("")
        self.on_id_change_calls = []
        self.populated_rows = []
        self.id_change_callback = None
        self._last_tracked_id = ""

    def on_id_change(self, **kwargs):
        self.on_id_change_calls.append(kwargs)
        new_id = self.id_var.get().strip()
        if new_id == self._last_tracked_id:
            return
        previous = self._last_tracked_id
        self._last_tracked_id = new_id
        if callable(self.id_change_callback):
            self.id_change_callback(self, previous, new_id)


class ClientFrameStub(BaseFrameStub):
    pass


class TeamFrameStub(BaseFrameStub):
    def __init__(self):
        super().__init__()
        self.nombres_var = DummyVar("")
        self.apellidos_var = DummyVar("")
        self.flag_var = DummyVar("")
        self.division_var = DummyVar("")
        self.area_var = DummyVar("")
        self.servicio_var = DummyVar("")
        self.puesto_var = DummyVar("")
        self.fecha_carta_inmediatez_var = DummyVar("")
        self.fecha_carta_renuncia_var = DummyVar("")
        self.nombre_agencia_var = DummyVar("")
        self.codigo_agencia_var = DummyVar("")
        self.tipo_falta_var = DummyVar("")
        self.tipo_sancion_var = DummyVar("")


class RiskFrameStub(BaseFrameStub):
    def __init__(self):
        super().__init__()
        self.lider_var = DummyVar("")
        self.descripcion_var = DummyVar("")
        self.criticidad_var = DummyVar("")
        self.exposicion_var = DummyVar("")
        self.planes_var = DummyVar("")


class NormFrameStub:
    def __init__(self):
        self.id_var = DummyVar("")
        self.descripcion_var = DummyVar("")
        self.fecha_var = DummyVar("")
        self.acapite_var = DummyVar("")
        self.detalle_var = DummyVar("")
        self._detalle_text = ""

    def _set_detalle_text(self, value: str):
        self._detalle_text = value or ""
        self.detalle_var.set(self._detalle_text)

    def _get_detalle_text(self):
        return self._detalle_text

    @staticmethod
    def _shorten_preview(text: str, max_length: int = 60) -> str:
        clean = " ".join(str(text or "").split())
        if len(clean) <= max_length:
            return clean
        return clean[: max_length - 1].rstrip() + "…"


class ClaimStub:
    def __init__(self):
        self.data = {}
        self.id_var = DummyVar("")

    def set_data(self, payload):
        self.data = dict(payload)
        self.id_var.set(payload.get('id_reclamo', ''))

    def get_data(self):
        return dict(self.data)


class ProductFrameStub(BaseFrameStub):
    def __init__(self):
        super().__init__()
        self.involvements = []
        self.client_involvements = []
        self.claims = []
        self.persisted_lookups = 0

    def find_claim_by_id(self, claim_id):
        for claim in self.claims:
            if claim.data.get('id_reclamo') == claim_id:
                return claim
        return None

    def obtain_claim_slot(self):
        claim = ClaimStub()
        self.claims.append(claim)
        return claim

    def persist_lookup_snapshot(self):
        self.persisted_lookups += 1

    def add_client_involvement(self):
        row = InvolvementRowStub()
        self.client_involvements.append(row)
        return row


class InvolvementRowStub:
    def __init__(self):
        self.client_var = DummyVar("")
        self.team_var = DummyVar("")
        self.monto_var = DummyVar("")


def build_slot_factory(container, factory, *, on_create=None):
    def _obtain(self):
        frame = factory()
        container.append(frame)
        if callable(on_create):
            on_create(self, frame)
        return frame

    return _obtain


def build_involvement_slot():
    def _obtain(self, product_frame):
        for inv in getattr(product_frame, 'involvements', []):
            if not inv.team_var.get().strip():
                return inv
        row = InvolvementRowStub()
        product_frame.involvements.append(row)
        return row

    return _obtain


def build_client_involvement_slot():
    def _obtain(self, product_frame):
        for inv in getattr(product_frame, 'client_involvements', []):
            if not inv.client_var.get().strip():
                return inv
        row = InvolvementRowStub()
        product_frame.client_involvements.append(row)
        return row

    return _obtain


def build_populate_method(id_field):
    def _populate(self, frame, row, preserve_existing=False):
        value = (row.get(id_field) or "").strip()
        if preserve_existing and (frame.id_var.get().strip() or frame.populated_rows):
            if not frame.id_var.get().strip():
                frame.id_var.set(value)
            return
        frame.id_var.set(value)
        for key, raw in (row or {}).items():
            attr_name = f"{key}_var"
            if hasattr(frame, attr_name):
                getattr(frame, attr_name).set((raw or "").strip())
        frame.populated_rows.append(dict(row))

    return _populate
