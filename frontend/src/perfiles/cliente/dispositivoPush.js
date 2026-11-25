// Registro de este navegador y limpieza previa al logout. Dueño: Luis.
import { eliminarDispositivo, obtenerPerfil, registrarDispositivo } from '../../api/usuarios';
import { alCerrarSesion } from '../../sesion/SesionContext';
import { getApp, SDK_VERSION } from 'firebase/app';
import '../../firebase/firebaseConfig';

const CLAVE = 'subsonic.dispositivoPush';
let quitarAlSalir = null;

function apuntarLimpieza(registro, restaurado = false) {
  quitarAlSalir?.();
  const quitar = alCerrarSesion(async () => {
    try {
      // Tras recargar, no dar de baja el dispositivo de una cuenta anterior usando otra sesión.
      if (restaurado && (await obtenerPerfil()).id !== registro.usuarioId) return;
      await desactivarPush(registro.usuarioId);
    } finally { quitar(); }
  });
  quitarAlSalir = quitar;
}
export function dispositivoActual(usuarioId) {
  try {
    const registro = JSON.parse(localStorage.getItem(CLAVE));
    return registro?.usuarioId === usuarioId ? registro : null;
  } catch { return null; }
}

export async function activarPush(usuarioId, prueba = false) {
  if (!usuarioId) throw new Error('Inicia sesión antes de registrar el dispositivo.');
  let registro = dispositivoActual(usuarioId);
  if (registro && registro.prueba !== prueba) {
    await desactivarPush(usuarioId); registro = null;
  }
  if (!registro || registro.prueba !== prueba) {
    let token;
    if (prueba) token = `dev-web-${crypto.randomUUID()}`;
    else {
      if (!('Notification' in window) || !('serviceWorker' in navigator)) {
        throw new Error('Este navegador no admite notificaciones push.');
      }
      const permiso = await Notification.requestPermission();
      if (permiso !== 'granted') throw new Error('No se ha concedido permiso para mostrar notificaciones.');
      const vapidKey = import.meta.env.VITE_FIREBASE_VAPID_KEY;
      if (!vapidKey) throw new Error('Falta configurar la clave pública VAPID para las notificaciones de este navegador.');
      const { getMessaging, getToken, isSupported } = await import('firebase/messaging');
      if (!(await isSupported())) throw new Error('Firebase Cloud Messaging no es compatible con este navegador.');
      const aplicacion = getApp();
      const parametros = new URLSearchParams({ config: JSON.stringify(aplicacion.options), sdk: SDK_VERSION });
      await navigator.serviceWorker.register(`/usuarios-notificaciones-sw.js?${parametros}`);
      const serviceWorkerRegistration = await navigator.serviceWorker.ready;
      token = await getToken(getMessaging(aplicacion), { vapidKey, serviceWorkerRegistration });
      if (!token) throw new Error('No se ha obtenido un token para este navegador.');
    }
    registro = { usuarioId, token, prueba };
  }
  await registrarDispositivo(registro.token);
  try { localStorage.setItem(CLAVE, JSON.stringify(registro)); }
  catch (error) { await eliminarDispositivo(registro.token); throw error; }
  apuntarLimpieza(registro);
  return registro;
}

/** Llamar antes de cerrar la sesión, mientras api() todavía puede obtener el token del usuario. */
export async function desactivarPush(usuarioId) {
  const registro = dispositivoActual(usuarioId);
  if (!registro) return;
  await eliminarDispositivo(registro.token);
  quitarAlSalir?.(); quitarAlSalir = null;
  localStorage.removeItem(CLAVE);
  if (!registro.prueba) {
    try {
      const { deleteToken, getMessaging } = await import('firebase/messaging');
      await deleteToken(getMessaging(getApp()));
    } catch { /* La baja en el backend ya está confirmada; no bloquear el cierre de sesión. */ }
  }
}

// Este módulo lo carga la aplicación al importar la pestaña: recupera la limpieza tras un refresh,
// incluso si después no se vuelve a visitar Notificaciones.
try {
  const guardado = JSON.parse(localStorage.getItem(CLAVE));
  if (guardado?.usuarioId && guardado?.token) apuntarLimpieza(guardado, true);
} catch { /* Navegación privada o registro inexistente. */ }
