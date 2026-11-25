import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './cliente';
import {
  cambiarEstadoAlquiler, cambiarEstadoEvento, crearEvento, crearEspacio, crearTarifa, listarAlquileres,
  listarEspacios, listarTarifas, modificarEvento, modificarEspacio, modificarTarifa, solicitarAlquiler,
} from './espacios';

vi.mock('./cliente', () => ({ api: vi.fn() }));

describe('API de espacios', () => {
  beforeEach(() => vi.mocked(api).mockReset());

  it('busca espacios con filtros y devuelve el total', async () => {
    const resultado = { datos: [{ id: 'escenario-1' }], total: 1 };
    const filtros = { evento_id: 'evento-1', tipo: 'ESCENARIO', disponible: true };
    vi.mocked(api).mockResolvedValue(resultado);

    expect(await listarEspacios(filtros)).toEqual(resultado);
    expect(api).toHaveBeenCalledWith('/espacios', { parametros: filtros, conTotal: true });
  });

  it('lista las tarifas de un evento', async () => {
    const tarifas = [{ id: 'tarifa-1', tipo_pase: 'DAY', precio: 89 }];
    vi.mocked(api).mockResolvedValue(tarifas);

    expect(await listarTarifas('evento/1')).toEqual(tarifas);
    expect(api).toHaveBeenCalledWith('/eventos/evento%2F1/tarifas');
  });

  it('propaga errores del gateway', async () => {
    const error = Object.assign(new Error('Evento no encontrado'), { status: 404 });
    vi.mocked(api).mockRejectedValue(error);

    await expect(listarTarifas('evento-1')).rejects.toBe(error);
  });

  it('envía las operaciones de gestión con las rutas, métodos y cuerpos del contrato', async () => {
    const evento = { titulo: 'Festival' };
    const espacio = { nombre: 'Puesto' };
    const tarifa = { tipo_pase: 'DAY', precio: 89, cupo_total: 200 };
    const alquiler = { fecha_inicio: '2026-07-14T08:00:00Z', fecha_fin: '2026-07-15T18:00:00Z' };

    await crearEvento(evento);
    expect(api).toHaveBeenLastCalledWith('/eventos', { metodo: 'POST', cuerpo: evento });
    await modificarEvento('evento/1', evento);
    expect(api).toHaveBeenLastCalledWith('/eventos/evento%2F1', { metodo: 'PUT', cuerpo: evento });
    await cambiarEstadoEvento('evento/1', 'CANCELADO', 'Alerta meteorológica');
    expect(api).toHaveBeenLastCalledWith('/eventos/evento%2F1', {
      metodo: 'PATCH', cuerpo: { estado: 'CANCELADO', motivo: 'Alerta meteorológica' },
    });

    await crearEspacio(espacio);
    expect(api).toHaveBeenLastCalledWith('/espacios', { metodo: 'POST', cuerpo: espacio });
    await modificarEspacio('espacio/1', espacio);
    expect(api).toHaveBeenLastCalledWith('/espacios/espacio%2F1', { metodo: 'PUT', cuerpo: espacio });
    await crearTarifa('evento/1', tarifa);
    expect(api).toHaveBeenLastCalledWith('/eventos/evento%2F1/tarifas', { metodo: 'POST', cuerpo: tarifa });
    await modificarTarifa('evento/1', 'tarifa/1', tarifa);
    expect(api).toHaveBeenLastCalledWith('/eventos/evento%2F1/tarifas/tarifa%2F1', { metodo: 'PUT', cuerpo: tarifa });

    await solicitarAlquiler('espacio/1', alquiler);
    expect(api).toHaveBeenLastCalledWith('/espacios/espacio%2F1/alquileres', { metodo: 'POST', cuerpo: alquiler });
    await listarAlquileres({ estado: 'PENDIENTE' });
    expect(api).toHaveBeenLastCalledWith('/alquileres', { parametros: { estado: 'PENDIENTE' }, conTotal: true });
    await cambiarEstadoAlquiler('alquiler/1', 'APROBADO');
    expect(api).toHaveBeenLastCalledWith('/alquileres/alquiler%2F1', {
      metodo: 'PATCH', cuerpo: { estado: 'APROBADO' },
    });
  });
});
