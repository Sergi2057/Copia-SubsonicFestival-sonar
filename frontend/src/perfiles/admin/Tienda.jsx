// src/perfiles/admin/Tienda.jsx — Dueño: Sergio
// Productos (crear, editar, retirar), sus tallas y stock (añadir, modificar, eliminar) y pedidos (cambiar estado).
// API: /productos, /productos/{id}/variantes, /pedidos (ms-tienda); GET /eventos (ms-espacios)
import { useState } from 'react';
import {
  cambiarEstadoPedido, crearProducto, crearVariante, eliminarVariante, listarPedidos, listarProductos,
  modificarProducto, modificarVariante, retirarProducto,
} from '../../api/tienda';
import { useEventos } from '../../analitica/useDatos';
import { useDatosRecargables } from '../useDatosRecargables';
import {
  ESTADOS_PEDIDO, TALLAS, euros, fechaPedido, mensajeError, nombreTalla, siguientesEstados,
} from '../../pages/Tienda/tiendaUtil';
import '../escaletaTienda.css';

/** Sin evento_id, GET /productos solo da el merch general: se pide también el de cada evento y se junta. */
async function cargarTodosLosProductos(eventoIds) {
  const listas = await Promise.all([undefined, ...eventoIds].map(
    (eventoId) => listarProductos({ evento_id: eventoId, limite: 100 }).then(({ datos }) => datos),
  ));
  const porId = new Map(listas.flat().map((p) => [p.id, p]));
  return [...porId.values()].sort((a, b) => a.id.localeCompare(b.id));
}
const cargarPedidos = (estado) => listarPedidos({ estado: estado || undefined, limite: 100 }).then(({ datos }) => datos);

const productoVacio = { id: '', nombre: '', precio: '', descripcion: '', imagen_url: '', evento_id: '', activo: true };

function FilaVariante({ producto, variante, ocupado, alGuardar, alEliminar }) {
  const [talla, setTalla] = useState(variante.talla);
  const [stock, setStock] = useState(String(variante.stock));
  const cambios = {};
  if (talla !== variante.talla) cambios.talla = talla;
  if (stock !== '' && Number(stock) !== variante.stock) cambios.stock = Number(stock);
  const hayCambios = Object.keys(cambios).length > 0;
  const etiqueta = `${producto.nombre} ${nombreTalla(variante.talla)}`;

  return (
    <tr>
      <td>
        <select value={talla} onChange={(e) => setTalla(e.target.value)} aria-label={`Talla de ${etiqueta}`}>
          {TALLAS.map((t) => <option key={t} value={t}>{nombreTalla(t)}</option>)}
        </select>
      </td>
      <td>
        <input type="number" min="0" value={stock} onChange={(e) => setStock(e.target.value)} aria-label={`Stock de ${etiqueta}`}
          style={{ width: 90 }} />
      </td>
      <td>
        <span className={`et-insignia ${variante.activa ? 'et-insignia-verde' : 'et-insignia-gris'}`}>
          {variante.activa ? 'A la venta' : 'Retirada'}
        </span>
      </td>
      <td className="et-acciones" style={{ marginTop: 0 }}>
        <button type="button" className="et-boton" disabled={!hayCambios || ocupado} onClick={() => alGuardar(variante, cambios)}>
          Guardar
        </button>
        {variante.activa && (
          <button type="button" className="et-peligro" disabled={ocupado} onClick={() => alEliminar(variante)}
            aria-label={`Eliminar talla ${etiqueta}`}>
            Eliminar
          </button>
        )}
      </td>
    </tr>
  );
}

function NuevaTalla({ producto, ocupado, alCrear }) {
  const activas = new Set(producto.variantes.filter((v) => v.activa).map((v) => v.talla));
  const libres = TALLAS.filter((t) => !activas.has(t));
  const [talla, setTalla] = useState(libres[0] || '');
  const [stock, setStock] = useState('0');
  if (libres.length === 0) return null;
  const elegida = libres.includes(talla) ? talla : libres[0];
  return (
    <form className="et-mini-form" onSubmit={(e) => { e.preventDefault(); alCrear(elegida, Number(stock)); }}>
      <label>Nueva talla
        <select value={elegida} onChange={(e) => setTalla(e.target.value)} aria-label={`Nueva talla de ${producto.nombre}`}>
          {libres.map((t) => <option key={t} value={t}>{nombreTalla(t)}</option>)}
        </select>
      </label>
      <label>Stock
        <input type="number" min="0" required value={stock} onChange={(e) => setStock(e.target.value)}
          aria-label={`Stock inicial de ${producto.nombre}`} style={{ width: 90 }} />
      </label>
      <button type="submit" className="et-boton" disabled={ocupado}>Añadir talla</button>
    </form>
  );
}

function Productos({ eventos, avisar }) {
  const listaEventos = eventos.datos || [];
  const productos = useDatosRecargables(eventos.cargando ? null : cargarTodosLosProductos, listaEventos.map((e) => e.id));
  const [form, setForm] = useState(productoVacio);
  const [editando, setEditando] = useState(null);
  const [ocupado, setOcupado] = useState(null);
  const nombreEvento = (eventoId) => listaEventos.find((e) => e.id === eventoId)?.titulo || eventoId;

  const ejecutar = async (clave, accion, mensajeOk) => {
    setOcupado(clave);
    avisar('', '');
    try {
      const resultado = await accion();
      avisar('', typeof mensajeOk === 'function' ? mensajeOk(resultado) : mensajeOk);
      productos.recargar();
      return true;
    } catch (e) {
      avisar(mensajeError(e), '');
      return false;
    } finally {
      setOcupado(null);
    }
  };

  const guardarProducto = async (e) => {
    e.preventDefault();
    const datos = {
      id: form.id.trim(), nombre: form.nombre.trim(), precio: Number(form.precio),
      descripcion: form.descripcion.trim() || null, imagen_url: form.imagen_url.trim() || null,
      evento_id: form.evento_id || null, activo: form.activo,
    };
    const ok = await ejecutar('producto', () => (editando ? modificarProducto(editando, datos) : crearProducto(datos)),
      editando ? `Producto ${datos.nombre} actualizado.` : `Producto ${datos.nombre} creado. Añádele sus tallas abajo.`);
    if (ok) { setForm(productoVacio); setEditando(null); }
  };

  const editar = (p) => {
    setEditando(p.id);
    setForm({ id: p.id, nombre: p.nombre, precio: String(p.precio), descripcion: p.descripcion || '',
      imagen_url: p.imagen_url || '', evento_id: p.evento_id || '', activo: p.activo });
  };

  const retirar = (p) => {
    if (!window.confirm(`¿Retirar ${p.nombre} del catálogo? Los pedidos antiguos lo seguirán mostrando.`)) return;
    ejecutar(p.id, () => retirarProducto(p.id), `${p.nombre} retirado del catálogo.`);
  };

  const eliminarTalla = (p, v) => {
    if (!window.confirm(`¿Eliminar la talla ${nombreTalla(v.talla)} de ${p.nombre}?`)) return;
    // ms-tienda la borra si nunca se ha vendido y la retira (activa = false) si ya tiene ventas
    ejecutar(v.id, () => eliminarVariante(p.id, v.id),
      `Talla ${nombreTalla(v.talla)} de ${p.nombre} eliminada (si tenía ventas, queda retirada).`);
  };

  const campo = (clave) => ({ value: form[clave], onChange: (e) => setForm({ ...form, [clave]: e.target.value }) });

  return (
    <>
      <form className="et-form" onSubmit={guardarProducto} aria-label={editando ? 'Editar producto' : 'Nuevo producto'}>
        <h3>{editando ? `Editar ${editando}` : 'Nuevo producto'}</h3>
        <div className="et-form-grid">
          <label>Identificador
            <input required pattern="[a-z0-9-]+" maxLength={50} placeholder="camiseta-2027" disabled={Boolean(editando)}
              title="Minúsculas, números y guiones" {...campo('id')} />
          </label>
          <label>Nombre<input required maxLength={150} {...campo('nombre')} /></label>
          <label>Precio (€)<input required type="number" min="0" step="0.01" {...campo('precio')} /></label>
          <label>Exclusivo de un evento
            <select {...campo('evento_id')}>
              <option value="">No (merchandising general)</option>
              {listaEventos.map((ev) => <option key={ev.id} value={ev.id}>{ev.titulo}</option>)}
            </select>
          </label>
          <label className="et-ancho">Imagen (URL)<input maxLength={500} placeholder="/camiseta.jpg" {...campo('imagen_url')} /></label>
          <label className="et-ancho">Descripción<textarea {...campo('descripcion')} /></label>
          {editando && (
            <label className="et-check">
              <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} />
              A la venta (desmárcalo para retirarlo; márcalo para volver a venderlo)
            </label>
          )}
        </div>
        <div className="et-acciones">
          {editando && (
            <button type="button" className="et-boton" onClick={() => { setEditando(null); setForm(productoVacio); }}>
              Cancelar
            </button>
          )}
          <button type="submit" className="btn-primary" disabled={ocupado === 'producto'}>
            {editando ? 'Guardar cambios' : 'Crear producto'}
          </button>
        </div>
      </form>

      {productos.cargando && !productos.datos && <p role="status">Cargando productos…</p>}
      {productos.error && <p className="et-error" role="alert">{productos.error.message}</p>}
      <div className="et-tarjetas">
        {(productos.datos || []).map((p) => (
          <article key={p.id} className={`et-tarjeta ${p.activo ? '' : 'et-tarjeta-retirada'}`} aria-label={p.nombre}>
            <div className="et-tarjeta-cabecera">
              <div>
                <h3>{p.nombre}</h3>
                <span className="et-apagado">{p.id} · {euros(p.precio)}{p.evento_id ? ` · ${nombreEvento(p.evento_id)}` : ''}</span>
              </div>
              <span className={`et-insignia ${p.activo ? 'et-insignia-verde' : 'et-insignia-gris'}`}>
                {p.activo ? 'A la venta' : 'Retirado'}
              </span>
            </div>
            <div className="et-tabla-envoltura">
              <table className="et-tabla">
                <thead><tr><th>Talla</th><th>Stock</th><th>Estado</th><th><span className="et-apagado">Acciones</span></th></tr></thead>
                <tbody>
                  {p.variantes.map((v) => (
                    <FilaVariante key={`${v.id}-${v.talla}-${v.stock}-${v.activa}`} producto={p} variante={v}
                      ocupado={ocupado !== null}
                      alGuardar={(variante, cambios) => ejecutar(variante.id, () => modificarVariante(p.id, variante.id, cambios),
                        `Talla ${nombreTalla(cambios.talla || variante.talla)} de ${p.nombre} actualizada.`)}
                      alEliminar={(variante) => eliminarTalla(p, variante)} />
                  ))}
                  {p.variantes.length === 0 && <tr><td colSpan={4} className="et-apagado">Sin tallas todavía.</td></tr>}
                </tbody>
              </table>
            </div>
            <NuevaTalla key={p.variantes.map((v) => `${v.talla}${v.activa}`).join()} producto={p} ocupado={ocupado !== null}
              alCrear={(talla, stock) => ejecutar(`${p.id}-nueva`, () => crearVariante(p.id, { talla, stock }),
                `Talla ${nombreTalla(talla)} añadida a ${p.nombre}.`)} />
            <div className="et-acciones">
              <button type="button" className="et-boton" onClick={() => editar(p)}>Editar</button>
              {p.activo && (
                <button type="button" className="et-peligro" disabled={ocupado !== null} onClick={() => retirar(p)}>
                  Retirar
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

function Pedidos({ eventos, avisar }) {
  const [estado, setEstado] = useState('');
  const pedidos = useDatosRecargables(cargarPedidos, estado);
  const [ocupado, setOcupado] = useState(null);
  const nombreEvento = (eventoId) => eventos.datos?.find((e) => e.id === eventoId)?.titulo || eventoId;

  const avanzar = async (pedido, nuevo) => {
    setOcupado(pedido.id);
    avisar('', '');
    try {
      await cambiarEstadoPedido(pedido.id, nuevo);
      avisar('', `Pedido ${pedido.id}: ${ESTADOS_PEDIDO[nuevo]}.`);
      pedidos.recargar();
    } catch (e) {
      avisar(mensajeError(e), '');
    } finally {
      setOcupado(null);
    }
  };

  return (
    <>
      <div className="et-filtros">
        <label>Estado
          <select value={estado} onChange={(e) => setEstado(e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(ESTADOS_PEDIDO).map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>
      </div>
      {pedidos.cargando && !pedidos.datos && <p role="status">Cargando pedidos…</p>}
      {pedidos.error && <p className="et-error" role="alert">{pedidos.error.message}</p>}
      {pedidos.datos?.length === 0 && <p>No hay pedidos{estado ? ' en ese estado' : ''}.</p>}
      <div className="et-tarjetas">
        {(pedidos.datos || []).map((pedido) => (
          <article key={pedido.id} className="et-tarjeta" aria-label={`Pedido ${pedido.id}`}>
            <div className="et-tarjeta-cabecera">
              <div>
                <h3>{pedido.id}</h3>
                <span className="et-apagado">{fechaPedido(pedido.creado_en)} · {pedido.usuario_id}</span>
              </div>
              <span className="et-insignia">{ESTADOS_PEDIDO[pedido.estado] || pedido.estado}</span>
            </div>
            <ul className="et-lista">
              {pedido.lineas.map((l) => (
                <li key={l.variante_id}><span>{l.cantidad} × {l.producto_nombre} ({nombreTalla(l.talla)})</span>
                  <span>{euros(l.precio_unitario * l.cantidad)}</span></li>
              ))}
            </ul>
            <p>{pedido.entrega === 'DOMICILIO' ? `Envío a: ${pedido.direccion_envio || '—'}`
              : `Recogida en ${nombreEvento(pedido.evento_id_recogida)}`}</p>
            <div className="et-acciones">
              <span className="et-total">{euros(pedido.importe_total)}</span>
              {siguientesEstados(pedido).map((nuevo) => (
                <button key={nuevo} type="button" className="btn-primary" disabled={ocupado !== null}
                  onClick={() => avanzar(pedido, nuevo)}>
                  Marcar {ESTADOS_PEDIDO[nuevo].toLowerCase()}
                </button>
              ))}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

export default function Tienda() {
  const [pestana, setPestana] = useState('productos');
  const eventos = useEventos();
  const [aviso, setAviso] = useState({ error: '', mensaje: '' });
  const avisar = (error, mensaje) => setAviso({ error, mensaje });

  return (
    <div className="et-panel" aria-labelledby="et-tienda-titulo">
      <header className="et-panel-heading">
        <h2 id="et-tienda-titulo">Tienda</h2>
        <p>Catálogo de merchandising, tallas y stock, y gestión de los pedidos.</p>
      </header>
      <div className="et-tabs" role="tablist">
        {[['productos', 'Productos y stock'], ['pedidos', 'Pedidos']].map(([id, titulo]) => (
          <button key={id} type="button" role="tab" aria-selected={pestana === id} className={pestana === id ? 'activo' : ''}
            onClick={() => { setPestana(id); avisar('', ''); }}>
            {titulo}
          </button>
        ))}
      </div>
      {aviso.error && <p className="et-error" role="alert">{aviso.error}</p>}
      {aviso.mensaje && <p className="et-ok" role="status">{aviso.mensaje}</p>}
      {pestana === 'productos' ? <Productos eventos={eventos} avisar={avisar} /> : <Pedidos eventos={eventos} avisar={avisar} />}
    </div>
  );
}
