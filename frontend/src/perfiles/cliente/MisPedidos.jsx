// src/perfiles/cliente/MisPedidos.jsx — Dueño: Sergio
// Pedidos de merchandising del cliente con su estado y cancelación (solo si están PAGADO).
// API: GET /pedidos, PATCH /pedidos/{id} (ms-tienda)
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { cambiarEstadoPedido, listarPedidos } from '../../api/tienda';
import { useEventos } from '../../analitica/useDatos';
import { useDatosRecargables } from '../useDatosRecargables';
import { ESTADOS_PEDIDO, euros, fechaPedido, mensajeError, nombreTalla } from '../../pages/Tienda/tiendaUtil';
import '../escaletaTienda.css';

const cargarPedidos = () => listarPedidos({ limite: 100 }).then(({ datos }) => datos);

const claseEstado = (estado) => ({
  CANCELADO: 'et-insignia-roja', ENTREGADO: 'et-insignia-verde', PAGADO: 'et-insignia-gris',
}[estado] || '');

export default function MisPedidos() {
  const pedidos = useDatosRecargables(cargarPedidos);
  const eventos = useEventos();
  const nombreEvento = (eventoId) => eventos.datos?.find((e) => e.id === eventoId)?.titulo || eventoId;
  const [ocupado, setOcupado] = useState(null);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');

  const cancelar = async (pedido) => {
    if (!window.confirm(`¿Cancelar el pedido ${pedido.id}? Se te devolverán ${euros(pedido.importe_total)}.`)) return;
    setOcupado(pedido.id);
    setError('');
    setMensaje('');
    try {
      await cambiarEstadoPedido(pedido.id, 'CANCELADO');
      setMensaje(`Pedido ${pedido.id} cancelado. El reembolso llegará en unos días.`);
      pedidos.recargar();
    } catch (e) {
      setError(mensajeError(e));
    } finally {
      setOcupado(null);
    }
  };

  return (
    <div className="et-panel" aria-labelledby="et-pedidos-titulo">
      <header className="et-panel-heading">
        <h2 id="et-pedidos-titulo">Mis pedidos</h2>
        <p>Tus compras de merchandising. Puedes cancelar un pedido mientras no se haya empezado a preparar.</p>
      </header>
      {error && <p className="et-error" role="alert">{error}</p>}
      {mensaje && <p className="et-ok" role="status">{mensaje}</p>}
      {pedidos.cargando && !pedidos.datos && <p role="status">Cargando pedidos…</p>}
      {pedidos.error && <p className="et-error" role="alert">{pedidos.error.message}</p>}
      {pedidos.datos?.length === 0 && (
        <p>Todavía no has hecho ningún pedido. <Link to="/tienda">Ir a la tienda</Link></p>
      )}
      <div className="et-tarjetas">
        {(pedidos.datos || []).map((pedido) => (
          <article key={pedido.id} className="et-tarjeta" aria-label={`Pedido ${pedido.id}`}>
            <div className="et-tarjeta-cabecera">
              <div>
                <h3>{pedido.id}</h3>
                <span className="et-apagado">{fechaPedido(pedido.creado_en)}</span>
              </div>
              <span className={`et-insignia ${claseEstado(pedido.estado)}`}>{ESTADOS_PEDIDO[pedido.estado] || pedido.estado}</span>
            </div>
            <ul className="et-lista">
              {pedido.lineas.map((linea) => (
                <li key={linea.variante_id}>
                  <span>{linea.cantidad} × {linea.producto_nombre} ({nombreTalla(linea.talla)})</span>
                  <span>{euros(linea.precio_unitario * linea.cantidad)}</span>
                </li>
              ))}
            </ul>
            <p>
              {pedido.entrega === 'DOMICILIO'
                ? `Envío a: ${pedido.direccion_envio || '—'}`
                : `Recogida en el puesto oficial de ${nombreEvento(pedido.evento_id_recogida)}`}
            </p>
            <div className="et-acciones">
              <span className="et-total">{euros(pedido.importe_total)}</span>
              {pedido.estado === 'PAGADO' && (
                <button type="button" className="et-peligro" disabled={ocupado !== null} onClick={() => cancelar(pedido)}>
                  {ocupado === pedido.id ? 'Cancelando…' : 'Cancelar pedido'}
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
