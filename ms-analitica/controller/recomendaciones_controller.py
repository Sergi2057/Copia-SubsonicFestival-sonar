# ms-analitica/controller/recomendaciones_controller.py
# Endpoints de /recomendaciones y /interacciones (tags Recomendaciones e Interacciones)
from fastapi import APIRouter, Depends, Query, Response, status
from config.seguridad import UsuarioActual, requiere_rol, usuario_opcional
from model.dto.analitica_dto import (
    EspacioRecomendadoDTO, LoteInteraccionesDTO, RecomendacionesClienteDTO, RecomendacionesPopularesDTO,
)
from service import recomendaciones_service

router = APIRouter()


@router.get("/recomendaciones/me", response_model=RecomendacionesClienteDTO, tags=["Recomendaciones"],
            summary="Recomendaciones personalizadas del cliente")
def obtener_mis_recomendaciones(evento_id: str | None = Query(default=None),
                                usuario: UsuarioActual = Depends(requiere_rol("cliente"))):
    return recomendaciones_service.para_cliente(usuario.id, evento_id)


@router.get("/recomendaciones/populares", response_model=RecomendacionesPopularesDTO, tags=["Recomendaciones"],
            summary="Recomendaciones para visitantes")
def obtener_recomendaciones_populares():
    return recomendaciones_service.populares()


@router.get("/recomendaciones/espacios", response_model=list[EspacioRecomendadoDTO], tags=["Recomendaciones"],
            summary="Espacios recomendados para un proveedor")
def obtener_espacios_recomendados(evento_id: str | None = Query(default=None),
                                  usuario: UsuarioActual = Depends(requiere_rol("proveedor"))):
    return recomendaciones_service.espacios_para_proveedor(usuario.id, evento_id)


@router.post("/interacciones", status_code=status.HTTP_202_ACCEPTED, tags=["Interacciones"],
             summary="Registrar interacciones del front-end (en lote)")
def registrar_interacciones(lote: LoteInteraccionesDTO,
                            usuario: UsuarioActual | None = Depends(usuario_opcional)):
    recomendaciones_service.registrar_interacciones(usuario.id if usuario else None, lote)
    return Response(status_code=status.HTTP_202_ACCEPTED)
