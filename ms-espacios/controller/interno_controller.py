# ms-espacios/controller/interno_controller.py
# Rutas /internal/v1 (tag Interno): solo red interna, no las expone el API Gateway
from uuid import UUID
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from config.database import get_db
from config.seguridad import servicio_interno
from model.dto.evento_dto import ReservaAforoDTO, ReservaAforoEntradaDTO
from service import aforo_service

router = APIRouter(tags=["Interno"], dependencies=[Depends(servicio_interno)])


@router.post("/eventos/{evento_id}/reservas-aforo", response_model=ReservaAforoDTO,
             status_code=status.HTTP_201_CREATED, summary="Reservar aforo temporalmente")
def reservar_aforo(evento_id: str, datos: ReservaAforoEntradaDTO, db: Session = Depends(get_db)):
    return aforo_service.reservar_aforo(db, evento_id, datos)


@router.delete("/reservas-aforo/{reserva_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Liberar una reserva de aforo")
def liberar_reserva_aforo(reserva_id: UUID, db: Session = Depends(get_db)):
    aforo_service.liberar_reserva(db, reserva_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
