# ms-analitica/model/factory/factory_dao.py
from config.database import get_db
from model.dao.analitica_dao import AnaliticaDAO


class DAOFactory:
    @staticmethod
    def get_analitica_dao() -> AnaliticaDAO:
        return AnaliticaDAO(get_db())
