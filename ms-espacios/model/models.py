# ms-espacios/model/models.py
# Tablas de espacios_db (ver "Almacenamiento" en openapi.yaml)
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    JSON, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
    UniqueConstraint, Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# JSONB en PostgreSQL; JSON genérico en los tests con SQLite
ListaJSON = JSON().with_variant(JSONB(), "postgresql")


def ahora():
    return datetime.now(timezone.utc)


# TABLA RECINTOS: lugares físicos
class Recinto(Base):
    __tablename__ = "recintos"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre = Column(String(255), nullable=False)
    direccion = Column(String(255))
    ciudad = Column(String(100), nullable=False)
    pais = Column(String(100), nullable=False)
    latitud = Column(Numeric(9, 6))
    longitud = Column(Numeric(9, 6))
    aforo_maximo = Column(Integer, nullable=False)


# TABLA EVENTOS: ediciones del festival
class Evento(Base):
    __tablename__ = "eventos"

    id = Column(String(100), primary_key=True)  # ej: "evento-belgium"
    titulo = Column(String(200), nullable=False)
    pais = Column(String(100), nullable=False)
    recinto_id = Column(Uuid, ForeignKey("recintos.id"), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    descripcion = Column(Text)
    imagen_url = Column(String(500))
    tags = Column(ListaJSON, nullable=False, default=list)
    servicios_generales = Column(ListaJSON, nullable=False, default=list)
    estado = Column(String(20), nullable=False, default="BORRADOR")

    recinto = relationship("Recinto")
    tarifas = relationship("TarifaAcceso", back_populates="evento", cascade="all, delete-orphan")
    espacios = relationship("Espacio", back_populates="evento", cascade="all, delete-orphan")


# TABLA TIPOS_ESPACIO: catálogo de tipos
class TipoEspacio(Base):
    __tablename__ = "tipos_espacio"

    codigo = Column(String(30), primary_key=True)
    nombre = Column(String(100), nullable=False)
    alquilable = Column(Boolean, nullable=False)


# TABLA ESPACIOS: áreas concretas de un recinto para un evento
class Espacio(Base):
    __tablename__ = "espacios"

    id = Column(String(50), primary_key=True)  # ej: "espacio-001"
    evento_id = Column(String(100), ForeignKey("eventos.id"), nullable=False, index=True)
    tipo = Column(String(30), ForeignKey("tipos_espacio.codigo"), nullable=False)
    nombre = Column(String(200), nullable=False)
    zona = Column(String(200))
    tamano = Column(String(100))
    dimensiones = Column(String(100))
    aforo = Column(Integer)
    precio_alquiler = Column(Numeric(10, 2))
    servicios = Column(ListaJSON, nullable=False, default=list)
    descripcion = Column(Text)
    disponible = Column(Boolean, nullable=False, default=True)

    evento = relationship("Evento", back_populates="espacios")
    tipo_espacio = relationship("TipoEspacio")
    alquileres = relationship("Alquiler", back_populates="espacio", cascade="all, delete-orphan")


# TABLA ALQUILERES: alquiler de un espacio por un proveedor
class Alquiler(Base):
    __tablename__ = "alquileres"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    espacio_id = Column(String(50), ForeignKey("espacios.id"), nullable=False, index=True)
    proveedor_id = Column(String(128), nullable=False, index=True)  # UID en ms-usuarios (sin FK)
    fecha_inicio = Column(DateTime(timezone=True), nullable=False)
    fecha_fin = Column(DateTime(timezone=True), nullable=False)
    importe = Column(Numeric(10, 2), nullable=False)
    estado = Column(String(20), nullable=False, default="PENDIENTE")
    comentarios = Column(Text)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=ahora)

    espacio = relationship("Espacio", back_populates="alquileres")


# TABLA TARIFAS_ACCESO: precios de las entradas y cupos
class TarifaAcceso(Base):
    __tablename__ = "tarifas_acceso"
    __table_args__ = (
        UniqueConstraint("evento_id", "tipo_pase", name="uq_tarifa_evento_tipo"),
        CheckConstraint("cupo_vendido <= cupo_total", name="ck_tarifa_sin_sobreventa"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    evento_id = Column(String(100), ForeignKey("eventos.id"), nullable=False)
    tipo_pase = Column(String(20), nullable=False)  # DAY, WEEKEND o VIP
    precio = Column(Numeric(8, 2), nullable=False)
    cupo_total = Column(Integer, nullable=False)
    cupo_vendido = Column(Integer, nullable=False, default=0)

    evento = relationship("Evento", back_populates="tarifas")
    reservas = relationship("ReservaAforo", back_populates="tarifa", cascade="all, delete-orphan")


# TABLA RESERVAS_AFORO: reservas temporales durante una compra
class ReservaAforo(Base):
    __tablename__ = "reservas_aforo"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    tarifa_id = Column(Uuid, ForeignKey("tarifas_acceso.id"), nullable=False, index=True)
    usuario_id = Column(String(128), nullable=False)
    estado = Column(String(20), nullable=False, default="PENDIENTE")  # PENDIENTE, CONFIRMADA o LIBERADA
    expira_en = Column(DateTime(timezone=True), nullable=False)

    tarifa = relationship("TarifaAcceso", back_populates="reservas")


# TABLA PROVEEDORES: réplica de solo lectura (propietario: ms-usuarios)
class Proveedor(Base):
    __tablename__ = "proveedores"

    proveedor_id = Column(String(128), primary_key=True)
    nombre_comercial = Column(String(200))
    tipo_servicio = Column(String(100))
    activo = Column(Boolean, nullable=False, default=True)


class EventoProcesado(Base):
    __tablename__ = "eventos_procesados"

    id_evento = Column(String(128), primary_key=True)
    tipo = Column(String(120), nullable=False)
    procesado_en = Column(DateTime(timezone=True), nullable=False, default=ahora)
