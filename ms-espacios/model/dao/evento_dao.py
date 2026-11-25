# ms-espacios/model/dao/evento_dao.py
# Acceso a las tablas eventos, recintos, tarifas_acceso y reservas_aforo
from datetime import date, datetime
from uuid import UUID
from sqlalchemy import String, cast, func, select, update
from sqlalchemy.orm import Session, selectinload
from model.models import Evento, Recinto, ReservaAforo, TarifaAcceso


class EventoDAO:
    # ── Eventos ──────────────────────────────────────────────

    def listar(self, db: Session, *, estados: list[str], pais: str | None, tag: str | None,
               desde: date | None, hasta: date | None, limite: int, desplazamiento: int) -> tuple[list[Evento], int]:
        consulta = select(Evento).where(Evento.estado.in_(estados))
        if pais:
            consulta = consulta.where(func.lower(Evento.pais) == pais.lower())
        if tag:
            # Funciona igual con JSONB (PostgreSQL) y JSON (SQLite de los tests)
            consulta = consulta.where(cast(Evento.tags, String).like(f'%"{tag}"%'))
        if desde:
            consulta = consulta.where(Evento.fecha_fin >= desde)
        if hasta:
            consulta = consulta.where(Evento.fecha_inicio <= hasta)

        total = db.scalar(select(func.count()).select_from(consulta.subquery()))
        eventos = db.scalars(
            consulta.order_by(Evento.fecha_inicio, Evento.id).limit(limite).offset(desplazamiento)
        ).all()
        return list(eventos), total

    def obtener(self, db: Session, evento_id: str, *, bloquear: bool = False) -> Evento | None:
        consulta = select(Evento).where(Evento.id == evento_id).options(selectinload(Evento.recinto))
        if bloquear:
            consulta = consulta.with_for_update(of=Evento)
        return db.scalar(consulta)

    def crear(self, db: Session, evento: Evento) -> Evento:
        db.add(evento)
        db.flush()
        return evento

    def eliminar(self, db: Session, evento: Evento) -> None:
        db.delete(evento)

    # ── Recintos ─────────────────────────────────────────────

    def listar_recintos(self, db: Session) -> list[Recinto]:
        return list(db.scalars(select(Recinto).order_by(Recinto.nombre)).all())

    def obtener_recinto(self, db: Session, recinto_id: UUID) -> Recinto | None:
        return db.get(Recinto, recinto_id)

    def crear_recinto(self, db: Session, recinto: Recinto) -> Recinto:
        db.add(recinto)
        db.flush()
        return recinto

    def tiene_eventos_en_recinto(self, db: Session, recinto_id: UUID) -> bool:
        return db.scalar(
            select(func.count()).select_from(Evento).where(Evento.recinto_id == recinto_id)
        ) > 0

    def eliminar_recinto(self, db: Session, recinto: Recinto) -> None:
        db.delete(recinto)

    # ── Tarifas ──────────────────────────────────────────────

    def listar_tarifas(self, db: Session, evento_id: str) -> list[TarifaAcceso]:
        return list(db.scalars(
            select(TarifaAcceso).where(TarifaAcceso.evento_id == evento_id).order_by(TarifaAcceso.precio)
        ).all())

    def obtener_tarifa(self, db: Session, evento_id: str, tarifa_id: UUID, *, bloquear: bool = False):
        consulta = select(TarifaAcceso).where(TarifaAcceso.id == tarifa_id, TarifaAcceso.evento_id == evento_id)
        if bloquear:
            consulta = consulta.with_for_update()
        return db.scalar(consulta)

    def obtener_tarifa_por_tipo(self, db: Session, evento_id: str, tipo_pase: str, *, bloquear: bool = False):
        consulta = select(TarifaAcceso).where(TarifaAcceso.evento_id == evento_id,
                                              TarifaAcceso.tipo_pase == tipo_pase)
        if bloquear:
            consulta = consulta.with_for_update()
        return db.scalar(consulta)

    def crear_tarifa(self, db: Session, tarifa: TarifaAcceso) -> TarifaAcceso:
        db.add(tarifa)
        db.flush()
        return tarifa

    def entradas_vendidas_evento(self, db: Session, evento_id: str) -> int:
        return db.scalar(
            select(func.coalesce(func.sum(TarifaAcceso.cupo_vendido), 0)).where(TarifaAcceso.evento_id == evento_id)
        )

    # ── Reservas de aforo ────────────────────────────────────

    def reservas_pendientes(self, db: Session, tarifa_id: UUID, ahora: datetime) -> int:
        return db.scalar(
            select(func.count()).select_from(ReservaAforo).where(
                ReservaAforo.tarifa_id == tarifa_id,
                ReservaAforo.estado == "PENDIENTE",
                ReservaAforo.expira_en > ahora,
            )
        )

    def caducar_reservas(self, db: Session, ahora: datetime) -> int:
        """Libera las reservas pendientes que han superado su tiempo."""
        resultado = db.execute(
            update(ReservaAforo)
            .where(ReservaAforo.estado == "PENDIENTE", ReservaAforo.expira_en <= ahora)
            .values(estado="LIBERADA")
        )
        return resultado.rowcount

    def obtener_reserva(self, db: Session, reserva_id: UUID, *, bloquear: bool = False) -> ReservaAforo | None:
        consulta = select(ReservaAforo).where(ReservaAforo.id == reserva_id)
        if bloquear:
            consulta = consulta.with_for_update()
        return db.scalar(consulta)

    def crear_reserva(self, db: Session, reserva: ReservaAforo) -> ReservaAforo:
        db.add(reserva)
        db.flush()
        return reserva
