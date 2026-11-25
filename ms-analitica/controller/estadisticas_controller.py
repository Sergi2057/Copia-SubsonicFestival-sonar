# ms-analitica/controller/estadisticas_controller.py
# Endpoints de /estadisticas (tag Estadísticas)
from datetime import date
from fastapi import APIRouter, Depends, Query
from config.seguridad import UsuarioActual, requiere_rol
from model.dto.analitica_dto import (
    AgruparPor, EstadisticasTiendaDTO, MetricaOcupacionDTO, MetricaVentasDTO, PopularidadArtistaDTO,
    PrevisionAfluenciaDTO, ResumenDTO,
)
from service import estadisticas_service

router = APIRouter(prefix="/estadisticas", tags=["Estadísticas"])
SOLO_ADMIN = Depends(requiere_rol("admin"))


@router.get("/resumen", response_model=ResumenDTO, summary="Indicadores principales del panel de administración")
def obtener_resumen(evento_id: str | None = Query(default=None), _: UsuarioActual = SOLO_ADMIN):
    return estadisticas_service.resumen(evento_id)


@router.get("/ventas", response_model=list[MetricaVentasDTO], summary="Ventas de entradas por evento, día y tipo")
def obtener_ventas(evento_id: str | None = Query(default=None), desde: date | None = Query(default=None),
                   hasta: date | None = Query(default=None), agrupar_por: AgruparPor = Query(default=AgruparPor.DIA),
                   _: UsuarioActual = SOLO_ADMIN):
    return estadisticas_service.ventas(evento_id, desde, hasta, agrupar_por)


@router.get("/ocupacion", response_model=list[MetricaOcupacionDTO], summary="Ocupación de espacios y alquileres")
def obtener_ocupacion(evento_id: str = Query(), _: UsuarioActual = SOLO_ADMIN):
    return estadisticas_service.ocupacion(evento_id)


@router.get("/afluencia", response_model=list[PrevisionAfluenciaDTO],
            summary="Previsión de afluencia por escenario y franja")
def obtener_afluencia(evento_id: str = Query(), fecha: date | None = Query(default=None),
                      _: UsuarioActual = SOLO_ADMIN):
    return estadisticas_service.afluencia(evento_id, fecha)


@router.get("/tienda", response_model=EstadisticasTiendaDTO, summary="Ventas de merchandising")
def obtener_estadisticas_tienda(desde: date | None = Query(default=None), hasta: date | None = Query(default=None),
                                _: UsuarioActual = SOLO_ADMIN):
    return estadisticas_service.tienda(desde, hasta)


@router.get("/artistas-populares", response_model=list[PopularidadArtistaDTO], summary="Ranking de artistas")
def obtener_artistas_populares(evento_id: str | None = Query(default=None),
                               limite: int = Query(default=10, ge=1, le=50)):
    return estadisticas_service.popularidad(evento_id, limite)
