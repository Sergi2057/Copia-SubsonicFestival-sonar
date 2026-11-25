# ms-escaleta/service/escaleta_service.py
# Lógica de negocio de slots, pases, publicación de la escaleta y reacciones a eventos de ms-espacios
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from config.errores import ErrorApi
from config.settings import HORA_CORTE_DIA
from eventos.publicador import publicar
from model.dto.escaleta_dto import (
    EscaletaDTO, EstadoPase, PaseCambioDTO, PaseDTO, PaseEntradaDTO, PaseResumenDTO, PublicacionDTO, SlotDTO,
    SlotEntradaDTO, TipoSlot,
)
from model.factory.factory_dao import DAOFactory
from model.models import Escenario, EventoReplica, Pase, Publicacion, Slot
from service import cache
from service.difusor import difusor

escaleta_dao = DAOFactory.get_escaleta_dao()
artista_dao = DAOFactory.get_artista_dao()

CACHE_SEGUNDOS = 3600

TRANSICIONES_PASE = {
    EstadoPase.PROGRAMADO: {EstadoPase.CONFIRMADO, EstadoPase.CANCELADO},
    EstadoPase.CONFIRMADO: {EstadoPase.EN_CURSO, EstadoPase.CANCELADO},
    EstadoPase.EN_CURSO: {EstadoPase.FINALIZADO},
}


def utc(fecha: datetime) -> datetime:
    """Normaliza a UTC (SQLite devuelve fechas sin zona; se guardan siempre en UTC)."""
    return fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha.astimezone(timezone.utc)


def dia_de_festival(inicio: datetime) -> date:
    """Un pase a la 01:00 pertenece a la noche del día anterior."""
    return (utc(inicio) - timedelta(hours=HORA_CORTE_DIA)).date()


def _clave_cache(evento_id: str) -> str:
    return f"escaleta:{evento_id}"


# ── Conversión a DTO ────────────────────────────────────────

def a_pase_dto(pase: Pase) -> PaseDTO:
    return PaseDTO(id=pase.id, slot_id=pase.slot_id, artista_id=pase.artista_id,
                   artista_nombre=pase.artista.nombre if pase.artista else None, formato=pase.formato,
                   estado=pase.estado, notas_tecnicas=pase.notas_tecnicas, version=pase.version)


def a_slot_dto(slot: Slot) -> SlotDTO:
    return SlotDTO(id=slot.id, evento_id=slot.evento_id, espacio_id=slot.espacio_id, inicio=utc(slot.inicio),
                   fin=utc(slot.fin), tipo=slot.tipo, pase=a_pase_dto(slot.pase) if slot.pase else None)


def a_resumen(pase: Pase) -> PaseResumenDTO:
    return PaseResumenDTO(pase_id=pase.id, artista_id=pase.artista_id, artista=pase.artista.nombre,
                          escenario=pase.slot.escenario.nombre, inicio=utc(pase.slot.inicio),
                          fin=utc(pase.slot.fin), estado=pase.estado)


# ── Escaleta publicada (público) ────────────────────────────

def obtener_escaleta(db: Session, evento_id: str) -> dict:
    """La consulta más frecuente: se sirve desde caché (Redis) y, si no está, desde la última publicación."""
    escaleta = cache.obtener(_clave_cache(evento_id))
    if escaleta is None:
        publicacion = escaleta_dao.ultima_publicacion(db, evento_id)
        if not publicacion:
            raise ErrorApi(404, "ESCALETA_NO_PUBLICADA", f"El evento {evento_id} no tiene escaleta publicada")
        escaleta = publicacion.instantanea
        cache.guardar(_clave_cache(evento_id), escaleta, CACHE_SEGUNDOS)
    return escaleta


def obtener_escaleta_escenario(db: Session, evento_id: str, espacio_id: str) -> dict:
    escaleta = obtener_escaleta(db, evento_id)
    resultado = None
    for dia in escaleta["dias"]:
        for escenario in dia["escenarios"]:
            if escenario["espacio_id"] == espacio_id:
                resultado = resultado or {"espacio_id": espacio_id, "nombre": escenario["nombre"], "pases": []}
                resultado["pases"] += escenario["pases"]
    if not resultado:
        raise ErrorApi(404, "ESCENARIO_NO_ENCONTRADO", f"El escenario {espacio_id} no aparece en la escaleta")
    return resultado


def comprobar_evento_existe(db: Session, evento_id: str) -> None:
    if not escaleta_dao.obtener_evento(db, evento_id) and not escaleta_dao.ultima_publicacion(db, evento_id):
        raise ErrorApi(404, "EVENTO_NO_ENCONTRADO", f"No existe el evento {evento_id}")


# ── Publicación ─────────────────────────────────────────────

def _construir_dias(db: Session, evento_id: str) -> list[dict]:
    """Agrupa los pases del borrador por día de festival y escenario."""
    por_dia: dict[date, dict[str, dict]] = defaultdict(dict)
    for slot in escaleta_dao.listar_slots(db, evento_id):
        if not slot.pase:
            continue
        escenarios = por_dia[dia_de_festival(slot.inicio)]
        escenario = escenarios.setdefault(slot.espacio_id, {"espacio_id": slot.espacio_id,
                                                             "nombre": slot.escenario.nombre, "pases": []})
        escenario["pases"].append(a_resumen(slot.pase).model_dump(mode="json"))
    return [
        {"fecha": dia.isoformat(), "escenarios": sorted(escenarios.values(), key=lambda e: e["nombre"])}
        for dia, escenarios in sorted(por_dia.items())
    ]


def publicar_escaleta(db: Session, evento_id: str, admin_id: str) -> Publicacion:
    evento = escaleta_dao.obtener_evento(db, evento_id)
    if not evento:
        raise ErrorApi(404, "EVENTO_NO_ENCONTRADO", f"No existe el evento {evento_id}")
    if evento.estado == "CANCELADO":
        raise ErrorApi(409, "EVENTO_NO_ADMITE_ESCALETA", "El evento está cancelado")

    dias = _construir_dias(db, evento_id)
    anterior = escaleta_dao.ultima_publicacion(db, evento_id)
    if anterior and anterior.instantanea["dias"] == dias:
        raise ErrorApi(409, "SIN_CAMBIOS", "No hay cambios desde la última publicación")

    version = (anterior.version if anterior else 0) + 1
    publicada_en = datetime.now(timezone.utc)
    instantanea = EscaletaDTO(evento_id=evento_id, version=version, publicada_en=publicada_en,
                              dias=dias).model_dump(mode="json")
    publicacion = escaleta_dao.crear_publicacion(db, Publicacion(
        evento_id=evento_id, version=version, publicada_en=publicada_en, publicada_por=admin_id,
        instantanea=instantanea))
    db.commit()

    cache.guardar(_clave_cache(evento_id), instantanea, CACHE_SEGUNDOS)
    # El evento lleva la escaleta completa: ms-analitica la usa para «mi escaleta» y la afluencia
    publicar("escaleta.publicada", {"evento_id": evento_id, "version": version, "dias": dias})
    difusor.emitir(evento_id, "escaleta.publicada", {"tipo": "escaleta.publicada", "version": version})
    return publicacion


def listar_publicaciones(db: Session, evento_id: str) -> list[PublicacionDTO]:
    return [PublicacionDTO(evento_id=p.evento_id, version=p.version, publicada_en=utc(p.publicada_en),
                           publicada_por=p.publicada_por)
            for p in escaleta_dao.listar_publicaciones(db, evento_id)]


# ── Slots (borrador) ────────────────────────────────────────

def listar_slots(db: Session, evento_id: str, espacio_id: str | None, fecha: date | None) -> list[SlotDTO]:
    desde = hasta = None
    if fecha:
        desde = datetime.combine(fecha, time(HORA_CORTE_DIA), tzinfo=timezone.utc)
        hasta = desde + timedelta(days=1)
    return [a_slot_dto(s) for s in escaleta_dao.listar_slots(db, evento_id, espacio_id=espacio_id,
                                                             desde=desde, hasta=hasta)]


def obtener_slot(db: Session, slot_id: UUID, *, bloquear: bool = False) -> Slot:
    slot = escaleta_dao.obtener_slot(db, slot_id, bloquear=bloquear)
    if not slot:
        raise ErrorApi(404, "SLOT_NO_ENCONTRADO", f"No existe el slot {slot_id}")
    return slot


def _escenario_del_evento(db: Session, evento_id: str, espacio_id: str) -> Escenario:
    escenario = escaleta_dao.obtener_escenario(db, espacio_id)
    if not escenario:
        raise ErrorApi(404, "ESCENARIO_NO_ENCONTRADO", f"No existe el escenario {espacio_id}")
    if escenario.evento_id != evento_id:
        raise ErrorApi(400, "ESCENARIO_DE_OTRO_EVENTO", f"El escenario {espacio_id} no es del evento {evento_id}")
    return escenario


def _comprobar_huecos(db: Session, espacio_id: str, inicio: datetime, fin: datetime, *,
                      slot_id: UUID | None = None, pase: Pase | None = None, artista_id: UUID | None = None):
    if escaleta_dao.slot_solapado(db, espacio_id, inicio, fin, excluir_id=slot_id):
        raise ErrorApi(409, "SLOT_SOLAPADO", "El slot se solapa con otro del mismo escenario")
    artista_id = artista_id or (pase.artista_id if pase else None)
    if artista_id and escaleta_dao.pase_solapado_de_artista(db, artista_id, inicio, fin,
                                                            excluir_pase_id=pase.id if pase else None):
        raise ErrorApi(409, "ARTISTA_SOLAPADO", "El artista ya tiene otro pase a esa hora")


def _commit(db: Session):
    """La restricción de exclusión de PostgreSQL es la última barrera ante peticiones simultáneas."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ErrorApi(409, "SLOT_SOLAPADO", "El slot se solapa con otro del mismo escenario")


def crear_slot(db: Session, evento_id: str, datos: SlotEntradaDTO) -> SlotDTO:
    evento = escaleta_dao.obtener_evento(db, evento_id)
    if not evento:
        raise ErrorApi(404, "EVENTO_NO_ENCONTRADO", f"No existe el evento {evento_id}")
    if evento.estado != "PUBLICADO":
        raise ErrorApi(409, "EVENTO_NO_ADMITE_ESCALETA", f"El evento está {evento.estado}")
    _escenario_del_evento(db, evento_id, datos.espacio_id)
    inicio, fin = utc(datos.inicio), utc(datos.fin)
    _comprobar_huecos(db, datos.espacio_id, inicio, fin)
    slot = escaleta_dao.crear_slot(db, Slot(evento_id=evento_id, espacio_id=datos.espacio_id, inicio=inicio, fin=fin,
                                            tipo=datos.tipo.value))
    _commit(db)
    return a_slot_dto(obtener_slot(db, slot.id))


def modificar_slot(db: Session, slot_id: UUID, datos: SlotEntradaDTO) -> SlotDTO:
    slot = obtener_slot(db, slot_id, bloquear=True)
    _escenario_del_evento(db, slot.evento_id, datos.espacio_id)
    if slot.pase and datos.tipo != TipoSlot.ACTUACION:
        raise ErrorApi(400, "SLOT_CON_PASE", "Un slot con pase asignado debe ser de tipo ACTUACION")
    inicio, fin = utc(datos.inicio), utc(datos.fin)
    _comprobar_huecos(db, datos.espacio_id, inicio, fin, slot_id=slot.id, pase=slot.pase)
    slot.espacio_id, slot.inicio, slot.fin, slot.tipo = datos.espacio_id, inicio, fin, datos.tipo.value
    if slot.pase:
        slot.pase.version += 1
    _commit(db)
    return a_slot_dto(obtener_slot(db, slot_id))


def eliminar_slot(db: Session, slot_id: UUID) -> None:
    db.delete(obtener_slot(db, slot_id, bloquear=True))
    db.commit()


# ── Pases ───────────────────────────────────────────────────

def obtener_pase(db: Session, pase_id: UUID, *, bloquear: bool = False) -> Pase:
    pase = escaleta_dao.obtener_pase(db, pase_id, bloquear=bloquear)
    if not pase:
        raise ErrorApi(404, "PASE_NO_ENCONTRADO", f"No existe el pase {pase_id}")
    return pase


def crear_pase(db: Session, slot_id: UUID, datos: PaseEntradaDTO) -> PaseDTO:
    slot = obtener_slot(db, slot_id, bloquear=True)
    if slot.tipo != TipoSlot.ACTUACION.value:
        raise ErrorApi(400, "SLOT_SIN_ACTUACION", f"Un slot de tipo {slot.tipo} no admite artistas")
    if slot.pase:
        raise ErrorApi(409, "SLOT_OCUPADO", "El slot ya tiene un pase asignado")
    if not artista_dao.obtener(db, datos.artista_id):
        raise ErrorApi(404, "ARTISTA_NO_ENCONTRADO", f"No existe el artista {datos.artista_id}")
    _comprobar_huecos(db, slot.espacio_id, utc(slot.inicio), utc(slot.fin), slot_id=slot.id,
                      artista_id=datos.artista_id)
    pase = escaleta_dao.crear_pase(db, Pase(slot_id=slot.id, artista_id=datos.artista_id, formato=datos.formato.value,
                                            notas_tecnicas=datos.notas_tecnicas, estado="PROGRAMADO", version=1))
    db.commit()
    return a_pase_dto(obtener_pase(db, pase.id))


def modificar_pase(db: Session, pase_id: UUID, datos: PaseCambioDTO) -> PaseDTO:
    pase = obtener_pase(db, pase_id, bloquear=True)
    if datos.version != pase.version:
        raise ErrorApi(409, "VERSION_OBSOLETA", "Otro administrador ha modificado el pase; recárgalo",
                       {"version_actual": pase.version})

    if datos.estado and datos.estado.value != pase.estado:
        if datos.estado not in TRANSICIONES_PASE.get(EstadoPase(pase.estado), set()):
            raise ErrorApi(409, "TRANSICION_NO_PERMITIDA", f"No se puede pasar de {pase.estado} a {datos.estado.value}")
        pase.estado = datos.estado.value

    slot = pase.slot
    if datos.inicio or datos.fin or datos.espacio_id:
        inicio = utc(datos.inicio) if datos.inicio else utc(slot.inicio)
        fin = utc(datos.fin) if datos.fin else utc(slot.fin)
        espacio_id = datos.espacio_id or slot.espacio_id
        if fin <= inicio:
            raise ErrorApi(400, "PETICION_NO_VALIDA", "fin debe ser posterior a inicio")
        _escenario_del_evento(db, slot.evento_id, espacio_id)
        _comprobar_huecos(db, espacio_id, inicio, fin, slot_id=slot.id, pase=pase)
        slot.inicio, slot.fin, slot.espacio_id = inicio, fin, espacio_id

    if datos.formato:
        pase.formato = datos.formato.value
    pase.version += 1
    _commit(db)

    pase = obtener_pase(db, pase_id)
    _avisar_cambio(pase, datos.motivo)
    return a_pase_dto(pase)


def _avisar_cambio(pase: Pase, motivo: str | None = None) -> None:
    resumen = a_resumen(pase)
    cancelado = pase.estado == EstadoPase.CANCELADO.value
    tipo = "escaleta.pase.cancelado" if cancelado else "escaleta.pase.modificado"
    publicar(tipo, {"pase_id": str(pase.id), "evento_id": pase.slot.evento_id, "artista_id": str(pase.artista_id),
                    "artista_nombre": resumen.artista, "escenario": resumen.escenario,
                    "inicio_nuevo": resumen.inicio.isoformat(), "fin_nuevo": resumen.fin.isoformat(),
                    "estado": pase.estado, "motivo": motivo})
    tipo_sse = "pase.cancelado" if cancelado else "pase.modificado"
    difusor.emitir(pase.slot.evento_id, tipo_sse,
                   {"tipo": tipo_sse, "pase": resumen.model_dump(mode="json"), "version": pase.version})


def eliminar_pase(db: Session, pase_id: UUID) -> None:
    db.delete(obtener_pase(db, pase_id, bloquear=True))
    db.commit()


# ── Reacciones a eventos de ms-espacios (se conectarán a RabbitMQ) ──

def al_cambiar_espacio(db: Session, tipo_evento: str, datos: dict) -> None:
    """espacios.espacio.creado / actualizado / eliminado: réplica de escenarios."""
    if datos.get("tipo") != "ESCENARIO":
        return
    if tipo_evento == "espacios.espacio.eliminado":
        escenario = escaleta_dao.obtener_escenario(db, datos["espacio_id"])
        if escenario and not escaleta_dao.listar_slots(db, escenario.evento_id, espacio_id=escenario.espacio_id):
            db.delete(escenario)
    else:
        escaleta_dao.guardar_escenario(db, Escenario(
            espacio_id=datos["espacio_id"], evento_id=datos["evento_id"], nombre=datos["nombre"],
            aforo=datos.get("aforo"), actualizado_en=datetime.now(timezone.utc)))
    db.commit()


def al_cambiar_estado_evento(db: Session, evento_id: str, estado: str) -> None:
    """espacios.evento.publicado permite crear slots; espacios.evento.cancelado cancela todos los pases."""
    escaleta_dao.guardar_evento(db, EventoReplica(evento_id=evento_id, estado=estado,
                                                  actualizado_en=datetime.now(timezone.utc)))
    cancelados = []
    if estado == "CANCELADO":
        for pase in escaleta_dao.pases_de_evento(db, evento_id):
            if pase.estado not in (EstadoPase.FINALIZADO.value, EstadoPase.CANCELADO.value):
                pase.estado = EstadoPase.CANCELADO.value
                pase.version += 1
                cancelados.append(pase.id)
    db.commit()
    for pase_id in cancelados:
        _avisar_cambio(obtener_pase(db, pase_id), "Evento cancelado")
