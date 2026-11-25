# ms-espacios/eventos/manejadores.py
# Qué hace ms-espacios con cada evento que consume (ver "Eventos que consume" en openapi.yaml)
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from config.database import SessionLocal
from eventos.consumidor import Consumidor
from model.models import EventoProcesado
from service import aforo_service, espacio_service


def _registrar_cancelacion(db, sobre: dict) -> bool:
    id_evento = sobre.get("id_evento")
    if not id_evento:
        raise ValueError("El evento de cancelación no incluye id_evento")

    db.add(EventoProcesado(id_evento=id_evento, tipo=sobre["tipo"]))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if db.get(EventoProcesado, id_evento) is not None:
            return True
        raise
    return False


def manejar(sobre: dict) -> None:
    tipo, datos = sobre["tipo"], sobre["datos"]
    db = SessionLocal()
    try:
        if tipo == "usuarios.entrada.comprada":
            aforo_service.confirmar_reserva(db, UUID(datos["reserva_id"]))
        elif tipo == "usuarios.entrada.cancelada":
            if _registrar_cancelacion(db, sobre):
                return
            aforo_service.liberar_plaza_vendida(db, datos["evento_id"], datos["tipo_pase"])
            db.commit()
        elif tipo in ("usuarios.proveedor.actualizado", "usuarios.proveedor.desactivado"):
            espacio_service.actualizar_replica_proveedor(db, datos)
        elif tipo == "usuarios.usuario.eliminado":
            espacio_service.anonimizar_alquileres(db, datos["usuario_id"])
        else:
            raise ValueError(f"Evento no soportado por ms-espacios: {tipo}")
    finally:
        db.close()


consumidor = Consumidor(
    cola="ms-espacios",
    claves=["usuarios.entrada.comprada", "usuarios.entrada.cancelada",
            "usuarios.proveedor.*", "usuarios.usuario.eliminado"],
    manejador=manejar,
)
