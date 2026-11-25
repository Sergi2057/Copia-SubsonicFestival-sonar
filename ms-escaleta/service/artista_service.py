# ms-escaleta/service/artista_service.py
# Lógica de negocio del catálogo de artistas
from uuid import UUID
from sqlalchemy.orm import Session
from config.errores import ErrorApi
from eventos.publicador import publicar
from model.dto.escaleta_dto import ArtistaDetalleDTO, ArtistaDTO, ArtistaEntradaDTO, PaseResumenDTO
from model.factory.factory_dao import DAOFactory
from model.models import Artista
from service import youtube

artista_dao = DAOFactory.get_artista_dao()
escaleta_dao = DAOFactory.get_escaleta_dao()


def datos_artista(artista: Artista) -> dict:
    return {"artista_id": str(artista.id), "nombre": artista.nombre, "generos": artista.generos,
            "pais": artista.pais}


def buscar(db: Session, **filtros):
    return artista_dao.listar(db, **filtros)


def obtener(db: Session, artista_id: UUID) -> Artista:
    artista = artista_dao.obtener(db, artista_id)
    if not artista:
        raise ErrorApi(404, "ARTISTA_NO_ENCONTRADO", f"No existe el artista {artista_id}")
    return artista


def obtener_detalle(db: Session, artista_id: UUID) -> ArtistaDetalleDTO:
    """Ficha con sus pases PUBLICADOS (los del borrador no se muestran al público)."""
    artista = obtener(db, artista_id)
    pases = []
    for publicacion in escaleta_dao.ultimas_publicaciones(db):
        for dia in publicacion.instantanea["dias"]:
            for escenario in dia["escenarios"]:
                pases += [p for p in escenario["pases"] if p["artista_id"] == str(artista_id)]
    pases.sort(key=lambda p: p["inicio"])
    return ArtistaDetalleDTO(**ArtistaDTO.model_validate(artista).model_dump(),
                             pases=[PaseResumenDTO(**p) for p in pases])


def crear(db: Session, datos: ArtistaEntradaDTO) -> Artista:
    artista = artista_dao.crear(db, Artista(**datos.model_dump()))
    db.commit()
    publicar("escaleta.artista.creado", datos_artista(artista))
    return artista


def modificar(db: Session, artista_id: UUID, datos: ArtistaEntradaDTO) -> Artista:
    artista = obtener(db, artista_id)
    for campo, valor in datos.model_dump().items():
        setattr(artista, campo, valor)
    db.commit()
    publicar("escaleta.artista.actualizado", datos_artista(artista))
    return artista


def eliminar(db: Session, artista_id: UUID) -> None:
    artista = obtener(db, artista_id)
    if artista_dao.tiene_pases(db, artista_id):
        raise ErrorApi(409, "ARTISTA_CON_PASES", "El artista tiene pases asignados")
    db.delete(artista)
    db.commit()


def videos(db: Session, artista_id: UUID) -> list[dict]:
    artista = obtener(db, artista_id)
    return youtube.videos_de_artista(str(artista.id), artista.nombre, artista.youtube_channel_id)
