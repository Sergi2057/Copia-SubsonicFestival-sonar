# infra/prueba_integracion.py
# Prueba de integración: recorre de punta a punta los flujos que cruzan servicios (por RabbitMQ y
# por el API Gateway) y dice cuáles pasan. Solo usa la librería estándar de Python.
#
# Antes (desde la carpeta infra):
#   python servicios.py preparar
#   docker compose -f docker-compose.global.yml up -d --build
#   python servicios.py poblar
# Y después:
#   python prueba_integracion.py            (todos los flujos)
#   python prueba_integracion.py 1 3        (solo los flujos 1 y 3)
#
# Cada ejecución crea sus propios datos (evento, usuarios…) con un sufijo aleatorio, así que se
# puede repetir sin limpiar. Los datos de prueba que usa: uid-cliente-david, evento-belgium,
# espacio-002, el producto gorra-black y el artista 22222222-2222-4222-8222-000000000001.
import base64
import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

INFRA = Path(__file__).resolve().parent
COMPOSE = ["docker", "compose", "-f", str(INFRA / "docker-compose.global.yml")]
URL = {"escaleta": "http://localhost:8001", "espacios": "http://localhost:8002", "usuarios": "http://localhost:8003",
       "tienda": "http://localhost:8004", "analitica": "http://localhost:8005", "gateway": "http://localhost:8000"}
RABBITMQ_API = "http://localhost:15672/api"
SEGUNDOS_ESPERA = 30  # lo que se espera a que un evento llegue y se procese

ADMIN = {"X-User-Id": "uid-admin-jose", "X-User-Rol": "ADMIN"}
DAVID = {"X-User-Id": "uid-cliente-david", "X-User-Rol": "CLIENTE"}
ARTISTA = "22222222-2222-4222-8222-000000000001"
SUFIJO = uuid.uuid4().hex[:6]


class Fallo(Exception):
    pass


# ── Utilidades ──────────────────────────────────────────────

def http(metodo: str, servicio: str, ruta: str, cuerpo=None, cabeceras=None) -> tuple[int, object]:
    url = ruta if ruta.startswith("http") else f"{URL[servicio]}{ruta}"
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(url, data=datos, method=metodo,
                                      headers={"Content-Type": "application/json", **(cabeceras or {})})
    try:
        with urllib.request.urlopen(peticion, timeout=15) as r:
            texto = r.read().decode()
            return r.status, json.loads(texto) if texto else None
    except urllib.error.HTTPError as e:
        texto = e.read().decode()
        try:
            return e.code, json.loads(texto)
        except ValueError:
            return e.code, texto


def esperado(respuesta: tuple[int, object], *codigos: int) -> object:
    estado, cuerpo = respuesta
    if estado not in codigos:
        raise Fallo(f"respuesta {estado} (se esperaba {codigos}): {str(cuerpo)[:200]}")
    return cuerpo


def esperar(condicion, segundos: int = SEGUNDOS_ESPERA, pausa: float = 1.0):
    """Repite condicion() hasta que devuelva algo verdadero o se acabe el tiempo."""
    limite = time.time() + segundos
    while True:
        resultado = condicion()
        if resultado or time.time() > limite:
            return resultado
        time.sleep(pausa)


def sql(base: str, consulta: str) -> str:
    # base = "espacios", "usuarios"… (usuario, contraseña y nombre de BD siguen el mismo patrón)
    salida = subprocess.run([*COMPOSE, "exec", "-T", f"{base}-db", "psql", "-U", base, "-d", f"{base}_db",
                             "-tAc", consulta], capture_output=True, text=True)
    return salida.stdout.strip()


def mongo(expresion: str) -> str:
    salida = subprocess.run([*COMPOSE, "exec", "-T", "analitica-mongo", "mongosh", "analitica_db", "--quiet",
                             "--eval", expresion], capture_output=True, text=True)
    return salida.stdout.strip()


def logs(servicio: str, desde: str) -> str:
    salida = subprocess.run([*COMPOSE, "logs", "--no-color", "--since", desde, servicio],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    return salida.stdout


def rabbitmq(metodo: str, ruta: str, cuerpo=None):
    credenciales = base64.b64encode(b"subsonic:subsonic").decode()
    peticion = urllib.request.Request(f"{RABBITMQ_API}{ruta}", method=metodo,
                                      data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                      headers={"Authorization": f"Basic {credenciales}",
                                               "Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=15) as r:
        return json.loads(r.read().decode() or "null")


def ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def variante_gorra() -> str:
    producto = esperado(http("GET", "tienda", "/api/v1/productos/gorra-black"), 200)
    return producto["variantes"][0]["id"]


def pedido_recogida(cabeceras: dict, evento_id: str, variante: str):
    return http("POST", "tienda", "/api/v1/pedidos", {
        "lineas": [{"variante_id": variante, "cantidad": 1}], "entrega": "RECOGIDA_EVENTO",
        "evento_id_recogida": evento_id, "token_pago": "tok_integracion"}, cabeceras)


# ── Flujo 1: compra de una entrada ──────────────────────────

def flujo_1_compra() -> str:
    entrada = esperado(http("POST", "usuarios", "/api/v1/usuarios/me/entradas",
                            {"evento_id": "evento-belgium", "tipo_pase": "DAY", "token_pago": "tok_integracion"},
                            DAVID), 201)
    reserva_id = sql("usuarios", f"select reserva_id from entradas where id = '{entrada['id']}'")
    if not reserva_id:
        raise Fallo("ms-usuarios no guardó la reserva de la entrada")

    estado = esperar(lambda: sql("espacios", f"select estado from reservas_aforo where id = '{reserva_id}'")
                     == "CONFIRMADA" and "CONFIRMADA")
    if not estado:
        raise Fallo("ms-espacios no confirmó la reserva (¿consume usuarios.entrada.comprada?)")

    en_analitica = esperar(lambda: mongo(
        f"db.eventos_dominio.countDocuments({{'datos.entrada_id': '{entrada['id']}'}})") not in ("", "0"))
    if not en_analitica:
        raise Fallo("ms-analitica no registró la venta (¿consume con la clave #?)")
    return f"entrada {entrada['id']}: reserva CONFIRMADA en ms-espacios y venta registrada en ms-analitica"


# ── Flujo 2: cambio en la escaleta ──────────────────────────

def flujo_2_cambio_escaleta() -> str:
    escaleta = esperado(http("GET", "escaleta", "/api/v1/escaletas/evento-belgium"), 200)
    pase = escaleta["dias"][0]["escenarios"][0]["pases"][0]

    # David necesita el artista en favoritos, una entrada del evento y un móvil registrado: los cambios
    # de horario se avisan solo por push (Firebase Cloud Messaging)
    esperado(http("POST", "usuarios", "/api/v1/usuarios/me/favoritos", {"artista_id": pase["artista_id"]}, DAVID),
             201, 409)
    esperado(http("POST", "usuarios", "/api/v1/usuarios/me/dispositivos",
                  {"fcm_token": "token-prueba-integracion", "plataforma": "ANDROID"}, DAVID), 201)
    esperado(http("POST", "usuarios", "/api/v1/usuarios/me/entradas",
                  {"evento_id": "evento-belgium", "tipo_pase": "DAY", "token_pago": "tok_integracion"}, DAVID), 201)

    # Suscripción SSE en un hilo, como haría la app
    recibido: list[str] = []

    def escuchar():
        try:
            with urllib.request.urlopen(f"{URL['escaleta']}/api/v1/escaletas/evento-belgium/cambios",
                                        timeout=SEGUNDOS_ESPERA) as r:
                for linea in r:
                    recibido.append(linea.decode())
                    if pase["pase_id"] in recibido[-1]:
                        return
        except Exception:  # noqa: BLE001 - fin del tiempo o conexión cerrada
            pass

    threading.Thread(target=escuchar, daemon=True).start()
    time.sleep(2)

    desde = ahora_iso()
    actual = esperado(http("GET", "escaleta", f"/api/v1/pases/{pase['pase_id']}"), 200)
    nuevo_formato = "LIVE" if actual["formato"] != "LIVE" else "DJ_SET"
    esperado(http("PATCH", "escaleta", f"/api/v1/pases/{pase['pase_id']}",
                  {"version": actual["version"], "formato": nuevo_formato, "motivo": "Prueba de integración"},
                  ADMIN), 200)

    if not esperar(lambda: any(pase["pase_id"] in l for l in recibido), segundos=10):
        raise Fallo("la app conectada por SSE no recibió pase.modificado")
    def push_a_david():
        return any("[push] uid-cliente-david" in linea and pase["artista"] in linea
                   for linea in logs("ms-usuarios", desde).splitlines())

    if not esperar(push_a_david):
        raise Fallo("ms-usuarios no envió el push a David (¿consume escaleta.pase.modificado?)")
    return f"pase de {pase['artista']}: aviso por SSE y push de ms-usuarios a David"


# ── Flujo 3: cancelación de un evento ───────────────────────

def flujo_3_cancelacion_evento() -> str:
    evento_id = f"evento-prueba-{SUFIJO}"
    recinto = esperado(http("POST", "espacios", "/api/v1/recintos", {
        "nombre": f"Recinto prueba {SUFIJO}", "ciudad": "Cáceres", "pais": "España", "aforo_maximo": 1000}, ADMIN), 201)
    esperado(http("POST", "espacios", "/api/v1/eventos", {
        "id": evento_id, "titulo": f"Evento de prueba {SUFIJO}", "pais": "España", "recinto_id": recinto["id"],
        "fecha_inicio": "2027-01-10", "fecha_fin": "2027-01-12"}, ADMIN), 201)
    esperado(http("POST", "espacios", f"/api/v1/eventos/{evento_id}/tarifas",
                  {"tipo_pase": "DAY", "precio": 10, "cupo_total": 100}, ADMIN), 201)
    escenario = esperado(http("POST", "espacios", "/api/v1/espacios", {
        "evento_id": evento_id, "tipo": "ESCENARIO", "nombre": "Escenario prueba", "aforo": 500,
        "disponible": False}, ADMIN), 201)
    esperado(http("PATCH", "espacios", f"/api/v1/eventos/{evento_id}", {"estado": "PUBLICADO"}, ADMIN), 200)

    # ms-escaleta solo admite slots cuando le han llegado el escenario y el evento publicado
    slot = esperar(lambda: http("POST", "escaleta", f"/api/v1/escaletas/{evento_id}/slots", {
        "espacio_id": escenario["id"], "inicio": "2027-01-10T22:00:00+01:00", "fin": "2027-01-10T23:00:00+01:00",
        "tipo": "ACTUACION"}, ADMIN))
    if not slot or slot[0] != 201:
        raise Fallo(f"ms-escaleta no recibió el escenario o el evento publicado: {slot}")
    pase = esperado(http("POST", "escaleta", f"/api/v1/slots/{slot[1]['id']}/pases",
                         {"artista_id": ARTISTA, "formato": "DJ_SET"}, ADMIN), 201)

    entrada = esperado(http("POST", "usuarios", "/api/v1/usuarios/me/entradas",
                            {"evento_id": evento_id, "tipo_pase": "DAY", "token_pago": "tok_integracion"}, DAVID), 201)
    variante = variante_gorra()
    antes = esperar(lambda: pedido_recogida(DAVID, evento_id, variante)[0] == 201)
    if not antes:
        raise Fallo("ms-tienda no acepta recogidas en el evento publicado (¿consume espacios.evento.publicado?)")

    esperado(http("PATCH", "espacios", f"/api/v1/eventos/{evento_id}",
                  {"estado": "CANCELADO", "motivo": "Prueba de integración"}, ADMIN), 200)

    problemas = []
    if not esperar(lambda: http("GET", "escaleta", f"/api/v1/pases/{pase['id']}")[1].get("estado") == "CANCELADO"):
        problemas.append("ms-escaleta no canceló el pase")
    if not esperar(lambda: http("GET", "usuarios", f"/api/v1/usuarios/me/entradas/{entrada['id']}",
                                cabeceras=DAVID)[1].get("estado") == "CANCELADA"):
        problemas.append("ms-usuarios no canceló la entrada")
    if not esperar(lambda: pedido_recogida(DAVID, evento_id, variante)[0] != 201):
        problemas.append("ms-tienda sigue aceptando recogidas en el evento cancelado")
    if problemas:
        raise Fallo("; ".join(problemas))
    return f"{evento_id} cancelado: pase cancelado, entrada cancelada y recogida rechazada"


# ── Flujo 4: borrado de una cuenta (RGPD) ───────────────────

def flujo_4_rgpd() -> str:
    proveedor = {"X-User-Id": f"uid-prueba-prov-{SUFIJO}", "X-User-Rol": "PROVEEDOR",
                 "X-User-Email": f"prov-{SUFIJO}@prueba.com"}
    cliente = {"X-User-Id": f"uid-prueba-cli-{SUFIJO}", "X-User-Rol": "CLIENTE",
               "X-User-Email": f"cli-{SUFIJO}@prueba.com"}

    esperado(http("POST", "usuarios", "/api/v1/usuarios", {
        "nombre": "Proveedor prueba", "rol": "PROVEEDOR",
        "proveedor": {"nombre_comercial": f"Prueba {SUFIJO}", "tipo_servicio": "Comida"}}, proveedor), 201)
    # ms-espacios solo deja alquilar cuando le ha llegado el proveedor a su réplica
    alquiler = esperar(lambda: http("POST", "espacios", "/api/v1/espacios/espacio-002/alquileres", {
        "fecha_inicio": "2027-03-01T08:00:00+01:00", "fecha_fin": "2027-03-02T20:00:00+01:00"}, proveedor))
    if not alquiler or alquiler[0] != 201:
        raise Fallo(f"ms-espacios no recibió el proveedor nuevo (usuarios.proveedor.actualizado): {alquiler}")

    esperado(http("POST", "usuarios", "/api/v1/usuarios", {"nombre": "Cliente prueba", "rol": "CLIENTE"}, cliente), 201)
    esperado(http("POST", "usuarios", "/api/v1/usuarios/me/favoritos", {"artista_id": ARTISTA}, cliente), 201)
    pedido = esperado(http("POST", "tienda", "/api/v1/pedidos", {
        "lineas": [{"variante_id": variante_gorra(), "cantidad": 1}], "entrega": "DOMICILIO",
        "direccion_envio": "Calle Prueba 1", "token_pago": "tok_integracion"}, cliente), 201)
    time.sleep(3)  # que ms-analitica reciba el favorito antes del borrado

    esperado(http("DELETE", "usuarios", "/api/v1/usuarios/me", cabeceras=proveedor), 204)
    esperado(http("DELETE", "usuarios", "/api/v1/usuarios/me", cabeceras=cliente), 204)

    problemas = []
    if not esperar(lambda: http("GET", "espacios", f"/api/v1/alquileres/{alquiler[1]['id']}",
                                cabeceras=ADMIN)[1].get("proveedor_id") == "anonimizado"):
        problemas.append("ms-espacios no anonimizó el alquiler")
    if not esperar(lambda: http("GET", "tienda", f"/api/v1/pedidos/{pedido['id']}",
                                cabeceras=ADMIN)[1].get("usuario_id") == "anonimizado"):
        problemas.append("ms-tienda no anonimizó el pedido")
    if not esperar(lambda: mongo(f"db.favoritos.countDocuments({{usuario_id: '{cliente['X-User-Id']}'}}) + "
                                 f"db.eventos_dominio.countDocuments({{'datos.usuario_id': '{cliente['X-User-Id']}'}})")
                   == "0"):
        problemas.append("ms-analitica no anonimizó al cliente")
    if problemas:
        raise Fallo("; ".join(problemas))
    return "proveedor y cliente borrados: alquiler, pedido y analítica anonimizados"


# ── Flujo 5: mensaje que falla ──────────────────────────────

def flujo_5_dlq() -> str:
    # Un usuarios.entrada.comprada sin reserva_id ni evento_id: los consumidores deben fallar,
    # reintentar 3 veces y dejarlo en la cola de mensajes fallidos
    id_evento = str(uuid.uuid4())
    sobre = {"id_evento": id_evento, "tipo": "usuarios.entrada.comprada", "version": 1, "origen": "prueba",
             "fecha": ahora_iso(), "correlation_id": str(uuid.uuid4()), "datos": {"entrada_id": "rota"}}
    rabbitmq("POST", "/exchanges/%2F/subsonic.events/publish", {
        "properties": {"delivery_mode": 2, "content_type": "application/json"},
        "routing_key": "usuarios.entrada.comprada", "payload": json.dumps(sobre), "payload_encoding": "string"})

    def en_dlq():
        mensajes = rabbitmq("POST", "/queues/%2F/subsonic.dlq/get",
                            {"count": 200, "ackmode": "ack_requeue_true", "encoding": "auto"})
        return any(id_evento in m["payload"] for m in mensajes)

    if not esperar(en_dlq, pausa=2):
        raise Fallo("el mensaje defectuoso no llegó a subsonic.dlq")
    return f"mensaje {id_evento[:8]} en subsonic.dlq tras los reintentos"


# ── Flujo 6: todo a través del API Gateway ──────────────────

def flujo_6_gateway() -> str:
    # El front-end solo habla con el gateway y manda el token; en el entorno global el gateway acepta
    # tokens de desarrollo dev:<uid>:<ROL>[:<email>] en lugar de los de Firebase
    david = {"Authorization": "Bearer dev:uid-cliente-david:CLIENTE"}
    problemas = []

    if http("GET", "gateway", "/api/v1/eventos")[0] != 200:
        problemas.append("la ruta pública /eventos no responde")
    if http("GET", "gateway", "/api/v1/usuarios/me")[0] != 401:
        problemas.append("una ruta privada responde sin token")
    if http("GET", "gateway", "/api/v1/usuarios/me",
            cabeceras={"Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4In0.falso"})[0] != 401:
        problemas.append("acepta un token de Firebase falso")
    if http("GET", "gateway", "/api/v1/usuarios", cabeceras={**david, "X-User-Rol": "ADMIN"})[0] != 403:
        problemas.append("un cliente que se envía X-User-Rol: ADMIN entra como administrador")
    if http("POST", "gateway", "/internal/v1/eventos/evento-belgium/reservas-aforo", {})[0] != 404:
        problemas.append("las rutas /internal son accesibles desde fuera")

    # Registro de un usuario nuevo de Firebase, que aún no tiene rol, y compra con David
    nuevo = {"Authorization": f"Bearer dev:uid-prueba-gw-{SUFIJO}::gw-{SUFIJO}@prueba.com"}
    if http("POST", "gateway", "/api/v1/usuarios", {"nombre": "Usuario gateway", "rol": "CLIENTE"}, nuevo)[0] != 201:
        problemas.append("un usuario sin rol no puede registrarse")
    entrada = http("POST", "gateway", "/api/v1/usuarios/me/entradas",
                   {"evento_id": "evento-belgium", "tipo_pase": "DAY", "token_pago": "tok_integracion"}, david)
    if entrada[0] != 201:
        problemas.append(f"la compra de una entrada falla: {entrada}")

    # Cambios de la escaleta en directo (SSE) a través del gateway
    recibido: list[str] = []

    def escuchar():
        try:
            peticion = urllib.request.Request(f"{URL['gateway']}/api/v1/escaletas/evento-belgium/cambios",
                                              headers={"Accept": "text/event-stream"})
            with urllib.request.urlopen(peticion, timeout=SEGUNDOS_ESPERA) as r:
                for linea in r:
                    if linea.startswith(b"data:"):
                        recibido.append(linea.decode())
                        return
        except Exception:  # noqa: BLE001 - fin del tiempo o conexión cerrada
            pass

    threading.Thread(target=escuchar, daemon=True).start()
    time.sleep(2)
    admin = {"Authorization": "Bearer dev:uid-admin-jose:ADMIN"}
    pase_id = http("GET", "gateway", "/api/v1/escaletas/evento-belgium")[1]["dias"][0]["escenarios"][0]["pases"][0][
        "pase_id"]
    actual = esperado(http("GET", "gateway", f"/api/v1/pases/{pase_id}"), 200)
    esperado(http("PATCH", "gateway", f"/api/v1/pases/{pase_id}", {
        "version": actual["version"], "formato": "LIVE" if actual["formato"] != "LIVE" else "DJ_SET",
        "motivo": "Prueba del gateway"}, admin), 200)
    if not esperar(lambda: recibido, segundos=10):
        problemas.append("el SSE de la escaleta no llega a través del gateway")

    if problemas:
        raise Fallo("; ".join(problemas))
    return "rutas públicas y privadas, tokens falsos, cabeceras inventadas, /internal, registro, compra y SSE"


# ── Ejecución ───────────────────────────────────────────────

FLUJOS = {
    "1": ("Compra de una entrada", flujo_1_compra),
    "2": ("Cambio en la escaleta", flujo_2_cambio_escaleta),
    "3": ("Cancelación de un evento", flujo_3_cancelacion_evento),
    "4": ("Borrado de una cuenta (RGPD)", flujo_4_rgpd),
    "5": ("Mensaje que falla (DLQ)", flujo_5_dlq),
    "6": ("Todo a través del API Gateway", flujo_6_gateway),
}


def comprobar_entorno() -> None:
    caidos = [s for s in URL if http("GET", s, "/salud")[0] != 200]
    try:
        rabbitmq("GET", "/overview")
    except Exception:  # noqa: BLE001
        caidos.append("rabbitmq")
    if caidos:
        print(f"No responden: {', '.join(caidos)}. Arranca antes el entorno global (ver la cabecera del script).")
        sys.exit(2)


def main() -> None:
    comprobar_entorno()
    elegidos = sys.argv[1:] or list(FLUJOS)
    resultados = []
    for numero in elegidos:
        nombre, flujo = FLUJOS[numero]
        print(f"\n[{numero}] {nombre}…", flush=True)
        try:
            detalle = flujo()
            resultados.append((numero, nombre, True, detalle))
            print(f"    PASA  {detalle}")
        except Exception as e:  # noqa: BLE001 - un flujo roto no para los demás
            resultados.append((numero, nombre, False, str(e)))
            print(f"    FALLA {e}")

    print("\n" + "=" * 70)
    for numero, nombre, ok, _ in resultados:
        print(f"  {'PASA ' if ok else 'FALLA'}  {numero}. {nombre}")
    pasan = sum(ok for *_, ok, _ in resultados)
    print(f"\n  {pasan} de {len(resultados)} flujos pasan")
    sys.exit(0 if pasan == len(resultados) else 1)


if __name__ == "__main__":
    main()
