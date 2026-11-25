import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  cambiarEstadoEvento, crearEvento, listarEventos, listarRecintos, listarTarifas, modificarEvento,
  modificarRecinto,
} from '../../api/espacios';
import Eventos from './Eventos';

vi.mock('../../api/espacios', () => ({
  cambiarEstadoEvento: vi.fn(), crearEvento: vi.fn(), crearRecinto: vi.fn(), crearTarifa: vi.fn(),
  eliminarEvento: vi.fn(), eliminarRecinto: vi.fn(), eliminarTarifa: vi.fn(), listarEventos: vi.fn(),
  listarRecintos: vi.fn(), listarTarifas: vi.fn(), modificarEvento: vi.fn(), modificarRecinto: vi.fn(),
  modificarTarifa: vi.fn(),
}));

describe('Administración de eventos', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarEventos).mockResolvedValue({ datos: [
      { id: 'evento-1', titulo: 'Festival', pais: 'Bélgica', estado: 'BORRADOR', fecha_inicio: '2026-07-18', fecha_fin: '2026-07-27' },
    ] });
    vi.mocked(listarRecintos).mockResolvedValue([{ id: 'recinto-1', nombre: 'Dreamville Grounds', ciudad: 'Boom', pais: 'Bélgica', aforo_maximo: 50000 }]);
    vi.mocked(listarTarifas).mockResolvedValue([]);
  });

  it('publica un evento en borrador', async () => {
    render(<Eventos />);
    fireEvent.click(await screen.findByRole('button', { name: 'Publicar' }));
    await waitFor(() => expect(cambiarEstadoEvento).toHaveBeenCalledWith('evento-1', 'PUBLICADO', undefined));
  });

  it('crea un evento con etiquetas y servicios convertidos a listas', async () => {
    render(<Eventos />);
    await screen.findByRole('heading', { name: 'Crear evento' });
    fireEvent.change(screen.getByLabelText(/Identificador/), { target: { value: 'evento-brazil' } });
    fireEvent.change(screen.getByLabelText('Título'), { target: { value: 'Festival Brasil' } });
    fireEvent.change(screen.getByLabelText('País'), { target: { value: 'Brasil' } });
    fireEvent.change(screen.getByLabelText('Recinto'), { target: { value: 'recinto-1' } });
    fireEvent.change(screen.getByLabelText('Fecha de inicio'), { target: { value: '2026-08-01' } });
    fireEvent.change(screen.getByLabelText('Fecha de fin'), { target: { value: '2026-08-02' } });
    fireEvent.change(screen.getByLabelText('Etiquetas (separadas por coma)'), { target: { value: 'house, techno' } });
    fireEvent.change(screen.getByLabelText('Servicios generales (separados por coma)'), { target: { value: 'Agua, Primeros auxilios' } });
    fireEvent.click(screen.getByRole('button', { name: 'Crear evento' }));

    await waitFor(() => expect(crearEvento).toHaveBeenCalledWith(expect.objectContaining({
      id: 'evento-brazil', recinto_id: 'recinto-1', tags: ['house', 'techno'],
      servicios_generales: ['Agua', 'Primeros auxilios'],
    })));
  });

  it('edita eventos con descripción e imagen nulas', async () => {
    vi.mocked(listarEventos).mockResolvedValueOnce({ datos: [
      { id: 'evento-1', titulo: 'Festival', pais: 'Bélgica', recinto_id: 'recinto-1', estado: 'BORRADOR',
        fecha_inicio: '2026-07-18', fecha_fin: '2026-07-27', descripcion: null, imagen_url: null },
    ] });
    render(<Eventos />);
    fireEvent.click(await screen.findByRole('button', { name: 'Editar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar evento' }));

    await waitFor(() => expect(modificarEvento).toHaveBeenCalledWith('evento-1', expect.objectContaining({
      descripcion: '', imagen_url: '',
    })));
  });

  it('edita recintos con dirección nula', async () => {
    vi.mocked(listarRecintos).mockResolvedValueOnce([
      { id: 'recinto-1', nombre: 'Dreamville Grounds', direccion: null, ciudad: 'Boom',
        pais: 'Bélgica', aforo_maximo: 50000 },
    ]);
    render(<Eventos />);
    fireEvent.click(await screen.findByRole('button', { name: 'Recintos' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Editar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar recinto' }));

    await waitFor(() => expect(modificarRecinto).toHaveBeenCalledWith('recinto-1', expect.objectContaining({
      direccion: '',
    })));
  });

  it('muestra errores al cargar los eventos', async () => {
    vi.mocked(listarEventos).mockRejectedValue(new Error('No se pudieron cargar'));
    render(<Eventos />);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudieron cargar');
  });
});
