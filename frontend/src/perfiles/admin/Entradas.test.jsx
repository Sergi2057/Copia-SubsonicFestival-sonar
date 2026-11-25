import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarEntradasAdmin, resolverCancelacion } from '../../api/usuarios';
import { listarEventos } from '../../api/espacios';
import Entradas from './Entradas';

vi.mock('../../api/usuarios', () => ({ listarEntradasAdmin: vi.fn(), resolverCancelacion: vi.fn() }));
vi.mock('../../api/espacios', () => ({ listarEventos: vi.fn() }));
const entrada = { id: 'entrada-1', evento_id: 'evento-1', evento_titulo: 'Subsonic', tipo_pase: 'DAY',
  precio_pagado: 50, estado: 'CANCELACION_SOLICITADA', motivo_cancelacion: 'No puedo asistir' };
describe('Administración de entradas', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarEventos).mockResolvedValue({ datos: [{ id: 'evento-2', titulo: 'Subsonic Brasil' }], total: 1 });
    vi.mocked(listarEntradasAdmin).mockResolvedValue({ datos: [entrada], total: 1 });
  });
  it.each([['Aceptar cancelación', 'CANCELADA'], ['Rechazar solicitud', 'ACTIVA']])('resuelve: %s', async (boton, estado) => {
    vi.mocked(listarEntradasAdmin).mockResolvedValueOnce({ datos: [entrada], total: 1 }).mockResolvedValue({ datos: [], total: 0 });
    render(<Entradas />);
    expect(await screen.findByText('No puedo asistir')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: boton }));
    expect(resolverCancelacion).toHaveBeenCalledWith('entrada-1', estado);
    expect(await screen.findByRole('status')).toHaveTextContent(estado === 'CANCELADA' ? 'Cancelación aceptada' : 'Solicitud rechazada');
    expect(await screen.findByText('No hay entradas con estos filtros.')).toBeInTheDocument();
  });
  it('filtra por evento y estado', async () => {
    render(<Entradas />);
    await screen.findByText('Subsonic');
    await userEvent.selectOptions(screen.getByLabelText('Estado'), 'USADA');
    await userEvent.selectOptions(await screen.findByLabelText('Evento'), 'evento-2');
    expect(screen.getByRole('option', { name: 'Subsonic Brasil' }).selected).toBe(true);
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' }));
    await screen.findByText('Subsonic');
    expect(listarEntradasAdmin).toHaveBeenLastCalledWith({ estado: 'USADA', evento_id: 'evento-2', limite: 20, desplazamiento: 0 });
    await userEvent.selectOptions(screen.getByLabelText('Evento'), '');
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' }));
    expect(listarEntradasAdmin).toHaveBeenLastCalledWith({ estado: 'USADA', evento_id: '', limite: 20, desplazamiento: 0 });
  });
  it('permite reintentar la carga de eventos sin ocultar las entradas', async () => {
    vi.mocked(listarEventos).mockRejectedValueOnce(new Error('No se pueden cargar los eventos'));
    render(<Entradas />);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pueden cargar los eventos');
    expect(await screen.findByText('No puedo asistir')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('option', { name: 'Subsonic Brasil' })).toBeInTheDocument();
    expect(listarEventos).toHaveBeenCalledTimes(2);
  });
  it('muestra un conflicto al resolver y conserva la solicitud', async () => {
    vi.mocked(resolverCancelacion).mockRejectedValue(new Error('La solicitud ya está resuelta'));
    render(<Entradas />);
    await userEvent.click(await screen.findByRole('button', { name: 'Aceptar cancelación' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('La solicitud ya está resuelta');
  });
  it('muestra errores al cargar', async () => {
    vi.mocked(listarEntradasAdmin).mockRejectedValue(new Error('No se pueden cargar las entradas'));
    render(<Entradas />);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pueden cargar las entradas');
  });
});
