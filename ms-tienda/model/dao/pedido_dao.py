# ms-tienda/model/dao/pedido_dao.py
# Acceso a las tablas pedidos y lineas_pedido
from uuid import UUID
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload
from model.models import LineaPedido, Pedido, Variante

_CARGA_LINEAS = selectinload(Pedido.lineas).selectinload(LineaPedido.variante).selectinload(Variante.producto)


class PedidoDAO:
    def listar(self, db: Session, *, usuario_id: str | None, estado: str | None,
               evento_id_recogida: str | None, limite: int, desplazamiento: int) -> tuple[list[Pedido], int]:
        consulta = select(Pedido)
        if usuario_id:
            consulta = consulta.where(Pedido.usuario_id == usuario_id)
        if estado:
            consulta = consulta.where(Pedido.estado == estado)
        if evento_id_recogida:
            consulta = consulta.where(Pedido.evento_id_recogida == evento_id_recogida)

        total = db.scalar(select(func.count()).select_from(consulta.subquery()))
        pedidos = db.scalars(
            consulta.options(_CARGA_LINEAS)
            .order_by(Pedido.creado_en.desc())
            .limit(limite)
            .offset(desplazamiento)
        ).all()
        return list(pedidos), total

    def obtener(self, db: Session, pedido_id: str, *, bloquear: bool = False) -> Pedido | None:
        consulta = select(Pedido).where(Pedido.id == pedido_id).options(_CARGA_LINEAS)
        if bloquear:
            consulta = consulta.with_for_update(of=Pedido)
        return db.scalar(consulta)

    def crear(self, db: Session, pedido: Pedido) -> Pedido:
        db.add(pedido)
        db.flush()
        return pedido

    def variante_en_pedidos(self, db: Session, variante_id: UUID, estados: set[str] | None = None) -> bool:
        """¿Aparece la variante en algún pedido (opcionalmente, solo en pedidos con esos estados)?"""
        consulta = select(LineaPedido.pedido_id).where(LineaPedido.variante_id == variante_id)
        if estados:
            consulta = consulta.join(Pedido).where(Pedido.estado.in_(estados))
        return db.scalar(consulta.limit(1)) is not None

    def anonimizar_de_usuario(self, db: Session, usuario_id: str) -> int:
        """RGPD: desvincula los pedidos del cliente eliminado y borra su dirección."""
        resultado = db.execute(
            update(Pedido)
            .where(Pedido.usuario_id == usuario_id)
            .values(usuario_id="anonimizado", direccion_envio=None)
        )
        return resultado.rowcount
