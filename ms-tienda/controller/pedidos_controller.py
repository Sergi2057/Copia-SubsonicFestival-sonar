# ms-tienda/controller/pedidos_controller.py
# Endpoints de /pedidos (tag Pedidos de openapi.yaml)
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from config.database import get_db
from config.seguridad import UsuarioActual, requiere_rol
from model.dto.pedido_dto import CambioEstadoDTO, EstadoPedido, PedidoDTO, PedidoEntradaDTO
from service import pedido_service

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.get("", response_model=list[PedidoDTO], summary="Listar pedidos")
def listar_pedidos(
    response: Response,
    estado: EstadoPedido | None = Query(default=None),
    evento_id_recogida: str | None = Query(default=None, description="Pedidos que se recogen en un evento (solo admin)"),
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    usuario: UsuarioActual = Depends(requiere_rol("cliente", "admin")),
    db: Session = Depends(get_db),
):
    pedidos, total = pedido_service.listar_pedidos(
        db, usuario, estado=estado.value if estado else None, evento_id_recogida=evento_id_recogida,
        limite=limite, desplazamiento=desplazamiento,
    )
    response.headers["X-Total-Count"] = str(total)
    return [PedidoDTO.desde_modelo(p) for p in pedidos]


@router.post("", response_model=PedidoDTO, status_code=status.HTTP_201_CREATED, summary="Realizar un pedido")
def crear_pedido(
    datos: PedidoEntradaDTO,
    response: Response,
    usuario: UsuarioActual = Depends(requiere_rol("cliente")),
    db: Session = Depends(get_db),
):
    pedido = pedido_service.crear_pedido(db, usuario, datos)
    response.headers["Location"] = f"/api/v1/pedidos/{pedido.id}"
    return PedidoDTO.desde_modelo(pedido)


@router.get("/{pedido_id}", response_model=PedidoDTO, summary="Obtener un pedido")
def obtener_pedido(
    pedido_id: str,
    usuario: UsuarioActual = Depends(requiere_rol("cliente", "admin")),
    db: Session = Depends(get_db),
):
    return PedidoDTO.desde_modelo(pedido_service.obtener_pedido(db, usuario, pedido_id))


@router.patch("/{pedido_id}", response_model=PedidoDTO, summary="Cambiar el estado de un pedido")
def cambiar_estado_pedido(
    pedido_id: str,
    datos: CambioEstadoDTO,
    usuario: UsuarioActual = Depends(requiere_rol("cliente", "admin")),
    db: Session = Depends(get_db),
):
    return PedidoDTO.desde_modelo(pedido_service.cambiar_estado(db, usuario, pedido_id, datos.estado))
