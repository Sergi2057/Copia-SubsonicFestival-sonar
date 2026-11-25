# ms-espacios/config/database.py
# Conexión a PostgreSQL (espacios_db) mediante SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config
from config.settings import BASE_DIR, DATABASE_URL
from model.models import Base, TipoEspacio

# SQLite solo se usa en los tests (sin Docker); en local y en contenedor es PostgreSQL
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Catálogo fijo de tipos de espacio
TIPOS_ESPACIO = [
    ("ESCENARIO", "Escenario", False),
    ("FOOD_BEVERAGE", "Food & Beverage", True),
    ("MERCHANDISING", "Merchandising", True),
    ("ACAMPADA", "Acampada", True),
    ("VIP", "Zona VIP", True),
    ("SERVICIOS", "Servicios", True),
]


def crear_tablas():
    """Aplica las migraciones y carga el catálogo fijo de tipos de espacio."""
    configuracion = Config(str(BASE_DIR / "alembic.ini"))
    with engine.begin() as conexion:
        configuracion.attributes["connection"] = conexion
        command.upgrade(configuracion, "head")

    db = SessionLocal()
    try:
        for codigo, nombre, alquilable in TIPOS_ESPACIO:
            if not db.get(TipoEspacio, codigo):
                db.add(TipoEspacio(codigo=codigo, nombre=nombre, alquilable=alquilable))
        db.commit()
    finally:
        db.close()


def get_db():
    """Dependencia de FastAPI: una sesión por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
