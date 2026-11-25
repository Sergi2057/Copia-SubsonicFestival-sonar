# ms-escaleta/tests/test_migraciones.py
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
            assert conexion.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
            # La migración y models.py describen el mismo esquema
            assert compare_metadata(MigrationContext.configure(conexion), Base.metadata) == []
            command.downgrade(config, "base")
            assert inspect(conexion).get_table_names() == ["alembic_version"]
    finally:
        engine.dispose()


def test_bd_de_la_semana_1_se_adopta_sin_perder_datos(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'antigua.db').as_posix()}")
    try:
        # Como la dejaba create_all en la semana 1: tablas y datos, pero sin alembic_version
        Base.metadata.create_all(engine)
        with engine.begin() as conexion:
            conexion.execute(text("INSERT INTO eventos (evento_id, estado, actualizado_en) "
                                  "VALUES ('evento-viejo', 'PUBLICADO', '2026-10-19')"))
        monkeypatch.setattr(database, "engine", engine)

        database.crear_tablas()  # no falla por "la tabla ya existe"
        database.crear_tablas()

        with engine.connect() as conexion:
            assert conexion.scalar(text("SELECT estado FROM eventos WHERE evento_id = 'evento-viejo'")) == "PUBLICADO"
            assert conexion.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
    finally:
        engine.dispose()


def test_sql_de_postgresql_incluye_la_restriccion_de_exclusion(tmp_path):
    entorno = os.environ | {"DATABASE_URL": "postgresql+psycopg://prueba:prueba@localhost/prueba"}
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(BASE_DIR / "alembic.ini"), "upgrade", "head", "--sql"],
        cwd=tmp_path, env=entorno, capture_output=True, text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    sql = resultado.stdout
    for fragmento in ("CREATE EXTENSION IF NOT EXISTS btree_gist",
                      "ADD CONSTRAINT ex_slots_sin_solape EXCLUDE USING gist "
                      "(espacio_id WITH =, tstzrange(inicio, fin) WITH &&)",
                      "generos JSONB", "instantanea JSONB", "id UUID",
                      "CONSTRAINT ck_slot_fin_posterior CHECK (fin > inicio)"):
        assert fragmento in sql, fragmento
    # La restricción va después de crear slots
    assert sql.index("CREATE TABLE slots") < sql.index("ex_slots_sin_solape")


def test_cli_funciona_fuera_de_la_carpeta_del_servicio(tmp_path):
    archivo = tmp_path / "ruta con espacios.db"
    entorno = os.environ | {"DATABASE_URL": f"sqlite:///{archivo.as_posix()}"}
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(BASE_DIR / "alembic.ini"), "upgrade", "head"],
        cwd=tmp_path, env=entorno, capture_output=True, text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert archivo.exists()
