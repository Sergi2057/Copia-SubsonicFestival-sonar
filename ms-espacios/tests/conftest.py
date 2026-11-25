# ms-espacios/tests/conftest.py
# Los tests usan una BD SQLite temporal para no depender de Docker
import os
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import text

_bd = Path(tempfile.mkdtemp()) / "espacios_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_bd.as_posix()}"
os.environ["RABBITMQ_URL"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from config.database import engine  # noqa: E402
from main import app  # noqa: E402
from model.models import Base  # noqa: E402

ADMIN = {"X-User-Id": "admin-1", "X-User-Rol": "admin"}
CLIENTE = {"X-User-Id": "cliente-1", "X-User-Rol": "cliente"}
OTRO_CLIENTE = {"X-User-Id": "cliente-2", "X-User-Rol": "cliente"}


@pytest.fixture
def cliente_http():
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conexion:
        conexion.execute(text("DROP TABLE IF EXISTS alembic_version"))
    with TestClient(app) as c:
        yield c
PROVEEDOR = {"X-User-Id": "prov-1", "X-User-Rol": "PROVEEDOR"}  # el rol puede venir en mayúsculas
SERVICIO = {"X-Service-Token": "token-servicio-dev"}
