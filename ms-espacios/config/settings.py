# ms-espacios/config/settings.py
# Configuración del servicio leída de variables de entorno (.env en local, docker-compose en contenedor)
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

NOMBRE_SERVICIO = "ms-espacios"
PREFIJO_API = "/api/v1"
PREFIJO_INTERNO = "/internal/v1"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://espacios:espacios@localhost:5436/espacios_db",
)
PUERTO = int(os.getenv("PUERTO", "8002"))

# Token compartido por los servicios de la red interna (cabecera X-Service-Token)
TOKEN_SERVICIO = os.getenv("TOKEN_SERVICIO", "token-servicio-dev")

# Reglas de negocio
MINUTOS_RESERVA_AFORO = int(os.getenv("MINUTOS_RESERVA_AFORO", "10"))
