# ms-tienda/config/settings.py
# Configuración del servicio leída de variables de entorno (.env en local, docker-compose en contenedor)
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

NOMBRE_SERVICIO = "ms-tienda"
PREFIJO_API = "/api/v1"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://tienda:tienda@localhost:5434/tienda_db",
)
PUERTO = int(os.getenv("PUERTO", "8004"))

# Reglas de negocio
UMBRAL_STOCK_BAJO = int(os.getenv("UMBRAL_STOCK_BAJO", "5"))
