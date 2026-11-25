# gateway · API Gateway de Subsonic Festival

Única puerta de entrada del front-end a los 5 microservicios. El front-end llama siempre a `http://localhost:8000/api/v1/...` y el gateway:

1. **Comprueba el token de Firebase** que llega en `Authorization: Bearer <token>`.
2. **Añade la identidad** que leen los microservicios: `X-User-Id` (UID), `X-User-Rol` (claim `rol`) y `X-User-Email`. Si el cliente envía estas cabeceras por su cuenta, se descartan.
3. **Reenvía la petición** al microservicio que atiende ese recurso y devuelve su respuesta tal cual (estado, cuerpo, `X-Total-Count`, `Location`…).

No tiene base de datos ni lógica de negocio: los permisos por rol los sigue comprobando cada microservicio.

## Qué recurso va a cada microservicio

| Ruta `/api/v1/...` | Microservicio |
|---|---|
| `escaletas`, `slots`, `pases`, `artistas` | ms-escaleta (8001) |
| `eventos`, `recintos`, `tipos-espacio`, `espacios`, `alquileres` | ms-espacios (8002) |
| `usuarios`, `proveedores`, `entradas` | ms-usuarios (8003) |
| `productos`, `pedidos` | ms-tienda (8004) |
| `estadisticas`, `recomendaciones`, `interacciones` | ms-analitica (8005) |

La tabla está en [config/settings.py](config/settings.py) (`RUTAS`). Las rutas internas entre servicios (`/internal/v1/...`) **no** se publican: solo se reenvía lo que empieza por `/api/v1/`.

## Autenticación

- **Sin token**: la petición pasa sin identidad. Las rutas públicas (catálogo, eventos, escaleta…) funcionan; las demás las rechaza el microservicio con `401`.
- **Token de Firebase**: se comprueban la firma (claves públicas de Google), la caducidad, el emisor y que sea del proyecto `subsonicfestivall3g1`. **No hace falta `firebase-claves.json`**: el gateway no tiene ninguna clave privada.
- **Token no válido o caducado**: `401` con `TOKEN_NO_VALIDO` o `TOKEN_CADUCADO`, sin llegar al microservicio.
- **Usuario recién creado en Firebase**: todavía no tiene rol, así que solo se envían `X-User-Id` y `X-User-Email`. Con eso puede hacer `POST /usuarios` (registro). ms-usuarios le asigna entonces el rol en Firebase, y **el front-end tiene que renovar el token** (`getIdToken(true)`) para que el nuevo token lleve el rol.

### Modo desarrollo (sin Firebase)

Con `MODO_AUTENTICACION=desarrollo` se aceptan además tokens con este formato, para probar desde Postman, scripts o tests sin iniciar sesión:

```
Authorization: Bearer dev:<uid>:<ROL>[:<email>]
Authorization: Bearer dev:uid-cliente-david:CLIENTE
Authorization: Bearer dev:uid-admin-jose:ADMIN
Authorization: Bearer dev:uid-nuevo::nuevo@example.com      (sin rol: para probar el registro)
```

Los tokens reales de Firebase siguen funcionando en este modo. **Nunca se activa en producción**: por defecto vale `firebase` y los tokens `dev:` se rechazan.

## Otras cosas que hace

- **`X-Correlation-Id`**: si no llega, lo crea; lo pasa al microservicio y lo devuelve en la respuesta, así se puede seguir una petición en los logs de todos los servicios.
- **CORS**: solo los orígenes de `CORS_ORIGENES` (por defecto el de Vite, `http://localhost:5173`). Los microservicios no necesitan configurar CORS para el front-end.
- **Errores propios** (formato común `{codigo, mensaje, detalles, correlation_id}`):

  | Estado | Código | Cuándo |
  |---|---|---|
  | 400 | `RUTA_NO_VALIDA` | La ruta contiene `.` o `..` |
  | 401 | `TOKEN_NO_VALIDO` / `TOKEN_CADUCADO` | Token mal formado, falso o caducado |
  | 404 | `RUTA_NO_ENCONTRADA` | Ningún microservicio atiende ese recurso |
  | 503 | `SERVICIO_NO_DISPONIBLE` | El microservicio está parado |
  | 504 | `TIEMPO_AGOTADO` | El microservicio tarda más de 15 s |

- **SSE de la escaleta** (`GET /escaletas/{evento_id}/cambios` con `Accept: text/event-stream`): se reenvía como flujo y sin límite de tiempo. Es público, así que funciona con `EventSource`, que no puede enviar la cabecera `Authorization`.
- **`GET /salud`**: estado del gateway y de cada microservicio (`ok`, `error 500` o `no disponible`).

## Ejecutar

Con todo el sistema (lo normal): el gateway está en el `docker-compose.global.yml` de la rama `infra`, en el puerto 8000.

Solo el gateway, con los microservicios ya arrancados en tu equipo:

```bash
cd gateway
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env               # Mac/Linux: cp .env.example .env
python main.py                       # http://localhost:8000/salud
```

Ejemplo:

```bash
curl http://localhost:8000/api/v1/eventos
curl -H "Authorization: Bearer dev:uid-cliente-david:CLIENTE" http://localhost:8000/api/v1/usuarios/me
```

## Desde el front-end

```js
const token = await auth.currentUser?.getIdToken();   // Firebase renueva el token solo cuando caduca
const respuesta = await fetch(`http://localhost:8000/api/v1${ruta}`, {
  ...opciones,
  headers: { "Content-Type": "application/json", ...(token && { Authorization: `Bearer ${token}` }) },
});
```

## Tests

```bash
pytest -q
```

37 tests sin Docker ni Firebase: los microservicios se sustituyen por un transporte simulado de httpx y la comprobación del token de Firebase por una función falsa.

Comprobado además con el sistema completo arrancado:
- Rutas públicas y privadas.
- Un cliente que se envía `X-User-Rol: ADMIN` recibe 403.
- Compra de una entrada.
- Las rutas `/internal` dan 404.
- Un token de Firebase falso da 401, comprobado contra las claves reales de Google.
- Los cambios de la escaleta llegan en directo por SSE a través del gateway.
