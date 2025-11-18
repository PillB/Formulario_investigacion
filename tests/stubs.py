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


class BaseFrameStub:
    def __init__(self):
        self.id_var = DummyVar("")
        self.on_id_change_calls = []
        self.populated_rows = []

    def on_id_change(self, **kwargs):
        self.on_id_change_calls.append(kwargs)


class ClientFrameStub(BaseFrameStub):
    pass


class TeamFrameStub(BaseFrameStub):
    pass


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


class InvolvementRowStub:
    def __init__(self):
        self.team_var = DummyVar("")
        self.monto_var = DummyVar("")


def build_slot_factory(container, factory):
    def _obtain(self):
        frame = factory()
        container.append(frame)
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


def build_populate_method(id_field):
    def _populate(self, frame, row, preserve_existing=False):
        value = (row.get(id_field) or "").strip()
        frame.id_var.set(value)
        frame.populated_rows.append(dict(row))

    return _populate
