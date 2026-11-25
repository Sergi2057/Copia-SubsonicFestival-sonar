import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarEventos } from '../../api/espacios';
import { registrarInteraccion } from '../../analitica/interacciones';
import BuscadorEventos from './BuscadorEventos';

vi.mock('../../api/espacios', () => ({ listarEventos: vi.fn() }));
vi.mock('../../analitica/interacciones', () => ({ registrarInteraccion: vi.fn() }));

describe('Buscador de eventos', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarEventos).mockResolvedValue({ datos: [
      { id: 'evento-1', titulo: 'Subsonic Belgium', pais: 'Bélgica', fecha_inicio: '2026-07-18', fecha_fin: '2026-07-27', tags: ['techno'] },
      { id: 'evento-2', titulo: 'Festival Brasil', pais: 'Brasil', fecha_inicio: '2026-08-01', fecha_fin: '2026-08-02', tags: ['house'] },
    ], total: 2 });
  });

  it('carga eventos, filtra y abre la ficha', async () => {
    render(<MemoryRouter><BuscadorEventos /></MemoryRouter>);
    expect((await screen.findAllByRole('link', { name: 'Ver evento' }))[0]).toHaveAttribute('href', '/evento/evento-1');
    fireEvent.change(screen.getByLabelText('Buscar eventos'), { target: { value: 'techno' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar eventos' }));
    expect(registrarInteraccion).toHaveBeenCalledWith('BUSCAR', 'techno');
    expect(screen.getByText('Subsonic Belgium')).toBeInTheDocument();
    expect(screen.queryByText('Festival Brasil')).not.toBeInTheDocument();
  });

  it('muestra errores del gateway', async () => {
    vi.mocked(listarEventos).mockRejectedValue(new Error('Gateway no disponible'));
    render(<MemoryRouter><BuscadorEventos /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('Gateway no disponible');
  });
});
