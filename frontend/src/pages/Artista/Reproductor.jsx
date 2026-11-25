// src/pages/Artista/Reproductor.jsx — Dueño: Sergio
// Reproductor de vídeos y playlists de YouTube de un artista (lo usan Música de Inicio y la ficha del artista).
// Usa las clases music-player-card, player-*, playlist-* de main.css.
// El padre debe darle key={artista.id} para que al cambiar de artista empiece por su primer vídeo.
import { useState } from 'react';
import { urlIncrustada } from '../Evento/escaletaUtil';
import './Artista.css';

export function Iniciales({ nombre, imagen, clase = '' }) {
  if (imagen) return <img src={imagen} alt={nombre} className={clase} />;
  const iniciales = (nombre || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase();
  return <div className={`artista-iniciales ${clase}`} aria-hidden="true">{iniciales}</div>;
}

export default function Reproductor({ artista, videos, cargando, error }) {
  const [elegido, setElegido] = useState(0);
  const video = videos?.[elegido];
  const url = video ? urlIncrustada(video) : null;

  return (
    <div className="music-player-card">
      <div className="player-header">
        <div className="player-cover-large"><Iniciales nombre={artista.nombre} imagen={artista.imagen_url} /></div>
        <div className="player-info-large">
          <h3>{video?.titulo || artista.nombre}</h3>
          <p>{artista.nombre}</p>
          <div className="player-tags">
            {(artista.generos || []).map((genero) => <span key={genero} className="tag">{genero}</span>)}
          </div>
        </div>
      </div>

      <div className="player-body">
        {cargando && <p role="status">Cargando vídeos…</p>}
        {error && <p className="artista-error" role="alert">{error.message}</p>}
        {!cargando && !error && videos?.length === 0 && (
          <p>No hay vídeos disponibles de {artista.nombre} en este momento.</p>
        )}
        {url && (
          <iframe title={video.titulo} src={url} width="100%" height="360" className="artista-iframe"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
        )}
      </div>

      {videos?.length > 0 && (
        <div className="playlist-list">
          {videos.map((v, i) => (
            <button key={v.url} type="button" className={`playlist-item artista-pista ${i === elegido ? 'active' : ''}`}
              aria-pressed={i === elegido} onClick={() => setElegido(i)}>
              <span className="track-num">{String(i + 1).padStart(2, '0')}</span>
              <span className="track-name">{v.titulo}</span>
              <span className="track-time">{v.tipo === 'PLAYLIST' ? 'Playlist' : 'Vídeo'}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
