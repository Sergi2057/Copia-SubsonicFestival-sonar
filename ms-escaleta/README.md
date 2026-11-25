# ms-escaleta · Artistas, slots, pases y escaleta

Microservicio de la ASEE de Subsonic Festival (GA02). El contrato está en [openapi.yaml](openapi.yaml).

**Tecnologías:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, PostgreSQL 16 (restricción de exclusión con `btree_gist`), Redis 7, RabbitMQ (pika), Server-Sent Events, API de YouTube, Docker.
**Puerto:** 8001 · **BD:** `escaleta_db` (PostgreSQL, puerto 5435) · **Caché:** Redis (puerto 6380) · **Cola:** `ms-escaleta`.

## Arrancar con Docker (recomendado)

Primero RabbitMQ (rama `infra`), porque el servicio se une a su red `subsonic`:

```bash
cd infra && docker compose up -d && cd ..
cd ms-escaleta
docker compose up --build
docker compose exec ms-escaleta python scripts/poblar_bd.py    # datos de prueba + escaletas publicadas
```

API y documentación: http://localhost:8001/docs

Para ver los vídeos de YouTube, crea un `.env` en esta carpeta con `YOUTUBE_API_KEY=...` (la misma clave del `.env` del monolito). `docker compose` lo lee solo. El `.env` está en el `.gitignore`: **no lo subas nunca**.

## Migraciones (Alembic)

Al arrancar, el servicio ejecuta `alembic upgrade head`. La migración inicial ([0001](migrations/versions/0001_esquema_inicial_de_escaleta.py)) crea las tablas y, solo en PostgreSQL, la extensión `btree_gist` y la restricción de exclusión `ex_slots_sin_solape`, que el autogenerado no detecta.

```bash
alembic upgrade head                              # aplicar a mano
alembic revision --autogenerate -m "descripción"  # nueva migración tras cambiar model/models.py (revísala)
```

Si tu base de datos de Docker viene de la semana 1 (creada con `create_all`), no hace falta borrarla: al arrancar se detecta y se marca como revisión `0001` sin tocar los datos.

## Eventos (RabbitMQ)

`eventos/publicador.py` y `eventos/consumidor.py` son copia de la plantilla de `infra`. Lo que hace este servicio con cada evento está en [eventos/manejadores.py](eventos/manejadores.py):

| Evento que consume | Función |
|---|---|
| `espacios.espacio.creado` / `actualizado` / `eliminado` | `escaleta_service.al_cambiar_espacio` (réplica de escenarios, solo tipo `ESCENARIO`) |
| `espacios.evento.publicado` / `cancelado` | `escaleta_service.al_cambiar_estado_evento` (habilita el evento o cancela sus pases) |

Sin `RABBITMQ_URL` los eventos solo se escriben en el log y el consumidor no arranca (así funcionan los tests).

## Desarrollar en local (con recarga automática)

```bash
cd ms-escaleta
docker compose up -d escaleta-db escaleta-redis    # y RabbitMQ de infra si quieres eventos
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

Usan una base de datos SQLite temporal, la caché en memoria y ningún RabbitMQ, así que no hace falta Docker. Incluyen los consumidores ([test_mensajeria.py](tests/test_mensajeria.py)) y las migraciones ([test_migraciones.py](tests/test_migraciones.py)); este último comprueba el SQL de PostgreSQL con `alembic upgrade head --sql`.

## Probar los cambios en directo (SSE)

```bash
curl -N http://localhost:8001/api/v1/escaletas/evento-belgium/cambios
```

Con esa conexión abierta, modifica un pase desde `/docs` (`PATCH /pases/{id}` con `X-User-Rol: ADMIN` y la `version` actual). Verás llegar `event: pase.modificado`.

## Reglas de negocio implementadas

- **Sin solapes por escenario**: se comprueba en el servicio y, además, con una restricción `EXCLUDE USING gist` de PostgreSQL que protege ante peticiones simultáneas.
- **Un artista no puede estar en dos escenarios a la vez** (409 `ARTISTA_SOLAPADO`).
- **Control de concurrencia optimista**: `PATCH /pases/{id}` exige la `version` actual. Si no coincide, responde 409 `VERSION_OBSOLETA` con la versión actual en `detalles`.
- **Borrador y publicación**: los visitantes solo ven la última versión publicada (una instantánea en JSONB servida desde Redis). Publicar sin cambios responde 409.
- **Día de festival**: un pase a la 01:00 pertenece a la noche anterior (corte a las 06:00 UTC, configurable con `HORA_CORTE_DIA`).
- **YouTube**: caché de 24 h y circuit breaker (tras 3 fallos se deja de llamar durante 60 s). Sin clave o sin respuesta devuelve `[]`.

## Estado (semana 2)

- ✅ Todos los endpoints de `openapi.yaml`, incluido el SSE de `/escaletas/{evento_id}/cambios`.
- ✅ Eventos por RabbitMQ: publica los suyos y consume los de ms-espacios (réplica de escenarios y estado de los eventos).
- ✅ Migraciones con Alembic, incluida la restricción de exclusión.
- ⏳ El SSE reparte los mensajes dentro de una sola réplica. Con varias réplicas hará falta Redis pub/sub.
