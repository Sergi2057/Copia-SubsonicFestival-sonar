import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
// Probar con el cliente HTTP real: este endpoint responde 201 sin JSON.
describe('Contrato HTTP real del registro de dispositivos', () => {
  beforeEach(() => vi.resetModules());
  afterEach(() => vi.unstubAllGlobals());
  it('acepta el 201 vacío sin confundirlo con un fallo del registro', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 201 })));
    const { registrarDispositivo } = await import('./usuarios');
    await expect(registrarDispositivo('token:FCM')).resolves.toBeNull();
    expect(fetch.mock.calls[0][1].body).toBe(JSON.stringify({ fcm_token: 'token:FCM', plataforma: 'WEB' }));
  });
  it('conserva los errores de autorización del backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => new Response(
      JSON.stringify({ codigo: 'SIN_PERMISO', mensaje: 'Cuenta desactivada' }), { status: 403 },
    )));
    const { registrarDispositivo } = await import('./usuarios');
    await expect(registrarDispositivo('token')).rejects.toMatchObject({ status: 403, codigo: 'SIN_PERMISO' });
  });
  it('conserva el error de conexión', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network error')));
    const { registrarDispositivo } = await import('./usuarios');
    await expect(registrarDispositivo('token')).rejects.toMatchObject({ codigo: 'SIN_CONEXION' });
  });
});
