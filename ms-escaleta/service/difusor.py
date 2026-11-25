# ms-escaleta/service/difusor.py
# Difusión de cambios en directo a las apps conectadas por Server-Sent Events.
# Cada conexión SSE tiene su cola; los endpoints (que se ejecutan en otro hilo) dejan los mensajes
# en las colas de los suscriptores del evento.
# Limitación: funciona dentro de una réplica. Con varias réplicas habría que repartir los mensajes
# con Redis pub/sub o con una cola de RabbitMQ por réplica.
import asyncio
import json
import threading
from collections import defaultdict


class Difusor:
    def __init__(self):
        self._suscriptores: dict[str, set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = defaultdict(set)
        self._lock = threading.Lock()

    def suscribir(self, evento_id: str) -> asyncio.Queue:
        cola: asyncio.Queue = asyncio.Queue(maxsize=100)
        with self._lock:
            self._suscriptores[evento_id].add((asyncio.get_running_loop(), cola))
        return cola

    def cancelar(self, evento_id: str, cola: asyncio.Queue) -> None:
        with self._lock:
            self._suscriptores[evento_id] = {s for s in self._suscriptores[evento_id] if s[1] is not cola}

    def num_suscriptores(self, evento_id: str) -> int:
        return len(self._suscriptores.get(evento_id, ()))

    def emitir(self, evento_id: str, tipo: str, datos: dict) -> None:
        mensaje = f"event: {tipo}\ndata: {json.dumps(datos, default=str, ensure_ascii=False)}\n\n"
        with self._lock:
            suscriptores = list(self._suscriptores.get(evento_id, ()))
        for loop, cola in suscriptores:
            loop.call_soon_threadsafe(self._encolar, cola, mensaje)

    @staticmethod
    def _encolar(cola: asyncio.Queue, mensaje: str) -> None:
        try:
            cola.put_nowait(mensaje)
        except asyncio.QueueFull:
            pass  # cliente demasiado lento: se pierde el mensaje; al reconectar pedirá la escaleta


difusor = Difusor()
