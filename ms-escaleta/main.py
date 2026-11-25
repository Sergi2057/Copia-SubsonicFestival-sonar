# ms-escaleta/main.py
# Punto de entrada del microservicio Escaleta
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from config.cors_config import configurar_cors
from config.database import crear_tablas
from config.errores import configurar_errores
from config.settings import NOMBRE_SERVICIO, PREFIJO_API, PUERTO
from controller import artistas_controller, escaleta_controller
from eventos.manejadores import consumidor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    crear_tablas()
    hilo_consumidor = consumidor.iniciar()  # None si no hay RABBITMQ_URL (tests)
    try:
        yield
    finally:
        consumidor.detener()
        if hilo_consumidor is not None:
            hilo_consumidor.join(timeout=10)


app = FastAPI(
    title="Subsonic Festival - ms-escaleta",
    version="1.0.0",
    description="Artistas, slots, pases, publicación de la escaleta y cambios en directo (SSE).",
    lifespan=lifespan,
)

configurar_cors(app)
configurar_errores(app)

app.include_router(escaleta_controller.router, prefix=PREFIJO_API)
app.include_router(artistas_controller.router, prefix=PREFIJO_API)


@app.get("/salud", tags=["Infraestructura"], summary="Comprobación de vida (gateway / Docker)")
def salud():
    return {"servicio": NOMBRE_SERVICIO, "estado": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PUERTO, reload=True)
