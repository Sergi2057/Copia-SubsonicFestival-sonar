# gateway/config/settings.py
# Configuración del API Gateway leída de variables de entorno (.env en local, docker-compose en contenedor)
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

NOMBRE_SERVICIO = "gateway"
PREFIJO_API = "/api/v1"
PUERTO = int(os.getenv("PUERTO", "8000"))

# Dirección de cada microservicio (en Docker, por su nombre dentro de la red "subsonic")
SERVICIOS = {
    "ms-escaleta": os.getenv("ESCALETA_URL", "http://localhost:8001"),
    "ms-espacios": os.getenv("ESPACIOS_URL", "http://localhost:8002"),
    "ms-usuarios": os.getenv("USUARIOS_URL", "http://localhost:8003"),
    "ms-tienda": os.getenv("TIENDA_URL", "http://localhost:8004"),
    "ms-analitica": os.getenv("ANALITICA_URL", "http://localhost:8005"),
}

# Primer segmento de la ruta (/api/v1/<recurso>/...) -> microservicio que la atiende
RUTAS = {
    "escaletas": "ms-escaleta", "slots": "ms-escaleta", "pases": "ms-escaleta", "artistas": "ms-escaleta",
    "eventos": "ms-espacios", "recintos": "ms-espacios", "tipos-espacio": "ms-espacios",
    "espacios": "ms-espacios", "alquileres": "ms-espacios",
    "usuarios": "ms-usuarios", "proveedores": "ms-usuarios", "entradas": "ms-usuarios",
    "productos": "ms-tienda", "pedidos": "ms-tienda",
    "estadisticas": "ms-analitica", "recomendaciones": "ms-analitica", "interacciones": "ms-analitica",
}

# Autenticación: "firebase" (por defecto) comprueba el ID token de Firebase.
# "desarrollo" acepta además tokens "dev:<uid>:<ROL>[:<email>]" para probar sin Firebase. NUNCA en producción.
MODO_AUTENTICACION = os.getenv("MODO_AUTENTICACION", "firebase").lower()
# Para comprobar el token basta con el ID del proyecto (claves públicas de Google), no hace falta la clave privada
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "subsonicfestivall3g1")

# Orígenes del front-end que pueden llamar a la API desde el navegador (separados por comas)
CORS_ORIGENES = [o.strip() for o in os.getenv(
    "CORS_ORIGENES", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

# Segundos de espera a un microservicio (el SSE de la escaleta no tiene límite de lectura)
TIEMPO_CONEXION = float(os.getenv("TIEMPO_CONEXION", "3"))
TIEMPO_RESPUESTA = float(os.getenv("TIEMPO_RESPUESTA", "15"))
