// src/perfiles/admin/escaleta/Artistas.jsx — Dueño: Sergio
// Catálogo de artistas: alta, edición y baja (no se puede borrar un artista con pases).
// API: GET/POST /artistas, PUT/DELETE /artistas/{id} (ms-escaleta)
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { crearArtista, eliminarArtista, listarArtistas, modificarArtista } from '../../../api/escaleta';
import { useDatosRecargables } from '../../useDatosRecargables';

const cargarArtistas = (q) => listarArtistas({ q: q || undefined, limite: 100 }).then(({ datos }) => datos);
const vacio = { nombre: '', generos: '', pais: '', biografia: '', imagen_url: '', youtube_channel_id: '', instagram: '' };

export default function Artistas({ avisar }) {
  const [busqueda, setBusqueda] = useState('');
  const artistas = useDatosRecargables(cargarArtistas, busqueda.trim());
  const [form, setForm] = useState(vacio);
  const [editando, setEditando] = useState(null);   // artista que se está editando
  const [ocupado, setOcupado] = useState(null);

  const campo = (clave) => ({ value: form[clave], onChange: (e) => setForm({ ...form, [clave]: e.target.value }) });

  const guardar = async (e) => {
    e.preventDefault();
    const redes = { ...(editando?.redes || {}) };
    if (form.instagram.trim()) redes.instagram = form.instagram.trim(); else delete redes.instagram;
    const datos = {
      nombre: form.nombre.trim(),
      generos: form.generos.split(',').map((g) => g.trim().toLowerCase()).filter(Boolean),
      pais: form.pais.trim() || null,
      biografia: form.biografia.trim() || null,
      imagen_url: form.imagen_url.trim() || null,
      youtube_channel_id: form.youtube_channel_id.trim() || null,
      redes,
    };
    if (datos.generos.length === 0) { avisar('Indica al menos un género.', ''); return; }
    setOcupado('form');
    avisar('', '');
    try {
      if (editando) await modificarArtista(editando.id, datos);
      else await crearArtista(datos);
      avisar('', editando ? `${datos.nombre} actualizado.` : `${datos.nombre} dado de alta.`);
      setEditando(null);
      setForm(vacio);
      artistas.recargar();
    } catch (err) {
      avisar(err.message, '');
    } finally {
      setOcupado(null);
    }
  };

  const editar = (a) => {
    setEditando(a);
    setForm({ nombre: a.nombre, generos: a.generos.join(', '), pais: a.pais || '', biografia: a.biografia || '',
      imagen_url: a.imagen_url || '', youtube_channel_id: a.youtube_channel_id || '', instagram: a.redes?.instagram || '' });
  };

  const eliminar = async (a) => {
    if (!window.confirm(`¿Eliminar a ${a.nombre} del catálogo?`)) return;
    setOcupado(a.id);
    avisar('', '');
    try {
      await eliminarArtista(a.id);
      avisar('', `${a.nombre} eliminado.`);
      artistas.recargar();
    } catch (err) {
      avisar(err.codigo === 'ARTISTA_CON_PASES'
        ? `${a.nombre} tiene pases en alguna escaleta: quítalos antes de eliminarlo.` : err.message, '');
    } finally {
      setOcupado(null);
    }
  };

  return (
    <>
      <form className="et-form" onSubmit={guardar} aria-label={editando ? 'Editar artista' : 'Nuevo artista'}>
        <h3>{editando ? `Editar ${editando.nombre}` : 'Nuevo artista'}</h3>
        <div className="et-form-grid">
          <label>Nombre<input required maxLength={255} {...campo('nombre')} /></label>
          <label>Géneros (separados por coma)<input required placeholder="trance, progressive" {...campo('generos')} /></label>
          <label>País<input {...campo('pais')} /></label>
          <label>Canal de YouTube (id)<input placeholder="UC…" {...campo('youtube_channel_id')} /></label>
          <label>Imagen (URL)<input {...campo('imagen_url')} /></label>
          <label>Instagram (URL)<input type="url" {...campo('instagram')} /></label>
          <label className="et-ancho">Biografía<textarea {...campo('biografia')} /></label>
        </div>
        <div className="et-acciones">
          {editando && <button type="button" className="et-boton" onClick={() => { setEditando(null); setForm(vacio); }}>Cancelar</button>}
          <button type="submit" className="btn-primary" disabled={ocupado === 'form'}>
            {editando ? 'Guardar cambios' : 'Dar de alta'}
          </button>
        </div>
      </form>

      <div className="et-filtros">
        <label>Buscar artista
          <input type="search" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Nombre" />
        </label>
      </div>
      {artistas.cargando && !artistas.datos && <p role="status">Cargando artistas…</p>}
      {artistas.error && <p className="et-error" role="alert">{artistas.error.message}</p>}
      {artistas.datos?.length === 0 && <p>No hay artistas{busqueda ? ` que coincidan con «${busqueda}»` : ''}.</p>}
      <div className="et-tarjetas">
        {(artistas.datos || []).map((a) => (
          <article key={a.id} className="et-tarjeta" aria-label={a.nombre}>
            <h3><Link to={`/artistas/${encodeURIComponent(a.id)}`}>{a.nombre}</Link></h3>
            <p className="et-apagado">{[a.pais, a.generos.join(', ')].filter(Boolean).join(' · ')}</p>
            <div className="et-acciones">
              <button type="button" className="et-boton" onClick={() => editar(a)}>Editar</button>
              <button type="button" className="et-peligro" disabled={ocupado !== null} onClick={() => eliminar(a)}
                aria-label={`Eliminar a ${a.nombre}`}>
                Eliminar
              </button>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
