# frontend · Subsonic Festival

Aplicación web en React 19 + Vite, a partir del front-end del monolito. Ahora **solo habla con el API Gateway** (`http://localhost:8000/api/v1`), que reenvía cada petición a su microservicio.

## Arrancar

1. Arranca el sistema completo desde la carpeta `infra`:

   ```bash
   docker compose -f docker-compose.global.yml up -d --build
   python servicios.py poblar
   ```

2. En esta carpeta:

   ```bash
   npm install
   copy .env.example .env        # Mac/Linux: cp .env.example .env
   npm run dev                   # http://localhost:5173
   ```

Con `VITE_MODO_DESARROLLO=true`, el modal de **Iniciar sesión** muestra **«Entrar como…»** con los usuarios de prueba. Funcionan sin Firebase gracias a los tokens `dev:` del gateway:

| Usuario | Rol |
|---|---|
| David | cliente |
| Ana | proveedora |
| José | administrador |
| Lucía | staff |

El login real con Google o con email también funciona, pero para que el token lleve el rol, ms-usuarios necesita `firebase-claves.json` (ver `infra/README.md`).

```bash
npm test          # tests (Vitest + Testing Library)
npm run lint      # ESLint
npm run build     # comprobar que compila
```

## Cómo está organizado

| Carpeta | Qué hay |
|---|---|
| `src/api/` | `cliente.js` (la función `api()` que llama al gateway con el token) y **un archivo por microservicio** con sus llamadas |
| `src/sesion/` | `useSesion()`: quién ha iniciado sesión, su perfil (`GET /usuarios/me`) y su rol |
| `src/perfiles/` | `/perfil`. Un panel por rol (cliente, proveedor, admin, staff) y **cada pestaña es un componente aparte** |
| `src/pages/` | Páginas públicas: Inicio (3 bloques), Calendario, Evento, Tienda, Artista |
| `src/components/` | Barra de navegación, login, pie y `Pendiente` |
| `src/analitica/` | Piezas de las pantallas de analítica (Paula) y `registrarInteraccion()` para las recomendaciones |

Cada pantalla que falta muestra el recuadro **«Pendiente · <dueño>»**. La cabecera de su archivo dice qué hay que hacer, qué rutas de la API usar y dónde está el código antiguo.

### Llamar a la API

```js
import { api } from './cliente';
export const listarEntradas = () => api('/usuarios/me/entradas');                    // en src/api/usuarios.js
export const comprar = (datos) => api('/usuarios/me/entradas', { metodo: 'POST', cuerpo: datos });
```

```jsx
import { listarEntradas } from '../../api/usuarios';
import { useSesion } from '../../sesion/SesionContext';

const { perfil, rol } = useSesion();   // rol: 'cliente' | 'proveedor' | 'admin' | 'staff'
try {
  setEntradas(await listarEntradas());
} catch (error) {
  setError(error.message);             // ErrorApi: error.status, error.codigo ('SIN_STOCK'…), error.message
}
```

Nunca uses `fetch` directamente ni pongas `http://localhost:8000` en un componente: así el token, los errores y la URL están en un único sitio.

### Registrar lo que ve el usuario (para las recomendaciones)

ms-analitica recomienda eventos y artistas según lo que cada usuario mira y busca. Basta **una línea** donde ocurre; se acumulan y se envían juntas cada 10 segundos (no hay que esperar ni tratar errores):

```js
import { registrarInteraccion } from '../../analitica/interacciones';

registrarInteraccion('VER_EVENTO', evento.id);       // DetallesEvento (Pedro), al cargar el evento
registrarInteraccion('BUSCAR', texto);               // BuscadorEventos (Pedro), al buscar
registrarInteraccion('VER_ARTISTA', artista.id);     // Artista (Sergio), al cargar el artista
registrarInteraccion('VER_PRODUCTO', producto.id);   // Tienda (Sergio), al abrir un producto
```

## Reparto: un dueño por archivo

| Quién | Archivos |
|---|---|
| **Paula** (base y ms-analitica) | `api/cliente.js`, `api/analitica.js`, `sesion/`, `App.jsx`, `components/NavBar.jsx`, `ModalLogin.jsx`, `perfiles/Perfil.jsx`, `PanelPerfil.jsx`, `CompletarRegistro.jsx`, las listas de pestañas (`PerfilCliente/Proveedor/Admin/Staff.jsx`), `pages/Inicio/Inicio.jsx`, `pages/Inicio/Recomendaciones.jsx`, `perfiles/cliente/Resumen.jsx`, `perfiles/admin/Resumen.jsx`, `perfiles/admin/Estadisticas.jsx` y `perfiles/admin/estadisticas/`, `perfiles/proveedor/EspaciosRecomendados.jsx`, `analitica/` |
| **Pedro** (ms-espacios) | `api/espacios.js`, `pages/Inicio/BuscadorEventos.jsx`, `pages/Calendario/`, `pages/Evento/DetallesEvento.jsx`, `perfiles/proveedor/Alquilar.jsx`, `perfiles/proveedor/MisAlquileres.jsx`, `perfiles/admin/Eventos.jsx`, `perfiles/admin/Espacios.jsx` |
| **Luis** (ms-usuarios) | `api/usuarios.js`, `pages/Evento/ModalCheckout.jsx`, `perfiles/comun/DatosPersonales.jsx`, `perfiles/cliente/MisEntradas.jsx`, `perfiles/cliente/Favoritos.jsx`, `perfiles/cliente/Notificaciones.jsx`, `perfiles/admin/Usuarios.jsx`, `perfiles/admin/Entradas.jsx`, `perfiles/staff/ValidarEntradas.jsx` |
| **Sergio** (ms-tienda y ms-escaleta) | `api/tienda.js`, `api/escaleta.js`, `pages/Tienda/`, `pages/Artista/`, `pages/Inicio/Musica.jsx`, `pages/Evento/CartelEvento.jsx`, `perfiles/cliente/MisPedidos.jsx`, `perfiles/admin/Escaleta.jsx`, `perfiles/admin/Tienda.jsx` |

### Reglas para no pisarnos

1. **Solo modificas tus archivos.** Las rutas (`App.jsx`) y las pestañas de cada perfil ya están todas creadas. Si necesitas una nueva, pídesela a Paula.
2. **Estilos:** no cambies las reglas que ya existen en `main.css` ni en los CSS de `perfiles/`, porque los usan las pantallas de los demás. Puedes **usar** sus clases. Lo nuevo va en tu propio CSS junto a tu componente (`MisEntradas.css`), importado desde él.
3. **Funciones de la API de otro servicio:** si tu pantalla necesita llamar a otro servicio, la función la añade su dueño en su archivo. Estas se piden ya y van **el primer día**:
   - Luis, en `api/usuarios.js`: `listarFavoritos`, `anadirFavorito` y `quitarFavorito`. Las usa Sergio en `CartelEvento` y en `Artista`.
   - Pedro, en `api/espacios.js`: `listarEspacios(filtros)` y `listarTarifas(eventoId)`. Las usan Sergio (escenarios del evento para crear slots), Pedro y Luis (la tarifa que se compra).
   - `listarEventos` ya existe. La usan Luis (control de acceso) y Sergio (evento de recogida en la tienda).
4. **Contrato de la ficha de evento:** Pedro coloca `<CartelEvento eventoId={id} />` (de Sergio) y `<ModalCheckout abierto onCerrar eventoId tarifa />` (de Luis). `tarifa` es un objeto de `GET /eventos/{id}/tarifas`. No cambiéis esos props sin avisar.

### Ramas

Durante el desarrollo, cada uno trabajó en su rama a partir de `frontend` (`frontend-espacios`, `frontend-usuarios`, `frontend-tienda` y `frontend-analitica`) y unió su trabajo con un pull request a `frontend` (PR #1 a #12). Al terminar, `frontend` se unió a `main` junto con el resto de ramas.

## Tests

Pon los tests junto al componente (`MisEntradas.test.jsx`). Para que no dependan del backend, simula `src/api/*` con `vi.mock`. Tienes un ejemplo completo en [src/perfiles/Perfil.test.jsx](src/perfiles/Perfil.test.jsx) (pantalla, sesión y API simulada) y otro en [src/api/cliente.test.js](src/api/cliente.test.js).

Mínimo por pantalla: que pinte los datos que devuelve la API, la acción principal (comprar, guardar, borrar…) y que muestre el mensaje de un error del backend.
