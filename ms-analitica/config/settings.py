# ms-analitica/config/settings.py
# Configuración del servicio leída de variables de entorno (.env en local, docker-compose en contenedor)
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

NOMBRE_SERVICIO = "ms-analitica"
PREFIJO_API = "/api/v1"

# "mongomock://" usa una base de datos en memoria (tests)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27018")
MONGO_DB = os.getenv("MONGO_DB", "analitica_db")
PUERTO = int(os.getenv("PUERTO", "8005"))

# Caché de estadísticas y recomendaciones. Vacío = caché en memoria
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6381/0")
SEGUNDOS_CACHE_ESTADISTICAS = 60
SEGUNDOS_CACHE_RECOMENDACIONES = 600
