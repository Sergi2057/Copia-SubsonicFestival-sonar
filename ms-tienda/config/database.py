# ms-tienda/config/database.py
# Conexión a PostgreSQL (tienda_db) mediante SQLAlchemy. El esquema lo crean las migraciones
# de Alembic (carpeta migrations/).
import logging
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from config.settings import BASE_DIR, DATABASE_URL

log = logging.getLogger("database")

# SQLite solo se usa en los tests (sin Docker); en local y en contenedor es PostgreSQL
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Revisión que equivale al esquema que creaba create_all en la semana 1 (sin eventos_recogida)
REVISION_SEMANA_1 = "0001"


def crear_tablas():
    """Aplica las migraciones pendientes (alembic upgrade head), también desde poblar_bd.py."""
    configuracion = Config(str(BASE_DIR / "alembic.ini"))
    with engine.begin() as conexion:
        configuracion.attributes["connection"] = conexion
        tablas = inspect(conexion).get_table_names()
        if "pedidos" in tablas and "alembic_version" not in tablas:
            # BD de la semana 1 (create_all): se marca como 0001 sin tocar los datos y después
            # upgrade añade solo lo nuevo (0002 eventos_recogida, 0003 variantes.activa)
            log.info("BD creada sin Alembic: se marca como revisión %s", REVISION_SEMANA_1)
            command.stamp(configuracion, REVISION_SEMANA_1)
        command.upgrade(configuracion, "head")


def get_db():
    """Dependencia de FastAPI: una sesión por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
