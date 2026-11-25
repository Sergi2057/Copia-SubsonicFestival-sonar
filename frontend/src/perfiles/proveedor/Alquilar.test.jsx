import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarEventos, listarEspacios, listarTiposEspacio, obtenerEspacio, solicitarAlquiler } from '../../api/espacios';
import Alquilar from './Alquilar';

vi.mock('../../api/espacios', () => ({
  listarEventos: vi.fn(), listarEspacios: vi.fn(), listarTiposEspacio: vi.fn(),
  obtenerEspacio: vi.fn(), solicitarAlquiler: vi.fn(),
}));

describe('Alquilar un espacio', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarEventos).mockResolvedValue({ datos: [{ id: 'evento-1', titulo: 'Festival' }] });
    vi.mocked(listarTiposEspacio).mockResolvedValue([{ codigo: 'FOOD_BEVERAGE', nombre: 'Food & Beverage', alquilable: true }]);
    vi.mocked(listarEspacios).mockResolvedValue({ datos: [
      { id: 'espacio-1', tipo: 'FOOD_BEVERAGE', nombre: 'Puesto central', zona: 'Zona A', evento_id: 'evento-1', precio_alquiler: 120, disponible: true },
    ] });
    vi.mocked(obtenerEspacio).mockResolvedValue({
      id: 'espacio-1', nombre: 'Puesto central', zona: 'Zona A', precio_alquiler: 120,
    });
    vi.mocked(solicitarAlquiler).mockResolvedValue({ id: 'alquiler-1' });
  });

  it('filtra por zona, carga el detalle y envía la solicitud', async () => {
    render(<Alquilar />);
    expect(await screen.findByText('Puesto central')).toBeInTheDocument();
    expect(screen.getByText('Zona A · Festival')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Zona'), { target: { value: 'zona a' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ver detalle y solicitar' }));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Inicio'), { target: { value: '2026-07-14T08:00' } });
    fireEvent.change(screen.getByLabelText('Fin'), { target: { value: '2026-07-15T18:00' } });
    fireEvent.change(screen.getByLabelText('Comentarios'), { target: { value: 'Acceso de montaje' } });
    fireEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));

    await waitFor(() => expect(solicitarAlquiler).toHaveBeenCalledWith('espacio-1', expect.objectContaining({
      comentarios: 'Acceso de montaje',
    })));
    const datos = vi.mocked(solicitarAlquiler).mock.calls[0][1];
    expect(new Date(datos.fecha_inicio).toISOString()).toBe(new Date('2026-07-14T08:00').toISOString());
    expect(await screen.findByRole('status')).toHaveTextContent('Solicitud de alquiler enviada');
  });

  it('muestra errores al cargar espacios', async () => {
    vi.mocked(listarEspacios).mockRejectedValue(new Error('No hay conexión'));
    render(<Alquilar />);
    expect(await screen.findByRole('alert')).toHaveTextContent('No hay conexión');
  });
});
