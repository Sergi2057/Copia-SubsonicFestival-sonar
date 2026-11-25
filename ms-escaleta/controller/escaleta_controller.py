# ms-escaleta/controller/escaleta_controller.py
# Endpoints de /escaletas, /slots y /pases (tags Escaleta, Slots y Pases)
import asyncio
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from config.database import SessionLocal, get_db
from config.seguridad import UsuarioActual, requiere_rol
from model.dto.escaleta_dto import (
    EscaletaDTO, EscaletaEscenarioDTO, PaseCambioDTO, PaseDTO, PaseEntradaDTO, PublicacionDTO, SlotDTO,
    SlotEntradaDTO,
)
from service import escaleta_service
from service.difusor import difusor

router = APIRouter()
SOLO_ADMIN = Depends(requiere_rol("admin"))
SEGUNDOS_KEEPALIVE = 15


# ── Escaleta publicada ──────────────────────────────────────

@router.get("/escaletas/{evento_id}", response_model=EscaletaDTO, tags=["Escaleta"],
            summary="Obtener la escaleta publicada de un evento")
def obtener_escaleta(evento_id: str, db: Session = Depends(get_db)):
    return escaleta_service.obtener_escaleta(db, evento_id)


@router.get("/escaletas/{evento_id}/escenarios/{espacio_id}", response_model=EscaletaEscenarioDTO,
            tags=["Escaleta"], summary="Obtener la escaleta de un escenario")
def obtener_escaleta_escenario(evento_id: str, espacio_id: str, db: Session = Depends(get_db)):
    return escaleta_service.obtener_escaleta_escenario(db, evento_id, espacio_id)


def _comprobar_evento(evento_id: str):
    db = SessionLocal()
    try:
        escaleta_service.comprobar_evento_existe(db, evento_id)
    finally:
        db.close()


@router.get("/escaletas/{evento_id}/cambios", tags=["Escaleta"],
            summary="Suscribirse a los cambios en directo de la escaleta",
            response_class=StreamingResponse,
            responses={200: {"content": {"text/event-stream": {}}, "description": "Flujo de eventos"}})
async def suscribir_cambios(evento_id: str, request: Request):
    await run_in_threadpool(_comprobar_evento, evento_id)

    async def flujo():
        cola = difusor.suscribir(evento_id)
        try:
            yield ": conectado\n\n"
            while not await request.is_disconnected():
                try:
                    yield await asyncio.wait_for(cola.get(), timeout=SEGUNDOS_KEEPALIVE)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"  # comentario SSE para que proxies no corten la conexión
        finally:
            difusor.cancelar(evento_id, cola)

    return StreamingResponse(flujo(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/escaletas/{evento_id}/publicaciones", response_model=list[PublicacionDTO], tags=["Escaleta"],
            summary="Historial de publicaciones de la escaleta")
def listar_publicaciones(evento_id: str, _: UsuarioActual = SOLO_ADMIN, db: Session = Depends(get_db)):
    return escaleta_service.listar_publicaciones(db, evento_id)


@router.post("/escaletas/{evento_id}/publicaciones", response_model=PublicacionDTO,
             status_code=status.HTTP_201_CREATED, tags=["Escaleta"],
             summary="Publicar una nueva versión de la escaleta")
def publicar_escaleta(evento_id: str, response: Response, admin: UsuarioActual = SOLO_ADMIN,
                      db: Session = Depends(get_db)):
    publicacion = escaleta_service.publicar_escaleta(db, evento_id, admin.id)
    response.headers["Location"] = f"/api/v1/escaletas/{evento_id}"
    return PublicacionDTO(evento_id=publicacion.evento_id, version=publicacion.version,
                          publicada_en=publicacion.publicada_en, publicada_por=publicacion.publicada_por)


# ── Slots ───────────────────────────────────────────────────

@router.get("/escaletas/{evento_id}/slots", response_model=list[SlotDTO], tags=["Slots"],
            summary="Listar los slots de un evento (borrador incluido)")
def listar_slots(evento_id: str, espacio_id: str | None = Query(default=None, description="Filtrar por escenario"),
                 fecha: date | None = Query(default=None, description="Filtrar por día"),
                 _: UsuarioActual = SOLO_ADMIN, db: Session = Depends(get_db)):
    return escaleta_service.listar_slots(db, evento_id, espacio_id, fecha)


@router.post("/escaletas/{evento_id}/slots", response_model=SlotDTO, status_code=status.HTTP_201_CREATED,
             tags=["Slots"], summary="Crear un slot en un escenario")
def crear_slot(evento_id: str, datos: SlotEntradaDTO, response: Response, _: UsuarioActual = SOLO_ADMIN,
               db: Session = Depends(get_db)):
    slot = escaleta_service.crear_slot(db, evento_id, datos)
    response.headers["Location"] = f"/api/v1/slots/{slot.id}"
    return slot


@router.get("/slots/{slot_id}", response_model=SlotDTO, tags=["Slots"], summary="Obtener un slot")
def obtener_slot(slot_id: UUID, _: UsuarioActual = SOLO_ADMIN, db: Session = Depends(get_db)):
    return escaleta_service.a_slot_dto(escaleta_service.obtener_slot(db, slot_id))


@router.put("/slots/{slot_id}", response_model=SlotDTO, tags=["Slots"], summary="Modificar un slot")
def modificar_slot(slot_id: UUID, datos: SlotEntradaDTO, _: UsuarioActual = SOLO_ADMIN,
                   db: Session = Depends(get_db)):
    return escaleta_service.modificar_slot(db, slot_id, datos)


@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Slots"],
               summary="Eliminar un slot")
def eliminar_slot(slot_id: UUID, _: UsuarioActual = SOLO_ADMIN, db: Session = Depends(get_db)):
    escaleta_service.eliminar_slot(db, slot_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Pases ───────────────────────────────────────────────────

@router.post("/slots/{slot_id}/pases", response_model=PaseDTO, status_code=status.HTTP_201_CREATED, tags=["Pases"],
             summary="Asignar un artista a un slot")
def crear_pase(slot_id: UUID, datos: PaseEntradaDTO, response: Response, _: UsuarioActual = SOLO_ADMIN,
               db: Session = Depends(get_db)):
    pase = escaleta_service.crear_pase(db, slot_id, datos)
    response.headers["Location"] = f"/api/v1/pases/{pase.id}"
    return pase


@router.get("/pases/{pase_id}", response_model=PaseDTO, tags=["Pases"], summary="Obtener un pase")
def obtener_pase(pase_id: UUID, db: Session = Depends(get_db)):
    return escaleta_service.a_pase_dto(escaleta_service.obtener_pase(db, pase_id))


@router.patch("/pases/{pase_id}", response_model=PaseDTO, tags=["Pases"],
              summary="Modificar un pase (retraso, cancelación, cambio de escenario…)")
def modificar_pase(pase_id: UUID, datos: PaseCambioDTO, _: UsuarioActual = SOLO_ADMIN,
                   db: Session = Depends(get_db)):
    return escaleta_service.modificar_pase(db, pase_id, datos)


@router.delete("/pases/{pase_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Pases"],
               summary="Quitar el artista de un slot")
def eliminar_pase(pase_id: UUID, _: UsuarioActual = SOLO_ADMIN, db: Session = Depends(get_db)):
    escaleta_service.eliminar_pase(db, pase_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
