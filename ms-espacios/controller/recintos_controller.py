# ms-espacios/controller/recintos_controller.py
# Endpoints de /recintos (tag Recintos)
from uuid import UUID
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from config.database import get_db
from config.seguridad import UsuarioActual, requiere_rol
from model.dto.evento_dto import RecintoDTO, RecintoEntradaDTO
from service import evento_service

router = APIRouter(prefix="/recintos", tags=["Recintos"])


@router.get("", response_model=list[RecintoDTO], summary="Listar recintos")
def listar_recintos(db: Session = Depends(get_db)):
    return evento_service.listar_recintos(db)


@router.post("", response_model=RecintoDTO, status_code=status.HTTP_201_CREATED, summary="Crear un recinto")
def crear_recinto(datos: RecintoEntradaDTO, response: Response,
                  _: UsuarioActual = Depends(requiere_rol("admin")), db: Session = Depends(get_db)):
    recinto = evento_service.crear_recinto(db, datos)
    response.headers["Location"] = f"/api/v1/recintos/{recinto.id}"
    return recinto


@router.get("/{recinto_id}", response_model=RecintoDTO, summary="Obtener un recinto")
def obtener_recinto(recinto_id: UUID, db: Session = Depends(get_db)):
    return evento_service.obtener_recinto(db, recinto_id)


@router.put("/{recinto_id}", response_model=RecintoDTO, summary="Modificar un recinto")
def modificar_recinto(recinto_id: UUID, datos: RecintoEntradaDTO,
                      _: UsuarioActual = Depends(requiere_rol("admin")), db: Session = Depends(get_db)):
    return evento_service.modificar_recinto(db, recinto_id, datos)


@router.delete("/{recinto_id}", operation_id="eliminarRecinto", status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar un recinto")
def eliminar_recinto(recinto_id: UUID, _: UsuarioActual = Depends(requiere_rol("admin")),
                     db: Session = Depends(get_db)):
    evento_service.eliminar_recinto(db, recinto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
