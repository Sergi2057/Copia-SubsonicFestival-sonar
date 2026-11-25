// src/pages/Artista/Artista.jsx — Dueño: Sergio
// Ficha del artista (/artistas/:id): biografía, géneros, redes, sus pases publicados, vídeos de YouTube y favorito.
// API: GET /artistas/{id}, GET /artistas/{id}/videos (ms-escaleta); favoritos (ms-usuarios)
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { listarVideos, obtenerArtista } from '../../api/escaleta';
import { anadirFavorito, listarFavoritos, quitarFavorito } from '../../api/usuarios';
import { registrarInteraccion } from '../../analitica/interacciones';
import { useDatos } from '../../analitica/useDatos';
import { useSesion } from '../../sesion/SesionContext';
import { ESTADOS_PASE, fechaHora, hora } from '../Evento/escaletaUtil';
import Reproductor, { Iniciales } from './Reproductor';
import './Artista.css';

const cargarIdsFavoritos = () => listarFavoritos().then((lista) => lista.map((f) => f.artista_id));

export default function Artista() {
  const { id } = useParams();
  const { rol } = useSesion();
  const esCliente = rol === 'cliente';
  const ficha = useDatos(obtenerArtista, id);
  const videos = useDatos(listarVideos, id);
  const favoritosCargados = useDatos(esCliente ? cargarIdsFavoritos : null);
  const [favoritoCambiado, setFavoritoCambiado] = useState(null);   // { id, valor } tras pulsar el botón
  const [guardando, setGuardando] = useState(false);
  const [errorFavorito, setErrorFavorito] = useState('');
  const artista = ficha.datos;

  useEffect(() => {
    if (artista) registrarInteraccion('VER_ARTISTA', artista.id);
  }, [artista]);

  if (ficha.cargando) return <main className="artista-pagina" role="status">Cargando artista…</main>;
  if (ficha.error) {
    return (
      <main className="artista-pagina">
        <p className="artista-error" role="alert">
          {ficha.error.status === 404 ? 'Este artista no existe.' : ficha.error.message}
        </p>
        <Link to="/" className="btn-outline-small">← Volver al inicio</Link>
      </main>
    );
  }

  const esFavorito = favoritoCambiado?.id === id
    ? favoritoCambiado.valor
    : Boolean(favoritosCargados.datos?.includes(id));

  const alternarFavorito = async () => {
    setErrorFavorito('');
    if (!esCliente) {
      setErrorFavorito('Inicia sesión como cliente para guardar artistas favoritos.');
      return;
    }
    setGuardando(true);
    try {
      if (esFavorito) await quitarFavorito(id);
      else await anadirFavorito(id);
      setFavoritoCambiado({ id, valor: !esFavorito });
    } catch (e) {
      setErrorFavorito(e.message);
    } finally {
      setGuardando(false);
    }
  };

  const redes = Object.entries(artista.redes || {}).filter(([, url]) => url);
  return (
    <main className="artista-pagina">
      <div className="artista-cabecera">
        <Iniciales nombre={artista.nombre} imagen={artista.imagen_url} clase="artista-foto" />
        <div className="artista-datos">
          <div className="section-label">Artista</div>
          <h1 className="artista-nombre">{artista.nombre}</h1>
          {artista.pais && <p className="artista-pais">{artista.pais}</p>}
          <div className="player-tags">
            {artista.generos.map((genero) => <span key={genero} className="tag">{genero}</span>)}
          </div>
          <button type="button" className={esFavorito ? 'btn-nav' : 'btn-outline-small'} onClick={alternarFavorito}
            disabled={guardando} aria-pressed={esFavorito}>
            <i className={`fa-${esFavorito ? 'solid' : 'regular'} fa-heart`} aria-hidden="true" />{' '}
            {esFavorito ? 'En tus favoritos' : 'Añadir a favoritos'}
          </button>
          {errorFavorito && <p className="artista-error" role="alert">{errorFavorito}</p>}
        </div>
      </div>

      {artista.biografia && <p className="artista-biografia">{artista.biografia}</p>}
      {redes.length > 0 && (
        <ul className="artista-redes" aria-label="Redes sociales">
          {redes.map(([red, url]) => (
            <li key={red}><a href={url} target="_blank" rel="noreferrer">{red}</a></li>
          ))}
        </ul>
      )}

      <div className="artista-bloque">
        <h2>Próximas actuaciones</h2>
        {artista.pases.length === 0 ? <p>Todavía no tiene actuaciones publicadas.</p> : (
          <ul className="artista-pases">
            {artista.pases.map((pase) => (
              <li key={pase.pase_id} className={pase.estado === 'CANCELADO' ? 'artista-pase-cancelado' : ''}>
                <span className="artista-pase-fecha">{fechaHora(pase.inicio)} – {hora(pase.fin)}</span>
                <span>{pase.escenario}</span>
                <span className="artista-pase-estado">{ESTADOS_PASE[pase.estado] || pase.estado}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="artista-bloque">
        <h2>Música</h2>
        <Reproductor key={id} artista={artista} videos={videos.datos} cargando={videos.cargando} error={videos.error} />
      </div>
    </main>
  );
}
