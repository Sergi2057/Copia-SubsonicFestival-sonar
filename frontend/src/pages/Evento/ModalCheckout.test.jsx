import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { comprarEntrada } from '../../api/usuarios';
import { useSesion } from '../../sesion/SesionContext';
import ModalCheckout from './ModalCheckout';

vi.mock('../../api/usuarios', () => ({ comprarEntrada: vi.fn() }));
vi.mock('../../sesion/SesionContext', () => ({ useSesion: vi.fn() }));
const tarifa = { id: 'tarifa-1', tipo_pase: 'DAY', precio: 50, disponibles: 2 };
const entrada = { id: 'entrada-1', evento_titulo: 'Subsonic', tipo_pase: 'DAY', precio_pagado: 50, codigo_qr: 'QR-firmado' };
const pintar = (props = {}) => render(<ModalCheckout abierto onCerrar={vi.fn()} eventoId="evento-1" tarifa={tarifa} {...props} />);

describe('Compra de entrada', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useSesion).mockReturnValue({ rol: 'cliente', perfil: { activo: true }, cargando: false });
    vi.mocked(comprarEntrada).mockResolvedValue(entrada);
  });
  it('muestra la tarifa seleccionada y entrega el QR de la compra', async () => {
    pintar();
    expect(screen.getByText('evento-1')).toBeInTheDocument();
    expect(screen.getByText('50 €')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar compra' }));
    expect(comprarEntrada).toHaveBeenCalledWith({ evento_id: 'evento-1', tipo_pase: 'DAY', token_pago: 'tok_ok' });
    expect(await screen.findByRole('heading', { name: 'Entrada comprada' })).toBeInTheDocument();
    expect(screen.getByTitle('QR de la entrada entrada-1')).toBeInTheDocument();
  });
  it('muestra el título opcional pero compra con el identificador del evento', async () => {
    pintar({ eventoTitulo: 'Subsonic Belgium' });
    expect(screen.getByText('Subsonic Belgium')).toBeInTheDocument();
    expect(screen.queryByText('evento-1')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar compra' }));
    expect(comprarEntrada).toHaveBeenCalledWith({ evento_id: 'evento-1', tipo_pase: 'DAY', token_pago: 'tok_ok' });
    expect(await screen.findByRole('heading', { name: 'Subsonic' })).toBeInTheDocument();
  });
  it('muestra el rechazo del backend y permite corregir el token', async () => {
    vi.mocked(comprarEntrada).mockRejectedValue(new Error('Pago rechazado'));
    pintar();
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar compra' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Pago rechazado');
    expect(screen.getByRole('button', { name: 'Confirmar compra' })).toBeEnabled();
  });
  it('evita dos compras mientras el pago está pendiente', async () => {
    vi.mocked(comprarEntrada).mockReturnValue(new Promise(() => {}));
    pintar();
    await userEvent.dblClick(screen.getByRole('button', { name: 'Confirmar compra' }));
    expect(comprarEntrada).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Procesando compra…' })).toBeDisabled();
  });
  it('no permite comprar sin sesión de cliente o sin cupo', () => {
    vi.mocked(useSesion).mockReturnValue({ rol: null, perfil: null });
    const { rerender } = pintar();
    expect(screen.getByRole('alert')).toHaveTextContent('Inicia sesión como cliente');
    expect(screen.getByRole('button', { name: 'Confirmar compra' })).toBeDisabled();
    vi.mocked(useSesion).mockReturnValue({ rol: 'cliente', perfil: { activo: true } });
    rerender(<ModalCheckout abierto onCerrar={vi.fn()} eventoId="evento-1" tarifa={{ ...tarifa, disponibles: 0 }} />);
    expect(screen.getByRole('alert')).toHaveTextContent('No quedan entradas');
  });
  it('respeta abierto y onCerrar y se puede cerrar con Escape', () => {
    const onCerrar = vi.fn();
    const { rerender } = pintar({ onCerrar });
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onCerrar).toHaveBeenCalledTimes(1);
    rerender(<ModalCheckout abierto={false} onCerrar={onCerrar} eventoId="evento-1" tarifa={tarifa} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
