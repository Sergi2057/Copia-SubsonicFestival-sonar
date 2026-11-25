# gateway/main.py
# Punto de entrada del API Gateway: única puerta de entrada del front-end a los 5 microservicios
import asyncio
import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from config.cors_config import configurar_cors
from config.errores import configurar_errores
from config.settings import MODO_AUTENTICACION, NOMBRE_SERVICIO, PUERTO, SERVICIOS
from controller import proxy_controller

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if MODO_AUTENTICACION == "desarrollo":
        log.warning("MODO_AUTENTICACION=desarrollo: se aceptan tokens dev:<uid>:<ROL>. No usar en producción")
    # Un solo cliente HTTP para todas las peticiones (reutiliza conexiones). Los tests lo sustituyen.
    if not hasattr(app.state, "cliente"):
        app.state.cliente = httpx.AsyncClient()
    try:
        yield
    finally:
        await app.state.cliente.aclose()


app = FastAPI(
    title="Subsonic Festival - API Gateway",
    version="1.0.0",
    description="Comprueba el token de Firebase, añade la identidad del usuario (X-User-Id, X-User-Rol, "
                "X-User-Email) y reenvía cada /api/v1/... al microservicio que la atiende.",
    lifespan=lifespan,
)

configurar_cors(app)
configurar_errores(app)


@app.get("/salud", tags=["Infraestructura"], summary="Estado del gateway y de cada microservicio")
async def salud(request: Request):
    async def comprobar(url: str) -> str:
        try:
            r = await request.app.state.cliente.get(f"{url}/salud", timeout=2)
            return "ok" if r.status_code == 200 else f"error {r.status_code}"
        except httpx.HTTPError:
            return "no disponible"

    estados = await asyncio.gather(*(comprobar(url) for url in SERVICIOS.values()))
    return {"servicio": NOMBRE_SERVICIO, "estado": "ok", "servicios": dict(zip(SERVICIOS, estados))}


app.include_router(proxy_controller.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PUERTO, reload=True)
