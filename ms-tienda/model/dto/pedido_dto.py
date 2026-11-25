# ms-tienda/model/dto/pedido_dto.py
# Esquemas Pedido, PedidoEntrada, LineaPedido, Entrega y EstadoPedido de openapi.yaml
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from model.dto.producto_dto import Talla


class Entrega(str, Enum):
    DOMICILIO = "DOMICILIO"
    RECOGIDA_EVENTO = "RECOGIDA_EVENTO"


class EstadoPedido(str, Enum):
    PAGADO = "PAGADO"
    PREPARADO = "PREPARADO"
    ENVIADO = "ENVIADO"
    LISTO_RECOGIDA = "LISTO_RECOGIDA"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"


class LineaPedidoEntradaDTO(BaseModel):
    variante_id: UUID
    cantidad: int = Field(ge=1, le=10)


class PedidoEntradaDTO(BaseModel):
    lineas: list[LineaPedidoEntradaDTO] = Field(min_length=1)
    entrega: Entrega
    direccion_envio: str | None = None
    evento_id_recogida: str | None = None
    token_pago: str = Field(min_length=1)

    @model_validator(mode="after")
    def comprobar_entrega(self):
        if self.entrega == Entrega.DOMICILIO and not self.direccion_envio:
            raise ValueError("direccion_envio es obligatoria si entrega = DOMICILIO")
        if self.entrega == Entrega.RECOGIDA_EVENTO and not self.evento_id_recogida:
            raise ValueError("evento_id_recogida es obligatorio si entrega = RECOGIDA_EVENTO")
        return self


class CambioEstadoDTO(BaseModel):
    estado: EstadoPedido


class LineaPedidoDTO(BaseModel):
    producto_id: str
    producto_nombre: str
    variante_id: UUID
    talla: Talla
    cantidad: int
    precio_unitario: float


class PedidoDTO(BaseModel):
    id: str
    usuario_id: str
    lineas: list[LineaPedidoDTO]
    importe_total: float
    entrega: Entrega
    direccion_envio: str | None = None
    evento_id_recogida: str | None = None
    estado: EstadoPedido
    pago_ref: str | None = None
    creado_en: datetime

    @classmethod
    def desde_modelo(cls, pedido) -> "PedidoDTO":
        return cls(
            id=pedido.id,
            usuario_id=pedido.usuario_id,
            lineas=[
                LineaPedidoDTO(
                    producto_id=linea.variante.producto.id,
                    producto_nombre=linea.variante.producto.nombre,
                    variante_id=linea.variante_id,
                    talla=linea.variante.talla,
                    cantidad=linea.cantidad,
                    precio_unitario=float(linea.precio_unitario),
                )
                for linea in pedido.lineas
            ],
            importe_total=float(pedido.importe_total),
            entrega=pedido.entrega,
            direccion_envio=pedido.direccion_envio,
            evento_id_recogida=pedido.evento_id_recogida,
            estado=pedido.estado,
            pago_ref=pedido.pago_ref,
            creado_en=pedido.creado_en,
        )
