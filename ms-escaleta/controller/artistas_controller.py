# ms-escaleta/controller/artistas_controller.py
# Endpoints de /artistas (tag Artistas)
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from config.database import get_db
from config.seguridad import UsuarioActual, requiere_rol
from model.dto.escaleta_dto import ArtistaDetalleDTO, ArtistaDTO, ArtistaEntradaDTO, VideoDTO
from service import artista_service

router = APIRouter(prefix="/artistas", tags=["Artistas"])
SOLO_ADMIN = Depends(requiere_rol("admin"))


@router.get("", response_model=list[ArtistaDTO], summary="Buscar artistas")
def buscar_artistas(
    response: Response,
    q: str | None = Query(default=None, description="Texto a buscar en el nombre"),
    genero: str | None = Query(default=None, examples=["techno"]),
    evento_id: str | None = Query(default=None, description="Solo artistas con algún pase en este evento"),
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    artistas, total = artista_service.buscar(db, q=q, genero=genero, evento_id=evento_id, limite=limite,
                                             desplazamiento=desplazamiento)
    response.headers["X-Total-Count"] = str(total)
    return artistas


@router.post("", response_model=ArtistaDTO, status_code=status.HTTP_201_CREATED, summary="Dar de alta un artista")
def crear_artista(datos: ArtistaEntradaDTO, response: Response, _: UsuarioActual = SOLO_ADMIN,
                  db: Session = Depends(get_db)):
    artista = artista_service.crear(db, datos)
    response.headers["Location"] = f"/api/v1/artistas/{artista.id}"
    return artista


@router.get("/{artista_id}", response_model=ArtistaDetalleDTO, summary="Obtener la ficha de un artista")
def obtener_artista(artista_id: UUID, db: Session = Depends(get_db)):
    return artista_service.obtener_detalle(db, artista_id)


@router.put("/{artista_id}", response_model=ArtistaDTO, summary="Modificar un artista")
def modificar_artista(artista_id: UUID, datos: ArtistaEntradaDTO, _: UsuarioActual = SOLO_ADMIN,
                      db: Session = Depends(get_db)):
    return artista_service.modificar(db, artista_id, datos)


@router.delete("/{artista_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un artista")
def eliminar_artista(artista_id: UUID, _: UsuarioActual = SOLO_ADMIN, db: Session = Depends(get_db)):
    artista_service.eliminar(db, artista_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{artista_id}/videos", response_model=list[VideoDTO], summary="Vídeos y playlists del artista")
def listar_videos(artista_id: UUID, db: Session = Depends(get_db)):
    return artista_service.videos(db, artista_id)
