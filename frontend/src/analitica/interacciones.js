// src/analitica/interacciones.js — Dueña: Paula
// Registro de lo que hace el usuario (eventos y artistas vistos, búsquedas…) para las recomendaciones.
// Las interacciones se acumulan y se envían juntas a POST /interacciones (ms-analitica):
// cada 10 segundos, al llegar a 100 o al ocultar la pestaña.
//
// Uso desde cualquier pantalla (una línea, no hay que esperar a nada):
//   import { registrarInteraccion } from '../../analitica/interacciones';
//   registrarInteraccion('VER_EVENTO', evento.id);      // VER_EVENTO | VER_ARTISTA | VER_PRODUCTO | BUSCAR
//   registrarInteraccion('BUSCAR', textoBuscado);
import { registrarInteracciones } from '../api/analitica';

export const ACCIONES = ['VER_EVENTO', 'VER_ARTISTA', 'VER_PRODUCTO', 'BUSCAR'];
const MAXIMO_LOTE = 100;      // máximo que acepta el backend en un envío
const ESPERA_MS = 10_000;
const CLAVE_SESION = 'subsonic.sesionAnalitica';

let pendientes = [];
let temporizador = null;

/** Identificador anónimo del navegador, para los visitantes sin cuenta. */
export function idSesion() {
  try {
    let id = localStorage.getItem(CLAVE_SESION);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(CLAVE_SESION, id);
    }
    return id;
  } catch {
    return undefined;   // sin almacenamiento (modo privado estricto): se envía sin sesión
  }
}

export function registrarInteraccion(accion, objetivoId) {
  if (!ACCIONES.includes(accion) || objetivoId === undefined || objetivoId === null || objetivoId === '') return;
  pendientes.push({ accion, objetivo_id: String(objetivoId).slice(0, 200), fecha: new Date().toISOString() });
  if (pendientes.length >= MAXIMO_LOTE) enviarPendientes();
  else if (!temporizador) temporizador = setTimeout(enviarPendientes, ESPERA_MS);
}

/** Envía lo acumulado. Si falla la red se reintenta en el siguiente envío; si el backend lo rechaza, se descarta. */
export async function enviarPendientes() {
  clearTimeout(temporizador);
  temporizador = null;
  if (pendientes.length === 0) return;
  const lote = pendientes.slice(0, MAXIMO_LOTE);
  pendientes = pendientes.slice(MAXIMO_LOTE);
  try {
    await registrarInteracciones({ sesion_id: idSesion(), interacciones: lote });
  } catch (error) {
    if (error?.codigo === 'SIN_CONEXION') pendientes = [...lote, ...pendientes].slice(0, MAXIMO_LOTE);
  }
  if (pendientes.length > 0 && !temporizador) temporizador = setTimeout(enviarPendientes, ESPERA_MS);
}

/** Solo para los tests. */
export function _reiniciar() {
  clearTimeout(temporizador);
  temporizador = null;
  pendientes = [];
}

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') enviarPendientes();
  });
}
