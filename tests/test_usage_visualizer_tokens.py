from analytics.usage_visualizer import infer_screen


def test_infer_screen_prefers_logical_widget_id():
    row = {"widget_id": "tab.riesgos.field.exposicion", "mensaje": ""}
    assert infer_screen(row) == "riesgos"


def test_infer_screen_still_uses_message_when_needed():
    row = {"widget_id": "", "mensaje": "alerta temprana generada"}
    assert infer_screen(row) == "alertas"
