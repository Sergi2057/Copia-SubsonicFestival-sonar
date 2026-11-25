import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorApi } from '../../api/cliente';
import { listarEventos } from '../../api/espacios';
import {
  cambiarEstadoPedido, crearProducto, crearVariante, eliminarVariante, listarPedidos, listarProductos, modificarVariante,
  retirarProducto,
} from '../../api/tienda';
import Tienda from './Tienda';

vi.mock('../../api/tienda', () => ({
  listarProductos: vi.fn(), crearProducto: vi.fn(), modificarProducto: vi.fn(), retirarProducto: vi.fn(),
  crearVariante: vi.fn(), modificarVariante: vi.fn(), eliminarVariante: vi.fn(),
  listarPedidos: vi.fn(), cambiarEstadoPedido: vi.fn(),
}));
vi.mock('../../api/espacios', () => ({ listarEventos: vi.fn() }));

const CAMISETA = {
  id: 'camiseta-2026', nombre: 'Camiseta Oficial', precio: 29.99, descripcion: null, imagen_url: null, evento_id: null,
  activo: true, variantes: [{ id: 'v-m', talla: 'M', stock: 30, activa: true }, { id: 'v-l', talla: 'L', stock: 0, activa: false }],
};
const EXCLUSIVA = { ...CAMISETA, id: 'camiseta-belgium', nombre: 'Camiseta Belgium', evento_id: 'evento-belgium',
  variantes: [{ id: 'v-b', talla: 'M', stock: 3, activa: true }] };

describe('admin · Tienda', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    vi.mocked(listarEventos).mockResolvedValue({ datos: [{ id: 'evento-belgium', titulo: 'Subsonic Belgium' }], total: 1 });
    vi.mocked(listarProductos).mockImplementation(async ({ evento_id: eventoId }) => ({
      datos: eventoId ? [CAMISETA, EXCLUSIVA] : [CAMISETA], total: 1,
    }));
  });

  it('junta el merchandising general y el de cada evento, con sus tallas retiradas', async () => {
    render(<Tienda />);
    const camiseta = await screen.findByRole('article', { name: 'Camiseta Oficial' });
    expect(screen.getByRole('article', { name: 'Camiseta Belgium' })).toHaveTextContent('Subsonic Belgium');
    expect(screen.getAllByRole('article')).toHaveLength(2);
    expect(within(camiseta).getByText('Retirada')).toBeInTheDocument();
    expect(listarProductos).toHaveBeenCalledWith({ evento_id: 'evento-belgium', limite: 100 });
  });

  it('crea un producto', async () => {
    vi.mocked(crearProducto).mockResolvedValue({});
    render(<Tienda />);
    await screen.findByRole('article', { name: 'Camiseta Oficial' });
    const form = screen.getByRole('form', { name: 'Nuevo producto' });
    await userEvent.type(within(form).getByLabelText('Identificador'), 'gorra-2027');
    await userEvent.type(within(form).getByLabelText('Nombre'), 'Gorra 2027');
    await userEvent.type(within(form).getByLabelText('Precio (€)'), '21.5');
    await userEvent.selectOptions(within(form).getByLabelText('Exclusivo de un evento'), 'evento-belgium');
    await userEvent.click(within(form).getByRole('button', { name: 'Crear producto' }));
    expect(crearProducto).toHaveBeenCalledWith({ id: 'gorra-2027', nombre: 'Gorra 2027', precio: 21.5, descripcion: null,
      imagen_url: null, evento_id: 'evento-belgium', activo: true });
    expect(await screen.findByRole('status')).toHaveTextContent('Producto Gorra 2027 creado');
  });

  it('cambia la talla y el stock, añade y elimina tallas y retira el producto', async () => {
    render(<Tienda />);
    const camiseta = await screen.findByRole('article', { name: 'Camiseta Oficial' });
    await userEvent.selectOptions(within(camiseta).getByLabelText('Talla de Camiseta Oficial M'), 'XL');
    const stock = within(camiseta).getByLabelText('Stock de Camiseta Oficial M');
    await userEvent.clear(stock);
    await userEvent.type(stock, '12');
    await userEvent.click(within(camiseta).getAllByRole('button', { name: 'Guardar' })[0]);
    expect(modificarVariante).toHaveBeenCalledWith('camiseta-2026', 'v-m', { talla: 'XL', stock: 12 });

    // La L está retirada: se puede volver a añadir (ms-tienda la reactiva)
    await userEvent.selectOptions(await within(camiseta).findByLabelText('Nueva talla de Camiseta Oficial'), 'L');
    await userEvent.click(within(camiseta).getByRole('button', { name: 'Añadir talla' }));
    expect(crearVariante).toHaveBeenCalledWith('camiseta-2026', { talla: 'L', stock: 0 });

    await userEvent.click(within(camiseta).getByRole('button', { name: 'Eliminar talla Camiseta Oficial M' }));
    expect(eliminarVariante).toHaveBeenCalledWith('camiseta-2026', 'v-m');

    await userEvent.click(within(camiseta).getByRole('button', { name: 'Retirar' }));
    expect(retirarProducto).toHaveBeenCalledWith('camiseta-2026');
  });

  it('muestra el error del backend al eliminar una talla con pedidos pendientes', async () => {
    vi.mocked(eliminarVariante).mockRejectedValue(new ErrorApi(409, 'VARIANTE_CON_PEDIDOS_PENDIENTES',
      'La talla M tiene pedidos pendientes de entregar'));
    render(<Tienda />);
    const camiseta = await screen.findByRole('article', { name: 'Camiseta Oficial' });
    await userEvent.click(within(camiseta).getByRole('button', { name: 'Eliminar talla Camiseta Oficial M' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('La talla M tiene pedidos pendientes de entregar');
  });

  it('avanza el estado de los pedidos según su entrega', async () => {
    const pedido = (id, estado, entrega) => ({ id, estado, entrega, usuario_id: 'uid-cliente-david', importe_total: 29.99,
      evento_id_recogida: entrega === 'RECOGIDA_EVENTO' ? 'evento-belgium' : null, direccion_envio: 'Calle Mayor 1',
      creado_en: '2026-11-10T10:00:00Z', lineas: [{ producto_nombre: 'Camiseta Oficial', variante_id: `v-${id}`, talla: 'M',
        cantidad: 1, precio_unitario: 29.99 }] });
    vi.mocked(listarPedidos).mockResolvedValue({ datos: [pedido('p-1', 'PREPARADO', 'RECOGIDA_EVENTO'),
      pedido('p-2', 'PREPARADO', 'DOMICILIO')], total: 2 });
    render(<Tienda />);
    await userEvent.click(screen.getByRole('tab', { name: 'Pedidos' }));
    const recogida = await screen.findByRole('article', { name: 'Pedido p-1' });
    expect(within(recogida).getByText('Recogida en Subsonic Belgium')).toBeInTheDocument();
    expect(within(screen.getByRole('article', { name: 'Pedido p-2' })).getByRole('button', { name: 'Marcar enviado' }))
      .toBeInTheDocument();
    await userEvent.click(within(recogida).getByRole('button', { name: 'Marcar listo para recoger' }));
    expect(cambiarEstadoPedido).toHaveBeenCalledWith('p-1', 'LISTO_RECOGIDA');

    await userEvent.selectOptions(screen.getByLabelText('Estado'), 'ENTREGADO');
    expect(listarPedidos).toHaveBeenLastCalledWith({ estado: 'ENTREGADO', limite: 100 });
  });
});
