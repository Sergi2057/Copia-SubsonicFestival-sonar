import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
const dobles = vi.hoisted(() => {
  const callbacks = new Set();
  return {
    callbacks,
    alCerrarSesion: vi.fn((callback) => {
      callbacks.add(callback);
      return vi.fn(() => callbacks.delete(callback));
    }),
    registrarDispositivo: vi.fn(), eliminarDispositivo: vi.fn(), obtenerPerfil: vi.fn(),
    getToken: vi.fn(), deleteToken: vi.fn(), isSupported: vi.fn(),
  };
});
vi.mock('../../api/usuarios', () => ({ registrarDispositivo: dobles.registrarDispositivo,
  eliminarDispositivo: dobles.eliminarDispositivo, obtenerPerfil: dobles.obtenerPerfil }));
vi.mock('../../sesion/SesionContext', () => ({ alCerrarSesion: dobles.alCerrarSesion }));
vi.mock('../../firebase/firebaseConfig', () => ({}));
vi.mock('firebase/app', () => ({ getApp: () => ({ options: { projectId: 'prueba' } }), SDK_VERSION: '12.12.0' }));
vi.mock('firebase/messaging', () => ({ getMessaging: () => ({}), getToken: dobles.getToken,
  deleteToken: dobles.deleteToken, isSupported: dobles.isSupported }));

describe('Dispositivo push y enganche de cierre de sesión', () => {
  beforeEach(() => {
    vi.resetModules(); vi.clearAllMocks(); localStorage.clear(); dobles.callbacks.clear();
    dobles.registrarDispositivo.mockResolvedValue(null); dobles.eliminarDispositivo.mockResolvedValue(null);
    dobles.obtenerPerfil.mockResolvedValue({ id: 'u1' }); dobles.getToken.mockResolvedValue('token-fcm:real');
    dobles.isSupported.mockResolvedValue(true);
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
  it('registra el token de prueba y lo elimina al ejecutar la limpieza autenticada', async () => {
    const push = await import('./dispositivoPush');
    const registro = await push.activarPush('u1', true);
    expect(dobles.registrarDispositivo).toHaveBeenCalledWith(registro.token);
    expect(dobles.callbacks.size).toBe(1);
    await [...dobles.callbacks][0]();
    expect(dobles.eliminarDispositivo).toHaveBeenCalledWith(registro.token);
    expect(dobles.callbacks.size).toBe(0);
    expect(push.dispositivoActual('u1')).toBeNull();
  });
  it('la baja manual desapunta la limpieza y no se repite al salir', async () => {
    const push = await import('./dispositivoPush');
    await push.activarPush('u1', true);
    await push.desactivarPush('u1');
    await push.desactivarPush('u1');
    expect(dobles.callbacks.size).toBe(0);
    expect(dobles.eliminarDispositivo).toHaveBeenCalledTimes(1);
  });
  it('volver a registrar sustituye el enganche anterior', async () => {
    const push = await import('./dispositivoPush');
    await push.activarPush('u1', true);
    const quitarAnterior = dobles.alCerrarSesion.mock.results[0].value;
    await push.activarPush('u1', true);
    expect(quitarAnterior).toHaveBeenCalled();
    expect(dobles.callbacks.size).toBe(1);
  });
  it('conserva el registro y permite reintentar una baja fallida', async () => {
    const push = await import('./dispositivoPush');
    await push.activarPush('u1', true);
    dobles.eliminarDispositivo.mockRejectedValueOnce(new Error('Sin conexión'));
    await expect(push.desactivarPush('u1')).rejects.toThrow('Sin conexión');
    expect(push.dispositivoActual('u1')).not.toBeNull();
    await push.desactivarPush('u1');
    expect(push.dispositivoActual('u1')).toBeNull();
  });
  it('recupera la limpieza tras recargar y comprueba el propietario', async () => {
    localStorage.setItem('subsonic.dispositivoPush', JSON.stringify({ usuarioId: 'u1', token: 't1', prueba: true }));
    await import('./dispositivoPush');
    dobles.obtenerPerfil.mockResolvedValue({ id: 'otro' });
    await [...dobles.callbacks][0]();
    expect(dobles.eliminarDispositivo).not.toHaveBeenCalled();
    expect(dobles.callbacks.size).toBe(0);
  });
  it('usa Firebase y el service worker para un registro real con permiso', async () => {
    vi.stubEnv('VITE_FIREBASE_VAPID_KEY', 'clave-publica');
    vi.stubGlobal('Notification', { requestPermission: vi.fn().mockResolvedValue('granted') });
    const registroSW = {};
    const registrarSW = vi.fn().mockResolvedValue(registroSW);
    vi.stubGlobal('navigator', { serviceWorker: { register: registrarSW, ready: Promise.resolve(registroSW) } });
    const push = await import('./dispositivoPush');
    await push.activarPush('u1');
    expect(registrarSW.mock.calls[0][0]).toContain('/usuarios-notificaciones-sw.js?');
    expect(dobles.getToken).toHaveBeenCalledWith({}, { vapidKey: 'clave-publica', serviceWorkerRegistration: registroSW });
    expect(dobles.registrarDispositivo).toHaveBeenCalledWith('token-fcm:real');
    await push.desactivarPush('u1');
    expect(dobles.deleteToken).toHaveBeenCalled();
  });
});
