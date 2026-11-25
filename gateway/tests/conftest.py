# gateway/tests/conftest.py
# Los microservicios se sustituyen por un transporte simulado de httpx: no hace falta Docker
import os
import sys
from pathlib import Path

import httpx
import pytest

os.environ["MODO_AUTENTICACION"] = "desarrollo"
os.environ["TIENDA_URL"] = "http://ms-tienda:8004"
os.environ["CORS_ORIGENES"] = "http://localhost:5173"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402


class ServiciosFalsos:
    """Guarda las peticiones que reenvía el gateway y responde lo que diga cada test."""

    def __init__(self):
        self.peticiones: list[httpx.Request] = []
        self.responder = lambda peticion: httpx.Response(200, json={"ok": True})

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        self.peticiones.append(peticion)
        return self.responder(peticion)

    @property
    def ultima(self) -> httpx.Request:
        return self.peticiones[-1]


@pytest.fixture
def servicios():
    return ServiciosFalsos()


@pytest.fixture
def cliente_http(servicios):
    app.state.cliente = httpx.AsyncClient(transport=httpx.MockTransport(servicios))
    with TestClient(app) as cliente:
        yield cliente
    del app.state.cliente
