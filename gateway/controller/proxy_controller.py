# gateway/controller/proxy_controller.py
# Única ruta del gateway: /api/v1/{ruta} -> microservicio correspondiente
from fastapi import APIRouter, Header, Request
from config.settings import PREFIJO_API
from service import autenticacion, enrutado

router = APIRouter(prefix=PREFIJO_API, tags=["API"])


@router.api_route("/{ruta:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                  summary="Reenvía la petición al microservicio que la atiende")
async def proxy(ruta: str, request: Request, authorization: str | None = Header(default=None)):
    identidad = await autenticacion.identificar(authorization)
    return await enrutado.reenviar(request.app.state.cliente, request, ruta, identidad)
