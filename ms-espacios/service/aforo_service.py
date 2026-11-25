# ms-espacios/service/aforo_service.py
# Reserva temporal de aforo durante la compra de una entrada (llamada síncrona desde ms-usuarios)
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from config.errores import ErrorApi
from config.settings import MINUTOS_RESERVA_AFORO
from eventos.publicador import publicar
from model.dto.evento_dto import EstadoEvento, ReservaAforoDTO, ReservaAforoEntradaDTO
from model.factory.factory_dao import DAOFactory
from model.models import ReservaAforo

evento_dao = DAOFactory.get_evento_dao()


def reservar_aforo(db: Session, evento_id: str, datos: ReservaAforoEntradaDTO) -> ReservaAforoDTO:
    ahora = datetime.now(timezone.utc)
    evento = evento_dao.obtener(db, evento_id)
    if not evento:
        raise ErrorApi(404, "EVENTO_NO_ENCONTRADO", f"No existe el evento {evento_id}")
    if evento.estado != EstadoEvento.PUBLICADO.value:
        raise ErrorApi(409, "EVENTO_NO_A_LA_VENTA", "El evento no está a la venta")

    # SELECT … FOR UPDATE de la tarifa: dos compras simultáneas no pueden ver el mismo hueco
    tarifa = evento_dao.obtener_tarifa_por_tipo(db, evento_id, datos.tipo_pase.value, bloquear=True)
    if not tarifa:
        raise ErrorApi(404, "TARIFA_NO_ENCONTRADA", f"El evento no tiene tarifa {datos.tipo_pase.value}")

    evento_dao.caducar_reservas(db, ahora)
    disponibles = tarifa.cupo_total - tarifa.cupo_vendido - evento_dao.reservas_pendientes(db, tarifa.id, ahora)
    if disponibles <= 0:
        db.rollback()
        raise ErrorApi(409, "SIN_CUPO", f"No quedan entradas {datos.tipo_pase.value} para este evento")

    reserva = evento_dao.crear_reserva(db, ReservaAforo(
        tarifa_id=tarifa.id, usuario_id=datos.usuario_id, estado="PENDIENTE",
        expira_en=ahora + timedelta(minutes=MINUTOS_RESERVA_AFORO),
    ))
    db.commit()

    if disponibles == 1:  # esta reserva era la última plaza
        publicar("espacios.aforo.agotado", {"evento_id": evento_id, "tipo_pase": tarifa.tipo_pase})

    return ReservaAforoDTO(reserva_id=reserva.id, evento_id=evento_id, tipo_pase=tarifa.tipo_pase,
                           precio=float(tarifa.precio), expira_en=reserva.expira_en,
                           evento_titulo=evento.titulo, fecha_inicio=evento.fecha_inicio, fecha_fin=evento.fecha_fin)


def liberar_reserva(db: Session, reserva_id: UUID) -> None:
    reserva = evento_dao.obtener_reserva(db, reserva_id, bloquear=True)
    if not reserva:
        raise ErrorApi(404, "RESERVA_NO_ENCONTRADA", f"No existe la reserva {reserva_id}")
    if reserva.estado == "CONFIRMADA":
        raise ErrorApi(409, "RESERVA_CONFIRMADA", "La reserva ya estaba confirmada")
    reserva.estado = "LIBERADA"
    db.commit()


# ── Reacciones a eventos de ms-usuarios (se conectarán a RabbitMQ) ──

def confirmar_reserva(db: Session, reserva_id: UUID) -> bool:
    """usuarios.entrada.comprada: la reserva pasa a CONFIRMADA y suma una entrada vendida.
    Es idempotente: si ya estaba confirmada no vuelve a sumar."""
    reserva = evento_dao.obtener_reserva(db, reserva_id, bloquear=True)
    if not reserva or reserva.estado == "CONFIRMADA":
        return False
    tarifa = evento_dao.obtener_tarifa(db, reserva.tarifa.evento_id, reserva.tarifa_id, bloquear=True)
    tarifa.cupo_vendido += 1
    reserva.estado = "CONFIRMADA"
    db.commit()
    return True


def liberar_plaza_vendida(db: Session, evento_id: str, tipo_pase: str) -> None:
    """usuarios.entrada.cancelada: devuelve una plaza al cupo."""
    tarifa = evento_dao.obtener_tarifa_por_tipo(db, evento_id, tipo_pase, bloquear=True)
    if tarifa and tarifa.cupo_vendido > 0:
        tarifa.cupo_vendido -= 1
        db.commit()
