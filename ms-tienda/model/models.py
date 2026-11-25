# ms-tienda/model/models.py
# Tablas de tienda_db (ver "Almacenamiento" en openapi.yaml)
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid,
    true,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# TABLA PRODUCTOS: catálogo
class Producto(Base):
    __tablename__ = "productos"

    id = Column(String(50), primary_key=True)  # identificador legible, ej: "camiseta-2026"
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text)
    precio = Column(Numeric(8, 2), nullable=False)
    imagen_url = Column(String(500))
    evento_id = Column(String(100), nullable=True)  # merchandising exclusivo de una edición (ref. ms-espacios)
    activo = Column(Boolean, nullable=False, default=True)

    variantes = relationship("Variante", back_populates="producto", order_by="Variante.talla")


# TABLA VARIANTES: tallas y stock de cada producto
class Variante(Base):
    __tablename__ = "variantes"
    __table_args__ = (
        UniqueConstraint("producto_id", "talla", name="uq_variante_producto_talla"),
        CheckConstraint("stock >= 0", name="ck_variante_stock_no_negativo"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    producto_id = Column(String(50), ForeignKey("productos.id"), nullable=False)
    talla = Column(String(10), nullable=False)  # XS, S, M, L, XL, XXL o UNICA
    stock = Column(Integer, nullable=False, default=0)
    # False = talla retirada: no sale en el catálogo ni se puede comprar, pero los pedidos antiguos la conservan
    activa = Column(Boolean, nullable=False, default=True, server_default=true())

    producto = relationship("Producto", back_populates="variantes")


# TABLA PEDIDOS: compras de merchandising
class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(String(50), primary_key=True)  # ej: "pedido-7f3c21ab"
    usuario_id = Column(String(128), nullable=False, index=True)  # ref. ms-usuarios
    importe_total = Column(Numeric(10, 2), nullable=False)
    entrega = Column(String(20), nullable=False)  # DOMICILIO o RECOGIDA_EVENTO
    direccion_envio = Column(Text, nullable=True)
    evento_id_recogida = Column(String(100), nullable=True)
    estado = Column(String(20), nullable=False, default="PAGADO")
    pago_ref = Column(String(100))
    creado_en = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    lineas = relationship("LineaPedido", back_populates="pedido", cascade="all, delete-orphan")


# TABLA LINEAS_PEDIDO: productos de cada pedido
class LineaPedido(Base):
    __tablename__ = "lineas_pedido"

    pedido_id = Column(String(50), ForeignKey("pedidos.id"), primary_key=True)
    variante_id = Column(Uuid, ForeignKey("variantes.id"), primary_key=True)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(8, 2), nullable=False)  # precio en el momento de la compra

    pedido = relationship("Pedido", back_populates="lineas")
    variante = relationship("Variante")


# TABLA EVENTOS_RECOGIDA: réplica mínima del estado de cada evento (eventos espacios.evento.*).
# Solo se aceptan pedidos con RECOGIDA_EVENTO en eventos PUBLICADOS.
class EventoRecogida(Base):
    __tablename__ = "eventos_recogida"

    evento_id = Column(String(100), primary_key=True)  # ref. ms-espacios
    estado = Column(String(20), nullable=False)  # PUBLICADO o CANCELADO
    actualizado_en = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
