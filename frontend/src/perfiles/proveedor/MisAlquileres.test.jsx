import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { cambiarEstadoAlquiler, listarAlquileres, listarEventos } from '../../api/espacios';
import MisAlquileres from './MisAlquileres';

vi.mock('../../api/espacios', () => ({
  cambiarEstadoAlquiler: vi.fn(), listarAlquileres: vi.fn(), listarEventos: vi.fn(),
}));

describe('Mis alquileres', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarAlquileres).mockResolvedValue({ datos: [
      { id: 'alquiler-1', estado: 'PENDIENTE', evento_id: 'evento-1', espacio_id: 'espacio-1', importe: 120 },
    ] });
    vi.mocked(listarEventos).mockResolvedValue({ datos: [{ id: 'evento-1', titulo: 'Festival' }] });
    vi.mocked(cambiarEstadoAlquiler).mockResolvedValue({});
  });

  it('muestra solicitudes y permite cancelarlas', async () => {
    vi.mocked(listarAlquileres).mockResolvedValueOnce({ datos: [
      { id: 'alquiler-1', estado: 'PENDIENTE', evento_id: 'evento-1', espacio_id: 'espacio-1',
        espacio: { nombre: 'Puesto central' }, proveedor_nombre: 'Proveedor', importe: 120 },
    ] }).mockResolvedValueOnce({ datos: [] });
    render(<MisAlquileres />);
    expect(await screen.findByText('Evento: Festival')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Puesto central' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar solicitud' }));
    await waitFor(() => expect(cambiarEstadoAlquiler).toHaveBeenCalledWith('alquiler-1', 'CANCELADO'));
    expect(await screen.findByText('No tienes alquileres en este estado.')).toBeInTheDocument();
  });

  it('muestra errores de carga', async () => {
    vi.mocked(listarAlquileres).mockRejectedValue(new Error('Error del gateway'));
    render(<MisAlquileres />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Error del gateway');
  });
});
