// src/perfiles/admin/Eventos.jsx — Dueño: Pedro
import { useEffect, useState } from 'react';
import {
  cambiarEstadoEvento, crearEvento, crearRecinto, crearTarifa, eliminarEvento, eliminarRecinto,
  eliminarTarifa, listarEventos, listarRecintos, listarTarifas, modificarEvento, modificarRecinto,
  modificarTarifa,
} from '../../api/espacios';
import '../espacios.css';

const lista = (respuesta) => respuesta?.datos || respuesta || [];
const eventoVacio = () => ({
  id: '', titulo: '', pais: '', recinto_id: '', fecha_inicio: '', fecha_fin: '',
  descripcion: '', imagen_url: '', tags: '', servicios_generales: '',
});
const recintoVacio = () => ({
  nombre: '', direccion: '', ciudad: '', pais: '', aforo_maximo: '', latitud: '', longitud: '',
});
const separar = (texto) => texto.split(',').map((valor) => valor.trim()).filter(Boolean);

export default function Eventos() {
  const [eventos, setEventos] = useState([]);
  const [recintos, setRecintos] = useState([]);
  const [tarifas, setTarifas] = useState([]);
  const [pestana, setPestana] = useState('eventos');
  const [eventoForm, setEventoForm] = useState(eventoVacio);
  const [eventoEditando, setEventoEditando] = useState(null);
  const [recintoForm, setRecintoForm] = useState(recintoVacio);
  const [recintoEditando, setRecintoEditando] = useState(null);
  const [eventoTarifasId, setEventoTarifasId] = useState('');
  const [tarifaForm, setTarifaForm] = useState({ tipo_pase: 'DAY', precio: '', cupo_total: '' });
  const [tarifaEditando, setTarifaEditando] = useState(null);
  const [motivos, setMotivos] = useState({});
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');

  const recargar = async () => {
    setError('');
    try {
      const [eventosResultado, recintosResultado] = await Promise.all([listarEventos(), listarRecintos()]);
      const siguientesEventos = lista(eventosResultado);
      setEventos(siguientesEventos);
      setRecintos(lista(recintosResultado));
      setEventoTarifasId((actual) => actual || siguientesEventos[0]?.id || '');
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => { recargar(); }, []);

  useEffect(() => {
    if (!eventoTarifasId) {
      setTarifas([]);
      return;
    }
    let cancelado = false;
    listarTarifas(eventoTarifasId)
      .then((resultado) => { if (!cancelado) setTarifas(resultado); })
      .catch((e) => { if (!cancelado) setError(e.message); });
    return () => { cancelado = true; };
  }, [eventoTarifasId]);

  const editarEvento = (evento) => {
    setEventoEditando(evento.id);
    setEventoForm({
      ...eventoVacio(),
      ...Object.fromEntries(Object.entries(evento).map(([campo, valor]) => [campo, valor ?? ''])),
      tags: (evento.tags || []).join(', '),
      servicios_generales: (evento.servicios_generales || []).join(', '),
    });
    setPestana('eventos');
  };

  const guardarEvento = async (e) => {
    e.preventDefault();
    setError('');
    setMensaje('');
    const datos = {
      id: eventoForm.id.trim(),
      titulo: eventoForm.titulo.trim(),
      pais: eventoForm.pais.trim(),
      recinto_id: eventoForm.recinto_id,
      fecha_inicio: eventoForm.fecha_inicio,
      fecha_fin: eventoForm.fecha_fin,
      descripcion: eventoForm.descripcion.trim(),
      imagen_url: eventoForm.imagen_url.trim(),
      tags: separar(eventoForm.tags),
      servicios_generales: separar(eventoForm.servicios_generales),
    };
    try {
      if (eventoEditando) await modificarEvento(eventoEditando, datos);
      else await crearEvento(datos);
      setEventoForm(eventoVacio());
      setEventoEditando(null);
      setMensaje(eventoEditando ? 'Evento actualizado.' : 'Evento creado.');
      await recargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const cambiarEstado = async (evento, estado) => {
    const motivo = estado === 'CANCELADO' ? motivos[evento.id]?.trim() : undefined;
    if (estado === 'CANCELADO' && !motivo) {
      setError('Indica el motivo antes de cancelar el evento.');
      return;
    }
    setError('');
    setMensaje('');
    try {
      await cambiarEstadoEvento(evento.id, estado, motivo);
      setMensaje(`Evento ${estado.toLocaleLowerCase()}.`);
      await recargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const borrarEvento = async (evento) => {
    if (!window.confirm(`¿Eliminar el evento ${evento.titulo}?`)) return;
    setError('');
    try {
      await eliminarEvento(evento.id);
      setMensaje('Evento eliminado.');
      await recargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const guardarRecinto = async (e) => {
    e.preventDefault();
    setError('');
    setMensaje('');
    const datos = {
      nombre: recintoForm.nombre.trim(), direccion: recintoForm.direccion.trim(),
      ciudad: recintoForm.ciudad.trim(), pais: recintoForm.pais.trim(),
      aforo_maximo: Number(recintoForm.aforo_maximo),
      ...(recintoForm.latitud !== '' ? { latitud: Number(recintoForm.latitud) } : {}),
      ...(recintoForm.longitud !== '' ? { longitud: Number(recintoForm.longitud) } : {}),
    };
    try {
      if (recintoEditando) await modificarRecinto(recintoEditando, datos);
      else await crearRecinto(datos);
      setRecintoForm(recintoVacio());
      setRecintoEditando(null);
      setMensaje(recintoEditando ? 'Recinto actualizado.' : 'Recinto creado.');
      await recargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const borrarRecinto = async (recinto) => {
    if (!window.confirm(`¿Eliminar el recinto ${recinto.nombre}?`)) return;
    setError('');
    try {
      await eliminarRecinto(recinto.id);
      setMensaje('Recinto eliminado.');
      await recargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const editarTarifa = (tarifa) => {
    setTarifaEditando(tarifa.id);
    setTarifaForm({ tipo_pase: tarifa.tipo_pase, precio: String(tarifa.precio), cupo_total: String(tarifa.cupo_total) });
  };

  const guardarTarifa = async (e) => {
    e.preventDefault();
    setError('');
    setMensaje('');
    const datos = { ...tarifaForm, precio: Number(tarifaForm.precio), cupo_total: Number(tarifaForm.cupo_total) };
    try {
      if (tarifaEditando) await modificarTarifa(eventoTarifasId, tarifaEditando, datos);
      else await crearTarifa(eventoTarifasId, datos);
      setTarifaEditando(null);
      setTarifaForm({ tipo_pase: 'DAY', precio: '', cupo_total: '' });
      setTarifas(await listarTarifas(eventoTarifasId));
      setMensaje(tarifaEditando ? 'Tarifa actualizada.' : 'Tarifa creada.');
    } catch (err) {
      setError(err.message);
    }
  };

  const borrarTarifa = async (tarifa) => {
    if (!window.confirm(`¿Eliminar la tarifa ${tarifa.tipo_pase}?`)) return;
    setError('');
    try {
      await eliminarTarifa(eventoTarifasId, tarifa.id);
      setTarifas(await listarTarifas(eventoTarifasId));
      setMensaje('Tarifa eliminada.');
    } catch (err) {
      setError(err.message);
    }
  };

  const campoEvento = (nombre, etiqueta, tipo = 'text', requerido = false) => (
    <label key={nombre}>{etiqueta}
      <input type={tipo} required={requerido} value={eventoForm[nombre] || ''}
        disabled={nombre === 'id' && Boolean(eventoEditando)}
        onChange={(e) => setEventoForm({ ...eventoForm, [nombre]: e.target.value })} />
    </label>
  );

  return (
    <div className="pe-panel" aria-labelledby="pe-eventos-title">
      <header className="pe-panel-heading"><h2 id="pe-eventos-title">Eventos y recintos</h2>
        <p>Administra eventos, pases y lugares del festival.</p></header>
      <div className="pe-tabs" aria-label="Gestión">
        <button type="button" className={pestana === 'eventos' ? 'activo' : ''} onClick={() => setPestana('eventos')}>Eventos y tarifas</button>
        <button type="button" className={pestana === 'recintos' ? 'activo' : ''} onClick={() => setPestana('recintos')}>Recintos</button>
      </div>
      {error && <p className="pe-error" role="alert">{error}</p>}
      {mensaje && <p className="pe-success" role="status">{mensaje}</p>}
      {cargando && <p role="status">Cargando gestión de eventos…</p>}
      {!cargando && pestana === 'eventos' && <>
        <form className="pe-form" onSubmit={guardarEvento}>
          <h3>{eventoEditando ? 'Editar evento' : 'Crear evento'}</h3>
          <div className="pe-form-grid">
            {campoEvento('id', 'Identificador (evento-…) ', 'text', true)}
            {campoEvento('titulo', 'Título', 'text', true)}
            {campoEvento('pais', 'País', 'text', true)}
            <label>Recinto<select required value={eventoForm.recinto_id}
              onChange={(e) => setEventoForm({ ...eventoForm, recinto_id: e.target.value })}>
              <option value="">Selecciona un recinto</option>
              {recintos.map((recinto) => <option key={recinto.id} value={recinto.id}>{recinto.nombre}</option>)}
            </select></label>
            {campoEvento('fecha_inicio', 'Fecha de inicio', 'date', true)}
            {campoEvento('fecha_fin', 'Fecha de fin', 'date', true)}
            {campoEvento('imagen_url', 'URL de imagen')}
            {campoEvento('tags', 'Etiquetas (separadas por coma)')}
            <label className="pe-form-wide">Descripción<textarea value={eventoForm.descripcion}
              onChange={(e) => setEventoForm({ ...eventoForm, descripcion: e.target.value })} /></label>
            <label className="pe-form-wide">Servicios generales (separados por coma)<textarea
              value={eventoForm.servicios_generales}
              onChange={(e) => setEventoForm({ ...eventoForm, servicios_generales: e.target.value })} /></label>
          </div>
          <div className="pe-actions">
            {eventoEditando && <button className="btn-secondary" type="button" onClick={() => {
              setEventoEditando(null); setEventoForm(eventoVacio());
            }}>Dejar de editar</button>}
            <button className="btn-primary" type="submit">{eventoEditando ? 'Guardar evento' : 'Crear evento'}</button>
          </div>
        </form>

        <div className="pe-cards">
          {eventos.map((evento) => (
            <article className="pe-card" key={evento.id}>
              <span className="pe-badge">{evento.estado}</span>
              <h3>{evento.titulo}</h3><p>{evento.pais} · {evento.fecha_inicio} – {evento.fecha_fin}</p>
              <div className="pe-actions">
                <button className="btn-secondary" type="button" onClick={() => editarEvento(evento)}>Editar</button>
                {evento.estado === 'BORRADOR' && <button className="btn-primary" type="button"
                  onClick={() => cambiarEstado(evento, 'PUBLICADO')}>Publicar</button>}
                {evento.estado === 'PUBLICADO' && <>
                  <button className="btn-secondary" type="button" onClick={() => cambiarEstado(evento, 'FINALIZADO')}>Finalizar</button>
                  <button className="pe-danger" type="button" onClick={() => cambiarEstado(evento, 'CANCELADO')}>Cancelar</button>
                  <label>Motivo<input aria-label={`Motivo de cancelación para ${evento.titulo}`}
                    value={motivos[evento.id] || ''}
                    onChange={(e) => setMotivos({ ...motivos, [evento.id]: e.target.value })} /></label>
                </>}
                {evento.estado === 'BORRADOR' && <button className="pe-danger" type="button" onClick={() => borrarEvento(evento)}>Eliminar</button>}
              </div>
            </article>
          ))}
        </div>

        <div className="pe-subsection" aria-labelledby="pe-tarifas-title">
          <h3 id="pe-tarifas-title">Tarifas</h3>
          <label>Evento<select value={eventoTarifasId} onChange={(e) => {
            setEventoTarifasId(e.target.value); setTarifaEditando(null);
          }}>
            <option value="">Selecciona un evento</option>
            {eventos.map((evento) => <option key={evento.id} value={evento.id}>{evento.titulo}</option>)}
          </select></label>
          {eventoTarifasId && <form className="pe-form" onSubmit={guardarTarifa}>
            <div className="pe-form-grid">
              <label>Tipo de pase<select value={tarifaForm.tipo_pase} onChange={(e) => setTarifaForm({ ...tarifaForm, tipo_pase: e.target.value })}>
                {['DAY', 'WEEKEND', 'VIP'].map((tipoPase) => <option key={tipoPase}>{tipoPase}</option>)}
              </select></label>
              <label>Precio (€)<input type="number" min="0" step="0.01" required value={tarifaForm.precio}
                onChange={(e) => setTarifaForm({ ...tarifaForm, precio: e.target.value })} /></label>
              <label>Cupo total<input type="number" min="0" step="1" required value={tarifaForm.cupo_total}
                onChange={(e) => setTarifaForm({ ...tarifaForm, cupo_total: e.target.value })} /></label>
            </div>
            <div className="pe-actions"><button className="btn-primary" type="submit">
              {tarifaEditando ? 'Guardar tarifa' : 'Añadir tarifa'}</button></div>
          </form>}
          <div className="pe-cards">
            {tarifas.map((tarifa) => <article className="pe-card" key={tarifa.id}>
              <h4>{tarifa.tipo_pase}</h4><p>{tarifa.precio} € · {tarifa.disponibles} disponibles</p>
              <div className="pe-actions">
                <button className="btn-secondary" type="button" onClick={() => editarTarifa(tarifa)}>Editar</button>
                <button className="pe-danger" type="button" onClick={() => borrarTarifa(tarifa)}>Eliminar</button>
              </div>
            </article>)}
          </div>
        </div>
      </>}

      {!cargando && pestana === 'recintos' && <>
        <form className="pe-form" onSubmit={guardarRecinto}>
          <h3>{recintoEditando ? 'Editar recinto' : 'Crear recinto'}</h3>
          <div className="pe-form-grid">
            {['nombre', 'direccion', 'ciudad', 'pais'].map((campo) => <label key={campo}>
              {campo[0].toUpperCase() + campo.slice(1)}<input required={campo !== 'direccion'} value={recintoForm[campo]}
                onChange={(e) => setRecintoForm({ ...recintoForm, [campo]: e.target.value })} />
            </label>)}
            <label>Aforo máximo<input type="number" min="1" required value={recintoForm.aforo_maximo}
              onChange={(e) => setRecintoForm({ ...recintoForm, aforo_maximo: e.target.value })} /></label>
            <label>Latitud<input type="number" step="any" value={recintoForm.latitud}
              onChange={(e) => setRecintoForm({ ...recintoForm, latitud: e.target.value })} /></label>
            <label>Longitud<input type="number" step="any" value={recintoForm.longitud}
              onChange={(e) => setRecintoForm({ ...recintoForm, longitud: e.target.value })} /></label>
          </div>
          <div className="pe-actions">
            {recintoEditando && <button type="button" className="btn-secondary" onClick={() => {
              setRecintoEditando(null); setRecintoForm(recintoVacio());
            }}>Dejar de editar</button>}
            <button type="submit" className="btn-primary">{recintoEditando ? 'Guardar recinto' : 'Crear recinto'}</button>
          </div>
        </form>
        <div className="pe-cards">
          {recintos.map((recinto) => <article className="pe-card" key={recinto.id}>
            <h3>{recinto.nombre}</h3><p>{recinto.ciudad}, {recinto.pais} · aforo {recinto.aforo_maximo}</p>
            <div className="pe-actions">
              <button className="btn-secondary" type="button" onClick={() => {
                setRecintoEditando(recinto.id);
                setRecintoForm({
                  ...recintoVacio(),
                  ...Object.fromEntries(Object.entries(recinto).map(([campo, valor]) => [campo, valor ?? ''])),
                  aforo_maximo: recinto.aforo_maximo == null ? '' : String(recinto.aforo_maximo),
                });
              }}>Editar</button>
              <button className="pe-danger" type="button" onClick={() => borrarRecinto(recinto)}>Eliminar</button>
            </div>
          </article>)}
        </div>
      </>}
    </div>
  );
}
