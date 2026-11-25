# ms-escaleta/tests/test_mensajeria.py
# Consumidores de eventos de ms-espacios. No necesitan RabbitMQ: se llama directamente a
# manejadores.manejar() con el sobre, igual que haría el consumidor al recibir el mensaje.
from unittest.mock import Mock

import pytest

from conftest import ADMIN
from eventos import manejadores
from eventos.publicador import construir_sobre

API = "/api/v1"
EVENTO = "evento-msg"


# ── Unitarios: cada evento llama a su función ──────────────

@pytest.mark.parametrize("tipo", manejadores.EVENTOS_ESPACIO)
def test_eventos_de_espacio_llaman_a_al_cambiar_espacio(monkeypatch, tipo):
    db, funcion = Mock(), Mock()
    monkeypatch.setattr(manejadores, "SessionLocal", Mock(return_value=db))
    monkeypatch.setattr(manejadores.escaleta_service, "al_cambiar_espacio", funcion)
    datos = {"espacio_id": "esc-1", "evento_id": EVENTO, "tipo": "ESCENARIO", "nombre": "Main"}

    manejadores.manejar({"tipo": tipo, "datos": datos})

    funcion.assert_called_once_with(db, tipo, datos)
    db.close.assert_called_once_with()


@pytest.mark.parametrize(("tipo", "estado"), [("espacios.evento.publicado", "PUBLICADO"),
                                              ("espacios.evento.cancelado", "CANCELADO")])
def test_eventos_de_estado_llaman_a_al_cambiar_estado_evento(monkeypatch, tipo, estado):
    db, funcion = Mock(), Mock()
    monkeypatch.setattr(manejadores, "SessionLocal", Mock(return_value=db))
    monkeypatch.setattr(manejadores.escaleta_service, "al_cambiar_estado_evento", funcion)

    manejadores.manejar({"tipo": tipo, "datos": {"evento_id": EVENTO, "estado": estado}})

    funcion.assert_called_once_with(db, EVENTO, estado)
    db.close.assert_called_once_with()


def test_evento_desconocido_falla_y_cierra_la_sesion(monkeypatch):
    # El consumidor lo reintentará y acabará en subsonic.dlq
    db = Mock()
    monkeypatch.setattr(manejadores, "SessionLocal", Mock(return_value=db))
    with pytest.raises(ValueError, match="Evento no soportado"):
        manejadores.manejar({"tipo": "espacios.otra.cosa", "datos": {}})
    db.close.assert_called_once_with()


def test_la_cola_escucha_justo_los_eventos_que_maneja():
    # Claves exactas (sin * ni #): todo lo que llega a la cola lo sabe tratar manejar()
    assert manejadores.consumidor.cola == "ms-escaleta"
    assert manejadores.consumidor.claves == ["espacios.espacio.creado", "espacios.espacio.actualizado",
                                             "espacios.espacio.eliminado", "espacios.evento.publicado",
                                             "espacios.evento.cancelado"]
    assert not any("*" in clave or "#" in clave for clave in manejadores.consumidor.claves)


# ── De punta a punta con la BD de los tests ────────────────

def espacio(tipo_evento, espacio_id="esc-main", tipo="ESCENARIO", nombre="Main Stage"):
    return construir_sobre(tipo_evento, {"espacio_id": espacio_id, "evento_id": EVENTO, "tipo": tipo,
                                         "nombre": nombre, "zona": "Norte", "aforo": 5000,
                                         "precio_alquiler": None, "disponible": True})


def evento(tipo_evento, estado):
    return construir_sobre(tipo_evento, {"evento_id": EVENTO, "titulo": "Test", "pais": "ES",
                                         "recinto_id": "r-1", "fecha_inicio": "2026-07-18",
                                         "fecha_fin": "2026-07-20", "estado": estado})


def test_crear_escenario_en_espacios_aparece_en_la_replica(cliente_http):
    c = cliente_http
    sobre = espacio("espacios.espacio.creado")
    manejadores.manejar(sobre)
    manejadores.manejar(sobre)  # RabbitMQ puede entregarlo dos veces: no pasa nada
    manejadores.manejar(espacio("espacios.espacio.creado", "esc-fb", tipo="FOOD_BEVERAGE"))  # se ignora
    manejadores.manejar(espacio("espacios.espacio.actualizado", nombre="Main Stage XL"))

    from config.database import SessionLocal
    from model.models import Escenario
    db = SessionLocal()
    try:
        escenarios = db.query(Escenario).all()
        assert [(e.espacio_id, e.nombre, e.aforo) for e in escenarios] == [("esc-main", "Main Stage XL", 5000)]
    finally:
        db.close()

    # Con el evento publicado ya se pueden crear slots en ese escenario
    manejadores.manejar(evento("espacios.evento.publicado", "PUBLICADO"))
    r = c.post(f"{API}/escaletas/{EVENTO}/slots", headers=ADMIN,
               json={"espacio_id": "esc-main", "inicio": "2026-07-18T22:00:00+02:00",
                     "fin": "2026-07-19T00:00:00+02:00", "tipo": "ACTUACION"})
    assert r.status_code == 201

    # Un escenario con slots no se borra de la réplica; uno sin slots, sí
    manejadores.manejar(espacio("espacios.espacio.creado", "esc-2", nombre="Trance Stage"))
    manejadores.manejar(espacio("espacios.espacio.eliminado"))
    manejadores.manejar(espacio("espacios.espacio.eliminado", "esc-2", nombre="Trance Stage"))
    db = SessionLocal()
    try:
        assert [e.espacio_id for e in db.query(Escenario).all()] == ["esc-main"]
    finally:
        db.close()


def test_evento_cancelado_en_espacios_cancela_los_pases(cliente_http):
    c = cliente_http
    manejadores.manejar(espacio("espacios.espacio.creado"))
    manejadores.manejar(evento("espacios.evento.publicado", "PUBLICADO"))
    artista = c.post(f"{API}/artistas", headers=ADMIN, json={"nombre": "Tiësto", "generos": ["house"]}).json()
    s = c.post(f"{API}/escaletas/{EVENTO}/slots", headers=ADMIN,
               json={"espacio_id": "esc-main", "inicio": "2026-07-18T22:00:00+02:00",
                     "fin": "2026-07-19T00:00:00+02:00", "tipo": "ACTUACION"}).json()
    pase = c.post(f"{API}/slots/{s['id']}/pases", headers=ADMIN,
                  json={"artista_id": artista["id"], "formato": "DJ_SET"}).json()

    cancelado = evento("espacios.evento.cancelado", "CANCELADO")
    manejadores.manejar(cancelado)
    manejadores.manejar(cancelado)  # repetido: no vuelve a subir la versión

    actual = c.get(f"{API}/pases/{pase['id']}").json()
    assert (actual["estado"], actual["version"]) == ("CANCELADO", pase["version"] + 1)

    # Con el evento cancelado ya no se admiten slots nuevos
    r = c.post(f"{API}/escaletas/{EVENTO}/slots", headers=ADMIN,
               json={"espacio_id": "esc-main", "inicio": "2026-07-19T01:00:00+02:00",
                     "fin": "2026-07-19T02:00:00+02:00", "tipo": "ACTUACION"})
    assert r.status_code == 409
