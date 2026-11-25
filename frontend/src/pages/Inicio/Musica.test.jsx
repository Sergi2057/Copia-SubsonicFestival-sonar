import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarArtistas, listarVideos } from '../../api/escaleta';
import Musica from './Musica';

vi.mock('../../api/escaleta', () => ({ listarArtistas: vi.fn(), listarVideos: vi.fn() }));

const ARTISTAS = [
  { id: 'a1', nombre: 'Armin van Buuren', generos: ['trance'], redes: {} },
  { id: 'a2', nombre: 'Tiësto', generos: ['house'], redes: {} },
];
const video = (titulo, id) => ({ titulo, url: `https://www.youtube.com/watch?v=${id}`, miniatura_url: null, tipo: 'VIDEO' });
const pintar = () => render(<MemoryRouter><Musica /></MemoryRouter>);

describe('Musica', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarArtistas).mockResolvedValue({ datos: ARTISTAS, total: 2 });
    vi.mocked(listarVideos).mockImplementation(async (id) => (id === 'a1' ? [video('Armin live', 'x1')] : [video('Tiësto set', 'x2')]));
  });

  it('empieza con el primer artista y cambia de artista y de vídeos al elegir otro', async () => {
    pintar();
    expect(await screen.findByTitle('Armin live')).toHaveAttribute('src', 'https://www.youtube.com/embed/x1');
    await userEvent.click(screen.getByRole('button', { name: 'Tiësto' }));
    expect(await screen.findByTitle('Tiësto set')).toBeInTheDocument();
    expect(listarVideos).toHaveBeenLastCalledWith('a2');
    expect(screen.getByRole('link', { name: 'Ver la ficha de Tiësto' })).toHaveAttribute('href', '/artistas/a2');
  });

  it('filtra los artistas por nombre', async () => {
    pintar();
    await screen.findByRole('button', { name: 'Tiësto' });
    await userEvent.type(screen.getByRole('searchbox', { name: 'Buscar artista' }), 'armin');
    expect(screen.queryByRole('button', { name: 'Tiësto' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Armin van Buuren' })).toBeInTheDocument();
  });

  it('muestra el error del backend', async () => {
    vi.mocked(listarArtistas).mockRejectedValue(new Error('No se puede conectar con el servidor'));
    pintar();
    expect(await screen.findByRole('alert')).toHaveTextContent('No se puede conectar con el servidor');
  });
});
