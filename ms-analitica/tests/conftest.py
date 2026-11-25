# ms-analitica/tests/conftest.py
# Los tests usan MongoDB en memoria (mongomock) y la caché en memoria: no hace falta Docker
import os
import sys
from pathlib import Path

import pytest

os.environ["MONGO_URL"] = "mongomock://"
os.environ["REDIS_URL"] = ""
os.environ["RABBITMQ_URL"] = ""  # sin RabbitMQ: el consumidor no arranca
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from config.database import get_db  # noqa: E402
from main import app  # noqa: E402

ADMIN = {"X-User-Id": "admin-1", "X-User-Rol": "ADMIN"}
CLIENTE = {"X-User-Id": "cliente-1", "X-User-Rol": "CLIENTE"}
PROVEEDOR = {"X-User-Id": "prov-1", "X-User-Rol": "PROVEEDOR"}


@pytest.fixture
def cliente_http():
    from service import cache
    db = get_db()
    for nombre in db.list_collection_names():
        db.drop_collection(nombre)
    cache._memoria.clear()
    with TestClient(app) as c:
        yield c
