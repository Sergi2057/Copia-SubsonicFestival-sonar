// src/api/escaleta.js — llamadas a ms-escaleta (a través del gateway).  Dueño: Sergio
// Rutas en docs/openapi/ms-escaleta.yaml.
import { api, urlApi } from './cliente';

const id = encodeURIComponent;

// ── Escaleta publicada (pública) ────────────────────────────
export const obtenerEscaleta = (eventoId) => api(`/escaletas/${id(eventoId)}`);

/** Tipos de aviso que manda el SSE de /escaletas/{evento_id}/cambios. */
export const TIPOS_CAMBIO = ['pase.modificado', 'pase.cancelado', 'escaleta.publicada'];

/**
 * Cambios en directo de la escaleta (SSE). Devuelve una función para dejar de escuchar.
 *   useEffect(() => escucharCambios(eventoId, (cambio) => …), [eventoId]);
 * cambio: { tipo: 'pase.modificado' | 'pase.cancelado', pase, version } o { tipo: 'escaleta.publicada', version }.
 * ms-escaleta envía cada aviso como un evento SSE con nombre (event: pase.modificado), así que no
 * basta con onmessage: hay que escuchar cada tipo. Si se corta la conexión, EventSource reconecta solo.
 */
export function escucharCambios(eventoId, alRecibir) {
  const fuente = new EventSource(urlApi(`/escaletas/${id(eventoId)}/cambios`));
  const recibir = (mensaje) => {
    try {
      alRecibir(JSON.parse(mensaje.data));
    } catch {
      // mensaje ilegible: se ignora
    }
  };
  TIPOS_CAMBIO.forEach((tipo) => fuente.addEventListener(tipo, recibir));
  return () => fuente.close();
}

// ── Artistas ────────────────────────────────────────────────
/** filtros: q, genero, evento_id, limite, desplazamiento → { datos, total } */
export const listarArtistas = (filtros) => api('/artistas', { parametros: filtros, conTotal: true });
/** Ficha con sus pases publicados. */
export const obtenerArtista = (artistaId) => api(`/artistas/${id(artistaId)}`);
export const crearArtista = (datos) => api('/artistas', { metodo: 'POST', cuerpo: datos });
export const modificarArtista = (artistaId, datos) => api(`/artistas/${id(artistaId)}`, { metodo: 'PUT', cuerpo: datos });
/** 409 ARTISTA_CON_PASES si tiene pases asignados. */
export const eliminarArtista = (artistaId) => api(`/artistas/${id(artistaId)}`, { metodo: 'DELETE' });
/** Vídeos y playlists de YouTube: [{ titulo, url, miniatura_url, tipo: 'VIDEO' | 'PLAYLIST' }] ([] si no hay). */
export const listarVideos = (artistaId) => api(`/artistas/${id(artistaId)}/videos`);

// ── Slots y pases (borrador, solo admin) ────────────────────
/** filtros: espacio_id, fecha (YYYY-MM-DD) */
export const listarSlots = (eventoId, filtros) => api(`/escaletas/${id(eventoId)}/slots`, { parametros: filtros });
/** datos: { espacio_id, inicio, fin, tipo } (fechas ISO con zona horaria) */
export const crearSlot = (eventoId, datos) => api(`/escaletas/${id(eventoId)}/slots`, { metodo: 'POST', cuerpo: datos });
export const modificarSlot = (slotId, datos) => api(`/slots/${id(slotId)}`, { metodo: 'PUT', cuerpo: datos });
export const eliminarSlot = (slotId) => api(`/slots/${id(slotId)}`, { metodo: 'DELETE' });
/** datos: { artista_id, formato, notas_tecnicas } */
export const crearPase = (slotId, datos) => api(`/slots/${id(slotId)}/pases`, { metodo: 'POST', cuerpo: datos });
/** cambios: { version (obligatoria), estado, inicio, fin, espacio_id, formato, motivo }. 409 VERSION_OBSOLETA si otro admin lo cambió. */
export const modificarPase = (paseId, cambios) => api(`/pases/${id(paseId)}`, { metodo: 'PATCH', cuerpo: cambios });
export const eliminarPase = (paseId) => api(`/pases/${id(paseId)}`, { metodo: 'DELETE' });

// ── Publicación ─────────────────────────────────────────────
export const listarPublicaciones = (eventoId) => api(`/escaletas/${id(eventoId)}/publicaciones`);
/** 409 SIN_CAMBIOS si no hay cambios desde la última publicación. */
export const publicarEscaleta = (eventoId) => api(`/escaletas/${id(eventoId)}/publicaciones`, { metodo: 'POST' });
