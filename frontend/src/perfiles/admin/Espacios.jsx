// src/perfiles/admin/Espacios.jsx — Dueño: Pedro
import { useCallback, useEffect, useState } from 'react';
import {
  cambiarEstadoAlquiler, crearEspacio, eliminarEspacio, listarAlquileres, listarEventos,
  listarEspacios, listarTiposEspacio, modificarEspacio,
} from '../../api/espacios';
import '../espacios.css';

const lista = (respuesta) => respuesta?.datos || respuesta || [];
const espacioVacio = () => ({
  evento_id: '', tipo: '', nombre: '', zona: '', tamano: '', dimensiones: '',
  aforo: '', precio_alquiler: '', servicios: '', descripcion: '', disponible: true,
});
const separar = (texto) => texto.split(',').map((valor) => valor.trim()).filter(Boolean);

export default function Espacios() {
  const [eventos, setEventos] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [espacios, setEspacios] = useState([]);
  const [alquileres, setAlquileres] = useState([]);
  const [filtroEvento, setFiltroEvento] = useState('');
  const [filtroTipo, setFiltroTipo] = useState('');
  const [form, setForm] = useState(espacioVacio);
  const [editando, setEditando] = useState(null);
  const [comentarios, setComentarios] = useState({});
  const [cargando, setCargando] = useState(true);
  const [ocupado, setOcupado] = useState(null);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');

  const recargar = useCallback(async () => {
    setError('');
    try {
      const [eventosResultado, tiposResultado, espaciosResultado, alquileresResultado] = await Promise.all([
        listarEventos(), listarTiposEspacio(),
        listarEspacios({ evento_id: filtroEvento || undefined, tipo: filtroTipo || undefined }),
        listarAlquileres({ evento_id: filtroEvento || undefined }),
      ]);
      setEventos(lista(eventosResultado));
      setTipos(tiposResultado);
      setEspacios(lista(espaciosResultado));
      setAlquileres(lista(alquileresResultado));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }, [filtroEvento, filtroTipo]);

  useEffect(() => { recargar(); }, [recargar]);

  const guardar = async (e) => {
    e.preventDefault();
    setError('');
    setMensaje('');
    setOcupado('espacio');
    const datos = {
      evento_id: form.evento_id,
      tipo: form.tipo,
      nombre: form.nombre.trim(),
      zona: form.zona.trim(),
      tamano: form.tamano.trim(),
      dimensiones: form.dimensiones.trim(),
      aforo: form.aforo === '' ? null : Number(form.aforo),
      precio_alquiler: form.precio_alquiler === '' ? null : Number(form.precio_alquiler),
      servicios: separar(form.servicios),
      descripcion: form.descripcion.trim(),
      disponible: form.disponible,
    };
    try {
      if (editando) await modificarEspacio(editando, datos);
      else await crearEspacio(datos);
      setMensaje(editando ? 'Espacio actualizado.' : 'Espacio creado.');
      setEditando(null);
      setForm(espacioVacio());
      await recargar();
    } catch (err) {
      setError(err.message);
    } finally {
      setOcupado(null);
    }
  };

  const editar = (espacio) => {
    setEditando(espacio.id);
    setForm({
      ...espacioVacio(),
      ...Object.fromEntries(Object.entries(espacio).map(([campo, valor]) => [campo, valor ?? ''])),
      aforo: espacio.aforo == null ? '' : String(espacio.aforo),
      precio_alquiler: espacio.precio_alquiler == null ? '' : String(espacio.precio_alquiler),
      servicios: (espacio.servicios || []).join(', '),
      disponible: espacio.disponible ?? true,
    });
  };

  const borrar = async (espacio) => {
    if (!window.confirm(`¿Eliminar el espacio ${espacio.nombre}?`)) return;
    setError('');
    setOcupado(espacio.id);
    try {
      await eliminarEspacio(espacio.id);
      setMensaje('Espacio eliminado.');
      await recargar();
    } catch (err) {
      setError(err.message);
    } finally {
      setOcupado(null);
    }
  };

  const resolverAlquiler = async (alquiler, estado) => {
    setError('');
    setMensaje('');
    setOcupado(alquiler.id);
    try {
      await cambiarEstadoAlquiler(alquiler.id, estado, comentarios[alquiler.id]?.trim() || undefined);
      setMensaje(`Solicitud ${estado === 'APROBADO' ? 'aprobada' : 'rechazada'}.`);
      await recargar();
    } catch (err) {
      setError(err.message);
    } finally {
      setOcupado(null);
    }
  };

  return (
    <div className="pe-panel" aria-labelledby="pe-espacios-title">
      <header className="pe-panel-heading"><h2 id="pe-espacios-title">Espacios y alquileres</h2>
        <p>Gestiona los espacios de cada evento y resuelve las solicitudes de proveedores.</p></header>
      {error && <p className="pe-error" role="alert">{error}</p>}
      {mensaje && <p className="pe-success" role="status">{mensaje}</p>}
      <div className="pe-filters">
        <label>Evento<select value={filtroEvento} onChange={(e) => setFiltroEvento(e.target.value)}>
          <option value="">Todos los eventos</option>
          {eventos.map((evento) => <option key={evento.id} value={evento.id}>{evento.titulo}</option>)}
        </select></label>
        <label>Tipo<select value={filtroTipo} onChange={(e) => setFiltroTipo(e.target.value)}>
          <option value="">Todos los tipos</option>
          {tipos.map((tipo) => <option key={tipo.codigo} value={tipo.codigo}>{tipo.nombre}</option>)}
        </select></label>
      </div>
      {cargando && <p role="status">Cargando espacios y solicitudes…</p>}
      {!cargando && <>
        <form className="pe-form" onSubmit={guardar}>
          <h3>{editando ? 'Editar espacio' : 'Crear espacio'}</h3>
          <div className="pe-form-grid">
            <label>Evento<select required value={form.evento_id} onChange={(e) => setForm({ ...form, evento_id: e.target.value })}>
              <option value="">Selecciona un evento</option>
              {eventos.map((evento) => <option key={evento.id} value={evento.id}>{evento.titulo}</option>)}
            </select></label>
            <label>Tipo<select required value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              <option value="">Selecciona un tipo</option>
              {tipos.map((tipo) => <option key={tipo.codigo} value={tipo.codigo}>{tipo.nombre}</option>)}
            </select></label>
            {['nombre', 'zona', 'tamano', 'dimensiones'].map((campo) => <label key={campo}>
              {campo[0].toUpperCase() + campo.slice(1)}<input required={campo === 'nombre'} value={form[campo]}
                onChange={(e) => setForm({ ...form, [campo]: e.target.value })} />
            </label>)}
            <label>Aforo<input type="number" min="0" value={form.aforo}
              onChange={(e) => setForm({ ...form, aforo: e.target.value })} /></label>
            <label>Precio alquiler (€)<input type="number" min="0" step="0.01" value={form.precio_alquiler}
              onChange={(e) => setForm({ ...form, precio_alquiler: e.target.value })} /></label>
            <label className="pe-form-wide">Servicios (separados por coma)<input value={form.servicios}
              onChange={(e) => setForm({ ...form, servicios: e.target.value })} /></label>
            <label className="pe-form-wide">Descripción<textarea value={form.descripcion}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></label>
            <label className="pe-check"><input type="checkbox" checked={form.disponible}
              onChange={(e) => setForm({ ...form, disponible: e.target.checked })} /> Disponible</label>
          </div>
          <div className="pe-actions">
            {editando && <button className="btn-secondary" type="button" onClick={() => {
              setEditando(null); setForm(espacioVacio());
            }}>Dejar de editar</button>}
            <button className="btn-primary" type="submit" disabled={ocupado === 'espacio'}>
              {editando ? 'Guardar espacio' : 'Crear espacio'}
            </button>
          </div>
        </form>

        <h3>Espacios registrados</h3>
        {espacios.length === 0 && <p>No hay espacios para estos filtros.</p>}
        <div className="pe-cards">
          {espacios.map((espacio) => <article className="pe-card" key={espacio.id}>
            <span className="pe-badge">{espacio.tipo}</span><h3>{espacio.nombre}</h3>
            <p>{espacio.evento_id} · {espacio.zona}</p>
            <p>{espacio.disponible ? 'Disponible' : 'No disponible'} · {espacio.precio_alquiler ?? '—'} €</p>
            <div className="pe-actions">
              <button className="btn-secondary" type="button" onClick={() => editar(espacio)}>Editar</button>
              <button className="pe-danger" type="button" disabled={ocupado === espacio.id}
                onClick={() => borrar(espacio)}>Eliminar</button>
            </div>
          </article>)}
        </div>

        <div className="pe-subsection" aria-labelledby="pe-solicitudes-title">
          <h3 id="pe-solicitudes-title">Solicitudes de alquiler</h3>
          {alquileres.length === 0 && <p>No hay solicitudes de alquiler.</p>}
          <div className="pe-cards">
            {alquileres.map((alquiler) => <article className="pe-card" key={alquiler.id}>
              <span className="pe-badge">{alquiler.estado}</span>
              <h4>{alquiler.proveedor_nombre || alquiler.proveedor_id}</h4>
              <p>Espacio {alquiler.espacio_id} · evento {alquiler.evento_id}</p>
              <p>{alquiler.fecha_inicio} – {alquiler.fecha_fin} · {alquiler.importe} €</p>
              {alquiler.comentarios && <p>{alquiler.comentarios}</p>}
              {alquiler.estado === 'PENDIENTE' && <>
                <label>Comentarios de resolución<textarea value={comentarios[alquiler.id] || ''}
                  onChange={(e) => setComentarios({ ...comentarios, [alquiler.id]: e.target.value })} /></label>
                <div className="pe-actions">
                  <button className="btn-primary" type="button" disabled={ocupado !== null}
                    onClick={() => resolverAlquiler(alquiler, 'APROBADO')}>Aprobar</button>
                  <button className="pe-danger" type="button" disabled={ocupado !== null}
                    onClick={() => resolverAlquiler(alquiler, 'RECHAZADO')}>Rechazar</button>
                </div>
              </>}
            </article>)}
          </div>
        </div>
      </>}
    </div>
  );
}
