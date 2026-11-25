# ms-tienda/eventos/manejadores.py
# Qué hace ms-tienda con cada evento que consume (ver "Eventos que consume" en openapi.yaml).
# Todas las reacciones son idempotentes: procesar dos veces el mismo mensaje deja todo igual.
from config.database import SessionLocal
from eventos.consumidor import Consumidor
from service import pedido_service

EVENTOS_ESTADO = ("espacios.evento.publicado", "espacios.evento.cancelado")


def manejar(sobre: dict) -> None:
    tipo, datos = sobre["tipo"], sobre["datos"]
    db = SessionLocal()
    try:
        if tipo == "usuarios.usuario.eliminado":
            pedido_service.anonimizar_pedidos_usuario(db, datos["usuario_id"])
        elif tipo in EVENTOS_ESTADO:
            pedido_service.al_cambiar_estado_evento(db, datos["evento_id"], datos["estado"])
        else:
            raise ValueError(f"Evento no soportado por ms-tienda: {tipo}")
    finally:
        db.close()


consumidor = Consumidor(
    cola="ms-tienda",
    claves=["usuarios.usuario.eliminado", *EVENTOS_ESTADO],
    manejador=manejar,
)
