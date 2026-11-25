# ms-tienda/tests/conftest.py
# Los tests usan una BD SQLite temporal para no depender de Docker
import os
import sys
import tempfile
from pathlib import Path

import pytest

_bd = Path(tempfile.mkdtemp()) / "tienda_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_bd.as_posix()}"
os.environ["RABBITMQ_URL"] = ""  # sin RabbitMQ: los eventos van al log y el consumidor no arranca
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from config.database import SessionLocal, engine  # noqa: E402
from main import app  # noqa: E402
from model.models import Base  # noqa: E402

ADMIN = {"X-User-Id": "admin-1", "X-User-Rol": "ADMIN"}  # el rol puede venir en mayúsculas
CLIENTE = {"X-User-Id": "cliente-1", "X-User-Rol": "cliente"}
OTRO_CLIENTE = {"X-User-Id": "cliente-2", "X-User-Rol": "cliente"}


@pytest.fixture
def cliente_http():
    # BD vacía en cada test: al arrancar, la app aplica las migraciones (alembic upgrade head)
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conexion:
        conexion.execute(text("DROP TABLE IF EXISTS alembic_version"))
    with TestClient(app) as c:
        yield c


def habilitar_recogida(evento_id: str = "evento-belgium", estado: str = "PUBLICADO") -> None:
    """Como si hubiera llegado espacios.evento.publicado (o .cancelado) de ms-espacios."""
    from service import pedido_service
    db = SessionLocal()
    try:
        pedido_service.al_cambiar_estado_evento(db, evento_id, estado)
    finally:
        db.close()
