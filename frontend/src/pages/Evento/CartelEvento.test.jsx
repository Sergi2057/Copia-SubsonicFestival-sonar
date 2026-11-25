import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { escucharCambios, obtenerEscaleta } from '../../api/escaleta';
import { anadirFavorito, listarFavoritos } from '../../api/usuarios';
import { useSesion } from '../../sesion/SesionContext';
import CartelEvento from './CartelEvento';
import { aplicarCambioPase, diaDeFestival, hora, urlIncrustada } from './escaletaUtil';

vi.mock('../../api/escaleta', () => ({ obtenerEscaleta: vi.fn(), escucharCambios: vi.fn() }));
vi.mock('../../api/usuarios', () => ({ listarFavoritos: vi.fn(), anadirFavorito: vi.fn(), quitarFavorito: vi.fn() }));
vi.mock('../../sesion/SesionContext', () => ({ useSesion: vi.fn() }));

const pase = (id, artistaId, artista, escenario, inicio, fin, estado = 'CONFIRMADO') => ({
  pase_id: id, artista_id: artistaId, artista, escenario, inicio, fin, estado,
});
const ARMIN = pase('p1', 'a1', 'Armin van Buuren', 'Main Stage', '2026-07-18T20:00:00Z', '2026-07-18T22:00:00Z');
const TIESTO = pase('p2', 'a2', 'Tiësto', 'Trance Stage', '2026-07-18T22:00:00Z', '2026-07-19T00:00:00Z');
const ESCALETA = {
  evento_id: 'evento-belgium', version: 3, publicada_en: '2026-07-01T10:00:00Z',
  dias: [{ fecha: '2026-07-18', escenarios: [
    { espacio_id: 'main', nombre: 'Main Stage', pases: [ARMIN] },
    { espacio_id: 'trance', nombre: 'Trance Stage', pases: [TIESTO] },
  ] }],
};

let enviarCambio;
const pintar = () => render(<MemoryRouter><CartelEvento eventoId="evento-belgium" /></MemoryRouter>);

describe('CartelEvento', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useSesion).mockReturnValue({ rol: null });
    vi.mocked(obtenerEscaleta).mockResolvedValue(ESCALETA);
    vi.mocked(escucharCambios).mockImplementation((_id, alRecibir) => { enviarCambio = alRecibir; return () => {}; });
    vi.mocked(listarFavoritos).mockResolvedValue([]);
  });

  it('pinta los artistas con enlace a su ficha y los horarios por escenario', async () => {
    pintar();
    expect(await screen.findByRole('link', { name: 'Armin van Buuren' })).toHaveAttribute('href', '/artistas/a1');
    expect(screen.getByText(/versión 3/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Horarios' }));
    expect(screen.getByRole('heading', { name: 'Main Stage' })).toBeInTheDocument();
    expect(within(screen.getByTestId('pase-p2')).getByText(`${hora(TIESTO.inicio)} – ${hora(TIESTO.fin)}`)).toBeInTheDocument();
    expect(obtenerEscaleta).toHaveBeenCalledWith('evento-belgium');
    expect(escucharCambios).toHaveBeenCalledWith('evento-belgium', expect.any(Function));
  });

  it('aplica en directo un cambio de horario y una cancelación', async () => {
    pintar();
    await userEvent.click(await screen.findByRole('tab', { name: 'Horarios' }));
    const retrasado = { ...TIESTO, inicio: '2026-07-18T23:30:00Z', fin: '2026-07-19T01:00:00Z' };
    act(() => enviarCambio({ tipo: 'pase.modificado', pase: retrasado, version: 2 }));
    expect(screen.getByRole('status')).toHaveTextContent(`Tiësto actúa a las ${hora(retrasado.inicio)}`);
    expect(within(screen.getByTestId('pase-p2')).getByText(`${hora(retrasado.inicio)} – ${hora(retrasado.fin)}`)).toBeInTheDocument();

    act(() => enviarCambio({ tipo: 'pase.cancelado', pase: { ...ARMIN, estado: 'CANCELADO' }, version: 2 }));
    expect(screen.getByRole('status')).toHaveTextContent('Cancelado: Armin van Buuren en Main Stage');
    expect(within(screen.getByTestId('pase-p1')).getByText('Cancelado')).toBeInTheDocument();
  });

  it('vuelve a pedir la escaleta cuando se publica una versión nueva', async () => {
    pintar();
    await screen.findByRole('link', { name: 'Armin van Buuren' });
    vi.mocked(obtenerEscaleta).mockResolvedValue({ ...ESCALETA, version: 4 });
    act(() => enviarCambio({ tipo: 'escaleta.publicada', version: 4 }));
    expect(await screen.findByText(/versión 4/)).toBeInTheDocument();
    expect(obtenerEscaleta).toHaveBeenCalledTimes(2);
  });

  it('un cliente añade un artista a favoritos', async () => {
    vi.mocked(useSesion).mockReturnValue({ rol: 'cliente' });
    vi.mocked(listarFavoritos).mockResolvedValue([{ artista_id: 'a2', artista_nombre: 'Tiësto' }]);
    pintar();
    expect(await screen.findByRole('button', { name: 'Quitar a Tiësto de favoritos' })).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(screen.getByRole('button', { name: 'Añadir a Armin van Buuren a favoritos' }));
    expect(anadirFavorito).toHaveBeenCalledWith('a1');
    expect(await screen.findByRole('button', { name: 'Quitar a Armin van Buuren de favoritos' })).toBeInTheDocument();
  });

  it('sin sesión de cliente pide iniciar sesión para guardar favoritos', async () => {
    pintar();
    await userEvent.click(await screen.findByRole('button', { name: 'Añadir a Tiësto a favoritos' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Inicia sesión como cliente');
    expect(anadirFavorito).not.toHaveBeenCalled();
    expect(listarFavoritos).not.toHaveBeenCalled();
  });

  it('avisa si la escaleta no está publicada y muestra otros errores del backend', async () => {
    vi.mocked(obtenerEscaleta).mockRejectedValueOnce(Object.assign(new Error('No publicada'), { status: 404 }));
    const { unmount } = pintar();
    expect(await screen.findByText('El cartel de este evento todavía no se ha publicado.')).toBeInTheDocument();
    unmount();
    vi.mocked(obtenerEscaleta).mockRejectedValueOnce(Object.assign(new Error('ms-escaleta no responde'), { status: 503 }));
    pintar();
    expect(await screen.findByRole('alert')).toHaveTextContent('ms-escaleta no responde');
  });
});

describe('aplicarCambioPase', () => {
  it('mueve el pase a su nuevo día y escenario y quita los que se quedan vacíos', () => {
    const movido = { ...ARMIN, escenario: 'Arena', inicio: '2026-07-20T21:00:00Z', fin: '2026-07-20T23:00:00Z' };
    const nueva = aplicarCambioPase(ESCALETA, movido);
    expect(nueva.dias.map((d) => d.fecha)).toEqual(['2026-07-18', '2026-07-20']);
    expect(nueva.dias[0].escenarios.map((e) => e.nombre)).toEqual(['Trance Stage']);
    expect(nueva.dias[1].escenarios[0]).toMatchObject({ nombre: 'Arena', pases: [movido] });
    expect(ESCALETA.dias[0].escenarios[0].pases).toEqual([ARMIN]);   // no modifica la original
  });

  it('urlIncrustada codifica los identificadores de YouTube', () => {
    expect(urlIncrustada({ tipo: 'VIDEO', url: 'https://www.youtube.com/watch?v=abc%2F..%3Fx%3D1' }))
      .toBe('https://www.youtube.com/embed/abc%2F..%3Fx%3D1');
    expect(urlIncrustada({ tipo: 'PLAYLIST', url: 'https://www.youtube.com/playlist?list=PL1%26autoplay%3D1' }))
      .toBe('https://www.youtube.com/embed/videoseries?list=PL1%26autoplay%3D1');
    expect(urlIncrustada({ tipo: 'VIDEO', url: 'no es una url' })).toBeNull();
  });

  it('un pase a la 01:00 cuenta como la noche anterior', () => {
    expect(diaDeFestival('2026-07-19T01:00:00Z')).toBe('2026-07-18');
    expect(diaDeFestival('2026-07-19T07:00:00Z')).toBe('2026-07-19');
  });
});
