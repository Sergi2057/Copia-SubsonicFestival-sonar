// src/api/tienda.js — llamadas a ms-tienda (a través del gateway).  Dueño: Sergio
// Rutas en docs/openapi/ms-tienda.yaml.
import { api } from './cliente';

const id = encodeURIComponent;

// ── Catálogo ────────────────────────────────────────────────
// El administrador recibe también los productos y tallas retirados (activo / activa = false)
export const listarProductos = (filtros) => api('/productos', { parametros: filtros, conTotal: true });
export const obtenerProducto = (productoId) => api(`/productos/${id(productoId)}`);
export const crearProducto = (datos) => api('/productos', { metodo: 'POST', cuerpo: datos });
/** PUT: hay que enviar el producto completo, con el mismo id. */
export const modificarProducto = (productoId, datos) => api(`/productos/${id(productoId)}`, { metodo: 'PUT', cuerpo: datos });
/** Retirada lógica: deja de salir en el catálogo, los pedidos antiguos lo conservan. */
export const retirarProducto = (productoId) => api(`/productos/${id(productoId)}`, { metodo: 'DELETE' });

// ── Tallas (variantes) ──────────────────────────────────────
/** Si la talla existía retirada, se reactiva con el stock nuevo. */
export const crearVariante = (productoId, datos) => api(`/productos/${id(productoId)}/variantes`, {
  metodo: 'POST', cuerpo: datos,
});
/** cambios: { talla }, { stock } o los dos. */
export const modificarVariante = (productoId, varianteId, cambios) => api(
  `/productos/${id(productoId)}/variantes/${id(varianteId)}`, { metodo: 'PATCH', cuerpo: cambios },
);
/** Sin ventas se borra; con ventas terminadas se retira; con pedidos pendientes, 409. */
export const eliminarVariante = (productoId, varianteId) => api(
  `/productos/${id(productoId)}/variantes/${id(varianteId)}`, { metodo: 'DELETE' },
);

// ── Pedidos ─────────────────────────────────────────────────
/** El cliente recibe solo los suyos; el administrador, todos (filtros: estado, evento_id_recogida). */
export const listarPedidos = (filtros) => api('/pedidos', { parametros: filtros, conTotal: true });
export const obtenerPedido = (pedidoId) => api(`/pedidos/${id(pedidoId)}`);
/** datos: { lineas: [{ variante_id, cantidad }], entrega, direccion_envio | evento_id_recogida, token_pago } */
export const crearPedido = (datos) => api('/pedidos', { metodo: 'POST', cuerpo: datos });
/** El cliente solo puede pasar a CANCELADO (si está PAGADO); el administrador avanza los estados. */
export const cambiarEstadoPedido = (pedidoId, estado) => api(`/pedidos/${id(pedidoId)}`, {
  metodo: 'PATCH', cuerpo: { estado },
});
