# ms-analitica/eventos/manejadores.py
# ms-analitica escucha TODOS los eventos (clave "#") y los pasa enteros al procesador.
# - procesar() recibe el sobre completo, no solo "datos": necesita id_evento (idempotencia) y fecha.
# - Si un mensaje llega repetido, procesar() lo detecta por su id_evento y no vuelve a sumar.
# - Si procesar() falla, lanza la excepción: el consumidor lo reintenta y, al tercer fallo, va a la DLQ.
import logging
from eventos.consumidor import Consumidor
from eventos.procesador import procesar

log = logging.getLogger("manejadores")


def manejar(sobre: dict) -> None:
    if not procesar(sobre):
        log.info("Evento ya procesado: %s %s", sobre.get("tipo"), sobre.get("id_evento"))


consumidor = Consumidor(cola="ms-analitica", claves=["#"], manejador=manejar)
