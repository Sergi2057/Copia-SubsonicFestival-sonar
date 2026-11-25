import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarEventos } from '../../api/espacios';
import { ErrorApi } from '../../api/cliente';
import { crearPedido, listarProductos } from '../../api/tienda';
import { registrarInteraccion } from '../../analitica/interacciones';
import { useSesion } from '../../sesion/SesionContext';
import Tienda from './Tienda';

vi.mock('../../api/tienda', () => ({ listarProductos: vi.fn(), crearPedido: vi.fn() }));
vi.mock('../../api/espacios', () => ({ listarEventos: vi.fn() }));
vi.mock('../../analitica/interacciones', () => ({ registrarInteraccion: vi.fn() }));
vi.mock('../../sesion/SesionContext', () => ({ useSesion: vi.fn() }));

const CAMISETA = {
  id: 'camiseta-2026', nombre: 'Camiseta Oficial', descripcion: 'Camiseta Subsonic 2026', precio: 29.99,
  imagen_url: '/camiseta.jpg', evento_id: null, activo: true,
  variantes: [{ id: 'v-s', talla: 'S', stock: 0, activa: true }, { id: 'v-m', talla: 'M', stock: 3, activa: true }],
};
const GORRA = { id: 'gorra-black', nombre: 'Gorra Black', precio: 19.99, imagen_url: null, evento_id: null, activo: true,
  variantes: [{ id: 'v-u', talla: 'UNICA', stock: 100, activa: true }] };
const EXCLUSIVA = { ...CAMISETA, id: 'camiseta-belgium', nombre: 'Camiseta Belgium', evento_id: 'evento-belgium' };

const pintar = () => render(<MemoryRouter><Tienda /></MemoryRouter>);

async function anadirAlCarrito(nombre, talla, cantidad = 1) {
  await userEvent.click(await screen.findByRole('button', { name: `Ver ${nombre}` }));
  const ficha = screen.getByRole('dialog');
  if (talla) await userEvent.click(within(ficha).getByRole('button', { name: talla }));
  if (cantidad > 1) await userEvent.selectOptions(within(ficha).getByLabelText('Cantidad'), String(cantidad));
  await userEvent.click(within(ficha).getByRole('button', { name: 'Añadir al carrito' }));
}

describe('Tienda', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useSesion).mockReturnValue({ rol: 'cliente' });
    vi.mocked(listarProductos).mockImplementation(async ({ evento_id: eventoId }) => ({
      datos: eventoId ? [CAMISETA, GORRA, EXCLUSIVA] : [CAMISETA, GORRA], total: 2,
    }));
    vi.mocked(listarEventos).mockResolvedValue({ datos: [{ id: 'evento-belgium', titulo: 'Subsonic Belgium', estado: 'PUBLICADO' }], total: 1 });
  });

  it('pinta el catálogo y añade el merchandising exclusivo del evento elegido', async () => {
    pintar();
    expect(await screen.findByText('Camiseta Oficial')).toBeInTheDocument();
    expect(screen.getByText('29,99 €')).toBeInTheDocument();
    expect(screen.queryByText('Camiseta Belgium')).not.toBeInTheDocument();
    await screen.findByRole('option', { name: 'Subsonic Belgium' });
    await userEvent.selectOptions(screen.getByLabelText('Merchandising exclusivo de'), 'evento-belgium');
    expect(await screen.findByText('Camiseta Belgium')).toBeInTheDocument();
    expect(listarProductos).toHaveBeenLastCalledWith({ evento_id: 'evento-belgium', limite: 100 });
  });

  it('al abrir un producto lo registra y no deja elegir tallas agotadas', async () => {
    pintar();
    await userEvent.click(await screen.findByRole('button', { name: 'Ver Camiseta Oficial' }));
    const ficha = screen.getByRole('dialog');
    expect(within(ficha).getByRole('button', { name: 'S' })).toBeDisabled();
    expect(within(ficha).getByRole('button', { name: 'M' })).toHaveAttribute('aria-pressed', 'true');
    expect(within(ficha).getByText('¡Solo quedan 3!')).toBeInTheDocument();
    expect(registrarInteraccion).toHaveBeenCalledWith('VER_PRODUCTO', 'camiseta-2026');
  });

  it('compra con recogida en un evento y vacía el carrito', async () => {
    vi.mocked(crearPedido).mockResolvedValue({ id: 'pedido-1a2b3c4d', importe_total: 79.97 });
    pintar();
    await anadirAlCarrito('Camiseta Oficial', 'M', 2);
    await anadirAlCarrito('Gorra Black');
    expect(screen.getByText('Total').parentElement).toHaveTextContent('79,97 €');

    await userEvent.click(screen.getByLabelText(/Recoger en un evento/));
    await userEvent.selectOptions(screen.getByLabelText('Evento de recogida'), 'evento-belgium');
    await userEvent.click(screen.getByRole('button', { name: 'Pagar 79,97 €' }));

    expect(crearPedido).toHaveBeenCalledWith({
      lineas: [{ variante_id: 'v-m', cantidad: 2 }, { variante_id: 'v-u', cantidad: 1 }],
      entrega: 'RECOGIDA_EVENTO', direccion_envio: undefined, evento_id_recogida: 'evento-belgium',
      token_pago: expect.stringMatching(/^tok_/),
    });
    expect(await screen.findByText(/Pedido pedido-1a2b3c4d realizado/)).toBeInTheDocument();
    expect(screen.getByText('El carrito está vacío.')).toBeInTheDocument();
  });

  it('muestra el error del backend y conserva el carrito', async () => {
    vi.mocked(crearPedido).mockRejectedValue(new ErrorApi(409, 'SIN_STOCK', 'No hay stock suficiente de la talla M',
      { disponible: 1 }));
    pintar();
    await anadirAlCarrito('Camiseta Oficial', 'M', 2);
    await userEvent.type(screen.getByLabelText('Dirección de envío'), 'Calle Mayor 1, Cáceres');
    await userEvent.click(screen.getByRole('button', { name: /^Pagar/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No hay stock suficiente de la talla M. Quedan 1.');
    expect(screen.getByText(/2 × Camiseta Oficial/)).toBeInTheDocument();
  });

  it('sin sesión de cliente se puede llenar el carrito pero pide iniciar sesión para pagar', async () => {
    vi.mocked(useSesion).mockReturnValue({ rol: null });
    pintar();
    await anadirAlCarrito('Gorra Black');
    expect(screen.getByText(/Inicia sesión como cliente/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Pagar/ })).not.toBeInTheDocument();
  });

  it('muestra el error si no carga el catálogo', async () => {
    vi.mocked(listarProductos).mockRejectedValue(new Error('ms-tienda no responde'));
    pintar();
    expect(await screen.findByRole('alert')).toHaveTextContent('ms-tienda no responde');
  });
});
