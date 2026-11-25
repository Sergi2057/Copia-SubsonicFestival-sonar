// src/pages/Inicio/Recomendaciones.test.jsx — recomendaciones de la portada, del cliente y del proveedor
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorApi } from '../../api/cliente';

vi.mock('../../api/analitica', () => ({
  obtenerMisRecomendaciones: vi.fn(), obtenerRecomendacionesPopulares: vi.fn(), obtenerEspaciosRecomendados: vi.fn(),
}));
vi.mock('../../api/espacios', () => ({ listarEventos: vi.fn() }));
vi.mock('../../sesion/SesionContext', () => ({ useSesion: vi.fn() }));

const api = await import('../../api/analitica');
const { listarEventos } = await import('../../api/espacios');
const { useSesion } = await import('../../sesion/SesionContext');
const { default: Recomendaciones } = await import('./Recomendaciones');
const { default: ResumenCliente } = await import('../../perfiles/cliente/Resumen');
const { default: EspaciosRecomendados } = await import('../../perfiles/proveedor/EspaciosRecomendados');

const POPULARES = {
  eventos: [{ evento_id: 'evento-belgium', titulo: 'Subsonic Belgium', puntuacion: 0.9, motivo: 'El más vendido' }],
  artistas: [{ artista_id: 'a1', artista: 'Armin van Buuren', favoritos: 5230, visitas: 18740, tendencia_7d: 0.15 }],
};
const MIAS = {
  eventos: [{ evento_id: 'evento-brasil', titulo: 'Subsonic Brasil', puntuacion: 0.87, motivo: 'Actúan 3 de tus artistas favoritos' }],
  artistas: [{ artista_id: 'a2', artista: 'Tiësto', puntuacion: 0.79, motivo: 'Porque te gusta Armin van Buuren' }],
  mi_escaleta: [],
};

const pintar = (elemento) => render(<MemoryRouter>{elemento}</MemoryRouter>);
const conSesion = (rol) => vi.mocked(useSesion).mockReturnValue({ rol, cargando: false });

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
  vi.mocked(listarEventos).mockReset().mockResolvedValue({
    datos: [{ id: 'evento-belgium', titulo: 'Subsonic Belgium' }], total: 1,
  });
});

describe('Recomendaciones de la portada', () => {
  it('sin sesión muestra lo más popular', async () => {
    conSesion(null);
    api.obtenerRecomendacionesPopulares.mockResolvedValue(POPULARES);

    pintar(<Recomendaciones />);

    expect(await screen.findByRole('link', { name: 'Subsonic Belgium' })).toHaveAttribute('href', '/evento/evento-belgium');
    expect(screen.getByRole('heading', { name: 'Lo más popular' })).toBeInTheDocument();
    expect(screen.getByText('+15 % esta semana')).toBeInTheDocument();
    expect(api.obtenerMisRecomendaciones).not.toHaveBeenCalled();
  });

  it('un cliente ve las suyas con el motivo', async () => {
    conSesion('cliente');
    api.obtenerMisRecomendaciones.mockResolvedValue(MIAS);

    pintar(<Recomendaciones />);

    expect(await screen.findByRole('heading', { name: 'Recomendado para ti' })).toBeInTheDocument();
    expect(screen.getByText('Actúan 3 de tus artistas favoritos')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Tiësto' })).toHaveAttribute('href', '/artistas/a2');
    expect(api.obtenerRecomendacionesPopulares).not.toHaveBeenCalled();
  });

  it.each([
    ['no tiene ninguna', () => api.obtenerMisRecomendaciones.mockResolvedValue({ eventos: [], artistas: [], mi_escaleta: [] })],
    ['su token aún no lleva el rol', () => api.obtenerMisRecomendaciones.mockRejectedValue(new ErrorApi(403, 'SIN_PERMISO', 'x'))],
  ])('si el cliente %s, muestra lo más popular', async (_caso, preparar) => {
    conSesion('cliente');
    preparar();
    api.obtenerRecomendacionesPopulares.mockResolvedValue(POPULARES);

    pintar(<Recomendaciones />);

    expect(await screen.findByRole('heading', { name: 'Lo más popular' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Subsonic Belgium' })).toBeInTheDocument();
  });

  it('si ms-analitica no manda el título del evento, lo toma de ms-espacios', async () => {
    conSesion(null);
    api.obtenerRecomendacionesPopulares.mockResolvedValue({
      eventos: [{ evento_id: 'evento-belgium', titulo: null, puntuacion: 1, motivo: 'x' }], artistas: [],
    });

    pintar(<Recomendaciones />);

    expect(await screen.findByRole('link', { name: 'Subsonic Belgium' })).toBeInTheDocument();
  });

  it('no pide nada mientras se carga la sesión', () => {
    vi.mocked(useSesion).mockReturnValue({ rol: null, cargando: true });

    pintar(<Recomendaciones />);

    expect(screen.getByRole('status')).toHaveTextContent('Cargando');
    expect(api.obtenerRecomendacionesPopulares).not.toHaveBeenCalled();
  });
});

describe('Inicio del cliente', () => {
  it('muestra mi escaleta con los pases que coinciden en horario', async () => {
    api.obtenerMisRecomendaciones.mockResolvedValue({
      ...MIAS,
      mi_escaleta: [
        { pase_id: 'p1', artista: 'Armin van Buuren', escenario: 'Main Stage',
          inicio: '2026-07-18T22:00:00+02:00', fin: '2026-07-19T00:00:00+02:00', solapa_con: ['p2'] },
        { pase_id: 'p2', artista: 'Charlotte de Witte', escenario: 'Techno Tent',
          inicio: '2026-07-18T23:00:00+02:00', fin: '2026-07-19T01:00:00+02:00', solapa_con: ['p1'] },
        { pase_id: 'p3', artista: 'Tiësto', escenario: 'Main Stage',
          inicio: '2026-07-18T19:00:00+02:00', fin: '2026-07-18T20:30:00+02:00', solapa_con: [] },
      ],
    });

    pintar(<ResumenCliente perfil={{ nombre: 'David' }} />);

    expect(await screen.findByRole('heading', { name: 'Hola, David' })).toBeInTheDocument();
    expect(await screen.findByText('2 pases coinciden en horario')).toBeInTheDocument();
    const filaArmin = screen.getAllByRole('cell', { name: 'Armin van Buuren' })[0].closest('tr');
    expect(filaArmin).toHaveClass('an-solapa');
    expect(filaArmin).toHaveTextContent('Charlotte de Witte');
    const filas = screen.getAllByRole('row').slice(1).map((f) => f.cells[1].textContent);
    expect(filas).toEqual(['Tiësto', 'Armin van Buuren', 'Charlotte de Witte']);   // ordenados por hora
  });

  it('sin favoritos le explica cómo rellenar su escaleta', async () => {
    api.obtenerMisRecomendaciones.mockResolvedValue({ eventos: [], artistas: [], mi_escaleta: [] });

    pintar(<ResumenCliente perfil={{ nombre: 'David' }} />);

    expect(await screen.findByText(/Añade artistas a «Artistas Favoritos»/)).toBeInTheDocument();
  });
});

describe('Espacios recomendados del proveedor', () => {
  it('muestra los espacios con el motivo y el nombre del evento', async () => {
    api.obtenerEspaciosRecomendados.mockResolvedValue([{
      espacio_id: 'espacio-001', evento_id: 'evento-belgium', tipo: 'FOOD_BEVERAGE', precio_alquiler: 1500,
      afluencia_estimada: 12000, puntuacion: 0.91, motivo: 'Zona con más paso de público en la edición anterior',
    }]);

    pintar(<EspaciosRecomendados />);

    expect(await screen.findByText('Zona con más paso de público en la edición anterior')).toBeInTheDocument();
    expect(screen.getByText('Food beverage · espacio-001')).toBeInTheDocument();
    expect(await screen.findByText('Subsonic Belgium', { selector: 'span' })).toBeInTheDocument();
    expect(screen.getByText('Público estimado: 12.000 personas')).toBeInTheDocument();
  });

  it('sin espacios libres lo dice', async () => {
    api.obtenerEspaciosRecomendados.mockResolvedValue([]);

    pintar(<EspaciosRecomendados />);

    expect(await screen.findByText(/No hay espacios libres/)).toBeInTheDocument();
  });
});
