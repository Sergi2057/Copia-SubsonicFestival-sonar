# infra · RabbitMQ y mensajería común

Infraestructura compartida de la ASEE de Subsonic Festival (GA02): el broker de eventos **RabbitMQ** y la **plantilla de mensajería** que cada microservicio copia en su rama. Los servicios no comparten código: el módulo se copia, no se importa.

## 1. Arrancar RabbitMQ

Con Docker Desktop abierto:

```bash
cd infra
docker compose up -d
```

- Mensajes: `amqp://subsonic:subsonic@localhost:5672/` (desde tu equipo) o `amqp://subsonic:subsonic@rabbitmq:5672/` (desde un contenedor).
- Panel web: http://localhost:15672, con usuario `subsonic` y contraseña `subsonic`. Ahí se ven las colas, los mensajes y la cola de fallidos.

Al arrancar se crean, desde [rabbitmq/definitions.json](rabbitmq/definitions.json):

| Elemento | Tipo | Para qué |
|---|---|---|
| `subsonic.events` | exchange topic | Todos los eventos. La clave de enrutado es el campo `tipo` (`usuarios.entrada.comprada`…). |
| `subsonic.dlx` | exchange fanout | Recibe los mensajes que han fallado demasiadas veces. |
| `subsonic.dlq` | cola | Mensajes fallidos, para revisarlos a mano en el panel. |
| red `subsonic` | red de Docker | Cada servicio se une a ella para llegar a `rabbitmq` por su nombre. |

Cada servicio crea su propia cola al arrancar (`ms-espacios`, `ms-usuarios`…). No hace falta declararlas aquí.

## 2. Conectar tu microservicio (unos 15 minutos)

**a) Copia los dos archivos** de [plantilla-mensajeria/eventos/](plantilla-mensajeria/eventos/) en la carpeta `eventos/` de tu servicio:

- `publicador.py` **sustituye** al que ya tienes. Tiene la misma función `publicar(tipo, datos)`, así que no cambia ningún import ni ninguna llamada.
- `consumidor.py` es nuevo.

**b) Añade** `pika==1.3.2` a tu `requirements.txt`.

**c) Crea `eventos/manejadores.py`**, con lo que hace tu servicio con cada evento que consume. Ejemplo real de ms-espacios, ya probado: [ejemplo-ms-espacios/manejadores.py](plantilla-mensajeria/ejemplo-ms-espacios/manejadores.py).

```python
def manejar(sobre: dict) -> None:
    tipo, datos = sobre["tipo"], sobre["datos"]
    db = SessionLocal()          # una sesión por mensaje
    try:
        if tipo == "usuarios.entrada.comprada":
            aforo_service.confirmar_reserva(db, UUID(datos["reserva_id"]))
        elif ...
    finally:
        db.close()

consumidor = Consumidor(cola="ms-espacios",
                        claves=["usuarios.entrada.comprada", "usuarios.entrada.cancelada",
                                "usuarios.proveedor.actualizado", "usuarios.proveedor.desactivado",
                                "usuarios.usuario.eliminado"],
                        manejador=manejar)
```

**Pon las claves exactas de los eventos que tratas**, no comodines. Las claves admiten comodines (`*` sustituye a una palabra y `#` a cualquier número de palabras), pero con ellos te llegan también eventos que no esperas. Por ejemplo, `usuarios.entrada.*` incluye `usuarios.entrada.validada`. Si tu manejador lanza un error con un tipo desconocido, cada uno de esos mensajes se reintenta 3 veces y acaba en `subsonic.dlq`. La única excepción es ms-analitica, que usa `["#"]` porque procesa todos los eventos.

**Si cambias las claves, borra a mano las que quitas.** La cola de tu servicio se guarda en RabbitMQ entre arranques, y el consumidor añade las claves nuevas pero no borra las antiguas. Por ejemplo, si cambias `usuarios.entrada.*` por las claves exactas, el comodín sigue enganchado a la cola y te siguen llegando los eventos que no esperas. Para quitarlo, elige una de estas dos opciones:

- En el panel (http://localhost:15672), entra en **Queues and Streams → tu cola → Bindings** y pulsa **Unbind** en la fila de la clave antigua.
- Borra los datos de RabbitMQ con `docker compose down -v` en `infra` (o con `docker compose -f docker-compose.global.yml down -v` si usas el entorno global, que borra también las bases de datos). Al volver a arrancar, la cola se crea solo con las claves actuales.

**d) Arráncalo en `main.py`:**

```python
from eventos.manejadores import consumidor

@asynccontextmanager
async def lifespan(_: FastAPI):
    crear_tablas()
    consumidor.iniciar()
    yield
    consumidor.detener()
```

**e) En tu `docker-compose.yml`**, añade la variable y la red al servicio de la API, y declara la red al final del archivo:

```yaml
  ms-espacios:
    build: .
    environment:
      RABBITMQ_URL: amqp://subsonic:subsonic@rabbitmq:5672/%2F
      # ...las variables que ya tenías
    networks:
      - default
      - subsonic

networks:
  subsonic:
    external: true
```

Para ejecutar con `python main.py` fuera de Docker, pon en tu `.env`: `RABBITMQ_URL=amqp://subsonic:subsonic@localhost:5672/%2F`.

**f) Orden de arranque:** primero `infra` (`docker compose up -d`) y después tu servicio. Si arrancas el servicio antes, `docker compose` falla porque no existe la red `subsonic`.

## 3. Cómo se comporta

- **Sin `RABBITMQ_URL`** (tus tests, o desarrollo sin Docker): `publicar()` solo escribe en el log y el consumidor no arranca. **Tus tests siguen pasando sin tocarlos.**
- **Publicar:** mensajes persistentes y con confirmación del broker. Si RabbitMQ no responde, lo reintenta una vez. Si vuelve a fallar, la operación de negocio NO se deshace y el evento queda en el log como `EVENTO NO PUBLICADO`.
- **Consumir:** se hace `ack` solo si tu manejador termina sin excepción. Si lanza una excepción, el mensaje se reintenta 3 veces y después va a `subsonic.dlq`. Si RabbitMQ se reinicia, el consumidor se reconecta solo cada 5 segundos.
- **Mensajes repetidos:** RabbitMQ puede entregar un mensaje dos veces. Tus manejadores tienen que ser idempotentes, es decir, que procesar dos veces el mismo evento no sume dos veces. Las funciones que ya existen lo cuidan; por ejemplo, `confirmar_reserva` no suma si la reserva ya estaba confirmada.
- El `correlation_id` del evento se propaga: lo que publiques dentro de un manejador lleva el mismo.

## 4. Tests de la plantilla

```bash
cd infra/plantilla-mensajeria
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Mac/Linux: source .venv/bin/activate
pip install pika==1.3.2 pytest
pytest -q
```

Hay 6 tests. Los 2 de RabbitMQ real (publicar y consumir por clave; mensaje que acaba en la DLQ tras 3 reintentos) se saltan si `infra` no está arrancado.

**Probado de punta a punta:** se compró una entrada en ms-usuarios, el evento llegó por RabbitMQ y ms-espacios dejó la reserva CONFIRMADA con `cupo_vendido` sumado.

## 5. Todo el sistema a la vez (`docker-compose` global)

[docker-compose.global.yml](docker-compose.global.yml) levanta RabbitMQ, los 5 microservicios con sus bases de datos y el **API Gateway**, todos en la red `subsonic`. Dentro de esa red los servicios se llaman por su nombre, por ejemplo ms-usuarios llama a `http://ms-espacios:8002`.

El front-end usa solo el gateway: `http://localhost:8000/api/v1/...`. En este entorno local el gateway acepta, además de los tokens de Firebase, tokens de desarrollo para probar sin iniciar sesión, por ejemplo `Authorization: Bearer dev:uid-cliente-david:CLIENTE`. Los detalles están en [gateway/README.md](../gateway/README.md).

**Login real con Google o con email:** para que el token lleve el rol, ms-usuarios necesita la clave de Firebase. Quien la tenga la deja en `infra/secretos/` (fuera de git) y añade una línea a `infra/.env`. Los pasos están en [secretos/LEEME.md](secretos/LEEME.md).

Cada servicio se construye desde su carpeta del repositorio (`../ms-usuarios`, `../gateway`…):

```bash
cd infra
docker compose -f docker-compose.global.yml up -d --build
python servicios.py poblar                                  # datos de prueba
```

- Si cambias el código de un servicio, repite `up -d --build`.
- Durante el desarrollo, cada servicio vivía en su rama y `servicios.py preparar` copiaba cada rama en `infra/servicios/`. Ya no hace falta: si te quedan esas copias, bórralas con `python servicios.py limpiar`.
- Para parar: `docker compose -f docker-compose.global.yml down`. Añade `-v` para borrar también los datos.
- Usa los mismos puertos que cada servicio por separado (8000 el gateway, 8001-8005 los servicios), así que **no arranques a la vez el global y un servicio suelto**.

## 6. Prueba de integración

[prueba_integracion.py](prueba_integracion.py) recorre de punta a punta los 6 flujos que cruzan servicios y dice cuáles pasan. Solo usa la librería estándar de Python. Necesita el entorno global arrancado y poblado (sección 5).

```bash
python prueba_integracion.py        # todos
python prueba_integracion.py 1 3    # solo algunos
```

| Flujo | Qué comprueba | Necesita el trabajo de |
|---|---|---|
| 1. Compra de una entrada | ms-espacios confirma la reserva y ms-analitica registra la venta | Pedro (espacios) y Sergio (analítica) |
| 2. Cambio en la escaleta | El aviso llega por SSE y ms-usuarios notifica a quien tiene el artista en favoritos y entrada | Luis (usuarios) |
| 3. Cancelación de un evento | ms-escaleta cancela el pase, ms-usuarios la entrada y ms-tienda rechaza recogidas | Sergio (escaleta y tienda) y Luis |
| 4. Borrado de una cuenta | ms-espacios, ms-tienda y ms-analitica anonimizan sus datos | Pedro, Sergio |
| 5. Mensaje que falla | Un evento defectuoso acaba en `subsonic.dlq` tras los reintentos | Cualquier consumidor conectado |
| 6. Todo a través del API Gateway | Rutas públicas y privadas, tokens falsos y cabeceras inventadas rechazados, `/internal` cerrado, registro de un usuario sin rol, compra de una entrada y SSE de la escaleta | Paula (gateway) |

Cada ejecución crea sus propios datos con un sufijo aleatorio, así que se puede repetir sin limpiar. Si un flujo falla, el mensaje dice qué servicio no reaccionó.
