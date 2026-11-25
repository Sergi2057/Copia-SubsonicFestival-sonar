// src/perfiles/cliente/Favoritos.jsx — Dueño: Luis
// Qué hacer: Lista de artistas favoritos y quitar favorito (añadir se hace desde la ficha del artista o el cartel del evento).
// API: GET /usuarios/me/favoritos, DELETE /usuarios/me/favoritos/{artista_id} (ms-usuarios)
// Referencia del monolito: legado/components/PerfilCliente/PerfilCliente.jsx (sección 'favoritos')
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { listarFavoritos, quitarFavorito } from '../../api/usuarios';
import { useDatos } from '../../analitica/useDatos';
import { AvisoUsuarios, CargaUsuarios } from '../comun/UsuariosUI';

export default function Favoritos() {
  const peticion = useDatos(listarFavoritos);
  const [ocupado, setOcupado] = useState(null);
  const [error, setError] = useState(null);
  const quitar = async (id) => {
    setOcupado(id); setError(null);
    try { await quitarFavorito(id); peticion.recargar(); }
    catch (e) { setError(e); }
    finally { setOcupado(null); }
  };
  return <div className="us-panel"><h2>Artistas favoritos</h2>
    <AvisoUsuarios error={error} />
    <CargaUsuarios peticion={peticion}>{(favoritos) => favoritos.length ? <div className="us-grid">
      {favoritos.map((f) => <article className="us-tarjeta" key={f.artista_id}>
        <h3><Link to={`/artistas/${encodeURIComponent(f.artista_id)}`}>{f.artista_nombre || f.artista_id}</Link></h3>
        <button className="btn-secondary" disabled={ocupado !== null} onClick={() => quitar(f.artista_id)}
          aria-label={`Quitar a ${f.artista_nombre || f.artista_id} de favoritos`}>
          {ocupado === f.artista_id ? 'Quitando…' : 'Quitar favorito'}</button>
      </article>)}
    </div> : <p>Aún no tienes artistas favoritos. Puedes añadirlos desde la ficha de artista o el cartel de un evento.</p>}</CargaUsuarios>
  </div>;
}
