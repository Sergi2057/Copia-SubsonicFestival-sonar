# gateway/service/autenticacion.py
# Comprueba el ID token de Firebase y obtiene la identidad que se pasa a los microservicios
import logging
from dataclasses import dataclass
import firebase_admin
from firebase_admin import auth, credentials
from google.auth.credentials import AnonymousCredentials
from starlette.concurrency import run_in_threadpool
from config.errores import ErrorApi
from config.settings import FIREBASE_PROJECT_ID, MODO_AUTENTICACION

log = logging.getLogger("autenticacion")

PREFIJO_DESARROLLO = "dev:"
_app_firebase: firebase_admin.App | None = None


@dataclass
class Identidad:
    id: str
    rol: str | None  # CLIENTE, PROVEEDOR, ADMIN o STAFF; None si aún no ha registrado su perfil
    email: str | None


class _SinCredenciales(credentials.Base):
    """Verificar un ID token solo usa las claves públicas de Google, pero firebase_admin exige una credencial."""

    def get_credential(self):
        return AnonymousCredentials()


def _firebase() -> firebase_admin.App:
    """Sin firebase-claves.json: para verificar tokens basta con el ID del proyecto."""
    global _app_firebase
    if _app_firebase is None:
        _app_firebase = firebase_admin.initialize_app(
            _SinCredenciales(), options={"projectId": FIREBASE_PROJECT_ID}, name="gateway")
    return _app_firebase


def _token_desarrollo(token: str) -> Identidad:
    """dev:<uid>:<ROL>[:<email>]. El rol puede ir vacío (dev:uid-nuevo:) para probar el registro."""
    partes = token[len(PREFIJO_DESARROLLO):].split(":", 2)
    if len(partes) < 2 or not partes[0]:
        raise ErrorApi(401, "TOKEN_NO_VALIDO", "Token de desarrollo mal formado: dev:<uid>:<ROL>[:<email>]")
    uid, rol = partes[0], partes[1].upper() or None
    return Identidad(id=uid, rol=rol, email=partes[2] if len(partes) == 3 else None)


def _verificar_firebase(token: str) -> Identidad:
    try:
        datos = auth.verify_id_token(token, app=_firebase())
    except auth.ExpiredIdTokenError:
        raise ErrorApi(401, "TOKEN_CADUCADO", "El token ha caducado; vuelve a pedirlo con getIdToken()")
    except (auth.InvalidIdTokenError, ValueError) as e:
        log.info("Token rechazado: %s", e)
        raise ErrorApi(401, "TOKEN_NO_VALIDO", "Falta el token o no es válido")
    except auth.CertificateFetchError:
        log.exception("No se pudieron descargar las claves públicas de Firebase")
        raise ErrorApi(503, "AUTENTICACION_NO_DISPONIBLE", "No se puede comprobar el token en este momento")
    rol = datos.get("rol")
    return Identidad(id=datos["uid"], rol=rol.upper() if isinstance(rol, str) else None, email=datos.get("email"))


async def identificar(cabecera_authorization: str | None) -> Identidad | None:
    """None si la petición no trae token (rutas públicas); ErrorApi 401 si lo trae y no es válido."""
    if not cabecera_authorization:
        return None
    tipo, _, token = cabecera_authorization.partition(" ")
    token = token.strip()
    if tipo.lower() != "bearer" or not token:
        raise ErrorApi(401, "TOKEN_NO_VALIDO", "La cabecera Authorization debe ser: Bearer <token>")
    if token.startswith(PREFIJO_DESARROLLO):
        if MODO_AUTENTICACION != "desarrollo":
            raise ErrorApi(401, "TOKEN_NO_VALIDO", "Los tokens de desarrollo están desactivados")
        return _token_desarrollo(token)
    # verify_id_token es bloqueante (puede descargar las claves de Google): fuera del bucle de eventos
    return await run_in_threadpool(_verificar_firebase, token)
