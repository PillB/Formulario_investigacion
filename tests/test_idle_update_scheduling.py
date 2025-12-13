from app import FraudCaseApp


class TkStub:
    def __init__(self):
        self.update_calls = 0
        self.after_idle_calls = []
        self.height = 600
        self.req_height = 580

    def update_idletasks(self):
        self.update_calls += 1

    def after_idle(self, callback):
        self.after_idle_calls.append(callback)
        return f"job-{len(self.after_idle_calls)}"

    def winfo_height(self):
        return self.height

    def winfo_reqheight(self):
        return self.req_height


class WrapperStub:
    def __init__(self):
        self.grid_calls = 0

    def grid(self):
        self.grid_calls += 1


class ScrollableStub:
    def __init__(self):
        self._scroll_refresh_pending = False
        self._scroll_refresh_height = None



def test_idle_updates_are_deferred_during_tab_transitions():
    tk_stub = TkStub()
    app = FraudCaseApp.__new__(FraudCaseApp)
    app.root = tk_stub
    app._pending_idle_update = False
    app._clients_row_weights = {
        "expanded": {"summary": 1, "detail": 1},
        "default": {"summary": 1, "detail": 1},
    }
    app.clients_detail_wrapper = WrapperStub()
    app._clients_detail_visible = False
    app._apply_clients_row_weights = lambda *_, **__: None
    app.clients_scrollable = None
    app.clients_toggle_btn = None

    app.show_clients_detail()

    scrollable = ScrollableStub()
    app._refresh_scrollable(scrollable, max_height=200)

    app._safe_update_idletasks()
    app._safe_update_idletasks()

    assert tk_stub.update_calls == 0
    assert len(tk_stub.after_idle_calls) >= 2
