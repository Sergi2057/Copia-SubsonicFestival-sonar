# ms-escaleta/config/settings.py
# Configuración del servicio leída de variables de entorno (.env en local, docker-compose en contenedor)
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

NOMBRE_SERVICIO = "ms-escaleta"
PREFIJO_API = "/api/v1"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://escaleta:escaleta@localhost:5435/escaleta_db",
)
PUERTO = int(os.getenv("PUERTO", "8001"))

# Caché de la escaleta publicada. Vacío = sin caché (se lee de PostgreSQL)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")

# API de YouTube. Vacío = /artistas/{id}/videos devuelve siempre []
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Hora a la que termina un "día de festival": un pase a las 01:00 pertenece a la noche anterior
HORA_CORTE_DIA = int(os.getenv("HORA_CORTE_DIA", "6"))
