# ms-tienda · Tienda de merchandising

Microservicio de la ASEE de Subsonic Festival (GA02). El contrato está en [openapi.yaml](openapi.yaml).

**Tecnologías:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, PostgreSQL 16, RabbitMQ (pika), Docker.
**Puerto:** 8004 · **BD:** `tienda_db` (PostgreSQL, puerto 5434 en tu equipo) · **Cola:** `ms-tienda`.

## Arrancar con Docker (recomendado)

Primero RabbitMQ (rama `infra`), porque el servicio se une a su red `subsonic`:

```bash
cd infra && docker compose up -d && cd ..
cd ms-tienda
docker compose up --build
```

- API y documentación: http://localhost:8004/docs
- Datos de prueba (con los contenedores arrancados):
  `docker compose exec ms-tienda python scripts/poblar_bd.py`

## Desarrollar en local (con recarga automática)

```bash
cd ms-tienda
docker compose up -d tienda-db        # solo la base de datos
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                # Mac/Linux: cp .env.example .env
python scripts/poblar_bd.py
python main.py
```

En VS Code selecciona el intérprete `ms-tienda/.venv` (Ctrl+Shift+P → *Python: Select Interpreter*).

## Tests

```bash
pytest -q
```

Usan una base de datos SQLite temporal y ningún RabbitMQ, así que no hace falta Docker. Incluyen los consumidores ([test_mensajeria.py](tests/test_mensajeria.py)) y las migraciones ([test_migraciones.py](tests/test_migraciones.py)).

## Migraciones (Alembic)

Al arrancar, el servicio ejecuta `alembic upgrade head`:

- [0001](migrations/versions/0001_esquema_inicial_de_tienda.py): el esquema de la semana 1 (productos, variantes, pedidos y líneas).
- [0002](migrations/versions/0002_eventos_de_recogida.py): la tabla `eventos_recogida`.
- [0003](migrations/versions/0003_variantes_activas.py): la columna `variantes.activa` (las variantes que ya existían quedan activas).

```bash
alembic upgrade head                              # aplicar a mano
alembic revision --autogenerate -m "descripción"  # nueva migración tras cambiar model/models.py (revísala)
```

Si tu base de datos de Docker viene de la semana 1 (creada con `create_all`), no hace falta borrarla: al arrancar se marca como `0001` sin tocar los datos y se aplican solo la `0002` y la `0003`. Si viene de la semana 2, se aplica solo la `0003`.

## Tallas (variantes)

- `PATCH /productos/{id}/variantes/{variante_id}` cambia la talla, el stock o los dos (400 si el cuerpo llega vacío, 409 `TALLA_DUPLICADA` si el producto ya tiene esa talla). Si cambia el stock, sigue avisando con `tienda.stock.bajo`.
- `DELETE /productos/{id}/variantes/{variante_id}`:
  - 409 `VARIANTE_CON_PEDIDOS_PENDIENTES` si está en pedidos `PAGADO`, `PREPARADO`, `ENVIADO` o `LISTO_RECOGIDA`.
  - Si nunca se ha vendido, se borra.
  - Si solo está en pedidos terminados, se retira (`activa = false`): desaparece del catálogo público y `POST /pedidos` la rechaza con 409 `VARIANTE_RETIRADA`. El administrador la sigue viendo.
- `POST /productos/{id}/variantes` con una talla retirada la reactiva (`activa = true`, con el stock nuevo) y devuelve 201 con el mismo id, así conserva su historial de pedidos. Con una talla activa sigue dando 409 `TALLA_DUPLICADA`.

## Eventos (RabbitMQ)

`eventos/publicador.py` y `eventos/consumidor.py` son copia de la plantilla de `infra`. Lo que hace este servicio con cada evento está en [eventos/manejadores.py](eventos/manejadores.py):

| Evento que consume | Función |
|---|---|
| `usuarios.usuario.eliminado` | `pedido_service.anonimizar_pedidos_usuario` (RGPD: `usuario_id = "anonimizado"` y sin dirección) |
| `espacios.evento.publicado` / `cancelado` | `pedido_service.al_cambiar_estado_evento` (habilita o deshabilita el evento como punto de recogida) |

**Recogida en evento:** un pedido con `RECOGIDA_EVENTO` solo se acepta si el evento está `PUBLICADO` en la tabla `eventos_recogida`. Si no, responde 409 `RECOGIDA_NO_DISPONIBLE` antes de tocar el stock o cobrar. Como en ms-espacios `CANCELADO` es definitivo, un `publicado` que llegue tarde no reabre un evento cancelado. Los pedidos ya hechos no se tocan.

Sin `RABBITMQ_URL` los eventos solo se escriben en el log y el consumidor no arranca (así funcionan los tests). `poblar_bd.py` da de alta como puntos de recogida los tres eventos publicados de prueba de ms-espacios.

## Autenticación

En producción el **API Gateway** valida el JWT de Firebase y añade las cabeceras `X-User-Id` y `X-User-Rol`.
Para probar sin gateway, envía tú esas cabeceras (en `/docs` o con curl):

```bash
curl -X POST http://localhost:8004/api/v1/pedidos \
  -H "X-User-Id: cliente-1" -H "X-User-Rol: cliente" -H "Content-Type: application/json" \
  -d '{"lineas":[{"variante_id":"<uuid>","cantidad":1}],"entrega":"RECOGIDA_EVENTO","evento_id_recogida":"evento-belgium","token_pago":"tok_123"}'
```

## Estructura

```text
ms-tienda/
├── config/        # settings, BD, errores comunes, seguridad (cabeceras del gateway), CORS
├── controller/    # endpoints /productos y /pedidos
├── service/       # lógica de negocio (stock, pedidos, estados) y pasarela de pago simulada
├── model/         # models.py (ORM), dao/, dto/ (Pydantic), factory/
├── eventos/       # publicador y consumidor de RabbitMQ (plantilla de infra) y manejadores
├── migrations/    # migraciones de Alembic
├── scripts/       # poblar_bd.py
└── tests/
```

## Estado (semana 2)

- ✅ Todos los endpoints de `openapi.yaml`, con sus reglas de negocio: stock con `SELECT … FOR UPDATE`, 402 si se rechaza el pago y se devuelve el stock, transiciones de estado y retirada lógica de productos.
- ✅ **Eventos** por RabbitMQ: publica `tienda.pedido.*` y `tienda.stock.bajo` y consume `usuarios.usuario.eliminado` y `espacios.evento.*`.
- ✅ Migraciones con Alembic.
- ⏳ **Pasarela de pago** simulada: los tokens que empiezan por `tok_rechazado` devuelven 402.
