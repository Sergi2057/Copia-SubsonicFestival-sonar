# ms-tienda/tests/test_migraciones.py
# Migraciones de Alembic. Sin Docker: se prueban sobre SQLite y, para PostgreSQL, se revisa el SQL
# que genera "alembic upgrade head --sql" (modo offline, no necesita conexión).
import os
import subprocess
import sys

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

import config.database as database
from config.settings import BASE_DIR
from model.models import Base


def configuracion(conexion):
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.attributes["connection"] = conexion
    return config


def test_upgrade_crea_el_esquema_del_modelo_y_downgrade_lo_borra(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'migraciones.db').as_posix()}")
    try:
        with engine.begin() as conexion:
            config = configuracion(conexion)
            command.upgrade(config, "head")
            command.upgrade(config, "head")  # dos veces: no hace nada
            assert set(inspect(conexion).get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
            assert conexion.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
            # Las migraciones y models.py describen el mismo esquema
            assert compare_metadata(MigrationContext.configure(conexion), Base.metadata) == []
            command.downgrade(config, "base")
            assert inspect(conexion).get_table_names() == ["alembic_version"]
    finally:
        engine.dispose()


def test_bd_de_la_semana_1_se_adopta_sin_perder_datos(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'antigua.db').as_posix()}")
    try:
        # Como la dejaba create_all en la semana 1: el esquema de 0001 (sin eventos_recogida ni
        # variantes.activa) y sin alembic_version
        with engine.begin() as conexion:
            command.upgrade(configuracion(conexion), "0001")
            conexion.execute(text("DROP TABLE alembic_version"))
            conexion.execute(text("INSERT INTO productos (id, nombre, precio, activo) "
                                  "VALUES ('gorra-black', 'Gorra Black', 19.99, 1)"))
            conexion.execute(text("INSERT INTO variantes (id, producto_id, talla, stock) "
                                  "VALUES ('3f1c9a2e6b7d4e8f9a0b1c2d3e4f5a6b', 'gorra-black', 'UNICA', 7)"))
        monkeypatch.setattr(database, "engine", engine)

        database.crear_tablas()  # no falla por "la tabla ya existe"
        database.crear_tablas()

        with engine.connect() as conexion:
            assert conexion.scalar(text("SELECT nombre FROM productos WHERE id = 'gorra-black'")) == "Gorra Black"
            assert conexion.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
            assert "eventos_recogida" in inspect(conexion).get_table_names()
            # 0003: las variantes que ya existían quedan activas
            assert conexion.scalar(text("SELECT activa FROM variantes WHERE producto_id = 'gorra-black'")) == 1
    finally:
        engine.dispose()


def test_sql_de_postgresql_incluye_tablas_y_restricciones(tmp_path):
    entorno = os.environ | {"DATABASE_URL": "postgresql+psycopg://prueba:prueba@localhost/prueba"}
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(BASE_DIR / "alembic.ini"), "upgrade", "head", "--sql"],
        cwd=tmp_path, env=entorno, capture_output=True, text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    for fragmento in ("CREATE TABLE eventos_recogida", "id UUID", "NUMERIC(10, 2)",
                      "CONSTRAINT ck_variante_stock_no_negativo CHECK (stock >= 0)",
                      "CONSTRAINT uq_variante_producto_talla UNIQUE (producto_id, talla)",
                      "CREATE INDEX ix_pedidos_usuario_id",
                      "ALTER TABLE variantes ADD COLUMN activa BOOLEAN DEFAULT true NOT NULL"):
        assert fragmento in resultado.stdout, fragmento


def test_cli_funciona_fuera_de_la_carpeta_del_servicio(tmp_path):
    archivo = tmp_path / "ruta con espacios.db"
    entorno = os.environ | {"DATABASE_URL": f"sqlite:///{archivo.as_posix()}"}
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(BASE_DIR / "alembic.ini"), "upgrade", "head"],
        cwd=tmp_path, env=entorno, capture_output=True, text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert archivo.exists()
