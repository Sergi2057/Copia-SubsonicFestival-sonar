# ms-espacios/service/evento_service.py
# Lógica de negocio de eventos, recintos y tarifas
from datetime import date, datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from config.errores import ErrorApi
from eventos.publicador import publicar
from model.dto.evento_dto import (
    CambioEstadoEventoDTO, EstadoEvento, EventoEntradaDTO, RecintoEntradaDTO, TarifaDTO, TarifaEntradaDTO,
)
from model.factory.factory_dao import DAOFactory
from model.models import Evento, Recinto, TarifaAcceso

evento_dao = DAOFactory.get_evento_dao()

# Estados visibles para visitantes, clientes y proveedores
ESTADOS_PUBLICOS = [EstadoEvento.PUBLICADO.value, EstadoEvento.FINALIZADO.value]

TRANSICIONES_EVENTO = {
    EstadoEvento.BORRADOR: {EstadoEvento.PUBLICADO, EstadoEvento.CANCELADO},
    EstadoEvento.PUBLICADO: {EstadoEvento.FINALIZADO, EstadoEvento.CANCELADO},
}


def _datos_evento(evento: Evento) -> dict:
    return {
        "evento_id": evento.id, "titulo": evento.titulo, "pais": evento.pais,
        "recinto_id": str(evento.recinto_id), "fecha_inicio": evento.fecha_inicio.isoformat(),
        "fecha_fin": evento.fecha_fin.isoformat(), "estado": evento.estado,
    }


# ── Eventos ─────────────────────────────────────────────────

def buscar_eventos(db: Session, *, es_admin: bool, estado: EstadoEvento | None, pais, tag,
                   desde: date | None, hasta: date | None, limite: int, desplazamiento: int):
    visibles = [e.value for e in EstadoEvento] if es_admin else ESTADOS_PUBLICOS
    estados = [estado.value] if estado and estado.value in visibles else ([] if estado else visibles)
    return evento_dao.listar(db, estados=estados, pais=pais, tag=tag, desde=desde, hasta=hasta,
                             limite=limite, desplazamiento=desplazamiento)


def obtener_evento(db: Session, evento_id: str, *, es_admin: bool = False, bloquear: bool = False) -> Evento:
    evento = evento_dao.obtener(db, evento_id, bloquear=bloquear)
    if not evento or (not es_admin and evento.estado not in ESTADOS_PUBLICOS):
        raise ErrorApi(404, "EVENTO_NO_ENCONTRADO", f"No existe el evento {evento_id}")
    return evento


def _comprobar_recinto(db: Session, recinto_id: UUID):
    if not evento_dao.obtener_recinto(db, recinto_id):
        raise ErrorApi(400, "RECINTO_NO_VALIDO", f"No existe el recinto {recinto_id}")


def crear_evento(db: Session, datos: EventoEntradaDTO) -> Evento:
    if evento_dao.obtener(db, datos.id):
        raise ErrorApi(409, "EVENTO_DUPLICADO", f"Ya existe un evento con id {datos.id}")
    _comprobar_recinto(db, datos.recinto_id)
    evento = evento_dao.crear(db, Evento(**datos.model_dump(), estado=EstadoEvento.BORRADOR.value))
    db.commit()
    return obtener_evento(db, evento.id, es_admin=True)


def modificar_evento(db: Session, evento_id: str, datos: EventoEntradaDTO) -> Evento:
    evento = obtener_evento(db, evento_id, es_admin=True)
    if datos.id != evento_id:
        raise ErrorApi(400, "PETICION_NO_VALIDA", "El id del cuerpo no coincide con el de la ruta")
    _comprobar_recinto(db, datos.recinto_id)
    for campo, valor in datos.model_dump(exclude={"id"}).items():
        setattr(evento, campo, valor)
    db.commit()
    publicar("espacios.evento.actualizado", _datos_evento(evento))
    return evento


def cambiar_estado_evento(db: Session, evento_id: str, datos: CambioEstadoEventoDTO) -> Evento:
    evento = obtener_evento(db, evento_id, es_admin=True, bloquear=True)
    actual = EstadoEvento(evento.estado)
    if datos.estado not in TRANSICIONES_EVENTO.get(actual, set()):
        raise ErrorApi(409, "TRANSICION_NO_PERMITIDA", f"No se puede pasar de {actual.value} a {datos.estado.value}")

    evento.estado = datos.estado.value
    db.commit()

    tipo = {
        EstadoEvento.PUBLICADO: "espacios.evento.publicado",
        EstadoEvento.CANCELADO: "espacios.evento.cancelado",
    }.get(datos.estado, "espacios.evento.actualizado")
    publicar(tipo, _datos_evento(evento) | ({"motivo": datos.motivo} if datos.motivo else {}))
    return evento


def eliminar_evento(db: Session, evento_id: str) -> None:
    evento = obtener_evento(db, evento_id, es_admin=True, bloquear=True)
    if evento.estado != EstadoEvento.BORRADOR.value:
        raise ErrorApi(409, "EVENTO_NO_BORRADOR", "Solo se pueden eliminar eventos en BORRADOR")
    if evento_dao.entradas_vendidas_evento(db, evento_id) > 0:
        raise ErrorApi(409, "EVENTO_CON_VENTAS", "El evento ya tiene entradas vendidas")
    evento_dao.eliminar(db, evento)
    db.commit()


# ── Recintos ────────────────────────────────────────────────

def listar_recintos(db: Session):
    return evento_dao.listar_recintos(db)


def obtener_recinto(db: Session, recinto_id: UUID) -> Recinto:
    recinto = evento_dao.obtener_recinto(db, recinto_id)
    if not recinto:
        raise ErrorApi(404, "RECINTO_NO_ENCONTRADO", f"No existe el recinto {recinto_id}")
    return recinto


def crear_recinto(db: Session, datos: RecintoEntradaDTO) -> Recinto:
    recinto = evento_dao.crear_recinto(db, Recinto(**datos.model_dump()))
    db.commit()
    return recinto


def modificar_recinto(db: Session, recinto_id: UUID, datos: RecintoEntradaDTO) -> Recinto:
    recinto = obtener_recinto(db, recinto_id)
    for campo, valor in datos.model_dump().items():
        setattr(recinto, campo, valor)
    db.commit()
    return recinto


def eliminar_recinto(db: Session, recinto_id: UUID) -> None:
    recinto = obtener_recinto(db, recinto_id)
    if evento_dao.tiene_eventos_en_recinto(db, recinto_id):
        raise ErrorApi(409, "RECINTO_CON_EVENTOS", "Hay eventos que se celebran en el recinto")
    evento_dao.eliminar_recinto(db, recinto)
    db.commit()


# ── Tarifas ─────────────────────────────────────────────────

def a_tarifa_dto(db: Session, tarifa: TarifaAcceso) -> TarifaDTO:
    pendientes = evento_dao.reservas_pendientes(db, tarifa.id, datetime.now(timezone.utc))
    return TarifaDTO(
        id=tarifa.id, evento_id=tarifa.evento_id, tipo_pase=tarifa.tipo_pase, precio=float(tarifa.precio),
        cupo_total=tarifa.cupo_total, disponibles=max(tarifa.cupo_total - tarifa.cupo_vendido - pendientes, 0),
    )


def listar_tarifas(db: Session, evento_id: str, *, es_admin: bool) -> list[TarifaDTO]:
    obtener_evento(db, evento_id, es_admin=es_admin)
    return [a_tarifa_dto(db, t) for t in evento_dao.listar_tarifas(db, evento_id)]


def crear_tarifa(db: Session, evento_id: str, datos: TarifaEntradaDTO) -> TarifaDTO:
    obtener_evento(db, evento_id, es_admin=True)
    if evento_dao.obtener_tarifa_por_tipo(db, evento_id, datos.tipo_pase.value):
        raise ErrorApi(409, "TARIFA_DUPLICADA", f"Ya existe una tarifa {datos.tipo_pase.value} en el evento")
    tarifa = evento_dao.crear_tarifa(db, TarifaAcceso(evento_id=evento_id, tipo_pase=datos.tipo_pase.value,
                                                      precio=datos.precio, cupo_total=datos.cupo_total))
    db.commit()
    return a_tarifa_dto(db, tarifa)


def _obtener_tarifa(db: Session, evento_id: str, tarifa_id: UUID) -> TarifaAcceso:
    obtener_evento(db, evento_id, es_admin=True)
    tarifa = evento_dao.obtener_tarifa(db, evento_id, tarifa_id, bloquear=True)
    if not tarifa:
        raise ErrorApi(404, "TARIFA_NO_ENCONTRADA", "No existe esa tarifa en el evento")
    return tarifa


def modificar_tarifa(db: Session, evento_id: str, tarifa_id: UUID, datos: TarifaEntradaDTO) -> TarifaDTO:
    tarifa = _obtener_tarifa(db, evento_id, tarifa_id)
    if datos.cupo_total < tarifa.cupo_vendido:
        raise ErrorApi(400, "CUPO_INSUFICIENTE",
                       f"El cupo total no puede ser menor que las entradas vendidas ({tarifa.cupo_vendido})")
    if datos.tipo_pase.value != tarifa.tipo_pase and evento_dao.obtener_tarifa_por_tipo(db, evento_id,
                                                                                         datos.tipo_pase.value):
        raise ErrorApi(400, "TARIFA_DUPLICADA", f"Ya existe una tarifa {datos.tipo_pase.value} en el evento")
    tarifa.tipo_pase = datos.tipo_pase.value
    tarifa.precio = datos.precio
    tarifa.cupo_total = datos.cupo_total
    db.commit()
    return a_tarifa_dto(db, tarifa)


def eliminar_tarifa(db: Session, evento_id: str, tarifa_id: UUID) -> None:
    tarifa = _obtener_tarifa(db, evento_id, tarifa_id)
    if tarifa.cupo_vendido > 0:
        raise ErrorApi(409, "TARIFA_CON_VENTAS", "La tarifa ya tiene entradas vendidas")
    db.delete(tarifa)
    db.commit()
