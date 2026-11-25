import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarVideos, obtenerArtista } from '../../api/escaleta';
import { anadirFavorito, listarFavoritos, quitarFavorito } from '../../api/usuarios';
import { registrarInteraccion } from '../../analitica/interacciones';
import { useSesion } from '../../sesion/SesionContext';
import Artista from './Artista';

vi.mock('../../api/escaleta', () => ({ obtenerArtista: vi.fn(), listarVideos: vi.fn() }));
vi.mock('../../api/usuarios', () => ({ listarFavoritos: vi.fn(), anadirFavorito: vi.fn(), quitarFavorito: vi.fn() }));
vi.mock('../../analitica/interacciones', () => ({ registrarInteraccion: vi.fn() }));
vi.mock('../../sesion/SesionContext', () => ({ useSesion: vi.fn() }));

const ARMIN = {
  id: 'a1', nombre: 'Armin van Buuren', generos: ['trance', 'progressive'], pais: 'Países Bajos',
  biografia: 'DJ y productor neerlandés.', imagen_url: null, youtube_channel_id: null,
  redes: { instagram: 'https://instagram.com/arminvanbuuren' },
  pases: [{ pase_id: 'p1', artista_id: 'a1', artista: 'Armin van Buuren', escenario: 'Trance Stage',
    inicio: '2026-07-18T19:00:00Z', fin: '2026-07-18T21:00:00Z', estado: 'CONFIRMADO' }],
};
const VIDEOS = [
  { titulo: 'A State of Trance 1200', url: 'https://www.youtube.com/watch?v=abc123', miniatura_url: null, tipo: 'VIDEO' },
  { titulo: 'Mejores temas', url: 'https://www.youtube.com/playlist?list=PL999', miniatura_url: null, tipo: 'PLAYLIST' },
];

const pintar = () => render(
  <MemoryRouter initialEntries={['/artistas/a1']}>
    <Routes><Route path="/artistas/:id" element={<Artista />} /></Routes>
  </MemoryRouter>,
);

describe('Artista', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useSesion).mockReturnValue({ rol: null });
    vi.mocked(obtenerArtista).mockResolvedValue(ARMIN);
    vi.mocked(listarVideos).mockResolvedValue(VIDEOS);
    vi.mocked(listarFavoritos).mockResolvedValue([]);
  });

  it('pinta la ficha, sus pases, sus redes y registra la visita', async () => {
    pintar();
    expect(await screen.findByRole('heading', { level: 1, name: 'Armin van Buuren' })).toBeInTheDocument();
    expect(screen.getByText('DJ y productor neerlandés.')).toBeInTheDocument();
    expect(screen.getByText('Trance Stage')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'instagram' })).toHaveAttribute('href', 'https://instagram.com/arminvanbuuren');
    expect(obtenerArtista).toHaveBeenCalledWith('a1');
    expect(registrarInteraccion).toHaveBeenCalledWith('VER_ARTISTA', 'a1');
  });

  it('reproduce sus vídeos y playlists de YouTube', async () => {
    pintar();
    expect(await screen.findByTitle('A State of Trance 1200')).toHaveAttribute('src', 'https://www.youtube.com/embed/abc123');
    await userEvent.click(screen.getByRole('button', { name: /Mejores temas/ }));
    expect(screen.getByTitle('Mejores temas')).toHaveAttribute('src', 'https://www.youtube.com/embed/videoseries?list=PL999');
  });

  it('sin vídeos (YouTube sin clave o caído) lo dice en lugar del reproductor', async () => {
    vi.mocked(listarVideos).mockResolvedValue([]);
    pintar();
    expect(await screen.findByText('No hay vídeos disponibles de Armin van Buuren en este momento.')).toBeInTheDocument();
  });

  it('un cliente lo añade y lo quita de favoritos', async () => {
    vi.mocked(useSesion).mockReturnValue({ rol: 'cliente' });
    pintar();
    await userEvent.click(await screen.findByRole('button', { name: /Añadir a favoritos/ }));
    expect(anadirFavorito).toHaveBeenCalledWith('a1');
    await userEvent.click(await screen.findByRole('button', { name: /En tus favoritos/ }));
    expect(quitarFavorito).toHaveBeenCalledWith('a1');
    expect(await screen.findByRole('button', { name: /Añadir a favoritos/ })).toBeInTheDocument();
  });

  it('muestra el error del backend al guardar el favorito', async () => {
    vi.mocked(useSesion).mockReturnValue({ rol: 'cliente' });
    vi.mocked(listarFavoritos).mockResolvedValue([{ artista_id: 'a1' }]);
    vi.mocked(quitarFavorito).mockRejectedValue(new Error('ms-usuarios no responde'));
    pintar();
    await userEvent.click(await screen.findByRole('button', { name: /En tus favoritos/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('ms-usuarios no responde');
  });

  it('avisa si el artista no existe', async () => {
    vi.mocked(obtenerArtista).mockRejectedValue(Object.assign(new Error('No existe'), { status: 404 }));
    pintar();
    expect(await screen.findByRole('alert')).toHaveTextContent('Este artista no existe.');
  });
});
