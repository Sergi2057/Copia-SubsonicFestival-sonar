# ms-analitica · Estadísticas y recomendaciones

Microservicio de la ASEE de Subsonic Festival (GA02). El contrato está en [openapi.yaml](openapi.yaml).

**Tecnologías:** Python 3.12, FastAPI, Pydantic 2, MongoDB 7 (pymongo), Redis 7, RabbitMQ (pika), Docker.
**Puerto:** 8005 · **BD:** `analitica_db` (MongoDB, puerto 27018) · **Caché:** Redis (puerto 6381) · **Cola:** `ms-analitica`.

> No es propietario de datos de negocio: **todo se calcula a partir de los eventos** del resto de servicios. Si se borra la base de datos, basta con volver a procesar los eventos.

## Arrancar con Docker (recomendado)

Primero RabbitMQ (rama `infra`), porque el servicio se une a su red `subsonic`:

```bash
cd infra && docker compose up -d && cd ..
cd ms-analitica
docker compose up --build
docker compose exec ms-analitica python scripts/poblar_bd.py    # procesa eventos de ejemplo
```

API y documentación: http://localhost:8005/docs

## Desarrollar en local (con recarga automática)

```bash
cd ms-analitica
docker compose up -d analitica-mongo analitica-redis
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                # Mac/Linux: cp .env.example .env
python scripts/poblar_bd.py
python main.py
```

## Tests

```bash
pytest -q
```

Usan MongoDB en memoria (`mongomock`) y ningún RabbitMQ, así que no hace falta Docker. [test_mensajeria.py](tests/test_mensajeria.py) pasa mensajes como los del broker por el consumidor (con un canal falso) y comprueba el `ack`, los duplicados y los reintentos.

No hay migraciones: MongoDB no tiene esquema y los índices se crean al arrancar (`crear_indices()`).

## Cómo funciona

- [eventos/manejadores.py](eventos/manejadores.py): el consumidor de RabbitMQ. La cola `ms-analitica` está enlazada a `subsonic.events` con la clave `#`, así que recibe **todos** los eventos y pasa el sobre completo a `procesar()`. `publicador.py` y `consumidor.py` son copia de la plantilla de `infra`. Sin `RABBITMQ_URL` el consumidor no arranca.
- [eventos/procesador.py](eventos/procesador.py): `procesar(sobre)` recibe cada evento con el sobre común.
  - Es **idempotente**: guarda el `id_evento` en `procesados`, así que un mensaje repetido no suma dos veces.
  - Guarda una copia en `eventos_dominio` y actualiza las métricas agregadas con `$inc`.
  - Si un manejador falla, desmarca el evento para que RabbitMQ lo vuelva a entregar.
- **Estadísticas** (admin): cacheadas 60 s en Redis.
- **Recomendaciones para clientes**: 60 % por contenido (géneros de sus favoritos) y 40 % colaborativo (favoritos de clientes con gustos parecidos). Se cachean y se invalidan al cambiar sus favoritos.
- **Mi escaleta**: los pases publicados de sus favoritos, con los solapamientos marcados en `solapa_con`.
- **Afluencia**: el público del día (entradas validadas o, si no hay, vendidas) se reparte entre los pases que coinciden en el tiempo según los favoritos de cada artista, con el aforo del escenario como límite.
- **Espacios para proveedores**: espacios libres de los tipos que ya alquiló. Se puntúan por público previsto del evento (50 %), demanda histórica de ese tipo (30 %) y precio (20 %).

## Estado (semana 2)

- ✅ Todos los endpoints de `openapi.yaml` y el procesador de todos los eventos que consume.
- ✅ Consumidor de RabbitMQ: cola `ms-analitica` con la clave `#`. `scripts/poblar_bd.py` sigue sirviendo para tener datos sin el resto de servicios.
- ⏳ El archivado de `eventos_dominio` a los 2 años.
