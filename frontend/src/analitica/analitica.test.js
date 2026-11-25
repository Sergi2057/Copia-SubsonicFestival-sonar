// src/analitica/analitica.test.js — formato de cifras y envío de interacciones en lote
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/analitica', () => ({ registrarInteracciones: vi.fn() }));

const { registrarInteracciones } = await import('../api/analitica');
const { registrarInteraccion, enviarPendientes, _reiniciar } = await import('./interacciones');
const { euros, legible, numero, porcentaje, variacion } = await import('./formato');
const { ErrorApi } = await import('../api/cliente');

const sinEspacios = (texto) => texto.replace(/\s/g, ' ');

describe('formato', () => {
  it('formatea cifras en español', () => {
    expect(numero(15688)).toBe('15.688');
    expect(sinEspacios(euros(2431500))).toBe('2.431.500 €');
    expect(porcentaje(0.82)).toBe('82 %');
    expect(variacion(0.15)).toBe('+15 %');
    expect(variacion(-0.08)).toBe('−8 %');
    expect(legible('FOOD_BEVERAGE')).toBe('Food beverage');
  });

  it('muestra un guion cuando falta el dato', () => {
    expect(numero(undefined)).toBe('—');
    expect(euros(null)).toBe('—');
    expect(porcentaje(undefined)).toBe('—');
  });
});

describe('interacciones', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    _reiniciar();
    localStorage.clear();
    vi.mocked(registrarInteracciones).mockReset().mockResolvedValue(null);
  });
  afterEach(() => vi.useRealTimers());

  it('acumula las interacciones y las envía juntas a los 10 segundos', async () => {
    registrarInteraccion('VER_EVENTO', 'evento-belgium');
    registrarInteraccion('BUSCAR', 'techno');

    expect(registrarInteracciones).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(10_000);

    expect(registrarInteracciones).toHaveBeenCalledTimes(1);
    const lote = vi.mocked(registrarInteracciones).mock.calls[0][0];
    expect(lote.interacciones.map((i) => [i.accion, i.objetivo_id])).toEqual([
      ['VER_EVENTO', 'evento-belgium'], ['BUSCAR', 'techno'],
    ]);
    expect(lote.sesion_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(lote.interacciones[0].fecha).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it('mantiene el mismo identificador de sesión entre envíos', async () => {
    registrarInteraccion('VER_ARTISTA', 'a1');
    await enviarPendientes();
    registrarInteraccion('VER_ARTISTA', 'a2');
    await enviarPendientes();

    const [primero, segundo] = vi.mocked(registrarInteracciones).mock.calls.map(([l]) => l.sesion_id);
    expect(primero).toBe(segundo);
  });

  it('envía en cuanto hay 100 sin esperar', () => {
    for (let i = 0; i < 100; i += 1) registrarInteraccion('VER_PRODUCTO', `p${i}`);

    expect(registrarInteracciones).toHaveBeenCalledTimes(1);
    expect(vi.mocked(registrarInteracciones).mock.calls[0][0].interacciones).toHaveLength(100);
  });

  it('ignora acciones desconocidas o sin objetivo', async () => {
    registrarInteraccion('COMPRAR', 'x');
    registrarInteraccion('VER_EVENTO', '');
    await vi.advanceTimersByTimeAsync(10_000);

    expect(registrarInteracciones).not.toHaveBeenCalled();
  });

  it('si no hay conexión las guarda para el siguiente envío', async () => {
    vi.mocked(registrarInteracciones).mockRejectedValueOnce(new ErrorApi(0, 'SIN_CONEXION', 'sin red'));
    registrarInteraccion('VER_EVENTO', 'e1');
    await enviarPendientes();
    await vi.advanceTimersByTimeAsync(10_000);

    expect(registrarInteracciones).toHaveBeenCalledTimes(2);
    expect(vi.mocked(registrarInteracciones).mock.calls[1][0].interacciones[0].objetivo_id).toBe('e1');
  });
});
