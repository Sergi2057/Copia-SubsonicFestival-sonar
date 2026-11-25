import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from config.database import SessionLocal
from model.factory.factory_dao import DAOFactory

log = logging.getLogger(__name__)

evento_dao = DAOFactory.get_evento_dao()
espacio_dao = DAOFactory.get_espacio_dao()


def ejecutar_tareas_periodicas() -> None:
    db = SessionLocal()
    try:
        ahora = datetime.now(timezone.utc)
        reservas_caducadas = evento_dao.caducar_reservas(db, ahora)
        alquileres_activados = espacio_dao.activar_alquileres_iniciados(db, ahora)
        db.commit()

        if reservas_caducadas or alquileres_activados:
            log.info(
                "Tareas periódicas: %s reservas caducadas, %s alquileres activados",
                reservas_caducadas,
                alquileres_activados,
            )
    except SQLAlchemyError:
        db.rollback()
        log.exception("Error de base de datos al ejecutar las tareas periódicas")
        raise
    finally:
        db.close()
