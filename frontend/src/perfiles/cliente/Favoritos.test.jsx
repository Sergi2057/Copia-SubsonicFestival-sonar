import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarFavoritos, quitarFavorito } from '../../api/usuarios';
import Favoritos from './Favoritos';

vi.mock('../../api/usuarios', () => ({ listarFavoritos: vi.fn(), quitarFavorito: vi.fn() }));
const pintar = () => render(<MemoryRouter><Favoritos /></MemoryRouter>);
describe('Favoritos', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarFavoritos).mockResolvedValue([{ artista_id: 'a1', artista_nombre: 'Armin' }]);
  });
  it('enlaza la ficha del artista y permite quitarlo', async () => {
    vi.mocked(listarFavoritos).mockResolvedValueOnce([{ artista_id: 'a1', artista_nombre: 'Armin' }]).mockResolvedValue([]);
    pintar();
    expect(await screen.findByRole('link', { name: 'Armin' })).toHaveAttribute('href', '/artistas/a1');
    await userEvent.click(screen.getByRole('button', { name: 'Quitar a Armin de favoritos' }));
    expect(quitarFavorito).toHaveBeenCalledWith('a1');
    expect(await screen.findByText(/Aún no tienes artistas favoritos/)).toBeInTheDocument();
  });
  it('conserva los datos si el backend rechaza la baja', async () => {
    vi.mocked(quitarFavorito).mockRejectedValue(new Error('No se ha podido quitar'));
    pintar();
    await userEvent.click(await screen.findByRole('button', { name: 'Quitar a Armin de favoritos' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se ha podido quitar');
    expect(screen.getByRole('link', { name: 'Armin' })).toBeInTheDocument();
  });
  it('muestra un error al cargar', async () => {
    vi.mocked(listarFavoritos).mockRejectedValue(new Error('Sin conexión'));
    pintar();
    expect(await screen.findByRole('alert')).toHaveTextContent('Sin conexión');
  });
});
