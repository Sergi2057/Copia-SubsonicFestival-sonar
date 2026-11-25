import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  cambiarEstadoAlquiler, crearEspacio, listarAlquileres, listarEventos, listarEspacios, listarTiposEspacio,
  modificarEspacio,
} from '../../api/espacios';
import Espacios from './Espacios';

vi.mock('../../api/espacios', () => ({
  cambiarEstadoAlquiler: vi.fn(), crearEspacio: vi.fn(), eliminarEspacio: vi.fn(),
  listarAlquileres: vi.fn(), listarEventos: vi.fn(), listarEspacios: vi.fn(),
  listarTiposEspacio: vi.fn(), modificarEspacio: vi.fn(),
}));

describe('Administración de espacios y alquileres', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarEventos).mockResolvedValue({ datos: [{ id: 'evento-1', titulo: 'Festival' }] });
    vi.mocked(listarTiposEspacio).mockResolvedValue([{ codigo: 'FOOD_BEVERAGE', nombre: 'Food & Beverage' }]);
    vi.mocked(listarEspacios).mockResolvedValue({ datos: [] });
    vi.mocked(listarAlquileres).mockResolvedValue({ datos: [
      { id: 'alquiler-1', estado: 'PENDIENTE', proveedor_nombre: 'Frituras Boom', espacio_id: 'espacio-1', evento_id: 'evento-1', importe: 120 },
    ] });
    vi.mocked(cambiarEstadoAlquiler).mockResolvedValue({});
    vi.mocked(crearEspacio).mockResolvedValue({ id: 'espacio-1' });
  });

  it('aprueba una solicitud pendiente', async () => {
    render(<Espacios />);
    fireEvent.click(await screen.findByRole('button', { name: 'Aprobar' }));
    await waitFor(() => expect(cambiarEstadoAlquiler).toHaveBeenCalledWith('alquiler-1', 'APROBADO', undefined));
  });

  it('crea un espacio asociado al evento y tipo seleccionados', async () => {
    render(<Espacios />);
    await screen.findByRole('heading', { name: 'Crear espacio' });
    fireEvent.change(screen.getAllByLabelText('Evento')[1], { target: { value: 'evento-1' } });
    fireEvent.change(screen.getAllByLabelText('Tipo')[1], { target: { value: 'FOOD_BEVERAGE' } });
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Puesto central' } });
    fireEvent.click(screen.getByRole('button', { name: 'Crear espacio' }));
    await waitFor(() => expect(crearEspacio).toHaveBeenCalledWith(expect.objectContaining({
      evento_id: 'evento-1', tipo: 'FOOD_BEVERAGE', nombre: 'Puesto central', disponible: true,
    })));
  });

  it('edita espacios con descripción nula y libera el botón de guardar', async () => {
    vi.mocked(listarEspacios).mockResolvedValueOnce({ datos: [
      { id: 'espacio-1', evento_id: 'evento-1', tipo: 'FOOD_BEVERAGE', nombre: 'Puesto central',
        zona: 'Zona A', tamano: '', dimensiones: '', descripcion: null, disponible: true,
        servicios: [], aforo: null, precio_alquiler: 120 },
    ] });
    render(<Espacios />);
    fireEvent.click(await screen.findByRole('button', { name: 'Editar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar espacio' }));

    await waitFor(() => expect(modificarEspacio).toHaveBeenCalledWith('espacio-1', expect.objectContaining({
      descripcion: '',
    })));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Crear espacio' })).toBeEnabled());
  });

  it('muestra los errores del gateway', async () => {
    vi.mocked(listarAlquileres).mockRejectedValue(new Error('Error de permisos'));
    render(<Espacios />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Error de permisos');
  });
});
