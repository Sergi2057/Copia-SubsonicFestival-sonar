# ms-escaleta/model/dao/artista_dao.py
# Acceso a la tabla artistas
from uuid import UUID
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session
from model.models import Artista, Pase, Slot


class ArtistaDAO:
    def listar(self, db: Session, *, q: str | None, genero: str | None, evento_id: str | None,
               limite: int, desplazamiento: int) -> tuple[list[Artista], int]:
        consulta = select(Artista)
        if q:
            consulta = consulta.where(func.lower(Artista.nombre).like(f"%{q.lower()}%"))
        if genero:
            # Funciona igual con JSONB (PostgreSQL) y JSON (SQLite de los tests)
            consulta = consulta.where(func.lower(cast(Artista.generos, String)).like(f'%"{genero.lower()}"%'))
        if evento_id:
            con_pase = select(Pase.artista_id).join(Slot).where(Slot.evento_id == evento_id)
            consulta = consulta.where(Artista.id.in_(con_pase))
        total = db.scalar(select(func.count()).select_from(consulta.subquery()))
        artistas = db.scalars(consulta.order_by(Artista.nombre).limit(limite).offset(desplazamiento)).all()
        return list(artistas), total

    def obtener(self, db: Session, artista_id: UUID) -> Artista | None:
        return db.get(Artista, artista_id)

    def crear(self, db: Session, artista: Artista) -> Artista:
        db.add(artista)
        db.flush()
        return artista

    def tiene_pases(self, db: Session, artista_id: UUID) -> bool:
        return db.scalar(select(func.count()).select_from(Pase).where(Pase.artista_id == artista_id)) > 0
