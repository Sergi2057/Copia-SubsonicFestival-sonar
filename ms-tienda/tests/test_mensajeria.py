# ms-tienda/tests/test_mensajeria.py
# Consumidores de eventos de ms-usuarios y ms-espacios. No necesitan RabbitMQ: se llama
# directamente a manejadores.manejar() con el sobre, igual que haría el consumidor.
from unittest.mock import Mock

import pytest

from conftest import ADMIN, CLIENTE
from eventos import manejadores
from eventos.publicador import construir_sobre

API = "/api/v1"
EVENTO = "evento-msg"


# ── Unitarios: cada evento llama a su función ──────────────

@pytest.mark.parametrize(
    ("tipo", "datos", "funcion", "argumentos"),
    [
        ("usuarios.usuario.eliminado", {"usuario_id": "cliente-1"},
         "anonimizar_pedidos_usuario", ("cliente-1",)),
        ("espacios.evento.publicado", {"evento_id": EVENTO, "estado": "PUBLICADO"},
         "al_cambiar_estado_evento", (EVENTO, "PUBLICADO")),
        ("espacios.evento.cancelado", {"evento_id": EVENTO, "estado": "CANCELADO", "motivo": "Lluvia"},
         "al_cambiar_estado_evento", (EVENTO, "CANCELADO")),
    ],
)
def test_cada_evento_llama_a_su_funcion_y_cierra_la_sesion(monkeypatch, tipo, datos, funcion, argumentos):
    db, accion = Mock(), Mock()
    monkeypatch.setattr(manejadores, "SessionLocal", Mock(return_value=db))
    monkeypatch.setattr(manejadores.pedido_service, funcion, accion)

    manejadores.manejar({"tipo": tipo, "datos": datos})

    accion.assert_called_once_with(db, *argumentos)
    db.close.assert_called_once_with()


def test_evento_desconocido_falla_y_cierra_la_sesion(monkeypatch):
    # El consumidor lo reintentará y acabará en subsonic.dlq
    db = Mock()
    monkeypatch.setattr(manejadores, "SessionLocal", Mock(return_value=db))
    with pytest.raises(ValueError, match="Evento no soportado"):
        manejadores.manejar({"tipo": "usuarios.otra.cosa", "datos": {}})
    db.close.assert_called_once_with()


def test_la_cola_escucha_justo_los_eventos_que_maneja():
    assert manejadores.consumidor.cola == "ms-tienda"
    assert manejadores.consumidor.claves == ["usuarios.usuario.eliminado", "espacios.evento.publicado",
                                             "espacios.evento.cancelado"]


# ── De punta a punta con la BD de los tests ────────────────

def evento(tipo, estado):
    return construir_sobre(tipo, {"evento_id": EVENTO, "titulo": "Test", "pais": "ES", "recinto_id": "r-1",
                                  "fecha_inicio": "2026-07-18", "fecha_fin": "2026-07-20", "estado": estado})


def gorra(c, stock=20):
    assert c.post(f"{API}/productos", headers=ADMIN,
                  json={"id": "gorra-black", "nombre": "Gorra", "precio": 20}).status_code == 201
    r = c.post(f"{API}/productos/gorra-black/variantes", headers=ADMIN, json={"talla": "UNICA", "stock": stock})
    return r.json()["id"]


def pedir(c, variante_id, entrega="RECOGIDA_EVENTO", cabeceras=CLIENTE):
    destino = ({"evento_id_recogida": EVENTO} if entrega == "RECOGIDA_EVENTO"
               else {"direccion_envio": "Calle Mayor 1, Cáceres"})
    return c.post(f"{API}/pedidos", headers=cabeceras, json={
        "lineas": [{"variante_id": variante_id, "cantidad": 1}], "entrega": entrega,
        "token_pago": "tok_ok", **destino})


def stock(c):
    return c.get(f"{API}/productos/gorra-black").json()["variantes"][0]["stock"]


def test_recogida_solo_en_eventos_publicados(cliente_http):
    c = cliente_http
    variante = gorra(c)

    # Evento desconocido (aún no ha llegado espacios.evento.publicado): se rechaza sin tocar el stock
    r = pedir(c, variante)
    assert r.status_code == 409 and r.json()["codigo"] == "RECOGIDA_NO_DISPONIBLE"
    assert stock(c) == 20

    publicado = evento("espacios.evento.publicado", "PUBLICADO")
    manejadores.manejar(publicado)
    manejadores.manejar(publicado)  # repetido: no pasa nada
    assert pedir(c, variante).status_code == 201

    manejadores.manejar(evento("espacios.evento.cancelado", "CANCELADO"))
    r = pedir(c, variante)
    assert r.status_code == 409 and r.json()["detalles"]["estado"] == "CANCELADO"
    assert stock(c) == 19  # solo descontó el pedido aceptado

    # Un "publicado" repetido que llega tarde no reabre un evento cancelado
    manejadores.manejar(publicado)
    assert pedir(c, variante).status_code == 409

    # Los pedidos a domicilio no dependen de ningún evento
    assert pedir(c, variante, entrega="DOMICILIO").status_code == 201


def test_borrar_cuenta_anonimiza_sus_pedidos(cliente_http):
    c = cliente_http
    variante = gorra(c)
    mio = pedir(c, variante, entrega="DOMICILIO").json()
    otro = pedir(c, variante, entrega="DOMICILIO", cabeceras={"X-User-Id": "cliente-2", "X-User-Rol": "cliente"}).json()

    eliminado = construir_sobre("usuarios.usuario.eliminado", {"usuario_id": "cliente-1"})
    manejadores.manejar(eliminado)
    manejadores.manejar(eliminado)  # repetido: no pasa nada

    anonimo = c.get(f"{API}/pedidos/{mio['id']}", headers=ADMIN).json()
    assert anonimo["usuario_id"] == "anonimizado" and anonimo["direccion_envio"] is None
    assert anonimo["importe_total"] == mio["importe_total"]  # el pedido se conserva para la contabilidad
    assert c.get(f"{API}/pedidos/{otro['id']}", headers=ADMIN).json()["usuario_id"] == "cliente-2"
