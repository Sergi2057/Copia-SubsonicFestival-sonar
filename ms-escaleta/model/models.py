# ms-escaleta/model/models.py
# Tablas de escaleta_db (ver "Almacenamiento" en openapi.yaml)
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    JSON, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# JSONB en PostgreSQL; JSON genérico en los tests con SQLite
DatosJSON = JSON().with_variant(JSONB(), "postgresql")


def ahora():
    return datetime.now(timezone.utc)


# TABLA ARTISTAS: catálogo de artistas
class Artista(Base):
    __tablename__ = "artistas"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre = Column(String(255), nullable=False, index=True)
    generos = Column(DatosJSON, nullable=False, default=list)
    pais = Column(String(100))
    biografia = Column(Text)
    imagen_url = Column(String(500))
    youtube_channel_id = Column(String(100))
    redes = Column(DatosJSON, nullable=False, default=dict)


# TABLA ESCENARIOS: réplica de los espacios de tipo ESCENARIO (propietario: ms-espacios)
class Escenario(Base):
    __tablename__ = "escenarios"

    espacio_id = Column(String(50), primary_key=True)
    evento_id = Column(String(100), nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    aforo = Column(Integer)
    actualizado_en = Column(DateTime(timezone=True), nullable=False, default=ahora)


# TABLA EVENTOS: réplica mínima del estado de cada evento (eventos espacios.evento.*)
# Solo se pueden crear slots en eventos PUBLICADOS.
class EventoReplica(Base):
    __tablename__ = "eventos"

    evento_id = Column(String(100), primary_key=True)
    estado = Column(String(20), nullable=False)
    actualizado_en = Column(DateTime(timezone=True), nullable=False, default=ahora)


# TABLA SLOTS: franjas horarias de cada escenario
class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (CheckConstraint("fin > inicio", name="ck_slot_fin_posterior"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    evento_id = Column(String(100), nullable=False, index=True)
    espacio_id = Column(String(50), ForeignKey("escenarios.espacio_id"), nullable=False)
    inicio = Column(DateTime(timezone=True), nullable=False)
    fin = Column(DateTime(timezone=True), nullable=False)
    tipo = Column(String(20), nullable=False)  # ACTUACION, CAMBIO_ESCENARIO o DESCANSO

    escenario = relationship("Escenario")
    pase = relationship("Pase", uselist=False, back_populates="slot", cascade="all, delete-orphan")


# TABLA PASES: actuaciones asignadas a los slots
class Pase(Base):
    __tablename__ = "pases"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    slot_id = Column(Uuid, ForeignKey("slots.id"), nullable=False, unique=True)  # un pase por slot
    artista_id = Column(Uuid, ForeignKey("artistas.id"), nullable=False, index=True)
    formato = Column(String(20), nullable=False)  # DJ_SET, LIVE o B2B
    estado = Column(String(20), nullable=False, default="PROGRAMADO")
    notas_tecnicas = Column(Text)
    version = Column(Integer, nullable=False, default=1)  # control de concurrencia optimista

    slot = relationship("Slot", back_populates="pase")
    artista = relationship("Artista")


# TABLA PUBLICACIONES: historial de versiones publicadas de la escaleta
class Publicacion(Base):
    __tablename__ = "publicaciones"

    evento_id = Column(String(100), primary_key=True)
    version = Column(Integer, primary_key=True)
    publicada_en = Column(DateTime(timezone=True), nullable=False, default=ahora)
    publicada_por = Column(String(128), nullable=False)
    instantanea = Column(DatosJSON, nullable=False)  # escaleta completa que se sirve tal cual
