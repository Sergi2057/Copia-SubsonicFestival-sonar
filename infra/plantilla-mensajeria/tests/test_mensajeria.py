# Tests de la plantilla de mensajería.
# - Los unitarios no necesitan RabbitMQ.
# - test_con_rabbitmq_* usan el RabbitMQ de infra/docker-compose.yml y se saltan si no está arrancado.
import json
import os
import time
import uuid
import pytest
from eventos import publicador
from eventos.consumidor import Consumidor

URL_LOCAL = "amqp://subsonic:subsonic@localhost:5672/%2F"


class CanalFalso:
    def __init__(self):
        self.acks, self.nacks, self.publicados = [], [], []

    def basic_ack(self, etiqueta):
        self.acks.append(etiqueta)

    def basic_nack(self, etiqueta, requeue=True):
        self.nacks.append((etiqueta, requeue))

    def basic_publish(self, exchange, clave, cuerpo, propiedades, mandatory=False):
        self.publicados.append((exchange, clave, cuerpo, propiedades))
        self.mandatory = mandatory


class Props:
    def __init__(self, headers=None):
        self.headers, self.type, self.message_id, self.correlation_id = headers, "x", "m", "c"


def mensaje(tipo="prueba.ok"):
    return json.dumps(publicador.construir_sobre(tipo, {"a": 1})).encode()


def test_sin_rabbitmq_solo_escribe_en_el_log(monkeypatch, caplog):
    monkeypatch.delenv("RABBITMQ_URL", raising=False)
    caplog.set_level("INFO")
    sobre = publicador.publicar("prueba.algo", {"x": 1})
    assert sobre["origen"] == "ms-prueba" and sobre["tipo"] == "prueba.algo"
    assert "sin RabbitMQ" in caplog.text
    assert Consumidor("c", ["#"], lambda s: None).iniciar() is None


def test_mensaje_correcto_se_confirma():
    canal, recibidos = CanalFalso(), []
    Consumidor("cola", ["#"], recibidos.append).procesar_mensaje(canal, 7, Props(), mensaje())
    assert canal.acks == [7] and recibidos[0]["datos"] == {"a": 1}


def test_fallo_se_reintenta_y_despues_va_a_la_dlq():
    def falla(sobre):
        raise RuntimeError("fallo")

    consumidor, canal = Consumidor("cola", ["#"], falla, max_reintentos=3), CanalFalso()
    consumidor.procesar_mensaje(canal, 1, Props(), mensaje())
    exchange, clave, _, props = canal.publicados[0]
    assert (exchange, clave, props.headers["x-reintentos"]) == ("", "cola", 1) and canal.acks == [1]
    assert canal.mandatory  # el reintento no se pierde si la cola no existe

    consumidor.procesar_mensaje(canal, 2, Props({"x-reintentos": 3}), mensaje())
    assert canal.nacks == [(2, False)]  # requeue=False -> dead letter exchange


def test_mensaje_ilegible_va_a_la_dlq():
    canal = CanalFalso()
    Consumidor("cola", ["#"], lambda s: None).procesar_mensaje(canal, 3, Props(), b"esto no es json")
    Consumidor("cola", ["#"], lambda s: None).procesar_mensaje(canal, 4, Props(), b"[1, 2]")  # JSON, pero no un sobre
    assert canal.nacks == [(3, False), (4, False)]


def test_contador_de_reintentos_estropeado_va_a_la_dlq():
    def falla(sobre):
        raise RuntimeError("fallo")

    canal = CanalFalso()
    Consumidor("cola", ["#"], falla).procesar_mensaje(canal, 5, Props({"x-reintentos": "no-es-un-numero"}), mensaje())
    assert canal.nacks == [(5, False)] and canal.publicados == []


# ── Con RabbitMQ real ───────────────────────────────────────

def _rabbitmq_disponible() -> bool:
    try:
        import pika
        pika.BlockingConnection(pika.URLParameters(URL_LOCAL)).close()
        return True
    except Exception:  # noqa: BLE001
        return False


con_rabbitmq = pytest.mark.skipif(not _rabbitmq_disponible(), reason="RabbitMQ de infra no arrancado")


def _esperar(condicion, segundos=10):
    limite = time.time() + segundos
    while time.time() < limite and not condicion():
        time.sleep(0.1)
    return condicion()


@con_rabbitmq
def test_con_rabbitmq_publicar_y_consumir(monkeypatch):
    monkeypatch.setenv("RABBITMQ_URL", URL_LOCAL)
    cola = f"test-{uuid.uuid4().hex[:8]}"
    recibidos = []
    consumidor = Consumidor(cola, ["prueba.entrada.*"], recibidos.append)
    consumidor.iniciar()
    try:
        assert _esperar(lambda: consumidor._conexion is not None and consumidor._conexion.is_open)
        time.sleep(0.5)  # cola declarada y enlazada
        enviado = publicador.publicar("prueba.entrada.comprada", {"entrada_id": "e1"})
        publicador.publicar("prueba.otra.cosa", {"no": "llega"})  # otra clave: no se recibe
        assert _esperar(lambda: len(recibidos) == 1)
        time.sleep(0.5)
        assert len(recibidos) == 1 and recibidos[0]["id_evento"] == enviado["id_evento"]
    finally:
        consumidor.detener()
        _borrar_cola(cola)


@con_rabbitmq
def test_con_rabbitmq_tras_3_reintentos_acaba_en_la_dlq(monkeypatch):
    import pika
    monkeypatch.setenv("RABBITMQ_URL", URL_LOCAL)
    cola, intentos = f"test-{uuid.uuid4().hex[:8]}", []

    def falla(sobre):
        intentos.append(sobre["id_evento"])
        raise RuntimeError("fallo simulado")

    consumidor = Consumidor(cola, ["prueba.falla"], falla)
    consumidor.iniciar()
    try:
        assert _esperar(lambda: consumidor._conexion is not None and consumidor._conexion.is_open)
        time.sleep(0.5)
        enviado = publicador.publicar("prueba.falla", {"x": 1})
        assert _esperar(lambda: len(intentos) == 4)  # el intento original + 3 reintentos

        # Se busca ESTE mensaje en la DLQ y se retira (sin tocar otros que pudiera haber)
        conexion = pika.BlockingConnection(pika.URLParameters(URL_LOCAL))
        canal = conexion.channel()
        # Los mensajes ajenos se apartan sin confirmar y se devuelven todos al final: si se
        # devolvieran uno a uno, RabbitMQ volvería a entregar siempre el primero
        encontrado, ajenos = False, []
        for _ in range(100):
            metodo, props, cuerpo = canal.basic_get("subsonic.dlq")
            if metodo is None:
                time.sleep(0.1)
                continue
            try:
                propio = json.loads(cuerpo).get("id_evento") == enviado["id_evento"]
            except ValueError:
                propio = False
            if propio:
                canal.basic_ack(metodo.delivery_tag)
                encontrado = True
                break
            ajenos.append(metodo.delivery_tag)
        for etiqueta in ajenos:
            canal.basic_nack(etiqueta, requeue=True)
        conexion.close()
        assert encontrado
    finally:
        consumidor.detener()
        _borrar_cola(cola)


def _borrar_cola(cola: str) -> None:
    import pika
    conexion = pika.BlockingConnection(pika.URLParameters(URL_LOCAL))
    conexion.channel().queue_delete(cola)
    conexion.close()


@pytest.fixture(autouse=True)
def sin_conexion_de_hilo():
    publicador._local.canal = None
    yield
    os.environ.pop("RABBITMQ_URL", None)
