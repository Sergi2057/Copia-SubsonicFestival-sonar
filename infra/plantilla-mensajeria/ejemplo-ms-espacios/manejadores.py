# ms-espacios/eventos/manejadores.py
# Qué hace ms-espacios con cada evento que consume (ver "Eventos que consume" en openapi.yaml)
from uuid import UUID
from config.database import SessionLocal
from eventos.consumidor import Consumidor
from service import aforo_service, espacio_service


def manejar(sobre: dict) -> None:
    tipo, datos = sobre["tipo"], sobre["datos"]
    db = SessionLocal()
    try:
        if tipo == "usuarios.entrada.comprada":
            aforo_service.confirmar_reserva(db, UUID(datos["reserva_id"]))
        elif tipo == "usuarios.entrada.cancelada":
            aforo_service.liberar_plaza_vendida(db, datos["evento_id"], datos["tipo_pase"])
        elif tipo in ("usuarios.proveedor.actualizado", "usuarios.proveedor.desactivado"):
            espacio_service.actualizar_replica_proveedor(db, datos)
        elif tipo == "usuarios.usuario.eliminado":
            espacio_service.anonimizar_alquileres(db, datos["usuario_id"])
    finally:
        db.close()


consumidor = Consumidor(
    cola="ms-espacios",
    # Claves exactas: con "usuarios.entrada.*" llegaría también usuarios.entrada.validada
    claves=["usuarios.entrada.comprada", "usuarios.entrada.cancelada",
            "usuarios.proveedor.actualizado", "usuarios.proveedor.desactivado",
            "usuarios.usuario.eliminado"],
    manejador=manejar,
)
