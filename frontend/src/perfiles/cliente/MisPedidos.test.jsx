import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorApi } from '../../api/cliente';
import { listarEventos } from '../../api/espacios';
import { cambiarEstadoPedido, listarPedidos } from '../../api/tienda';
import MisPedidos from './MisPedidos';

vi.mock('../../api/tienda', () => ({ listarPedidos: vi.fn(), cambiarEstadoPedido: vi.fn() }));
vi.mock('../../api/espacios', () => ({ listarEventos: vi.fn() }));

const pedido = (id, estado, extra = {}) => ({
  id, usuario_id: 'uid-cliente-david', estado, importe_total: 59.98, entrega: 'RECOGIDA_EVENTO',
  evento_id_recogida: 'evento-belgium', direccion_envio: null, pago_ref: 'pay_1', creado_en: '2026-11-10T10:00:00Z',
  lineas: [{ producto_id: 'camiseta-2026', producto_nombre: 'Camiseta Oficial', variante_id: `v-${id}`, talla: 'M',
    cantidad: 2, precio_unitario: 29.99 }],
  ...extra,
});
const pintar = () => render(<MemoryRouter><MisPedidos /></MemoryRouter>);

describe('MisPedidos', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    vi.mocked(listarEventos).mockResolvedValue({ datos: [{ id: 'evento-belgium', titulo: 'Subsonic Belgium' }], total: 1 });
    vi.mocked(listarPedidos).mockResolvedValue({
      datos: [pedido('pedido-1', 'PAGADO'), pedido('pedido-2', 'ENVIADO', { entrega: 'DOMICILIO', direccion_envio: 'Calle Mayor 1' })],
      total: 2,
    });
  });

  it('pinta los pedidos con sus líneas, su entrega y su estado', async () => {
    pintar();
    const primero = await screen.findByRole('article', { name: 'Pedido pedido-1' });
    expect(within(primero).getByText('2 × Camiseta Oficial (M)')).toBeInTheDocument();
    expect(within(primero).getByText('Pagado')).toBeInTheDocument();
    expect(await within(primero).findByText(/Recogida en el puesto oficial de Subsonic Belgium/)).toBeInTheDocument();
    const segundo = screen.getByRole('article', { name: 'Pedido pedido-2' });
    expect(within(segundo).getByText('Envío a: Calle Mayor 1')).toBeInTheDocument();
    expect(within(segundo).queryByRole('button', { name: 'Cancelar pedido' })).not.toBeInTheDocument();
  });

  it('cancela un pedido pagado y recarga la lista', async () => {
    pintar();
    const primero = await screen.findByRole('article', { name: 'Pedido pedido-1' });
    vi.mocked(listarPedidos).mockResolvedValue({ datos: [pedido('pedido-1', 'CANCELADO')], total: 1 });
    await userEvent.click(within(primero).getByRole('button', { name: 'Cancelar pedido' }));
    expect(cambiarEstadoPedido).toHaveBeenCalledWith('pedido-1', 'CANCELADO');
    expect(await screen.findByRole('status')).toHaveTextContent('Pedido pedido-1 cancelado');
    expect(await screen.findByText('Cancelado')).toBeInTheDocument();
  });

  it('muestra el error del backend si ya no se puede cancelar', async () => {
    vi.mocked(cambiarEstadoPedido).mockRejectedValue(new ErrorApi(409, 'TRANSICION_NO_PERMITIDA',
      'Solo se pueden cancelar pedidos en estado PAGADO (está PREPARADO)'));
    pintar();
    await userEvent.click(within(await screen.findByRole('article', { name: 'Pedido pedido-1' }))
      .getByRole('button', { name: 'Cancelar pedido' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Solo se pueden cancelar pedidos en estado PAGADO');
  });

  it('sin pedidos enlaza a la tienda', async () => {
    vi.mocked(listarPedidos).mockResolvedValue({ datos: [], total: 0 });
    pintar();
    expect(await screen.findByRole('link', { name: 'Ir a la tienda' })).toHaveAttribute('href', '/tienda');
  });
});
