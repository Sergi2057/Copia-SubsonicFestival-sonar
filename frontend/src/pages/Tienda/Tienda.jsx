// src/pages/Tienda/Tienda.jsx — Dueño: Sergio
// Catálogo con tallas y stock, carrito y pedido con entrega a domicilio o recogida en un evento.
// API: GET /productos, POST /pedidos (ms-tienda); GET /eventos (ms-espacios) para el merch exclusivo y la recogida
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { crearPedido, listarProductos } from '../../api/tienda';
import { registrarInteraccion } from '../../analitica/interacciones';
import { useDatos, useEventos } from '../../analitica/useDatos';
import { useSesion } from '../../sesion/SesionContext';
import { euros, mensajeError, nombreTalla } from './tiendaUtil';
import './Tienda.css';

const MAX_POR_LINEA = 10;   // lo que admite ms-tienda por línea
const cargarCatalogo = (eventoId) => listarProductos({ evento_id: eventoId || undefined, limite: 100 })
  .then(({ datos }) => datos);

function FichaProducto({ producto, alAnadir, alCerrar }) {
  const tallas = producto.variantes;
  const [talla, setTalla] = useState(() => tallas.find((v) => v.stock > 0)?.id ?? null);
  const [cantidad, setCantidad] = useState(1);
  const variante = tallas.find((v) => v.id === talla);
  const maximo = Math.min(variante?.stock ?? 0, MAX_POR_LINEA);

  return (
    <div className="tienda-fondo" role="presentation" onClick={alCerrar}>
      <div className="tienda-modal" role="dialog" aria-modal="true" aria-labelledby="tienda-ficha-titulo"
        onClick={(e) => e.stopPropagation()}>
        <button type="button" className="tienda-cerrar" onClick={alCerrar} aria-label="Cerrar">×</button>
        {producto.imagen_url && <img src={producto.imagen_url} alt={producto.nombre} className="tienda-modal-img" />}
        <div className="tienda-modal-info">
          <h3 id="tienda-ficha-titulo">{producto.nombre}</h3>
          <strong className="tienda-precio">{euros(producto.precio)}</strong>
          {producto.descripcion && <p>{producto.descripcion}</p>}
          <p className="tienda-etiqueta">Talla</p>
          <div className="tienda-tallas" role="group" aria-label="Talla">
            {tallas.map((v) => (
              <button key={v.id} type="button" disabled={v.stock === 0} aria-pressed={v.id === talla}
                className={`tienda-talla ${v.id === talla ? 'activa' : ''}`}
                onClick={() => { setTalla(v.id); setCantidad(1); }}
                title={v.stock === 0 ? 'Agotada' : `${v.stock} disponibles`}>
                {nombreTalla(v.talla)}
              </button>
            ))}
          </div>
          {tallas.length > 0 && !variante && <p className="tienda-aviso">Agotado en todas las tallas.</p>}
          {variante && variante.stock < 5 && <p className="tienda-aviso">¡Solo quedan {variante.stock}!</p>}
          <label className="tienda-etiqueta" htmlFor="tienda-cantidad">Cantidad</label>
          <select id="tienda-cantidad" value={cantidad} disabled={!variante}
            onChange={(e) => setCantidad(Number(e.target.value))}>
            {Array.from({ length: Math.max(maximo, 1) }, (_, i) => i + 1).map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <button type="button" className="btn-nav" disabled={!variante}
            onClick={() => alAnadir(producto, variante, cantidad)}>
            Añadir al carrito
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Tienda() {
  const { rol } = useSesion();
  const esCliente = rol === 'cliente';
  const [eventoId, setEventoId] = useState('');
  const catalogo = useDatos(cargarCatalogo, eventoId);
  const eventos = useEventos();
  const [abierto, setAbierto] = useState(null);
  const [carrito, setCarrito] = useState([]);
  const [entrega, setEntrega] = useState('DOMICILIO');
  const [direccion, setDireccion] = useState('');
  const [eventoRecogida, setEventoRecogida] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  const [confirmado, setConfirmado] = useState(null);

  const productos = catalogo.datos || [];
  const listaEventos = (eventos.datos || []).filter((e) => e.estado === 'PUBLICADO' || !e.estado);
  const total = carrito.reduce((suma, linea) => suma + linea.precio * linea.cantidad, 0);

  const abrir = (producto) => {
    setAbierto(producto);
    registrarInteraccion('VER_PRODUCTO', producto.id);
  };

  const anadir = (producto, variante, cantidad) => {
    setCarrito((actual) => {
      const existente = actual.find((l) => l.variante_id === variante.id);
      if (existente) {
        return actual.map((l) => (l.variante_id === variante.id
          ? { ...l, cantidad: Math.min(l.cantidad + cantidad, variante.stock, MAX_POR_LINEA) } : l));
      }
      return [...actual, { variante_id: variante.id, nombre: producto.nombre, talla: variante.talla,
        precio: producto.precio, cantidad }];
    });
    setAbierto(null);
    setConfirmado(null);
  };

  const pagar = async (e) => {
    e.preventDefault();
    setError('');
    setEnviando(true);
    try {
      const pedido = await crearPedido({
        lineas: carrito.map(({ variante_id: varianteId, cantidad }) => ({ variante_id: varianteId, cantidad })),
        entrega,
        direccion_envio: entrega === 'DOMICILIO' ? direccion.trim() : undefined,
        evento_id_recogida: entrega === 'RECOGIDA_EVENTO' ? eventoRecogida : undefined,
        token_pago: `tok_web_${Date.now()}`,   // pasarela simulada: nunca se envían datos de tarjeta
      });
      setConfirmado(pedido);
      setCarrito([]);
      catalogo.recargar();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <main id="tienda" className="bg-gradient tienda-pagina">
      <section>
        <div className="section-label">Official Merch</div>
        <h2>TIENDA SUBSONIC</h2>

        <div className="tienda-filtro">
          <label htmlFor="tienda-evento">Merchandising exclusivo de</label>
          <select id="tienda-evento" value={eventoId} onChange={(e) => setEventoId(e.target.value)}>
            <option value="">Solo el general</option>
            {listaEventos.map((ev) => <option key={ev.id} value={ev.id}>{ev.titulo}</option>)}
          </select>
        </div>

        <div className="tienda-layout">
          <div>
            {catalogo.cargando && <p role="status">Cargando catálogo…</p>}
            {catalogo.error && <p className="tienda-error" role="alert">{catalogo.error.message}</p>}
            {!catalogo.cargando && !catalogo.error && productos.length === 0 && <p>No hay productos a la venta.</p>}
            <div className="tienda-grid">
              {productos.map((producto) => {
                const agotado = !producto.variantes.some((v) => v.stock > 0);
                return (
                  <div key={producto.id} className="producto-card">
                    {producto.imagen_url && <img src={producto.imagen_url} alt={producto.nombre} />}
                    <div className="producto-info">
                      <span>{producto.nombre}</span>
                      {producto.evento_id && <small className="tienda-exclusivo">Edición exclusiva</small>}
                      <strong>{euros(producto.precio)}</strong>
                      <button type="button" className="btn-nav" onClick={() => abrir(producto)}
                        aria-label={`Ver ${producto.nombre}`}>
                        {agotado ? 'Agotado · ver' : 'Ver producto'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <aside className="tienda-carrito" aria-labelledby="tienda-carrito-titulo">
            <h3 id="tienda-carrito-titulo">Tu carrito</h3>
            {confirmado && (
              <p className="tienda-ok" role="status">
                Pedido {confirmado.id} realizado por {euros(confirmado.importe_total)}. Puedes seguirlo en{' '}
                <Link to="/perfil">Mi perfil → Mis pedidos</Link>.
              </p>
            )}
            {carrito.length === 0 ? <p>El carrito está vacío.</p> : (
              <>
                <ul className="tienda-lineas">
                  {carrito.map((linea) => (
                    <li key={linea.variante_id}>
                      <span>{linea.cantidad} × {linea.nombre} ({nombreTalla(linea.talla)})</span>
                      <span>{euros(linea.precio * linea.cantidad)}</span>
                      <button type="button" className="tienda-quitar" aria-label={`Quitar ${linea.nombre} ${linea.talla}`}
                        onClick={() => setCarrito((actual) => actual.filter((l) => l.variante_id !== linea.variante_id))}>
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
                <p className="tienda-total">Total <strong>{euros(total)}</strong></p>

                {!esCliente ? (
                  <p className="tienda-aviso">Inicia sesión como cliente (MI PERFIL) para completar la compra.</p>
                ) : (
                  <form onSubmit={pagar} className="tienda-pago">
                    <fieldset>
                      <legend>Entrega</legend>
                      <label>
                        <input type="radio" name="entrega" value="DOMICILIO" checked={entrega === 'DOMICILIO'}
                          onChange={() => setEntrega('DOMICILIO')} /> A domicilio
                      </label>
                      <label>
                        <input type="radio" name="entrega" value="RECOGIDA_EVENTO" checked={entrega === 'RECOGIDA_EVENTO'}
                          onChange={() => setEntrega('RECOGIDA_EVENTO')} /> Recoger en un evento
                      </label>
                    </fieldset>
                    {entrega === 'DOMICILIO' ? (
                      <label>Dirección de envío
                        <textarea required value={direccion} onChange={(e) => setDireccion(e.target.value)} rows={2} />
                      </label>
                    ) : (
                      <label>Evento de recogida
                        <select required value={eventoRecogida} onChange={(e) => setEventoRecogida(e.target.value)}>
                          <option value="">Elige un evento</option>
                          {listaEventos.map((ev) => <option key={ev.id} value={ev.id}>{ev.titulo}</option>)}
                        </select>
                      </label>
                    )}
                    <p className="tienda-nota">Pago simulado: no se piden ni se guardan datos de tarjeta.</p>
                    {error && <p className="tienda-error" role="alert">{error}</p>}
                    <button type="submit" className="btn-nav" disabled={enviando}>
                      {enviando ? 'Procesando pago…' : `Pagar ${euros(total)}`}
                    </button>
                  </form>
                )}
              </>
            )}
          </aside>
        </div>
      </section>

      {abierto && <FichaProducto key={abierto.id} producto={abierto} alAnadir={anadir} alCerrar={() => setAbierto(null)} />}
    </main>
  );
}
