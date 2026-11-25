# ms-tienda/model/dao/evento_recogida_dao.py
# Acceso a la tabla eventos_recogida (réplica del estado de los eventos de ms-espacios)
from sqlalchemy.orm import Session
from model.models import EventoRecogida


class EventoRecogidaDAO:
    def obtener(self, db: Session, evento_id: str) -> EventoRecogida | None:
        return db.get(EventoRecogida, evento_id)

    def guardar(self, db: Session, evento: EventoRecogida) -> EventoRecogida:
        """Inserta o actualiza (el evento puede llegar repetido)."""
        return db.merge(evento)
