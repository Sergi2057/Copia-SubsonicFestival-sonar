# ms-espacios/model/dao/espacio_dao.py
# Acceso a las tablas tipos_espacio, espacios, alquileres y proveedores (réplica)
from datetime import datetime
from uuid import UUID
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload
from model.models import Alquiler, Espacio, Proveedor, TipoEspacio

ESTADOS_QUE_OCUPAN = ("APROBADO", "ACTIVO")


class EspacioDAO:
    # ── Tipos y espacios ─────────────────────────────────────

    def listar_tipos(self, db: Session) -> list[TipoEspacio]:
        return list(db.scalars(select(TipoEspacio).order_by(TipoEspacio.codigo)).all())

    def obtener_tipo(self, db: Session, codigo: str) -> TipoEspacio | None:
        return db.get(TipoEspacio, codigo)

    def listar(self, db: Session, *, evento_id: str | None, tipo: str | None, disponible: bool | None,
               limite: int, desplazamiento: int) -> tuple[list[Espacio], int]:
        consulta = select(Espacio)
        if evento_id:
            consulta = consulta.where(Espacio.evento_id == evento_id)
        if tipo:
            consulta = consulta.where(Espacio.tipo == tipo)
        if disponible is not None:
            consulta = consulta.where(Espacio.disponible.is_(disponible))

        total = db.scalar(select(func.count()).select_from(consulta.subquery()))
        espacios = db.scalars(consulta.order_by(Espacio.id).limit(limite).offset(desplazamiento)).all()
        return list(espacios), total

    def obtener(self, db: Session, espacio_id: str, *, bloquear: bool = False) -> Espacio | None:
        consulta = select(Espacio).where(Espacio.id == espacio_id)
        if bloquear:
            consulta = consulta.with_for_update()
        return db.scalar(consulta)

    def crear(self, db: Session, espacio: Espacio) -> Espacio:
        db.add(espacio)
        db.flush()
        return espacio

    def eliminar(self, db: Session, espacio: Espacio) -> None:
        db.delete(espacio)

    # ── Alquileres ───────────────────────────────────────────

    def listar_alquileres(self, db: Session, *, proveedor_id: str | None, estado: str | None,
                          evento_id: str | None, limite: int, desplazamiento: int) -> tuple[list[Alquiler], int]:
        consulta = select(Alquiler).join(Espacio)
        if proveedor_id:
            consulta = consulta.where(Alquiler.proveedor_id == proveedor_id)
        if estado:
            consulta = consulta.where(Alquiler.estado == estado)
        if evento_id:
            consulta = consulta.where(Espacio.evento_id == evento_id)

        total = db.scalar(select(func.count()).select_from(consulta.subquery()))
        alquileres = db.scalars(
            consulta.options(selectinload(Alquiler.espacio))
            .order_by(Alquiler.creado_en.desc())
            .limit(limite)
            .offset(desplazamiento)
        ).all()
        return list(alquileres), total

    def obtener_alquiler(self, db: Session, alquiler_id: UUID, *, bloquear: bool = False) -> Alquiler | None:
        consulta = select(Alquiler).where(Alquiler.id == alquiler_id).options(selectinload(Alquiler.espacio))
        if bloquear:
            consulta = consulta.with_for_update(of=Alquiler)
        return db.scalar(consulta)

    def hay_solape(self, db: Session, espacio_id: str, inicio: datetime, fin: datetime,
                   excluir_id: UUID | None = None) -> bool:
        """¿Hay un alquiler aprobado o activo del espacio que se solape con [inicio, fin)?"""
        consulta = select(func.count()).select_from(Alquiler).where(
            Alquiler.espacio_id == espacio_id,
            Alquiler.estado.in_(ESTADOS_QUE_OCUPAN),
            Alquiler.fecha_inicio < fin,
            Alquiler.fecha_fin > inicio,
        )
        if excluir_id:
            consulta = consulta.where(Alquiler.id != excluir_id)
        return db.scalar(consulta) > 0

    def tiene_alquileres_que_ocupan(self, db: Session, espacio_id: str) -> bool:
        return db.scalar(
            select(func.count()).select_from(Alquiler).where(
                Alquiler.espacio_id == espacio_id, Alquiler.estado.in_(ESTADOS_QUE_OCUPAN)
            )
        ) > 0

    def crear_alquiler(self, db: Session, alquiler: Alquiler) -> Alquiler:
        db.add(alquiler)
        db.flush()
        return alquiler

    def activar_alquileres_iniciados(self, db: Session, ahora: datetime) -> int:
        """APROBADO -> ACTIVO cuando llega la fecha de inicio."""
        resultado = db.execute(
            update(Alquiler)
            .where(Alquiler.estado == "APROBADO", Alquiler.fecha_inicio <= ahora)
            .values(estado="ACTIVO")
        )
        return resultado.rowcount

    def rechazar_pendientes_de_proveedor(self, db: Session, proveedor_id: str) -> int:
        resultado = db.execute(
            update(Alquiler)
            .where(Alquiler.proveedor_id == proveedor_id, Alquiler.estado == "PENDIENTE")
            .values(estado="RECHAZADO", comentarios="Proveedor desactivado")
        )
        return resultado.rowcount

    def anonimizar_de_proveedor(self, db: Session, proveedor_id: str) -> int:
        resultado = db.execute(
            update(Alquiler).where(Alquiler.proveedor_id == proveedor_id)
            .values(proveedor_id="anonimizado", comentarios=None)
        )
        return resultado.rowcount

    # ── Réplica de proveedores ───────────────────────────────

    def obtener_proveedor(self, db: Session, proveedor_id: str) -> Proveedor | None:
        return db.get(Proveedor, proveedor_id)

    def guardar_proveedor(self, db: Session, proveedor: Proveedor) -> Proveedor:
        return db.merge(proveedor)

    def nombres_proveedores(self, db: Session, ids: set[str]) -> dict[str, str]:
        if not ids:
            return {}
        filas = db.execute(
            select(Proveedor.proveedor_id, Proveedor.nombre_comercial).where(Proveedor.proveedor_id.in_(ids))
        ).all()
        return {pid: nombre for pid, nombre in filas}

    def eliminar_proveedor(self, db: Session, proveedor_id: str) -> None:
        proveedor = db.get(Proveedor, proveedor_id)
        if proveedor:
            db.delete(proveedor)
