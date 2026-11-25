// src/api/cliente.test.js
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, configurarToken, ErrorApi, URL_API } from './cliente';

function respuesta(status, cuerpo, cabeceras = {}) {
  return new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), { status, headers: cabeceras });
}

describe('api()', () => {
  let fetchFalso;

  beforeEach(() => {
    fetchFalso = vi.spyOn(globalThis, 'fetch');
    configurarToken(async () => 'dev:uid-cliente-david:CLIENTE');
  });

  it('llama al gateway con el token y devuelve el JSON', async () => {
    fetchFalso.mockResolvedValue(respuesta(200, [{ id: 'evento-belgium' }]));

    const datos = await api('/eventos');

    expect(datos).toEqual([{ id: 'evento-belgium' }]);
    const [url, opciones] = fetchFalso.mock.calls[0];
    expect(url).toBe(`${URL_API}/eventos`);
    expect(opciones.headers.Authorization).toBe('Bearer dev:uid-cliente-david:CLIENTE');
  });

  it('sin sesión no envía Authorization', async () => {
    configurarToken(async () => null);
    fetchFalso.mockResolvedValue(respuesta(200, []));

    await api('/productos');

    expect(fetchFalso.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it('añade los parámetros y se salta los vacíos', async () => {
    fetchFalso.mockResolvedValue(respuesta(200, []));

    await api('/eventos', { parametros: { pais: 'Bélgica', tag: ['techno', 'house'], desde: '', estado: null } });

    const url = new URL(fetchFalso.mock.calls[0][0]);
    expect(url.searchParams.get('pais')).toBe('Bélgica');
    expect(url.searchParams.getAll('tag')).toEqual(['techno', 'house']);
    expect(url.searchParams.has('desde')).toBe(false);
    expect(url.searchParams.has('estado')).toBe(false);
  });

  it('envía el cuerpo como JSON', async () => {
    fetchFalso.mockResolvedValue(respuesta(201, { id: 'pedido-1' }));

    await api('/pedidos', { metodo: 'POST', cuerpo: { entrega: 'DOMICILIO' } });

    const opciones = fetchFalso.mock.calls[0][1];
    expect(opciones.method).toBe('POST');
    expect(opciones.headers['Content-Type']).toBe('application/json');
    expect(opciones.body).toBe('{"entrega":"DOMICILIO"}');
  });

  it('devuelve el total de X-Total-Count si se pide', async () => {
    fetchFalso.mockResolvedValue(respuesta(200, [{}, {}], { 'X-Total-Count': '42' }));

    expect(await api('/productos', { conTotal: true })).toEqual({ datos: [{}, {}], total: 42 });
  });

  it('204 devuelve null', async () => {
    fetchFalso.mockResolvedValue(respuesta(204));

    expect(await api('/usuarios/me/favoritos/x', { metodo: 'DELETE' })).toBeNull();
  });

  it('201 sin cuerpo devuelve null', async () => {
    fetchFalso.mockResolvedValue(respuesta(201));

    expect(await api('/usuarios/me/dispositivos', { metodo: 'POST', cuerpo: { fcm_token: 't' } })).toBeNull();
  });

  it('un error del backend se convierte en ErrorApi con su código', async () => {
    fetchFalso.mockResolvedValue(respuesta(409, { codigo: 'SIN_STOCK', mensaje: 'No hay stock de la talla M' }));

    const error = await api('/pedidos', { metodo: 'POST', cuerpo: {} }).catch((e) => e);

    expect(error).toBeInstanceOf(ErrorApi);
    expect(error).toMatchObject({ status: 409, codigo: 'SIN_STOCK', message: 'No hay stock de la talla M' });
  });

  it('con 401 pide un token nuevo y reintenta una vez', async () => {
    const obtenerToken = vi.fn(async (forzar) => (forzar ? 'token-nuevo' : 'token-caducado'));
    configurarToken(obtenerToken);
    fetchFalso.mockResolvedValueOnce(respuesta(401, { codigo: 'TOKEN_CADUCADO' }))
      .mockResolvedValueOnce(respuesta(200, { nombre: 'David' }));

    expect(await api('/usuarios/me')).toEqual({ nombre: 'David' });
    expect(fetchFalso.mock.calls[1][1].headers.Authorization).toBe('Bearer token-nuevo');
  });

  it('sin conexión lanza SIN_CONEXION', async () => {
    fetchFalso.mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(api('/eventos')).rejects.toMatchObject({ status: 0, codigo: 'SIN_CONEXION' });
  });
});
