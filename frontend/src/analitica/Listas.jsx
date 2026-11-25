// src/analitica/Listas.jsx — Dueña: Paula
// Tarjetas de eventos y artistas recomendados (portada y perfil del cliente).
import { Link } from 'react-router-dom';
import { numero, porcentaje, variacion } from './formato';
import { useEventos } from './useDatos';

const MAXIMO = 6;

export function ListaEventos({ eventos, personalizadas }) {
  // ms-analitica a veces no rellena el título: se toma de los eventos de ms-espacios
  const catalogo = useEventos(eventos.some((e) => !e.titulo));
  const titulo = (e) => e.titulo || catalogo.datos?.find((c) => c.id === e.evento_id)?.titulo || e.evento_id;
  return (
    <ul className="an-lista">
      {eventos.slice(0, MAXIMO).map((e) => (
        <li key={e.evento_id} className="an-item">
          <Link to={`/evento/${e.evento_id}`}>{titulo(e)}</Link>
          {e.motivo && <span className="an-motivo">{e.motivo}</span>}
          {personalizadas && e.puntuacion != null && (
            <span className="an-dato">Afinidad {porcentaje(e.puntuacion)}</span>
          )}
        </li>
      ))}
    </ul>
  );
}

export function ListaArtistas({ artistas }) {
  return (
    <ul className="an-lista">
      {artistas.slice(0, MAXIMO).map((a) => (
        <li key={a.artista_id} className="an-item">
          <Link to={`/artistas/${a.artista_id}`}>{a.artista || 'Artista'}</Link>
          {a.motivo && <span className="an-motivo">{a.motivo}</span>}
          {a.favoritos != null && <span className="an-dato">{numero(a.favoritos)} fans</span>}
          {Math.round((a.tendencia_7d || 0) * 100) !== 0 && (
            <span className={a.tendencia_7d > 0 ? 'an-dato an-sube' : 'an-dato an-baja'}>
              {variacion(a.tendencia_7d)} esta semana
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
