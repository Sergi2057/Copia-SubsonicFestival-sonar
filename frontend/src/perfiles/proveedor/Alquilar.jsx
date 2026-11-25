// src/perfiles/proveedor/Alquilar.jsx — Dueño: Pedro
import { useEffect, useMemo, useState } from 'react';
import {
  listarEventos, listarEspacios, listarTiposEspacio, obtenerEspacio, solicitarAlquiler,
} from '../../api/espacios';
import '../espacios.css';

const lista = (respuesta) => respuesta?.datos || respuesta || [];

export default function Alquilar() {
  const [eventos, setEventos] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [espacios, setEspacios] = useState([]);
  const [eventoId, setEventoId] = useState('');
  const [tipo, setTipo] = useState('');
  const [zona, setZona] = useState('');
  const [precioMaximo, setPrecioMaximo] = useState('');
  const [seleccionado, setSeleccionado] = useState(null);
  const [fechas, setFechas] = useState({ fecha_inicio: '', fecha_fin: '', comentarios: '' });
  const [cargando, setCargando] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');

  useEffect(() => {
    let cancelado = false;
    Promise.all([listarEventos({ estado: 'PUBLICADO' }), listarTiposEspacio()])
      .then(([eventosResultado, tiposResultado]) => {
        if (!cancelado) {
          setEventos(lista(eventosResultado));
          setTipos(tiposResultado);
        }
      })
      .catch((e) => { if (!cancelado) setError(e.message); })
      .finally(() => { if (!cancelado) setCargando(false); });
    return () => { cancelado = true; };
  }, []);

  useEffect(() => {
    let cancelado = false;
    setError('');
    setCargando(true);
    listarEspacios({ evento_id: eventoId || undefined, tipo: tipo || undefined, disponible: true })
      .then((resultado) => { if (!cancelado) setEspacios(lista(resultado)); })
      .catch((e) => { if (!cancelado) setError(e.message); })
      .finally(() => { if (!cancelado) setCargando(false); });
    return () => { cancelado = true; };
  }, [eventoId, tipo]);

  const visibles = useMemo(() => espacios.filter((espacio) => {
    const coincideZona = !zona || `${espacio.zona || ''} ${espacio.nombre}`.toLocaleLowerCase().includes(zona.toLocaleLowerCase());
    const coincidePrecio = !precioMaximo || (espacio.precio_alquiler != null && Number(espacio.precio_alquiler) <= Number(precioMaximo));
    return espacio.disponible && espacio.precio_alquiler != null && coincideZona && coincidePrecio;
  }), [espacios, zona, precioMaximo]);
  const tituloEvento = (id) => eventos.find((evento) => evento.id === id)?.titulo || id;

  const abrirDetalle = async (espacio) => {
    setError('');
    setMensaje('');
    try {
      setSeleccionado(await obtenerEspacio(espacio.id));
      setFechas({ fecha_inicio: '', fecha_fin: '', comentarios: '' });
    } catch (e) {
      setError(e.message);
    }
  };

  const enviarSolicitud = async (event) => {
    event.preventDefault();
    if (!seleccionado || new Date(fechas.fecha_fin) <= new Date(fechas.fecha_inicio)) {
      setError('La fecha de fin debe ser posterior a la fecha de inicio.');
      return;
    }
    setError('');
    setMensaje('');
    setOcupado(true);
    try {
      await solicitarAlquiler(seleccionado.id, {
        fecha_inicio: new Date(fechas.fecha_inicio).toISOString(),
        fecha_fin: new Date(fechas.fecha_fin).toISOString(),
        comentarios: fechas.comentarios.trim() || undefined,
      });
      setMensaje('Solicitud de alquiler enviada. Queda pendiente de aprobación.');
      setSeleccionado(null);
      setEspacios((actuales) => actuales.filter((espacio) => espacio.id !== seleccionado.id));
    } catch (e) {
      setError(e.message);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="pe-panel" aria-labelledby="pe-alquilar-title">
      <header className="pe-panel-heading"><h2 id="pe-alquilar-title">Alquilar un espacio</h2>
        <p>Busca espacios disponibles y envía tu solicitud al equipo del festival.</p></header>
      {error && <p className="pe-error" role="alert">{error}</p>}
      {mensaje && <p className="pe-success" role="status">{mensaje}</p>}
      <div className="pe-filters">
        <label>Evento<select value={eventoId} onChange={(e) => setEventoId(e.target.value)}>
          <option value="">Todos los eventos</option>
          {eventos.map((evento) => <option key={evento.id} value={evento.id}>{evento.titulo}</option>)}
        </select></label>
        <label>Tipo<select value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="">Todos los tipos</option>
          {tipos.filter((item) => item.alquilable).map((item) => (
            <option key={item.codigo} value={item.codigo}>{item.nombre}</option>
          ))}
        </select></label>
        <label>Zona<input value={zona} onChange={(e) => setZona(e.target.value)} placeholder="Buscar zona" /></label>
        <label>Precio máximo (€)<input type="number" min="0" value={precioMaximo}
          onChange={(e) => setPrecioMaximo(e.target.value)} /></label>
      </div>
      {cargando && <p role="status">Cargando espacios…</p>}
      {!cargando && !error && visibles.length === 0 && <p>No hay espacios disponibles con esos filtros.</p>}
      <div className="pe-cards">
        {visibles.map((espacio) => (
          <article className="pe-card" key={espacio.id}>
            <span className="pe-badge">{espacio.tipo}</span>
            <h3>{espacio.nombre}</h3>
            <p>{espacio.zona || 'Zona sin especificar'} · {tituloEvento(espacio.evento_id)}</p>
            <p>{espacio.descripcion || 'Sin descripción.'}</p>
            <p className="pe-price">{espacio.precio_alquiler} €</p>
            <button type="button" className="btn-primary" onClick={() => abrirDetalle(espacio)}>Ver detalle y solicitar</button>
          </article>
        ))}
      </div>
      {seleccionado && <div className="pe-modal-backdrop">
        <div className="pe-modal" role="dialog" aria-modal="true" aria-labelledby="pe-solicitud-title">
          <h3 id="pe-solicitud-title">{seleccionado.nombre}</h3>
          <p>{seleccionado.descripcion || 'Sin descripción.'}</p>
          <p>{seleccionado.zona} · {seleccionado.precio_alquiler} €</p>
          <form onSubmit={enviarSolicitud}>
            <label>Inicio<input type="datetime-local" required value={fechas.fecha_inicio}
              onChange={(e) => setFechas({ ...fechas, fecha_inicio: e.target.value })} /></label>
            <label>Fin<input type="datetime-local" required value={fechas.fecha_fin}
              onChange={(e) => setFechas({ ...fechas, fecha_fin: e.target.value })} /></label>
            <label>Comentarios<textarea value={fechas.comentarios}
              onChange={(e) => setFechas({ ...fechas, comentarios: e.target.value })} /></label>
            <div className="pe-actions">
              <button type="button" className="btn-secondary" disabled={ocupado} onClick={() => setSeleccionado(null)}>Cerrar</button>
              <button type="submit" className="btn-primary" disabled={ocupado}>{ocupado ? 'Enviando…' : 'Enviar solicitud'}</button>
            </div>
          </form>
        </div>
      </div>}
    </div>
  );
}
