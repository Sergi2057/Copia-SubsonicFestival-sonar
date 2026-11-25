# gateway/config/errores.py
# Formato común de errores de la ASEE: { codigo, mensaje, detalles, correlation_id }
import uuid
from contextvars import ContextVar
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# correlation-id de la petición en curso: el gateway lo crea y lo reenvía a los microservicios
correlation_id_actual: ContextVar[str] = ContextVar("correlation_id", default="")


class ErrorApi(Exception):
    """Error que se traduce a una respuesta HTTP con el formato común."""

    def __init__(self, status: int, codigo: str, mensaje: str, detalles: dict | None = None):
        super().__init__(mensaje)
        self.status = status
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalles = detalles


def respuesta_error(status: int, codigo: str, mensaje: str, detalles=None) -> JSONResponse:
    cuerpo = {"codigo": codigo, "mensaje": mensaje, "correlation_id": correlation_id_actual.get() or None}
    if detalles:
        cuerpo["detalles"] = detalles
    return JSONResponse(status_code=status, content=jsonable_encoder(cuerpo),
                        headers={"X-Correlation-Id": correlation_id_actual.get()})


def configurar_errores(app: FastAPI):
    @app.middleware("http")
    async def correlation_id(request: Request, call_next):
        cid = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        correlation_id_actual.set(cid)
        respuesta = await call_next(request)
        respuesta.headers["X-Correlation-Id"] = cid
        return respuesta

    @app.exception_handler(ErrorApi)
    async def error_api(_: Request, exc: ErrorApi):
        return respuesta_error(exc.status, exc.codigo, exc.mensaje, exc.detalles)

    @app.exception_handler(StarletteHTTPException)
    async def error_http(_: Request, exc: StarletteHTTPException):
        codigos = {404: "RUTA_NO_ENCONTRADA", 405: "METODO_NO_PERMITIDO"}
        return respuesta_error(exc.status_code, codigos.get(exc.status_code, "ERROR"), str(exc.detail))
