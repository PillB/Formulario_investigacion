"""Configuración compartida para las pruebas de la aplicación."""

import os
import sys
import pytest

import app as app_module


class MessageboxSpy:
    """Registra las llamadas a los diálogos estándar de Tkinter."""

    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def showinfo(self, title, message):
        self.infos.append((title, message))

    def showwarning(self, title, message):
        self.warnings.append((title, message))

    def showerror(self, title, message):
        self.errors.append((title, message))


@pytest.fixture
def messagebox_spy(monkeypatch):
    """Reemplaza ``messagebox`` para capturar mensajes durante las pruebas."""

    spy = MessageboxSpy()
    monkeypatch.setattr(app_module.messagebox, "showinfo", spy.showinfo)
    monkeypatch.setattr(app_module.messagebox, "showwarning", spy.showwarning)
    monkeypatch.setattr(app_module.messagebox, "showerror", spy.showerror)
    monkeypatch.setattr(app_module.messagebox, "askyesno", lambda *_, **__: True)
    return spy


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
