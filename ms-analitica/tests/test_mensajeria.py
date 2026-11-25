# ms-analitica/tests/test_mensajeria.py
# Consumidor de ms-analitica. Sin RabbitMQ: los mensajes (bytes JSON, como llegan del broker) se
# pasan a Consumidor.procesar_mensaje con un canal falso que apunta los ack, nack y reintentos.
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

from conftest import ADMIN
from config.database import get_db
from eventos import manejadores

API = "/api/v1"


class CanalFalso:
    def __init__(self):
        self.acks, self.nacks, self.reintentos = [], [], []

    def basic_ack(self, etiqueta):
        self.acks.append(etiqueta)

    def basic_nack(self, etiqueta, requeue=True):
        self.nacks.append((etiqueta, requeue))

    def basic_publish(self, exchange, clave, cuerpo, propiedades, mandatory=False):
        self.reintentos.append((clave, propiedades.headers["x-reintentos"]))


class Props:
    headers, type, message_id, correlation_id = None, "x", "m", "c"


def mensaje(tipo, datos, id_evento=None) -> bytes:
    sobre = {"id_evento": id_evento or str(uuid.uuid4()), "tipo": tipo, "version": 1, "origen": "ms-usuarios",
             "fecha": datetime.now(timezone.utc).isoformat(), "correlation_id": "cid-test", "datos": datos}
    return json.dumps(sobre).encode()


def compra(precio=199.0):
    return {"entrada_id": "e1", "usuario_id": "u1", "evento_id": "evento-belgium", "tipo_pase": "WEEKEND",
            "precio_pagado": precio, "reserva_id": None, "estado": "ACTIVA"}


def resumen(c):
    return c.get(f"{API}/estadisticas/resumen", headers=ADMIN).json()


def test_la_cola_escucha_todos_los_eventos():
    assert manejadores.consumidor.cola == "ms-analitica"
    assert manejadores.consumidor.claves == ["#"]


def test_manejar_pasa_el_sobre_completo_al_procesador(monkeypatch):
    procesar = Mock(return_value=True)
    monkeypatch.setattr(manejadores, "procesar", procesar)
    sobre = {"id_evento": "id-1", "tipo": "escaleta.pase.modificado", "fecha": "2026-11-01", "datos": {"x": 1}}
    manejadores.manejar(sobre)
    procesar.assert_called_once_with(sobre)  # el sobre entero, no solo "datos"


def test_compra_de_entrada_llega_al_resumen_y_un_duplicado_no_suma(cliente_http):
    c = cliente_http
    canal = CanalFalso()
    cuerpo = mensaje("usuarios.entrada.comprada", compra(), id_evento="evento-fijo")

    manejadores.consumidor.procesar_mensaje(canal, 1, Props(), cuerpo)
    manejadores.consumidor.procesar_mensaje(canal, 2, Props(), cuerpo)  # RabbitMQ lo entrega dos veces

    assert canal.acks == [1, 2] and canal.nacks == [] and canal.reintentos == []
    r = resumen(c)
    assert r["entradas_vendidas"] == 1 and r["ingresos_entradas"] == 199.0


def test_eventos_sin_reaccion_propia_se_guardan_y_se_confirman(cliente_http):
    # escaleta.pase.*, espacios.aforo.agotado…: solo se guardan en eventos_dominio
    canal = CanalFalso()
    manejadores.consumidor.procesar_mensaje(canal, 1, Props(),
                                            mensaje("escaleta.pase.modificado", {"pase_id": "p1"}, "pase-1"))
    assert canal.acks == [1]
    assert get_db().eventos_dominio.count_documents({"tipo": "escaleta.pase.modificado"}) == 1


def test_mensaje_que_falla_se_reintenta_sin_quedar_marcado(cliente_http):
    c = cliente_http
    canal = CanalFalso()
    roto = compra()
    del roto["precio_pagado"]  # el procesador no puede sumarlo
    cuerpo = mensaje("usuarios.entrada.comprada", roto, id_evento="evento-roto")

    manejadores.consumidor.procesar_mensaje(canal, 1, Props(), cuerpo)

    # El consumidor lo vuelve a poner en la cola con el contador de reintentos (y a la DLQ tras 3)
    assert canal.reintentos == [("ms-analitica", 1)] and canal.acks == [1]
    # No queda marcado como procesado: el reintento se procesará de verdad
    assert get_db().procesados.count_documents({"_id": "evento-roto"}) == 0
    assert resumen(c)["entradas_vendidas"] == 0
