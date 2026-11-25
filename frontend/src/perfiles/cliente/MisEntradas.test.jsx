import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarMisEntradas, solicitarCancelacion } from '../../api/usuarios';
import MisEntradas from './MisEntradas';

vi.mock('../../api/usuarios', () => ({ listarMisEntradas: vi.fn(), solicitarCancelacion: vi.fn() }));
const entrada = { id: 'entrada-1', evento_titulo: 'Subsonic Belgium', evento_id: 'evento-1', evento_fechas: 'Julio 2099',
  tipo_pase: 'DAY', precio_pagado: 50, estado: 'ACTIVA', codigo_qr: 'codigo-firmado' };
const pintar = () => render(<MemoryRouter><MisEntradas /></MemoryRouter>);

describe('Mis entradas', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarMisEntradas).mockResolvedValue([entrada]);
    vi.mocked(solicitarCancelacion).mockResolvedValue({});
  });
  it('muestra el evento y el QR firmado de la entrada', async () => {
    pintar();
    expect(await screen.findByText('Subsonic Belgium')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Mostrar QR' }));
    expect(screen.getByTitle('QR de la entrada entrada-1')).toBeInTheDocument();
  });
  it('solicita cancelación con motivo y vuelve a cargar el estado', async () => {
    vi.mocked(listarMisEntradas).mockResolvedValueOnce([entrada])
      .mockResolvedValue([{ ...entrada, estado: 'CANCELACION_SOLICITADA' }]);
    pintar();
    await userEvent.click(await screen.findByRole('button', { name: 'Solicitar cancelación' }));
    expect(screen.getByRole('button', { name: 'Enviar solicitud' })).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Motivo de cancelación'), 'No puedo asistir');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(solicitarCancelacion).toHaveBeenCalledWith('entrada-1', 'No puedo asistir');
    expect(await screen.findByText('CANCELACION SOLICITADA')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Mostrar QR' })).not.toBeInTheDocument();
  });
  it('conserva la entrada y muestra el rechazo de la cancelación', async () => {
    vi.mocked(solicitarCancelacion).mockRejectedValue(new Error('El evento ya ha empezado'));
    pintar();
    await userEvent.click(await screen.findByRole('button', { name: 'Solicitar cancelación' }));
    await userEvent.type(screen.getByLabelText('Motivo de cancelación'), 'No puedo asistir');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('El evento ya ha empezado');
  });
  it('explica el estado vacío y los errores al cargar', async () => {
    vi.mocked(listarMisEntradas).mockRejectedValueOnce(new Error('Servicio no disponible')).mockResolvedValue([]);
    pintar();
    expect(await screen.findByRole('alert')).toHaveTextContent('Servicio no disponible');
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText(/No tienes entradas/)).toBeInTheDocument();
  });
});
