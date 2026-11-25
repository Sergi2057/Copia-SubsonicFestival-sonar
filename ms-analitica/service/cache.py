# ms-analitica/service/cache.py
# Caché de las estadísticas (60 s) y de las recomendaciones de cada usuario.
# Usa Redis si está disponible; si no (tests, Redis caído) usa un diccionario en memoria,
# así que el servicio nunca falla por culpa de la caché.
import json
import logging
import time
from config.settings import REDIS_URL

log = logging.getLogger("cache")

_memoria: dict[str, tuple[float, str]] = {}
_redis = None
_redis_caido_hasta = 0.0


def _cliente():
    global _redis, _redis_caido_hasta
    if not REDIS_URL or time.time() < _redis_caido_hasta:
        return None
    if _redis is None:
        import redis
        _redis = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
    return _redis


def _redis_fallo(e: Exception):
    global _redis_caido_hasta
    log.warning("Redis no disponible (%s); se usa la caché en memoria durante 30 s", e)
    _redis_caido_hasta = time.time() + 30


def obtener(clave: str):
    cliente = _cliente()
    if cliente is not None:
        try:
            valor = cliente.get(clave)
            return json.loads(valor) if valor else None
        except Exception as e:  # noqa: BLE001 - cualquier fallo de Redis degrada a memoria
            _redis_fallo(e)
    caduca, valor = _memoria.get(clave, (0, None))
    return json.loads(valor) if valor and caduca > time.time() else None


def guardar(clave: str, valor, segundos: int) -> None:
    texto = json.dumps(valor, default=str)
    _memoria[clave] = (time.time() + segundos, texto)
    cliente = _cliente()
    if cliente is not None:
        try:
            cliente.set(clave, texto, ex=segundos)
        except Exception as e:  # noqa: BLE001
            _redis_fallo(e)


def borrar(clave: str) -> None:
    _memoria.pop(clave, None)
    cliente = _cliente()
    if cliente is not None:
        try:
            cliente.delete(clave)
        except Exception as e:  # noqa: BLE001
            _redis_fallo(e)
