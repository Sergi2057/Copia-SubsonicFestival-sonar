// src/pages/Inicio/Musica.jsx — Dueño: Sergio
// Bloque MÚSICA de la portada: selector de artistas del festival y reproductor con sus vídeos y playlists de YouTube.
// API: GET /artistas, GET /artistas/{id}/videos (ms-escaleta)
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { listarArtistas, listarVideos } from '../../api/escaleta';
import { useDatos } from '../../analitica/useDatos';
import Reproductor, { Iniciales } from '../Artista/Reproductor';
import './Musica.css';

const cargarArtistas = () => listarArtistas({ limite: 100 }).then(({ datos }) => datos);

export default function Musica() {
  const artistas = useDatos(cargarArtistas);
  const [busqueda, setBusqueda] = useState('');
  const [elegidoId, setElegidoId] = useState(null);
  const lista = artistas.datos || [];
  const elegido = lista.find((a) => a.id === elegidoId) || lista[0] || null;
  const videos = useDatos(elegido ? listarVideos : null, elegido?.id);
  const texto = busqueda.trim().toLowerCase();
  const visibles = texto ? lista.filter((a) => a.nombre.toLowerCase().includes(texto)) : lista;

  return (
    <section aria-labelledby="titulo-musica">
      <div className="section-label">Subsonic Radio</div>
      <h2 id="titulo-musica">MÚSICA DEL FESTIVAL</h2>

      {artistas.cargando && <p role="status">Cargando artistas…</p>}
      {artistas.error && <p className="artista-error" role="alert">{artistas.error.message}</p>}
      {!artistas.cargando && !artistas.error && lista.length === 0 && <p>Todavía no hay artistas en el cartel.</p>}

      {lista.length > 0 && (
        <>
          <input type="search" className="musica-buscar" value={busqueda} onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar artista" aria-label="Buscar artista" />
          <div className="music-artist-grid">
            {visibles.map((artista) => (
              <button key={artista.id} type="button" aria-pressed={artista.id === elegido?.id}
                className={`music-artist-card musica-tarjeta ${artista.id === elegido?.id ? 'activo' : ''}`}
                onClick={() => setElegidoId(artista.id)}>
                <Iniciales nombre={artista.nombre} imagen={artista.imagen_url} />
                <div className="music-artist-overlay"><span>{artista.nombre}</span></div>
              </button>
            ))}
            {visibles.length === 0 && <p>Ningún artista coincide con «{busqueda}».</p>}
          </div>
        </>
      )}

      {elegido && (
        <>
          <Reproductor key={elegido.id} artista={elegido} videos={videos.datos} cargando={videos.cargando}
            error={videos.error} />
          <p className="musica-ficha">
            <Link to={`/artistas/${encodeURIComponent(elegido.id)}`} className="btn-outline-small">
              Ver la ficha de {elegido.nombre}
            </Link>
          </p>
        </>
      )}
    </section>
  );
}
