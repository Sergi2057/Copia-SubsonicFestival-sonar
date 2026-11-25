# ms-escaleta/tests/test_youtube.py
# La clave de YouTube va en la URL (?key=...): no debe aparecer nunca en los logs.
import logging

import httpx

from service import cache, youtube

CLAVE = "clave-secreta-de-prueba"


def _preparar(monkeypatch, respuesta):
    monkeypatch.setattr(youtube, "YOUTUBE_API_KEY", CLAVE)
    monkeypatch.setattr(youtube, "_fallos", 0)
    monkeypatch.setattr(youtube, "_abierto_hasta", 0.0)
    cache._memoria.clear()

    def get(url, params, timeout):
        peticion = httpx.Request("GET", url, params=params)
        logging.getLogger("httpx").info("HTTP Request: GET %s", peticion.url)  # lo que hace httpx de verdad
        return respuesta(peticion)

    monkeypatch.setattr(youtube.httpx, "get", get)


def test_la_clave_no_aparece_en_el_log_si_youtube_responde(monkeypatch, caplog):
    item = {"id": {"kind": "youtube#video", "videoId": "abc"}, "snippet": {"title": "Set"}}
    _preparar(monkeypatch, lambda p: httpx.Response(200, json={"items": [item]}, request=p))
    caplog.set_level(logging.DEBUG)

    videos = youtube.videos_de_artista("a1", "Charlotte de Witte", None)

    assert videos[0]["url"] == "https://www.youtube.com/watch?v=abc"
    assert CLAVE not in caplog.text


def test_la_clave_no_aparece_en_el_log_si_youtube_falla(monkeypatch, caplog):
    _preparar(monkeypatch, lambda p: httpx.Response(403, json={"error": "cuota"}, request=p))
    caplog.set_level(logging.DEBUG)

    assert youtube.videos_de_artista("a1", "Charlotte de Witte", None) == []
    assert "YouTube no responde (403)" in caplog.text
    assert CLAVE not in caplog.text
