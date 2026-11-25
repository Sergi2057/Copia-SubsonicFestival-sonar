# ms-escaleta/model/factory/factory_dao.py
from model.dao.artista_dao import ArtistaDAO
from model.dao.escaleta_dao import EscaletaDAO


class DAOFactory:
    @staticmethod
    def get_artista_dao() -> ArtistaDAO:
        return ArtistaDAO()

    @staticmethod
    def get_escaleta_dao() -> EscaletaDAO:
        return EscaletaDAO()
