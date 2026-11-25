# ms-tienda/model/dao/producto_dao.py
# Acceso a las tablas productos y variantes
from uuid import UUID
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, selectinload
from model.models import Producto, Variante


class ProductoDAO:
    def listar(self, db: Session, *, evento_id: str | None, disponible: bool | None,
               incluir_inactivos: bool, limite: int, desplazamiento: int) -> tuple[list[Producto], int]:
        consulta = select(Producto)
        if not incluir_inactivos:
            consulta = consulta.where(Producto.activo.is_(True))
        # Sin evento_id solo se muestra el merchandising general; con él, también el exclusivo de ese evento
        if evento_id:
            consulta = consulta.where(or_(Producto.evento_id.is_(None), Producto.evento_id == evento_id))
        else:
            consulta = consulta.where(Producto.evento_id.is_(None))
        if disponible:
            consulta = consulta.where(
                exists().where(Variante.producto_id == Producto.id, Variante.activa.is_(True), Variante.stock > 0)
            )

        total = db.scalar(select(func.count()).select_from(consulta.subquery()))
        productos = db.scalars(
            consulta.options(selectinload(Producto.variantes))
            .order_by(Producto.id)
            .limit(limite)
            .offset(desplazamiento)
        ).all()
        return list(productos), total

    def obtener(self, db: Session, producto_id: str) -> Producto | None:
        return db.get(Producto, producto_id, options=[selectinload(Producto.variantes)])

    def crear(self, db: Session, producto: Producto) -> Producto:
        db.add(producto)
        db.flush()
        return producto

    # ── Variantes ────────────────────────────────────────────

    def obtener_variante(self, db: Session, variante_id: UUID) -> Variante | None:
        return db.get(Variante, variante_id)

    def obtener_variante_por_talla(self, db: Session, producto_id: str, talla: str) -> Variante | None:
        return db.scalar(
            select(Variante).where(Variante.producto_id == producto_id, Variante.talla == talla)
        )

    def bloquear_variantes(self, db: Session, variante_ids: list[UUID]) -> dict[UUID, Variante]:
        """SELECT … FOR UPDATE de las variantes (ordenadas por id para evitar interbloqueos)."""
        variantes = db.scalars(
            select(Variante)
            .where(Variante.id.in_(variante_ids))
            .order_by(Variante.id)
            .with_for_update()
        ).all()
        return {v.id: v for v in variantes}

    def crear_variante(self, db: Session, variante: Variante) -> Variante:
        db.add(variante)
        db.flush()
        return variante

    def eliminar_variante(self, db: Session, variante: Variante) -> None:
        db.delete(variante)
        db.flush()
