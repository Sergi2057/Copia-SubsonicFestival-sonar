# ms-espacios · Eventos, espacios, alquileres y aforo

Microservicio de la ASEE de Subsonic Festival (GA02). El contrato está en [openapi.yaml](openapi.yaml).

**Tecnologías:** Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, PostgreSQL 16 (JSONB), RabbitMQ, Docker.
**Puerto:** 8002 · **BD:** `espacios_db` (PostgreSQL, puerto 5436 en tu equipo).

## Arrancar con Docker (recomendado)

```bash
# En otro checkout en la rama infra:
cd infra
docker compose up -d

# En el checkout de la rama ms-espacios:
cd ms-espacios
docker compose up --build
docker compose exec ms-espacios python scripts/poblar_bd.py    # datos de prueba
```

API y documentación: http://localhost:8002/docs

## Desarrollar en local (con recarga automática)

```bash
cd ms-espacios
docker compose up -d espacios-db      # solo la base de datos
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                # Mac/Linux: cp .env.example .env
python scripts/poblar_bd.py
python main.py
```

RabbitMQ local se configura con `RABBITMQ_URL=amqp://subsonic:subsonic@localhost:5672/%2F` en `.env`.
Sin esa variable, la publicación queda en el log y el consumidor no se inicia. En Docker Compose,
el servicio usa la red externa `subsonic`; arranca primero `infra` para crearla.

Si la base de datos conserva tablas creadas por una versión antigua con `create_all` y todavía no
tiene la tabla `alembic_version`, registra el esquema inicial antes de arrancar la API. Desde
`ms-espacios`, con el entorno virtual y `DATABASE_URL` apuntando a esa base:

```bash
alembic stamp 252a6562f75f
```

Después, el arranque aplica las migraciones pendientes, incluida la tabla nueva de eventos
procesados. Para una base antigua en Docker, ejecuta desde `ms-espacios` antes de `docker compose up`:

```bash
docker compose run --rm --no-deps ms-espacios alembic stamp 252a6562f75f
```

## Tests

```bash
pytest -q
```

Usan una base de datos SQLite temporal, así que no hace falta Docker.

## Autenticación

- **Rutas públicas** (`/api/v1/...`): el API Gateway valida el JWT de Firebase y añade las cabeceras `X-User-Id` y `X-User-Rol`. Sin gateway, escríbelas tú en `/docs` (por ejemplo `X-User-Rol: admin`).
- **Rutas internas** (`/internal/v1/...`): no las expone el gateway. Las usa ms-usuarios con la cabecera `X-Service-Token` (por defecto `token-servicio-dev`).

## Datos de prueba

| Dato | Identificadores |
|---|---|
| Eventos (PUBLICADOS) | `evento-belgium`, `evento-thailand`, `evento-brasil`, con tarifas DAY/WEEKEND (y VIP en Bélgica) |
| Escenarios (los usa ms-escaleta) | `espacio-belgium-main-stage`, `espacio-belgium-trance-stage`, `espacio-thailand-ocean-stage`, … |
| Espacios alquilables | `espacio-001`, `espacio-002` (Bélgica) y `espacio-003` (Tailandia) |
| Proveedor activo (réplica) | `uid-proveedor-ana` |

## Estado

- ✅ Todos los endpoints de `openapi.yaml`, con sus reglas de negocio:
  - Estados de los eventos (los borradores solo los ve el administrador).
  - Sin alquileres aprobados que se solapen, con bloqueo de fila al solicitar y al aprobar.
  - Solo pueden solicitar alquileres los proveedores activos de la réplica.
  - **Reserva de aforo** con `SELECT … FOR UPDATE`, caducidad de 10 minutos y aviso `espacios.aforo.agotado`.
- ✅ Alembic aplica el esquema al arrancar; el catálogo de tipos se carga de forma idempotente.
- ✅ Tarea periódica cada minuto para caducar reservas y activar alquileres iniciados.
- ✅ Publicación y consumo de eventos por RabbitMQ cuando `RABBITMQ_URL` está configurada.
- ✅ Consumidores de compras/cancelaciones de entradas, cambios de proveedor y borrado de usuario.
