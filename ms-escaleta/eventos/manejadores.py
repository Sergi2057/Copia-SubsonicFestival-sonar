# ms-escaleta/eventos/manejadores.py
# Qué hace ms-escaleta con cada evento que consume (ver "Eventos que consume" en openapi.yaml).
# Las dos funciones son idempotentes: si RabbitMQ entrega dos veces el mismo mensaje, la réplica
# se sobrescribe con los mismos datos y los pases ya cancelados no se vuelven a tocar.
from config.database import SessionLocal
from eventos.consumidor import Consumidor
from service import escaleta_service

EVENTOS_ESPACIO = ("espacios.espacio.creado", "espacios.espacio.actualizado", "espacios.espacio.eliminado")
EVENTOS_ESTADO = ("espacios.evento.publicado", "espacios.evento.cancelado")


def manejar(sobre: dict) -> None:
    tipo, datos = sobre["tipo"], sobre["datos"]
    db = SessionLocal()
    try:
        if tipo in EVENTOS_ESPACIO:
            escaleta_service.al_cambiar_espacio(db, tipo, datos)
        elif tipo in EVENTOS_ESTADO:
            escaleta_service.al_cambiar_estado_evento(db, datos["evento_id"], datos["estado"])
        else:
            raise ValueError(f"Evento no soportado por ms-escaleta: {tipo}")
    finally:
        db.close()


# Claves exactas, sin comodines: con "espacios.evento.*" llegaría también espacios.evento.actualizado,
# que manejar() rechaza, y acabaría en la cola de fallidos tras 3 reintentos
consumidor = Consumidor(
    cola="ms-escaleta",
    claves=[*EVENTOS_ESPACIO, *EVENTOS_ESTADO],
    manejador=manejar,
)
