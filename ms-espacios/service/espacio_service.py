# ms-espacios/service/espacio_service.py
# Lógica de negocio de espacios, alquileres y réplica de proveedores
import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from config.errores import ErrorApi
from config.seguridad import UsuarioActual
from eventos.publicador import publicar
from model.dto.espacio_dto import (
    AlquilerDTO, AlquilerEntradaDTO, CambioEstadoAlquilerDTO, EspacioEntradaDTO, EstadoAlquiler,
)
from model.factory.factory_dao import DAOFactory
from model.models import Alquiler, Espacio, Proveedor

espacio_dao = DAOFactory.get_espacio_dao()
evento_dao = DAOFactory.get_evento_dao()

# Transiciones permitidas por rol (estado actual -> estados destino)
TRANSICIONES_ALQUILER = {
    "admin": {EstadoAlquiler.PENDIENTE: {EstadoAlquiler.APROBADO, EstadoAlquiler.RECHAZADO}},
    "proveedor": {EstadoAlquiler.PENDIENTE: {EstadoAlquiler.CANCELADO},
                  EstadoAlquiler.ACTIVO: {EstadoAlquiler.FINALIZADO}},
}


def utc(fecha: datetime) -> datetime:
    """Normaliza a UTC (SQLite devuelve fechas sin zona; se guardan siempre en UTC)."""
    return fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha.astimezone(timezone.utc)


def _datos_espacio(espacio: Espacio) -> dict:
    return {"espacio_id": espacio.id, "evento_id": espacio.evento_id, "tipo": espacio.tipo,
            "nombre": espacio.nombre, "zona": espacio.zona, "aforo": espacio.aforo,
            "precio_alquiler": float(espacio.precio_alquiler) if espacio.precio_alquiler is not None else None,
            "disponible": espacio.disponible}


def _datos_alquiler(alquiler: Alquiler) -> dict:
    return {"alquiler_id": str(alquiler.id), "espacio_id": alquiler.espacio_id,
            "evento_id": alquiler.espacio.evento_id, "proveedor_id": alquiler.proveedor_id,
            "fecha_inicio": utc(alquiler.fecha_inicio).isoformat(), "fecha_fin": utc(alquiler.fecha_fin).isoformat(),
            "importe": float(alquiler.importe), "estado": alquiler.estado}


# ── Espacios ────────────────────────────────────────────────

def listar_tipos(db: Session):
    return espacio_dao.listar_tipos(db)


def buscar_espacios(db: Session, **filtros):
    return espacio_dao.listar(db, **filtros)


def obtener_espacio(db: Session, espacio_id: str, *, bloquear: bool = False) -> Espacio:
    espacio = espacio_dao.obtener(db, espacio_id, bloquear=bloquear)
    if not espacio:
        raise ErrorApi(404, "ESPACIO_NO_ENCONTRADO", f"No existe el espacio {espacio_id}")
    return espacio


def _validar_espacio(db: Session, datos: EspacioEntradaDTO):
    if not evento_dao.obtener(db, datos.evento_id):
        raise ErrorApi(400, "EVENTO_NO_VALIDO", f"No existe el evento {datos.evento_id}")
    tipo = espacio_dao.obtener_tipo(db, datos.tipo.value)
    if tipo.alquilable and datos.precio_alquiler is None:
        raise ErrorApi(400, "PETICION_NO_VALIDA", "Un espacio alquilable necesita precio_alquiler")
    if not tipo.alquilable and datos.precio_alquiler is not None:
        raise ErrorApi(400, "PETICION_NO_VALIDA", f"Los espacios de tipo {tipo.codigo} no se alquilan")


def crear_espacio(db: Session, datos: EspacioEntradaDTO) -> Espacio:
    _validar_espacio(db, datos)
    espacio = espacio_dao.crear(db, Espacio(id=f"espacio-{uuid.uuid4().hex[:8]}", **datos.model_dump()))
    db.commit()
    publicar("espacios.espacio.creado", _datos_espacio(espacio))
    return espacio


def modificar_espacio(db: Session, espacio_id: str, datos: EspacioEntradaDTO) -> Espacio:
    espacio = obtener_espacio(db, espacio_id)
    _validar_espacio(db, datos)
    for campo, valor in datos.model_dump().items():
        setattr(espacio, campo, valor)
    db.commit()
    publicar("espacios.espacio.actualizado", _datos_espacio(espacio))
    return espacio


def eliminar_espacio(db: Session, espacio_id: str) -> None:
    espacio = obtener_espacio(db, espacio_id, bloquear=True)
    if espacio_dao.tiene_alquileres_que_ocupan(db, espacio_id):
        raise ErrorApi(409, "ESPACIO_CON_ALQUILERES", "El espacio tiene alquileres aprobados o activos")
    datos = _datos_espacio(espacio)
    espacio_dao.eliminar(db, espacio)
    db.commit()
    publicar("espacios.espacio.eliminado", datos)


# ── Alquileres ──────────────────────────────────────────────

def a_alquiler_dto(db: Session, alquileres: list[Alquiler]) -> list[AlquilerDTO]:
    nombres = espacio_dao.nombres_proveedores(db, {a.proveedor_id for a in alquileres})
    return [
        AlquilerDTO(
            id=a.id, espacio_id=a.espacio_id, evento_id=a.espacio.evento_id, proveedor_id=a.proveedor_id,
            proveedor_nombre=nombres.get(a.proveedor_id), fecha_inicio=utc(a.fecha_inicio),
            fecha_fin=utc(a.fecha_fin), importe=float(a.importe), estado=a.estado, comentarios=a.comentarios,
            creado_en=utc(a.creado_en),
        )
        for a in alquileres
    ]


def solicitar_alquiler(db: Session, usuario: UsuarioActual, espacio_id: str, datos: AlquilerEntradaDTO) -> Alquiler:
    proveedor = espacio_dao.obtener_proveedor(db, usuario.id)
    if not proveedor or not proveedor.activo:
        raise ErrorApi(403, "PROVEEDOR_NO_ACTIVO", "La cuenta de proveedor no existe o está desactivada")

    espacio = obtener_espacio(db, espacio_id, bloquear=True)
    if not espacio.tipo_espacio.alquilable or not espacio.disponible:
        raise ErrorApi(409, "ESPACIO_NO_DISPONIBLE", "El espacio no admite solicitudes de alquiler")

    inicio, fin = utc(datos.fecha_inicio), utc(datos.fecha_fin)
    if espacio_dao.hay_solape(db, espacio_id, inicio, fin):
        raise ErrorApi(409, "ALQUILER_SOLAPADO", "El espacio ya tiene un alquiler aprobado en esas fechas")

    # Importe = precio de alquiler por día (días completos o empezados)
    dias = max(math.ceil((fin - inicio).total_seconds() / 86400), 1)
    alquiler = espacio_dao.crear_alquiler(db, Alquiler(
        espacio_id=espacio_id, proveedor_id=usuario.id, fecha_inicio=inicio, fecha_fin=fin,
        importe=Decimal(espacio.precio_alquiler) * dias, estado=EstadoAlquiler.PENDIENTE.value,
        comentarios=datos.comentarios,
    ))
    db.commit()
    publicar("espacios.alquiler.solicitado", _datos_alquiler(alquiler))
    return alquiler


def listar_alquileres(db: Session, usuario: UsuarioActual, *, estado, evento_id, proveedor_id,
                      limite, desplazamiento):
    if usuario.rol == "proveedor":
        proveedor_id = usuario.id  # un proveedor solo ve los suyos
    return espacio_dao.listar_alquileres(db, proveedor_id=proveedor_id, estado=estado, evento_id=evento_id,
                                         limite=limite, desplazamiento=desplazamiento)


def obtener_alquiler(db: Session, usuario: UsuarioActual, alquiler_id: UUID, *, bloquear: bool = False) -> Alquiler:
    alquiler = espacio_dao.obtener_alquiler(db, alquiler_id, bloquear=bloquear)
    if not alquiler:
        raise ErrorApi(404, "ALQUILER_NO_ENCONTRADO", f"No existe el alquiler {alquiler_id}")
    if usuario.rol != "admin" and alquiler.proveedor_id != usuario.id:
        raise ErrorApi(403, "SIN_PERMISO", "El alquiler no pertenece al proveedor")
    return alquiler


def cambiar_estado_alquiler(db: Session, usuario: UsuarioActual, alquiler_id: UUID,
                            datos: CambioEstadoAlquilerDTO) -> Alquiler:
    alquiler = obtener_alquiler(db, usuario, alquiler_id, bloquear=True)
    actual = EstadoAlquiler(alquiler.estado)
    if datos.estado not in TRANSICIONES_ALQUILER.get(usuario.rol, {}).get(actual, set()):
        raise ErrorApi(409, "TRANSICION_NO_PERMITIDA",
                       f"Un {usuario.rol} no puede pasar un alquiler de {actual.value} a {datos.estado.value}")

    if datos.estado == EstadoAlquiler.APROBADO:
        espacio_dao.obtener(db, alquiler.espacio_id, bloquear=True)  # serializa aprobaciones del mismo espacio
        if espacio_dao.hay_solape(db, alquiler.espacio_id, utc(alquiler.fecha_inicio), utc(alquiler.fecha_fin),
                                  excluir_id=alquiler.id):
            raise ErrorApi(409, "ALQUILER_SOLAPADO", "Ya hay otro alquiler aprobado en esas fechas")

    alquiler.estado = datos.estado.value
    if datos.comentarios:
        alquiler.comentarios = datos.comentarios
    db.commit()

    tipo = {EstadoAlquiler.APROBADO: "espacios.alquiler.aprobado",
            EstadoAlquiler.RECHAZADO: "espacios.alquiler.rechazado",
            EstadoAlquiler.FINALIZADO: "espacios.alquiler.finalizado"}.get(datos.estado)
    if tipo:
        publicar(tipo, _datos_alquiler(alquiler))
    return alquiler


# ── Reacciones a eventos de ms-usuarios (se conectarán a RabbitMQ) ──

def actualizar_replica_proveedor(db: Session, datos: dict) -> None:
    """usuarios.proveedor.actualizado / desactivado."""
    proveedor = espacio_dao.guardar_proveedor(db, Proveedor(
        proveedor_id=datos["proveedor_id"], nombre_comercial=datos.get("nombre_comercial"),
        tipo_servicio=datos.get("tipo_servicio"), activo=datos.get("activo", True),
    ))
    if not proveedor.activo:
        espacio_dao.rechazar_pendientes_de_proveedor(db, proveedor.proveedor_id)
    db.commit()


def anonimizar_alquileres(db: Session, usuario_id: str) -> None:
    """usuarios.usuario.eliminado (RGPD)."""
    espacio_dao.anonimizar_de_proveedor(db, usuario_id)
    espacio_dao.eliminar_proveedor(db, usuario_id)
    db.commit()
