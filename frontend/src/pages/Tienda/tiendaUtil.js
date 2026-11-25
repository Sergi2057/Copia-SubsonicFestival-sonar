// src/pages/Tienda/tiendaUtil.js — Dueño: Sergio
// Utilidades de la tienda compartidas por el catálogo, Mis pedidos y el panel de admin.

export const TALLAS = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'UNICA'];
export const nombreTalla = (talla) => (talla === 'UNICA' ? 'Única' : talla);

export const euros = (importe) => `${Number(importe ?? 0).toLocaleString('es-ES', {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
})} €`;

export const ESTADOS_PEDIDO = {
  PAGADO: 'Pagado',
  PREPARADO: 'Preparado',
  ENVIADO: 'Enviado',
  LISTO_RECOGIDA: 'Listo para recoger',
  ENTREGADO: 'Entregado',
  CANCELADO: 'Cancelado',
};

/** Estados a los que puede pasar el administrador (igual que ms-tienda). */
export function siguientesEstados(pedido) {
  switch (pedido.estado) {
    case 'PAGADO': return ['PREPARADO'];
    case 'PREPARADO': return [pedido.entrega === 'DOMICILIO' ? 'ENVIADO' : 'LISTO_RECOGIDA'];
    case 'ENVIADO':
    case 'LISTO_RECOGIDA': return ['ENTREGADO'];
    default: return [];
  }
}

export const fechaPedido = (iso) => new Date(iso).toLocaleDateString('es-ES', {
  day: 'numeric', month: 'short', year: 'numeric',
});

/** Mensaje para el usuario a partir del error del backend (ErrorApi). */
export function mensajeError(error) {
  switch (error?.codigo) {
    case 'SIN_STOCK': return `${error.message}. Quedan ${error.detalles?.disponible ?? 0}.`;
    case 'PAGO_RECHAZADO': return 'La pasarela ha rechazado el pago. Prueba con otro método de pago.';
    default: return error?.message || 'No se ha podido completar la operación.';
  }
}
