# ms-espacios/model/factory/factory_dao.py
from model.dao.espacio_dao import EspacioDAO
from model.dao.evento_dao import EventoDAO


class DAOFactory:
    @staticmethod
    def get_evento_dao() -> EventoDAO:
        return EventoDAO()

    @staticmethod
    def get_espacio_dao() -> EspacioDAO:
        return EspacioDAO()
