# ms-escaleta/service/youtube.py
# Vídeos y playlists de un artista desde la API de YouTube Data v3.
# Caché de 24 h y circuit breaker: tras 3 fallos seguidos no se llama a YouTube durante 60 s.
# Si no hay clave o YouTube no responde se devuelve una lista vacía.
import logging
import time
import httpx
from config.settings import YOUTUBE_API_KEY
from service import cache

log = logging.getLogger("youtube")
# httpx escribe en INFO la URL de cada petición, y la de YouTube lleva la clave (?key=...):
# así no aparece en los logs
logging.getLogger("httpx").setLevel(logging.WARNING)

URL_BUSQUEDA = "https://www.googleapis.com/youtube/v3/search"
CACHE_SEGUNDOS = 24 * 3600
FALLOS_PARA_ABRIR = 3
SEGUNDOS_ABIERTO = 60

_fallos = 0
_abierto_hasta = 0.0


def _convertir(item: dict) -> dict | None:
    snippet, ident = item.get("snippet", {}), item.get("id", {})
    miniatura = snippet.get("thumbnails", {}).get("medium", {}).get("url")
    if ident.get("kind") == "youtube#video":
        return {"titulo": snippet.get("title", ""), "url": f"https://www.youtube.com/watch?v={ident['videoId']}",
                "miniatura_url": miniatura, "tipo": "VIDEO"}
    if ident.get("kind") == "youtube#playlist":
        return {"titulo": snippet.get("title", ""),
                "url": f"https://www.youtube.com/playlist?list={ident['playlistId']}",
                "miniatura_url": miniatura, "tipo": "PLAYLIST"}
    return None


def videos_de_artista(artista_id: str, nombre: str, channel_id: str | None) -> list[dict]:
    global _fallos, _abierto_hasta
    if not YOUTUBE_API_KEY:
        return []
    clave = f"youtube:{artista_id}"
    guardado = cache.obtener(clave)
    if guardado is not None:
        return guardado
    if time.time() < _abierto_hasta:
        return []  # circuito abierto

    # Con canal: lo último del canal. Sin canal: búsqueda por nombre (como en la versión actual)
    parametros = {"part": "snippet", "maxResults": 10, "type": "video,playlist", "key": YOUTUBE_API_KEY}
    if channel_id:
        parametros |= {"channelId": channel_id, "order": "date"}
    else:
        parametros |= {"q": nombre}

    try:
        respuesta = httpx.get(URL_BUSQUEDA, params=parametros, timeout=3)
        respuesta.raise_for_status()
    except httpx.HTTPError as e:
        _fallos += 1
        # Solo el tipo y el código HTTP: el texto del error incluye la URL con la clave
        estado = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else type(e).__name__
        log.warning("YouTube no responde (%s), fallo %s/%s", estado, _fallos, FALLOS_PARA_ABRIR)
        if _fallos >= FALLOS_PARA_ABRIR:
            _abierto_hasta, _fallos = time.time() + SEGUNDOS_ABIERTO, 0
        return []

    _fallos = 0
    videos = [v for v in (_convertir(i) for i in respuesta.json().get("items", [])) if v]
    cache.guardar(clave, videos, CACHE_SEGUNDOS)
    return videos
