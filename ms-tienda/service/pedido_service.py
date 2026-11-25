# ms-tienda/service/pedido_service.py
# Lógica de negocio de los pedidos: compra, estados, cancelación y RGPD
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from config.errores import ErrorApi
from config.seguridad import UsuarioActual
from eventos.publicador import publicar
from model.dto.pedido_dto import Entrega, EstadoPedido, PedidoEntradaDTO
from model.factory.factory_dao import DAOFactory
from model.models import EventoRecogida, LineaPedido, Pedido
from service import pasarela_pago
from service.producto_service import avisar_si_stock_bajo

producto_dao = DAOFactory.get_producto_dao()
pedido_dao = DAOFactory.get_pedido_dao()
evento_recogida_dao = DAOFactory.get_evento_recogida_dao()

# Estado de un evento (ms-espacios) en el que se puede recoger un pedido
EVENTO_PUBLICADO = "PUBLICADO"
EVENTO_CANCELADO = "CANCELADO"

# Transiciones que puede hacer el administrador (estado actual -> estados destino)
TRANSICIONES_ADMIN = {
    EstadoPedido.PAGADO: {EstadoPedido.PREPARADO},
    EstadoPedido.PREPARADO: {EstadoPedido.ENVIADO, EstadoPedido.LISTO_RECOGIDA},
    EstadoPedido.ENVIADO: {EstadoPedido.ENTREGADO},
    EstadoPedido.LISTO_RECOGIDA: {EstadoPedido.ENTREGADO},
}


def _datos_evento(pedido: Pedido) -> dict:
    return {
        "pedido_id": pedido.id,
        "usuario_id": pedido.usuario_id,
        "estado": pedido.estado,
        "importe_total": float(pedido.importe_total),
        "entrega": pedido.entrega,
        "evento_id_recogida": pedido.evento_id_recogida,
        "lineas": [
            {"variante_id": str(l.variante_id), "producto_id": l.variante.producto_id, "talla": l.variante.talla,
             "cantidad": l.cantidad, "precio_unitario": float(l.precio_unitario)}
            for l in pedido.lineas
        ],
    }


def listar_pedidos(db: Session, usuario: UsuarioActual, *, estado, evento_id_recogida, limite, desplazamiento):
    if usuario.rol == "cliente":
        if evento_id_recogida:
            raise ErrorApi(403, "SIN_PERMISO", "Solo el administrador puede filtrar por evento de recogida")
        return pedido_dao.listar(db, usuario_id=usuario.id, estado=estado, evento_id_recogida=None,
                                 limite=limite, desplazamiento=desplazamiento)
    return pedido_dao.listar(db, usuario_id=None, estado=estado, evento_id_recogida=evento_id_recogida,
                             limite=limite, desplazamiento=desplazamiento)


def obtener_pedido(db: Session, usuario: UsuarioActual, pedido_id: str, *, bloquear: bool = False) -> Pedido:
    pedido = pedido_dao.obtener(db, pedido_id, bloquear=bloquear)
    if not pedido:
        raise ErrorApi(404, "PEDIDO_NO_ENCONTRADO", f"No existe el pedido {pedido_id}")
    if usuario.rol != "admin" and pedido.usuario_id != usuario.id:
        raise ErrorApi(403, "SIN_PERMISO", "El pedido no pertenece al usuario")
    return pedido


def comprobar_punto_recogida(db: Session, evento_id: str) -> None:
    """Solo se recoge en eventos publicados (los conocemos por espacios.evento.publicado)."""
    evento = evento_recogida_dao.obtener(db, evento_id)
    if not evento or evento.estado != EVENTO_PUBLICADO:
        raise ErrorApi(409, "RECOGIDA_NO_DISPONIBLE",
                       f"No se puede recoger en el evento {evento_id}: no está publicado o se ha cancelado",
                       {"evento_id": evento_id, "estado": evento.estado if evento else None})


def crear_pedido(db: Session, usuario: UsuarioActual, datos: PedidoEntradaDTO) -> Pedido:
    # 0. Antes de tocar el stock o cobrar: el evento de recogida tiene que estar publicado
    if datos.entrega == Entrega.RECOGIDA_EVENTO:
        comprobar_punto_recogida(db, datos.evento_id_recogida)

    # Agrupar líneas repetidas de la misma talla
    cantidades: dict[uuid.UUID, int] = defaultdict(int)
    for linea in datos.lineas:
        cantidades[linea.variante_id] += linea.cantidad

    # 1. Bloquear las variantes y comprobar el stock (SELECT … FOR UPDATE)
    variantes = producto_dao.bloquear_variantes(db, list(cantidades))
    importe_total = Decimal("0")
    lineas = []
    for variante_id, cantidad in cantidades.items():
        variante = variantes.get(variante_id)
        if not variante or not variante.producto.activo:
            db.rollback()
            raise ErrorApi(400, "VARIANTE_NO_VALIDA", f"La variante {variante_id} no existe o no está a la venta")
        if not variante.activa:
            db.rollback()
            raise ErrorApi(409, "VARIANTE_RETIRADA",
                           f"La talla {variante.talla} de {variante.producto.nombre} ya no está a la venta",
                           {"variante_id": str(variante_id)})
        if variante.stock < cantidad:
            db.rollback()
            raise ErrorApi(409, "SIN_STOCK",
                           f"No hay stock suficiente de la talla {variante.talla} de {variante.producto.nombre}",
                           {"variante_id": str(variante_id), "disponible": variante.stock, "solicitado": cantidad})
        # 2. Descontar stock
        variante.stock -= cantidad
        precio = Decimal(variante.producto.precio)
        importe_total += precio * cantidad
        lineas.append(LineaPedido(variante_id=variante_id, cantidad=cantidad, precio_unitario=precio))

    # 3. Cobrar. Si falla, el rollback devuelve el stock
    try:
        pago_ref = pasarela_pago.cobrar(datos.token_pago, importe_total)
    except pasarela_pago.PagoRechazado as e:
        db.rollback()
        raise ErrorApi(402, "PAGO_RECHAZADO", str(e))

    # 4. Registrar el pedido como PAGADO
    pedido = Pedido(
        id=f"pedido-{uuid.uuid4().hex[:8]}",
        usuario_id=usuario.id,
        importe_total=importe_total,
        entrega=datos.entrega.value,
        direccion_envio=datos.direccion_envio if datos.entrega == Entrega.DOMICILIO else None,
        evento_id_recogida=datos.evento_id_recogida if datos.entrega == Entrega.RECOGIDA_EVENTO else None,
        estado=EstadoPedido.PAGADO.value,
        pago_ref=pago_ref,
        lineas=lineas,
    )
    pedido_dao.crear(db, pedido)
    db.commit()

    # 5. Eventos
    pedido = pedido_dao.obtener(db, pedido.id)
    publicar("tienda.pedido.creado", _datos_evento(pedido))
    for variante in variantes.values():
        avisar_si_stock_bajo(variante)
    return pedido


def cambiar_estado(db: Session, usuario: UsuarioActual, pedido_id: str, nuevo: EstadoPedido) -> Pedido:
    pedido = obtener_pedido(db, usuario, pedido_id, bloquear=True)
    actual = EstadoPedido(pedido.estado)

    if usuario.rol == "cliente":
        if nuevo != EstadoPedido.CANCELADO:
            raise ErrorApi(403, "SIN_PERMISO", "El cliente solo puede cancelar sus pedidos")
        if actual != EstadoPedido.PAGADO:
            raise ErrorApi(409, "TRANSICION_NO_PERMITIDA",
                           f"Solo se pueden cancelar pedidos en estado PAGADO (está {actual.value})")
        # Devolver stock y reembolsar
        variantes = producto_dao.bloquear_variantes(db, [l.variante_id for l in pedido.lineas])
        for linea in pedido.lineas:
            variantes[linea.variante_id].stock += linea.cantidad
        pasarela_pago.reembolsar(pedido.pago_ref, pedido.importe_total)
    elif usuario.rol == "admin":
        if nuevo not in TRANSICIONES_ADMIN.get(actual, set()):
            raise ErrorApi(409, "TRANSICION_NO_PERMITIDA", f"No se puede pasar de {actual.value} a {nuevo.value}")
        if nuevo == EstadoPedido.ENVIADO and pedido.entrega != Entrega.DOMICILIO.value:
            raise ErrorApi(409, "TRANSICION_NO_PERMITIDA", "Un pedido con recogida en evento no se envía")
        if nuevo == EstadoPedido.LISTO_RECOGIDA and pedido.entrega != Entrega.RECOGIDA_EVENTO.value:
            raise ErrorApi(409, "TRANSICION_NO_PERMITIDA", "Un pedido a domicilio no se recoge en evento")
    else:
        raise ErrorApi(403, "SIN_PERMISO", "El rol del usuario no permite esta operación")

    pedido.estado = nuevo.value
    db.commit()
    pedido = pedido_dao.obtener(db, pedido_id)
    publicar("tienda.pedido.actualizado", _datos_evento(pedido))
    return pedido


def anonimizar_pedidos_usuario(db: Session, usuario_id: str) -> int:
    """Reacción a usuarios.usuario.eliminado (RGPD). Repetirla no cambia nada."""
    n = pedido_dao.anonimizar_de_usuario(db, usuario_id)
    db.commit()
    return n


def al_cambiar_estado_evento(db: Session, evento_id: str, estado: str) -> None:
    """espacios.evento.publicado habilita el evento como punto de recogida; .cancelado lo deshabilita.

    Los pedidos ya hechos no se tocan: el administrador decide qué hacer con ellos.
    En ms-espacios CANCELADO es definitivo, así que un "publicado" que llegue después (mensaje
    repetido o desordenado) no vuelve a habilitar el evento.
    """
    actual = evento_recogida_dao.obtener(db, evento_id)
    if actual and actual.estado == EVENTO_CANCELADO:
        return
    evento_recogida_dao.guardar(db, EventoRecogida(evento_id=evento_id, estado=estado,
                                                   actualizado_en=datetime.now(timezone.utc)))
    db.commit()
