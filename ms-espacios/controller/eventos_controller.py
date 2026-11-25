# ms-espacios/controller/eventos_controller.py
# Endpoints de /eventos y /eventos/{evento_id}/tarifas (tags Eventos y Tarifas)
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from config.database import get_db
from config.seguridad import UsuarioActual, requiere_rol, usuario_opcional
from model.dto.evento_dto import (
    CambioEstadoEventoDTO, EstadoEvento, EventoDTO, EventoDetalleDTO, EventoEntradaDTO, TarifaDTO, TarifaEntradaDTO,
)
from service import evento_service

router = APIRouter(prefix="/eventos")
SOLO_ADMIN = Depends(requiere_rol("admin"))


def _es_admin(usuario: UsuarioActual | None) -> bool:
    return usuario is not None and usuario.rol == "admin"


@router.get("", response_model=list[EventoDTO], tags=["Eventos"], summary="Buscar eventos")
def buscar_eventos(
    response: Response,
    pais: str | None = Query(default=None, examples=["Bélgica"]),
    tag: str | None = Query(default=None, description="Etiqueta de búsqueda (género, temporada…)"),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    estado: EstadoEvento | None = Query(default=None),
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    usuario: UsuarioActual | None = Depends(usuario_opcional),
    db: Session = Depends(get_db),
):
    eventos, total = evento_service.buscar_eventos(
        db, es_admin=_es_admin(usuario), estado=estado, pais=pais, tag=tag, desde=desde, hasta=hasta,
        limite=limite, desplazamiento=desplazamiento,
    )
    response.headers["X-Total-Count"] = str(total)
    return eventos


@router.post("", response_model=EventoDTO, status_code=status.HTTP_201_CREATED, tags=["Eventos"],
             summary="Crear un evento")
def crear_evento(datos: EventoEntradaDTO, response: Response, _: UsuarioActual = SOLO_ADMIN,
                 db: Session = Depends(get_db)):
    evento = evento_service.crear_evento(db, datos)
    response.headers["Location"] = f"/api/v1/eventos/{evento.id}"
    return evento


@router.get("/{evento_id}", response_model=EventoDetalleDTO, tags=["Eventos"], summary="Obtener un evento")
def obtener_evento(evento_id: str, usuario: UsuarioActual | None = Depends(usuario_opcional),
                   db: Session = Depends(get_db)):
    return evento_service.obtener_evento(db, evento_id, es_admin=_es_admin(usuario))


@router.put("/{evento_id}", response_model=EventoDTO, tags=["Eventos"], summary="Modificar un evento")
def modificar_evento(evento_id: str, datos: EventoEntradaDTO, _: UsuarioActual = SOLO_ADMIN,
                     db: Session = Depends(get_db)):
    return evento_service.modificar_evento(db, evento_id, datos)


@router.patch("/{evento_id}", response_model=EventoDTO, tags=["Eventos"],
              summary="Cambiar el estado de un evento (publicar, cancelar, finalizar)")
def cambiar_estado_evento(evento_id: str, datos: CambioEstadoEventoDTO, _: UsuarioActual = SOLO_ADMIN,
                          db: Session = Depends(get_db)):
    return evento_service.cambiar_estado_evento(db, evento_id, datos)


@router.delete("/{evento_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Eventos"],
               summary="Eliminar un evento")
def eliminar_evento(evento_id: str, _: UsuarioActual = SOLO_ADMIN, db: Session = Depends(get_db)):
    evento_service.eliminar_evento(db, evento_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Tarifas ─────────────────────────────────────────────────

@router.get("/{evento_id}/tarifas", response_model=list[TarifaDTO], tags=["Tarifas"],
            summary="Tipos de entrada, precios y disponibilidad")
def listar_tarifas(evento_id: str, usuario: UsuarioActual | None = Depends(usuario_opcional),
                   db: Session = Depends(get_db)):
    return evento_service.listar_tarifas(db, evento_id, es_admin=_es_admin(usuario))


@router.post("/{evento_id}/tarifas", response_model=TarifaDTO, status_code=status.HTTP_201_CREATED,
             tags=["Tarifas"], summary="Crear una tarifa")
def crear_tarifa(evento_id: str, datos: TarifaEntradaDTO, _: UsuarioActual = SOLO_ADMIN,
                 db: Session = Depends(get_db)):
    return evento_service.crear_tarifa(db, evento_id, datos)


@router.put("/{evento_id}/tarifas/{tarifa_id}", response_model=TarifaDTO, tags=["Tarifas"],
            summary="Modificar precio o cupo de una tarifa")
def modificar_tarifa(evento_id: str, tarifa_id: UUID, datos: TarifaEntradaDTO, _: UsuarioActual = SOLO_ADMIN,
                     db: Session = Depends(get_db)):
    return evento_service.modificar_tarifa(db, evento_id, tarifa_id, datos)


@router.delete("/{evento_id}/tarifas/{tarifa_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tarifas"],
               summary="Eliminar una tarifa sin ventas")
def eliminar_tarifa(evento_id: str, tarifa_id: UUID, _: UsuarioActual = SOLO_ADMIN, db: Session = Depends(get_db)):
    evento_service.eliminar_tarifa(db, evento_id, tarifa_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
