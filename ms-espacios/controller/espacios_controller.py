# ms-espacios/controller/espacios_controller.py
# Endpoints de /tipos-espacio, /espacios y /alquileres (tags Espacios y Alquileres)
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from config.database import get_db
from config.seguridad import UsuarioActual, requiere_rol
from model.dto.espacio_dto import (
    AlquilerDTO, AlquilerEntradaDTO, CambioEstadoAlquilerDTO, CodigoTipoEspacio, EspacioDTO, EspacioEntradaDTO,
    EstadoAlquiler, TipoEspacioDTO,
)
from service import espacio_service

router = APIRouter()
SOLO_ADMIN = Depends(requiere_rol("admin"))


@router.get("/tipos-espacio", response_model=list[TipoEspacioDTO], tags=["Espacios"],
            summary="Catálogo de tipos de espacio")
def listar_tipos_espacio(db: Session = Depends(get_db)):
    return espacio_service.listar_tipos(db)


@router.get("/espacios", response_model=list[EspacioDTO], tags=["Espacios"], summary="Buscar espacios")
def buscar_espacios(
    response: Response,
    evento_id: str | None = Query(default=None, examples=["evento-belgium"]),
    tipo: CodigoTipoEspacio | None = Query(default=None),
    disponible: bool | None = Query(default=None),
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    espacios, total = espacio_service.buscar_espacios(
        db, evento_id=evento_id, tipo=tipo.value if tipo else None, disponible=disponible,
        limite=limite, desplazamiento=desplazamiento,
    )
    response.headers["X-Total-Count"] = str(total)
    return espacios


@router.post("/espacios", response_model=EspacioDTO, status_code=status.HTTP_201_CREATED, tags=["Espacios"],
             summary="Crear un espacio")
def crear_espacio(datos: EspacioEntradaDTO, response: Response, _: UsuarioActual = SOLO_ADMIN,
                  db: Session = Depends(get_db)):
    espacio = espacio_service.crear_espacio(db, datos)
    response.headers["Location"] = f"/api/v1/espacios/{espacio.id}"
    return espacio


@router.get("/espacios/{espacio_id}", response_model=EspacioDTO, tags=["Espacios"], summary="Obtener un espacio")
def obtener_espacio(espacio_id: str, db: Session = Depends(get_db)):
    return espacio_service.obtener_espacio(db, espacio_id)


@router.put("/espacios/{espacio_id}", response_model=EspacioDTO, tags=["Espacios"], summary="Modificar un espacio")
def modificar_espacio(espacio_id: str, datos: EspacioEntradaDTO, _: UsuarioActual = SOLO_ADMIN,
                      db: Session = Depends(get_db)):
    return espacio_service.modificar_espacio(db, espacio_id, datos)


@router.delete("/espacios/{espacio_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Espacios"],
               summary="Eliminar un espacio")
def eliminar_espacio(espacio_id: str, _: UsuarioActual = SOLO_ADMIN, db: Session = Depends(get_db)):
    espacio_service.eliminar_espacio(db, espacio_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Alquileres ──────────────────────────────────────────────

@router.post("/espacios/{espacio_id}/alquileres", response_model=AlquilerDTO, status_code=status.HTTP_201_CREATED,
             tags=["Alquileres"], summary="Solicitar el alquiler de un espacio")
def solicitar_alquiler(espacio_id: str, datos: AlquilerEntradaDTO, response: Response,
                       usuario: UsuarioActual = Depends(requiere_rol("proveedor")), db: Session = Depends(get_db)):
    alquiler = espacio_service.solicitar_alquiler(db, usuario, espacio_id, datos)
    response.headers["Location"] = f"/api/v1/alquileres/{alquiler.id}"
    return espacio_service.a_alquiler_dto(db, [alquiler])[0]


@router.get("/alquileres", response_model=list[AlquilerDTO], tags=["Alquileres"], summary="Listar alquileres")
def listar_alquileres(
    response: Response,
    estado: EstadoAlquiler | None = Query(default=None),
    evento_id: str | None = Query(default=None),
    proveedor_id: str | None = Query(default=None, description="Solo para admin"),
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    usuario: UsuarioActual = Depends(requiere_rol("proveedor", "admin")),
    db: Session = Depends(get_db),
):
    alquileres, total = espacio_service.listar_alquileres(
        db, usuario, estado=estado.value if estado else None, evento_id=evento_id, proveedor_id=proveedor_id,
        limite=limite, desplazamiento=desplazamiento,
    )
    response.headers["X-Total-Count"] = str(total)
    return espacio_service.a_alquiler_dto(db, alquileres)


@router.get("/alquileres/{alquiler_id}", response_model=AlquilerDTO, tags=["Alquileres"],
            summary="Obtener un alquiler")
def obtener_alquiler(alquiler_id: UUID, usuario: UsuarioActual = Depends(requiere_rol("proveedor", "admin")),
                     db: Session = Depends(get_db)):
    return espacio_service.a_alquiler_dto(db, [espacio_service.obtener_alquiler(db, usuario, alquiler_id)])[0]


@router.patch("/alquileres/{alquiler_id}", response_model=AlquilerDTO, tags=["Alquileres"],
              summary="Cambiar el estado de un alquiler")
def cambiar_estado_alquiler(alquiler_id: UUID, datos: CambioEstadoAlquilerDTO,
                            usuario: UsuarioActual = Depends(requiere_rol("proveedor", "admin")),
                            db: Session = Depends(get_db)):
    alquiler = espacio_service.cambiar_estado_alquiler(db, usuario, alquiler_id, datos)
    return espacio_service.a_alquiler_dto(db, [alquiler])[0]
