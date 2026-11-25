// src/analitica/Componentes.jsx — Dueña: Paula
// Piezas comunes de las pantallas de analítica: estado de carga, barra de porcentaje y selector de evento.
// El selector recibe la lista de useEventos() (src/analitica/useDatos.js).
import { porcentaje } from './formato';
import './analitica.css';

const vacio = (datos) => datos === null || datos === undefined || (Array.isArray(datos) && datos.length === 0);

/**
 * Muestra «Cargando…», el error (con botón de reintentar) o el contenido.
 *   <Carga peticion={useDatos(...)} vacio="No hay ventas">{(datos) => <Tabla datos={datos} />}</Carga>
 * Un 404 del backend (SIN_DATOS) se trata como «no hay datos», no como error.
 */
export function Carga({ peticion, vacio: textoVacio = 'No hay datos', children }) {
  const { cargando, error, datos, recargar } = peticion;
  if (cargando) return <p className="an-aviso" role="status">Cargando…</p>;
  if (error?.status === 404) return <p className="an-aviso">{textoVacio}</p>;
  if (error) {
    return (
      <div className="an-error" role="alert">
        <span>{error.message}</span>
        <button type="button" className="btn-secondary" onClick={recargar}>Reintentar</button>
      </div>
    );
  }
  if (vacio(datos)) return <p className="an-aviso">{textoVacio}</p>;
  return children(datos);
}

/** Barra horizontal de 0 a 1. aviso = a partir de qué fracción se pinta de color de alerta. */
export function Barra({ fraccion, aviso = 1.01 }) {
  const valor = Math.max(0, Math.min(1, Number(fraccion) || 0));
  return (
    <div className="an-barra" role="img" aria-label={porcentaje(fraccion)}>
      <span className={valor >= aviso ? 'an-barra-alerta' : undefined} style={{ width: `${valor * 100}%` }} />
    </div>
  );
}

/**
 * Desplegable de eventos de ms-espacios.
 * opcional = texto de la opción «todos» (p. ej. «Todo el festival»); sin él hay que elegir uno.
 */
export function SelectorEvento({ eventos, valor, onCambiar, opcional }) {
  return (
    <label className="an-campo">
      <span>Evento</span>
      <select value={valor ?? ''} onChange={(e) => onCambiar(e.target.value || null)}
        disabled={eventos.cargando || Boolean(eventos.error)}>
        <option value="">{eventos.cargando ? 'Cargando eventos…' : opcional || 'Elige un evento'}</option>
        {(eventos.datos || []).map((e) => <option key={e.id} value={e.id}>{e.titulo}</option>)}
      </select>
    </label>
  );
}
