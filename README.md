# 🎵 Subsonic Festival · Arquitectura de microservicios (ASEE · GA02)

Plataforma web para gestionar un festival de música electrónica con ediciones en varios países: venta de entradas con QR, cartel y horarios en directo, tienda de merchandising, alquiler de espacios para proveedores, control de acceso y estadísticas con recomendaciones.

Práctica 2 de la asignatura (Universidad de Extremadura, curso 2025-2026). El monolito de la práctica 1 se ha dividido en **5 microservicios** que se comunican por **REST** (síncrono) y por **eventos en RabbitMQ** (asíncrono), con un **API Gateway** como única entrada del front-end en React.

**Equipo GA02:** Paula Jiménez Cruz, Pedro Fernández, Luis Cansado y Sergio Almodóvar.

---

## 🧩 Arquitectura

```
                  React (frontend, :5173)
                           │  HTTP + token de Firebase
                           ▼
                  API Gateway (gateway, :8000)
        ┌──────────┬───────┴──┬───────────┬────────────┐
        ▼          ▼          ▼           ▼            ▼
  ms-escaleta  ms-espacios  ms-usuarios  ms-tienda  ms-analitica
    :8001        :8002        :8003       :8004        :8005
  PostgreSQL   PostgreSQL   PostgreSQL  PostgreSQL     MongoDB
   + Redis                                             + Redis
        └──────────┴──── RabbitMQ (exchange subsonic.events) ────┘
```

| Carpeta | Qué hace | Tecnología | Responsable |
|---|---|---|---|
| [gateway/](gateway/) | Única entrada: verifica el token de Firebase, añade la identidad y enruta a cada servicio. También reenvía el SSE del cartel en directo | FastAPI, httpx, Firebase Admin | Paula |
| [ms-usuarios/](ms-usuarios/) | Usuarios y proveedores, entradas con QR firmado, validación en la puerta, favoritos, notificaciones push | FastAPI, PostgreSQL, Alembic, Firebase Admin | Luis |
| [ms-espacios/](ms-espacios/) | Eventos, recintos, tarifas y aforo, espacios y alquileres | FastAPI, PostgreSQL, Alembic | Pedro |
| [ms-escaleta/](ms-escaleta/) | Artistas, slots, pases y publicación de la escaleta, cambios en directo (SSE), vídeos de YouTube | FastAPI, PostgreSQL, Redis, Alembic | Sergio |
| [ms-tienda/](ms-tienda/) | Catálogo, tallas y stock, pedidos con envío o recogida en un evento | FastAPI, PostgreSQL, Alembic | Sergio |
| [ms-analitica/](ms-analitica/) | Estadísticas para el administrador y recomendaciones de eventos, artistas y espacios | FastAPI, MongoDB, Redis | Sergio |
| [frontend/](frontend/) | Aplicación web (visitante, cliente, proveedor, administrador y staff) | React 19, Vite, React Router, Vitest | Todos, cada uno sus pantallas |
| [infra/](infra/) | RabbitMQ, `docker-compose` de todo el sistema, datos de prueba y prueba de integración | Docker Compose, RabbitMQ | Paula |
| [docs/](docs/) | Memoria de la práctica 1 y contratos OpenAPI de los 5 servicios | OpenAPI 3 | Todos |

Cada microservicio tiene su propia base de datos y su contrato en `openapi.yaml` (copia en [docs/openapi/](docs/openapi/)). Ningún servicio lee la base de datos de otro: cuando necesita datos ajenos, los pide por REST o guarda una réplica a partir de los eventos que publica su dueño (`usuarios.entrada.comprada`, `espacios.evento.cancelado`, `escaleta.publicada`…).

---

## 🚀 Arrancar el sistema completo

**Requisitos:** Docker Desktop, Python 3.10 o superior y Node.js 20 o superior.

### 1. Microservicios, gateway y RabbitMQ

```bash
cd infra
copy .env.example .env                                      # Mac/Linux: cp .env.example .env
docker compose -f docker-compose.global.yml up -d --build
python servicios.py poblar                                  # datos de prueba
```

- Gateway: http://localhost:8000/api/v1. Documentación de cada servicio en http://localhost:8001/docs … http://localhost:8005/docs.
- Panel de RabbitMQ: http://localhost:15672 (usuario y contraseña `subsonic`).
- Para parar: `docker compose -f docker-compose.global.yml down`. Añade `-v` para borrar también los datos.

> **Clave de YouTube:** el reproductor de música necesita `YOUTUBE_API_KEY` en `infra/.env`. Sin ella todo funciona, pero los artistas aparecen sin vídeos.

### 2. Aplicación web

```bash
cd frontend
npm install
copy .env.example .env                                      # Mac/Linux: cp .env.example .env
npm run dev                                                 # http://localhost:5173
```

### 3. Usuarios de prueba

Con `VITE_MODO_DESARROLLO=true` (viene así en `.env.example`), **Iniciar sesión** muestra los botones **«Entrar como…»**. Funcionan sin Firebase, gracias a los tokens de desarrollo que acepta el gateway en local:

| Usuario | Rol | Qué puede hacer |
|---|---|---|
| David | Cliente | Comprar entradas y merchandising, ver su QR, favoritos, recomendaciones, notificaciones |
| Ana | Proveedora | Buscar y alquilar espacios, ver sus alquileres y espacios recomendados |
| José | Administrador | Eventos, recintos, tarifas, espacios, escaleta, tienda, usuarios, entradas y estadísticas |
| Lucía | Staff | Validar entradas en la puerta |

> **Login real con Google o email:** las claves de Firebase no están en el repositorio. Para usarlo, deja `firebase-claves.json` en `infra/secretos/` como se explica en [infra/secretos/LEEME.md](infra/secretos/LEEME.md).

---

## ✅ Pruebas

| Qué | Cómo |
|---|---|
| Tests de cada microservicio y del gateway | `cd ms-usuarios` (o el que sea) → `pip install -r requirements.txt pytest` → `pytest -q` |
| Tests del frontend (163) | `cd frontend` → `npm test` · `npm run lint` · `npm run build` |
| **Prueba de integración** de los 6 flujos que cruzan servicios | Con el sistema arrancado y poblado: `cd infra` → `python prueba_integracion.py` |

La prueba de integración comprueba:
1. Compra de una entrada: ms-espacios confirma la reserva de aforo y ms-analitica registra la venta.
2. Cambio en la escaleta: llega el aviso en directo (SSE) y la notificación push a quien tiene ese artista en favoritos.
3. Cancelación de un evento: se cancelan pases y entradas, y la tienda rechaza recogidas en ese evento.
4. Borrado de una cuenta (RGPD): el resto de servicios anonimiza sus datos.
5. Mensaje que falla: acaba en la cola de errores `subsonic.dlq` tras los reintentos.
6. Seguridad del gateway: rutas públicas y privadas, tokens falsos, cabeceras inventadas y rutas `/internal` cerradas.

---

## 📚 Más información

- [infra/README.md](infra/README.md): RabbitMQ, mensajería común, entorno completo y prueba de integración.
- [gateway/README.md](gateway/README.md): autenticación y enrutado.
- README de cada microservicio: su modelo, sus eventos y cómo ejecutarlo por separado.
- [frontend/README.md](frontend/README.md): organización del código y reparto de pantallas.

El monolito de la práctica 1 (carpetas `backend/` y `subsonicFestival/`) se ha retirado de esta rama. Sigue disponible en el historial de git.
