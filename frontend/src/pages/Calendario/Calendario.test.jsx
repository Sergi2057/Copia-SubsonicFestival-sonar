import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarEventos } from '../../api/espacios';
import Calendario from './Calendario';

vi.mock('../../api/espacios', () => ({ listarEventos: vi.fn() }));

describe('Calendario', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarEventos).mockResolvedValue({ datos: [
      { id: 'evento-1', titulo: 'Subsonic Belgium', pais: 'Bélgica', fecha_inicio: '2026-07-18', fecha_fin: '2026-07-27' },
      { id: 'evento-2', titulo: 'Festival Brasil', pais: 'Brasil', fecha_inicio: '2026-08-01', fecha_fin: '2026-08-02' },
    ], total: 2 });
  });

  it('ordena y agrupa los eventos por mes con enlace a sus fichas', async () => {
    render(<MemoryRouter><Calendario /></MemoryRouter>);
    expect((await screen.findAllByRole('link', { name: 'Ver evento' }))[0]).toHaveAttribute('href', '/evento/evento-1');
    expect(screen.getByRole('region', { name: /julio de 2026/i })).toHaveTextContent('Subsonic Belgium');
    expect(screen.getByRole('region', { name: /agosto de 2026/i })).toHaveTextContent('Festival Brasil');
    expect(listarEventos).toHaveBeenCalledWith({ estado: 'PUBLICADO' });
  });

  it('muestra un error al cargar los eventos', async () => {
    vi.mocked(listarEventos).mockRejectedValue(new Error('No se pudo cargar'));
    render(<MemoryRouter><Calendario /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cargar');
  });
});
