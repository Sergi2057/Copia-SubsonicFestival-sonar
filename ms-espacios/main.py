# ms-espacios/main.py
# Punto de entrada del microservicio Espacios
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError
from config.cors_config import configurar_cors
from config.database import crear_tablas
from config.errores import configurar_errores
from config.settings import NOMBRE_SERVICIO, PREFIJO_API, PREFIJO_INTERNO, PUERTO
from controller import espacios_controller, eventos_controller, interno_controller, recintos_controller
from eventos.manejadores import consumidor
from service.tareas_periodicas import ejecutar_tareas_periodicas

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


async def ejecutar_tareas_cada_minuto() -> None:
    while True:
        try:
            await asyncio.to_thread(ejecutar_tareas_periodicas)
        except SQLAlchemyError:
            logging.error("La tarea periódica falló; se volverá a intentar en un minuto")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    crear_tablas()
    tarea = asyncio.create_task(ejecutar_tareas_cada_minuto())
    hilo_consumidor = consumidor.iniciar()
    try:
        yield
    finally:
        consumidor.detener()
        if hilo_consumidor is not None:
            hilo_consumidor.join(timeout=10)
        tarea.cancel()
        try:
            await tarea
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Subsonic Festival - ms-espacios",
    version="1.0.0",
    description="Eventos, recintos, espacios, alquileres, tarifas de acceso y aforo.",
    lifespan=lifespan,
)

configurar_cors(app)
configurar_errores(app)

app.include_router(eventos_controller.router, prefix=PREFIJO_API)
app.include_router(recintos_controller.router, prefix=PREFIJO_API)
app.include_router(espacios_controller.router, prefix=PREFIJO_API)
app.include_router(interno_controller.router, prefix=PREFIJO_INTERNO)


@app.get("/salud", tags=["Infraestructura"], summary="Comprobación de vida (gateway / Docker)")
def salud():
    return {"servicio": NOMBRE_SERVICIO, "estado": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PUERTO, reload=True)
