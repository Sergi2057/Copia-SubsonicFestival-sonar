// src/api/analitica.js — llamadas a ms-analitica (a través del gateway).  Dueña: Paula
// Rutas en docs/openapi/ms-analitica.yaml.
import { api } from './cliente';

// ---------- Estadísticas (rol admin, salvo artistas populares que es público) ----------

/** Indicadores principales. eventoId opcional: si falta, de todo el festival. */
export const obtenerResumen = (eventoId) => api('/estadisticas/resumen', { parametros: { evento_id: eventoId } });

/** Serie de ventas. filtros = { evento_id, desde, hasta, agrupar_por: 'DIA' | 'SEMANA' | 'TIPO_PASE' } */
export const obtenerVentas = (filtros) => api('/estadisticas/ventas', { parametros: filtros });

/** Ocupación por tipo de espacio de un evento (404 SIN_DATOS si no hay datos). */
export const obtenerOcupacion = (eventoId) => api('/estadisticas/ocupacion', { parametros: { evento_id: eventoId } });

/** Previsión de afluencia por escenario y franja de un evento. fecha opcional (AAAA-MM-DD). */
export const obtenerAfluencia = (eventoId, fecha) =>
  api('/estadisticas/afluencia', { parametros: { evento_id: eventoId, fecha } });

/** Ventas de la tienda por producto y talla, y tallas con poco stock. filtros = { desde, hasta } */
export const obtenerEstadisticasTienda = (filtros) => api('/estadisticas/tienda', { parametros: filtros });

/** Ranking de artistas por favoritos y visitas. filtros = { evento_id, limite } */
export const obtenerArtistasPopulares = (filtros) => api('/estadisticas/artistas-populares', { parametros: filtros });

// ---------- Recomendaciones ----------

/** Recomendaciones del cliente con sesión: { eventos, artistas, mi_escaleta, generadas_en } */
export const obtenerMisRecomendaciones = (eventoId) =>
  api('/recomendaciones/me', { parametros: { evento_id: eventoId } });

/** Lo más popular, para visitantes sin sesión: { eventos, artistas } */
export const obtenerRecomendacionesPopulares = () => api('/recomendaciones/populares');

/** Espacios recomendados para el proveedor con sesión, de mayor a menor puntuación. */
export const obtenerEspaciosRecomendados = (eventoId) =>
  api('/recomendaciones/espacios', { parametros: { evento_id: eventoId } });

// ---------- Interacciones ----------

/** Envía un lote de interacciones. Mejor usar registrarInteraccion() de src/analitica/interacciones.js. */
export const registrarInteracciones = (lote) => api('/interacciones', { metodo: 'POST', cuerpo: lote });
