# ms-tienda/model/factory/factory_dao.py
from model.dao.evento_recogida_dao import EventoRecogidaDAO
from model.dao.pedido_dao import PedidoDAO
from model.dao.producto_dao import ProductoDAO


class DAOFactory:
    @staticmethod
    def get_evento_recogida_dao() -> EventoRecogidaDAO:
        return EventoRecogidaDAO()

    @staticmethod
    def get_producto_dao() -> ProductoDAO:
        return ProductoDAO()

    @staticmethod
    def get_pedido_dao() -> PedidoDAO:
        return PedidoDAO()
