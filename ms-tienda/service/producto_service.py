# ms-tienda/service/producto_service.py
# Lógica de negocio del catálogo: productos, tallas y stock
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from config.errores import ErrorApi
from config.settings import UMBRAL_STOCK_BAJO
from eventos.publicador import publicar
from model.dto.pedido_dto import EstadoPedido
from model.dto.producto_dto import (
    ProductoDTO, ProductoEntradaDTO, VarianteCambioDTO, VarianteDTO, VarianteEntradaDTO,
)
from model.factory.factory_dao import DAOFactory
from model.models import Producto, Variante

producto_dao = DAOFactory.get_producto_dao()
pedido_dao = DAOFactory.get_pedido_dao()

# Pedidos que todavía no se han entregado: mientras existan, su talla no se puede eliminar
ESTADOS_PENDIENTES = {EstadoPedido.PAGADO.value, EstadoPedido.PREPARADO.value, EstadoPedido.ENVIADO.value,
                      EstadoPedido.LISTO_RECOGIDA.value}


def avisar_si_stock_bajo(variante: Variante):
    if variante.stock < UMBRAL_STOCK_BAJO:
        publicar("tienda.stock.bajo", {
            "producto_id": variante.producto_id,
            "variante_id": str(variante.id),
            "talla": variante.talla,
            "stock": variante.stock,
            "umbral": UMBRAL_STOCK_BAJO,
        })


def a_producto_dto(producto: Producto, *, es_admin: bool) -> ProductoDTO:
    """El catálogo público no muestra las tallas retiradas; el administrador las ve todas."""
    dto = ProductoDTO.model_validate(producto)
    if not es_admin:
        dto.variantes = [v for v in dto.variantes if v.activa]
    return dto


def listar_productos(db: Session, *, evento_id, disponible, es_admin: bool, limite: int, desplazamiento: int):
    return producto_dao.listar(
        db, evento_id=evento_id, disponible=disponible, incluir_inactivos=es_admin,
        limite=limite, desplazamiento=desplazamiento,
    )


def obtener_producto(db: Session, producto_id: str, *, es_admin: bool = False) -> Producto:
    producto = producto_dao.obtener(db, producto_id)
    # Los productos retirados solo los ve el administrador
    if not producto or (not producto.activo and not es_admin):
        raise ErrorApi(404, "PRODUCTO_NO_ENCONTRADO", f"No existe el producto {producto_id}")
    return producto


def crear_producto(db: Session, datos: ProductoEntradaDTO) -> Producto:
    if producto_dao.obtener(db, datos.id):
        raise ErrorApi(409, "PRODUCTO_DUPLICADO", f"Ya existe un producto con id {datos.id}")
    producto = producto_dao.crear(db, Producto(**datos.model_dump()))
    db.commit()
    return obtener_producto(db, producto.id, es_admin=True)


def modificar_producto(db: Session, producto_id: str, datos: ProductoEntradaDTO) -> Producto:
    producto = obtener_producto(db, producto_id, es_admin=True)
    if datos.id != producto_id:
        raise ErrorApi(400, "PETICION_NO_VALIDA", "El id del cuerpo no coincide con el de la ruta")
    for campo, valor in datos.model_dump(exclude={"id"}).items():
        setattr(producto, campo, valor)
    db.commit()
    return obtener_producto(db, producto_id, es_admin=True)


def retirar_producto(db: Session, producto_id: str) -> None:
    producto = obtener_producto(db, producto_id, es_admin=True)
    producto.activo = False
    db.commit()


def crear_variante(db: Session, producto_id: str, datos: VarianteEntradaDTO) -> Variante:
    obtener_producto(db, producto_id, es_admin=True)
    variante = producto_dao.obtener_variante_por_talla(db, producto_id, datos.talla.value)
    if variante and variante.activa:
        raise _talla_duplicada(datos.talla.value)
    if variante:
        # Talla retirada: se reactiva la misma fila para no perder su historial de pedidos
        variante.activa = True
        variante.stock = datos.stock
    else:
        variante = producto_dao.crear_variante(
            db, Variante(producto_id=producto_id, talla=datos.talla.value, stock=datos.stock)
        )
    db.commit()
    avisar_si_stock_bajo(variante)
    return variante


def _bloquear_variante(db: Session, producto_id: str, variante_id: UUID) -> Variante:
    """SELECT … FOR UPDATE: la compra también bloquea la fila, así que no se cruzan."""
    variante = producto_dao.bloquear_variantes(db, [variante_id]).get(variante_id)
    if not variante or variante.producto_id != producto_id:
        raise ErrorApi(404, "VARIANTE_NO_ENCONTRADA", "No existe esa talla para el producto")
    return variante


def _talla_duplicada(talla: str) -> ErrorApi:
    return ErrorApi(409, "TALLA_DUPLICADA", f"La talla {talla} ya existe para el producto")


def modificar_variante(db: Session, producto_id: str, variante_id: UUID, datos: VarianteCambioDTO) -> Variante:
    variante = _bloquear_variante(db, producto_id, variante_id)
    if datos.talla is not None and datos.talla.value != variante.talla:
        if producto_dao.obtener_variante_por_talla(db, producto_id, datos.talla.value):
            raise _talla_duplicada(datos.talla.value)
        variante.talla = datos.talla.value
    if datos.stock is not None:
        variante.stock = datos.stock
    try:
        db.commit()
    except IntegrityError:  # otra petición creó la misma talla a la vez (uq_variante_producto_talla)
        db.rollback()
        raise _talla_duplicada(datos.talla.value)
    if datos.stock is not None and variante.activa:
        avisar_si_stock_bajo(variante)
    return variante


def eliminar_variante(db: Session, producto_id: str, variante_id: UUID) -> None:
    """Sin ventas se borra; con ventas ya terminadas se retira (lineas_pedido la referencia)."""
    variante = _bloquear_variante(db, producto_id, variante_id)
    if pedido_dao.variante_en_pedidos(db, variante_id, ESTADOS_PENDIENTES):
        raise ErrorApi(409, "VARIANTE_CON_PEDIDOS_PENDIENTES",
                       f"La talla {variante.talla} tiene pedidos pendientes de entregar",
                       {"variante_id": str(variante_id)})
    if pedido_dao.variante_en_pedidos(db, variante_id):
        variante.activa = False
    else:
        producto_dao.eliminar_variante(db, variante)
    db.commit()
