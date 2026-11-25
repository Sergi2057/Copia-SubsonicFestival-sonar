# ms-escaleta/model/dao/escaleta_dao.py
# Acceso a las tablas slots, pases, publicaciones y réplicas (escenarios, eventos)
from datetime import datetime
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from model.models import Escenario, EventoReplica, Pase, Publicacion, Slot

_CARGA_SLOT = (selectinload(Slot.pase).selectinload(Pase.artista), selectinload(Slot.escenario))


class EscaletaDAO:
    # ── Slots ────────────────────────────────────────────────

    def listar_slots(self, db: Session, evento_id: str, *, espacio_id: str | None = None,
                     desde: datetime | None = None, hasta: datetime | None = None) -> list[Slot]:
        consulta = select(Slot).where(Slot.evento_id == evento_id).options(*_CARGA_SLOT)
        if espacio_id:
            consulta = consulta.where(Slot.espacio_id == espacio_id)
        if desde:
            consulta = consulta.where(Slot.inicio >= desde)
        if hasta:
            consulta = consulta.where(Slot.inicio < hasta)
        return list(db.scalars(consulta.order_by(Slot.inicio)).all())

    def obtener_slot(self, db: Session, slot_id: UUID, *, bloquear: bool = False) -> Slot | None:
        consulta = select(Slot).where(Slot.id == slot_id).options(*_CARGA_SLOT)
        if bloquear:
            consulta = consulta.with_for_update(of=Slot)
        return db.scalar(consulta)

    def crear_slot(self, db: Session, slot: Slot) -> Slot:
        db.add(slot)
        db.flush()
        return slot

    def slot_solapado(self, db: Session, espacio_id: str, inicio: datetime, fin: datetime,
                      excluir_id: UUID | None = None) -> Slot | None:
        consulta = select(Slot).where(Slot.espacio_id == espacio_id, Slot.inicio < fin, Slot.fin > inicio)
        if excluir_id:
            consulta = consulta.where(Slot.id != excluir_id)
        return db.scalar(consulta.limit(1))

    def pase_solapado_de_artista(self, db: Session, artista_id: UUID, inicio: datetime, fin: datetime,
                                 excluir_pase_id: UUID | None = None) -> Pase | None:
        """Otro pase no cancelado del artista que coincide en el tiempo (en cualquier escenario)."""
        consulta = select(Pase).join(Slot).where(
            Pase.artista_id == artista_id, Pase.estado != "CANCELADO", Slot.inicio < fin, Slot.fin > inicio,
        )
        if excluir_pase_id:
            consulta = consulta.where(Pase.id != excluir_pase_id)
        return db.scalar(consulta.limit(1))

    # ── Pases ────────────────────────────────────────────────

    def obtener_pase(self, db: Session, pase_id: UUID, *, bloquear: bool = False) -> Pase | None:
        consulta = select(Pase).where(Pase.id == pase_id).options(
            selectinload(Pase.artista), selectinload(Pase.slot).selectinload(Slot.escenario))
        if bloquear:
            consulta = consulta.with_for_update(of=Pase)
        return db.scalar(consulta)

    def crear_pase(self, db: Session, pase: Pase) -> Pase:
        db.add(pase)
        db.flush()
        return pase

    def pases_de_evento(self, db: Session, evento_id: str) -> list[Pase]:
        return list(db.scalars(
            select(Pase).join(Slot).where(Slot.evento_id == evento_id).options(selectinload(Pase.artista))
        ).all())

    # ── Publicaciones ────────────────────────────────────────

    def ultima_publicacion(self, db: Session, evento_id: str) -> Publicacion | None:
        return db.scalar(
            select(Publicacion).where(Publicacion.evento_id == evento_id).order_by(Publicacion.version.desc()).limit(1)
        )

    def listar_publicaciones(self, db: Session, evento_id: str) -> list[Publicacion]:
        return list(db.scalars(
            select(Publicacion).where(Publicacion.evento_id == evento_id).order_by(Publicacion.version.desc())
        ).all())

    def ultimas_publicaciones(self, db: Session) -> list[Publicacion]:
        """La última versión publicada de cada evento."""
        ultimas = select(Publicacion.evento_id, func.max(Publicacion.version).label("version")) \
            .group_by(Publicacion.evento_id).subquery()
        return list(db.scalars(
            select(Publicacion).join(ultimas, (Publicacion.evento_id == ultimas.c.evento_id)
                                     & (Publicacion.version == ultimas.c.version))
        ).all())

    def crear_publicacion(self, db: Session, publicacion: Publicacion) -> Publicacion:
        db.add(publicacion)
        db.flush()
        return publicacion

    # ── Réplicas ─────────────────────────────────────────────

    def obtener_escenario(self, db: Session, espacio_id: str) -> Escenario | None:
        return db.get(Escenario, espacio_id)

    def guardar_escenario(self, db: Session, escenario: Escenario) -> Escenario:
        return db.merge(escenario)

    def obtener_evento(self, db: Session, evento_id: str) -> EventoReplica | None:
        return db.get(EventoReplica, evento_id)

    def guardar_evento(self, db: Session, evento: EventoReplica) -> EventoReplica:
        return db.merge(evento)
