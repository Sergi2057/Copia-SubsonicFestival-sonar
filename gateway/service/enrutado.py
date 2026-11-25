# gateway/service/enrutado.py
# Decide a qué microservicio va cada ruta y reenvía la petición con la identidad del usuario
import logging
import httpx
from fastapi import Request
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse
from config.errores import ErrorApi, correlation_id_actual
from config.settings import PREFIJO_API, RUTAS, SERVICIOS, TIEMPO_CONEXION, TIEMPO_RESPUESTA
from service.autenticacion import Identidad

log = logging.getLogger("enrutado")

# Cabeceras que el cliente no puede enviar: las pone el gateway (X-User-*) o son solo entre servicios
CABECERAS_PROHIBIDAS = {"x-user-id", "x-user-rol", "x-user-email", "x-service-token"}
# Cabeceras de una sola conexión (RFC 9110) que no se reenvían
CABECERAS_DE_SALTO = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer",
                      "transfer-encoding", "upgrade", "host", "content-length"}


def servicio_de(ruta: str) -> str:
    """ruta sin el prefijo /api/v1, p. ej. 'productos/camiseta-2026/variantes'."""
    segmentos = ruta.split("/")
    if any(s in (".", "..") for s in segmentos):
        raise ErrorApi(400, "RUTA_NO_VALIDA", "La ruta no puede contener . ni ..")
    servicio = RUTAS.get(segmentos[0])
    if servicio is None:
        raise ErrorApi(404, "RUTA_NO_ENCONTRADA", f"Ningún microservicio atiende /{segmentos[0]}")
    return servicio


def _cabeceras_salida(request: Request, identidad: Identidad | None) -> dict[str, str]:
    # Las que se quitan aquí y se vuelven a poner abajo con su valor correcto
    propias = {"authorization", "x-correlation-id", "x-forwarded-for"}
    cabeceras = {k: v for k, v in request.headers.items()
                 if k.lower() not in CABECERAS_PROHIBIDAS | CABECERAS_DE_SALTO | propias}
    cabeceras["X-Correlation-Id"] = correlation_id_actual.get()
    if request.client:
        cabeceras["X-Forwarded-For"] = request.client.host
    if identidad is not None:
        cabeceras["X-User-Id"] = identidad.id
        if identidad.rol:
            cabeceras["X-User-Rol"] = identidad.rol
        if identidad.email:
            cabeceras["X-User-Email"] = identidad.email
    return cabeceras


async def reenviar(cliente: httpx.AsyncClient, request: Request, ruta: str,
                   identidad: Identidad | None) -> StreamingResponse:
    servicio = servicio_de(ruta)
    url = f"{SERVICIOS[servicio]}{PREFIJO_API}/{ruta}"
    sse = "text/event-stream" in request.headers.get("accept", "")
    # El SSE de la escaleta mantiene la conexión abierta: sin límite de lectura
    tiempo = httpx.Timeout(TIEMPO_RESPUESTA, connect=TIEMPO_CONEXION, read=None if sse else TIEMPO_RESPUESTA)
    peticion = cliente.build_request(
        request.method, url, params=request.query_params.multi_items(),
        headers=_cabeceras_salida(request, identidad), content=await request.body(), timeout=tiempo,
    )
    try:
        respuesta = await cliente.send(peticion, stream=True)
    except httpx.TimeoutException:
        log.warning("%s no respondió a tiempo: %s %s", servicio, request.method, url)
        raise ErrorApi(504, "TIEMPO_AGOTADO", f"{servicio} no ha respondido a tiempo", {"servicio": servicio})
    except httpx.TransportError as e:
        log.warning("%s no disponible: %s", servicio, e)
        raise ErrorApi(503, "SERVICIO_NO_DISPONIBLE", f"{servicio} no está disponible", {"servicio": servicio})

    # aiter_bytes entrega el cuerpo ya descomprimido, así que content-encoding no se reenvía
    cabeceras = {k: v for k, v in respuesta.headers.items()
                 if k.lower() not in CABECERAS_DE_SALTO | {"content-encoding"}}
    return StreamingResponse(respuesta.aiter_bytes(), status_code=respuesta.status_code, headers=cabeceras,
                             background=BackgroundTask(respuesta.aclose))
