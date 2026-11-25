# ms-tienda/controller/productos_controller.py
# Endpoints de /productos (tag Productos de openapi.yaml)
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from config.database import get_db
from config.seguridad import UsuarioActual, requiere_rol, usuario_opcional
from model.dto.producto_dto import (
    ProductoDTO, ProductoEntradaDTO, VarianteCambioDTO, VarianteDTO, VarianteEntradaDTO,
)
from service import producto_service

router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get("", response_model=list[ProductoDTO], summary="Catálogo de productos")
def listar_productos(
    response: Response,
    evento_id: str | None = Query(default=None, description="Incluir el merchandising exclusivo de este evento"),
    disponible: bool | None = Query(default=None, description="Solo productos con stock en alguna talla"),
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    usuario: UsuarioActual | None = Depends(usuario_opcional),
    db: Session = Depends(get_db),
):
    es_admin = usuario is not None and usuario.rol == "admin"
    productos, total = producto_service.listar_productos(
        db, evento_id=evento_id, disponible=disponible, es_admin=es_admin,
        limite=limite, desplazamiento=desplazamiento,
    )
    response.headers["X-Total-Count"] = str(total)
    return [producto_service.a_producto_dto(p, es_admin=es_admin) for p in productos]


@router.post("", response_model=ProductoDTO, status_code=status.HTTP_201_CREATED, summary="Crear un producto")
def crear_producto(
    datos: ProductoEntradaDTO,
    response: Response,
    _: UsuarioActual = Depends(requiere_rol("admin")),
    db: Session = Depends(get_db),
):
    producto = producto_service.crear_producto(db, datos)
    response.headers["Location"] = f"/api/v1/productos/{producto.id}"
    return producto


@router.get("/{producto_id}", response_model=ProductoDTO, summary="Obtener un producto")
def obtener_producto(
    producto_id: str,
    usuario: UsuarioActual | None = Depends(usuario_opcional),
    db: Session = Depends(get_db),
):
    es_admin = usuario is not None and usuario.rol == "admin"
    producto = producto_service.obtener_producto(db, producto_id, es_admin=es_admin)
    return producto_service.a_producto_dto(producto, es_admin=es_admin)


@router.put("/{producto_id}", response_model=ProductoDTO, summary="Modificar un producto")
def modificar_producto(
    producto_id: str,
    datos: ProductoEntradaDTO,
    _: UsuarioActual = Depends(requiere_rol("admin")),
    db: Session = Depends(get_db),
):
    return producto_service.modificar_producto(db, producto_id, datos)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Retirar un producto del catálogo")
def eliminar_producto(
    producto_id: str,
    _: UsuarioActual = Depends(requiere_rol("admin")),
    db: Session = Depends(get_db),
):
    producto_service.retirar_producto(db, producto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{producto_id}/variantes", response_model=VarianteDTO, status_code=status.HTTP_201_CREATED,
             summary="Añadir una talla a un producto")
def crear_variante(
    producto_id: str,
    datos: VarianteEntradaDTO,
    _: UsuarioActual = Depends(requiere_rol("admin")),
    db: Session = Depends(get_db),
):
    return producto_service.crear_variante(db, producto_id, datos)


@router.patch("/{producto_id}/variantes/{variante_id}", response_model=VarianteDTO,
              summary="Modificar una talla (talla o stock)")
def modificar_variante(
    producto_id: str,
    variante_id: UUID,
    datos: VarianteCambioDTO,
    _: UsuarioActual = Depends(requiere_rol("admin")),
    db: Session = Depends(get_db),
):
    return producto_service.modificar_variante(db, producto_id, variante_id, datos)


@router.delete("/{producto_id}/variantes/{variante_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar una talla de un producto")
def eliminar_variante(
    producto_id: str,
    variante_id: UUID,
    _: UsuarioActual = Depends(requiere_rol("admin")),
    db: Session = Depends(get_db),
):
    producto_service.eliminar_variante(db, producto_id, variante_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
