// src/perfiles/admin/Analitica.test.jsx — pestañas «Visión General» y «Estadísticas» del admin
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorApi } from '../../api/cliente';

vi.mock('../../api/analitica', () => ({
  obtenerResumen: vi.fn(), obtenerVentas: vi.fn(), obtenerOcupacion: vi.fn(), obtenerAfluencia: vi.fn(),
  obtenerEstadisticasTienda: vi.fn(), obtenerArtistasPopulares: vi.fn(),
}));
vi.mock('../../api/espacios', () => ({ listarEventos: vi.fn() }));

const api = await import('../../api/analitica');
const { listarEventos } = await import('../../api/espacios');
const { default: Resumen } = await import('./Resumen');
const { default: Estadisticas } = await import('./Estadisticas');

const EVENTOS = [{ id: 'evento-belgium', titulo: 'Subsonic Belgium' }, { id: 'evento-brasil', titulo: 'Subsonic Brasil' }];
const RESUMEN = {
  entradas_vendidas: 15688, ingresos_entradas: 2431500, ingresos_alquileres: 184000, ingresos_tienda: 36250,
  usuarios_registrados: 21430, ocupacion_espacios: 0.82, asistentes_hoy: 0, actualizado_en: '2026-07-18T16:00:00Z',
};

const pintar = (elemento) => render(<MemoryRouter>{elemento}</MemoryRouter>);

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
  vi.mocked(listarEventos).mockReset().mockResolvedValue({ datos: EVENTOS, total: 2 });
});

describe('Visión General', () => {
  it('muestra los indicadores del festival', async () => {
    api.obtenerResumen.mockResolvedValue(RESUMEN);

    pintar(<Resumen />);

    expect(await screen.findByText('15.688')).toBeInTheDocument();
    expect(screen.getByText(/2\.651\.750/)).toBeInTheDocument();          // entradas + alquileres + tienda
    expect(screen.getByText('82 %')).toBeInTheDocument();
    expect(screen.getByText('21.430')).toBeInTheDocument();
    expect(api.obtenerResumen).toHaveBeenCalledWith(null);
  });

  it('al elegir un evento pide sus cifras', async () => {
    api.obtenerResumen.mockResolvedValue(RESUMEN);
    pintar(<Resumen />);
    await screen.findByText('Subsonic Belgium');

    await userEvent.selectOptions(screen.getByLabelText('Evento'), 'evento-belgium');

    expect(api.obtenerResumen).toHaveBeenLastCalledWith('evento-belgium');
  });

  it('si falla muestra el error y deja reintentar', async () => {
    api.obtenerResumen
      .mockRejectedValueOnce(new ErrorApi(503, 'SERVICIO_NO_DISPONIBLE', 'ms-analitica no responde'))
      .mockResolvedValueOnce(RESUMEN);
    pintar(<Resumen />);

    expect(await screen.findByRole('alert')).toHaveTextContent('ms-analitica no responde');
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByText('15.688')).toBeInTheDocument();
  });
});

describe('Estadísticas', () => {
  it('empieza en la venta de entradas con el total', async () => {
    api.obtenerVentas.mockResolvedValue([
      { evento_id: 'evento-belgium', periodo: '2026-03-01', entradas: 412, ingresos: 65920, cancelaciones: 3 },
      { evento_id: 'evento-belgium', periodo: '2026-03-02', entradas: 100, ingresos: 16000, cancelaciones: 1 },
    ]);

    pintar(<Estadisticas />);

    const total = (await screen.findByText('Total')).closest('tr');
    expect(within(total).getByText('512')).toBeInTheDocument();
    expect(within(total).getByText(/81\.920/)).toBeInTheDocument();
    expect(api.obtenerVentas).toHaveBeenCalledWith(expect.objectContaining({ agrupar_por: 'DIA' }));
  });

  it('no pide ventas si «desde» es posterior a «hasta»', async () => {
    api.obtenerVentas.mockResolvedValue([]);
    pintar(<Estadisticas />);
    await screen.findByText('No hay ventas en ese periodo.');
    api.obtenerVentas.mockClear();

    await userEvent.type(screen.getByLabelText('Desde'), '2026-08-01');
    await userEvent.type(screen.getByLabelText('Hasta'), '2026-07-01');

    expect(screen.getByRole('alert')).toHaveTextContent('no puede ser posterior');
    expect(api.obtenerVentas).not.toHaveBeenCalledWith(expect.objectContaining({ desde: '2026-08-01', hasta: '2026-07-01' }));
  });

  it('la ocupación pide elegir evento y luego muestra la tabla', async () => {
    api.obtenerVentas.mockResolvedValue([]);
    api.obtenerOcupacion.mockResolvedValue([
      { evento_id: 'evento-belgium', tipo_espacio: 'FOOD_BEVERAGE', total: 40, alquilados: 33, ingresos_alquiler: 49500 },
    ]);
    pintar(<Estadisticas />);

    await userEvent.click(screen.getByRole('button', { name: 'Ocupación de espacios' }));
    expect(screen.getByText(/Elige un evento para ver/)).toBeInTheDocument();
    expect(api.obtenerOcupacion).not.toHaveBeenCalled();

    await screen.findByRole('option', { name: 'Subsonic Belgium' });
    await userEvent.selectOptions(screen.getByLabelText('Evento'), 'evento-belgium');

    expect(await screen.findByText('Food beverage')).toBeInTheDocument();
    expect(screen.getAllByText('83 %').length).toBeGreaterThan(0);
    expect(api.obtenerOcupacion).toHaveBeenCalledWith('evento-belgium');
  });

  it('un 404 sin datos se muestra como aviso, no como error', async () => {
    api.obtenerVentas.mockResolvedValue([]);
    api.obtenerAfluencia.mockRejectedValue(new ErrorApi(404, 'SIN_DATOS', 'No hay datos'));
    pintar(<Estadisticas />);

    await userEvent.click(screen.getByRole('button', { name: 'Previsión de afluencia' }));
    await screen.findByRole('option', { name: 'Subsonic Brasil' });
    await userEvent.selectOptions(screen.getByLabelText('Evento'), 'evento-brasil');

    expect(await screen.findByText(/No hay actuaciones programadas/)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('la afluencia marca las actuaciones casi llenas', async () => {
    api.obtenerVentas.mockResolvedValue([]);
    api.obtenerAfluencia.mockResolvedValue([{
      espacio_id: 'espacio-010', escenario: 'Main Stage', franjas: [
        { inicio: '2026-07-18T22:00:00+02:00', fin: '2026-07-19T00:00:00+02:00', artista: 'Armin van Buuren',
          asistentes_estimados: 18500, porcentaje_aforo: 0.95 },
        { inicio: '2026-07-18T20:00:00+02:00', fin: '2026-07-18T22:00:00+02:00', artista: 'Tiësto',
          asistentes_estimados: 9000, porcentaje_aforo: 0.45 },
      ],
    }]);
    pintar(<Estadisticas />);

    await userEvent.click(screen.getByRole('button', { name: 'Previsión de afluencia' }));
    await screen.findByRole('option', { name: 'Subsonic Belgium' });
    await userEvent.selectOptions(screen.getByLabelText('Evento'), 'evento-belgium');

    const armin = (await screen.findByText('Armin van Buuren')).closest('tr');
    expect(within(armin).getByText('Casi lleno')).toBeInTheDocument();
    expect(within(screen.getByText('Tiësto').closest('tr')).queryByText('Casi lleno')).not.toBeInTheDocument();
  });

  it('la tienda muestra las tallas a punto de agotarse', async () => {
    api.obtenerVentas.mockResolvedValue([]);
    api.obtenerEstadisticasTienda.mockResolvedValue({
      ventas: [{ producto_id: 'camiseta-2026', talla: 'M', unidades: 320, ingresos: 8000 }],
      stock_bajo: [{ producto_id: 'sudadera-2026', talla: 'XL', stock: 2 }],
    });
    pintar(<Estadisticas />);

    await userEvent.click(screen.getByRole('button', { name: 'Tienda' }));

    expect(await screen.findByText('sudadera-2026')).toBeInTheDocument();
    expect(screen.getByText('Quedan 2')).toBeInTheDocument();
    expect(screen.getByText('camiseta-2026')).toBeInTheDocument();
  });

  it('el ranking de artistas enlaza a su ficha y cambia el número', async () => {
    api.obtenerVentas.mockResolvedValue([]);
    api.obtenerArtistasPopulares.mockResolvedValue([
      { artista_id: 'a1', artista: 'Armin van Buuren', favoritos: 5230, visitas: 18740, tendencia_7d: 0.15 },
    ]);
    pintar(<Estadisticas />);

    await userEvent.click(screen.getByRole('button', { name: 'Artistas populares' }));

    expect(await screen.findByRole('link', { name: 'Armin van Buuren' })).toHaveAttribute('href', '/artistas/a1');
    expect(screen.getByText('+15 %')).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('Mostrar'), '20');
    expect(api.obtenerArtistasPopulares).toHaveBeenLastCalledWith({ evento_id: null, limite: 20 });
  });
});
