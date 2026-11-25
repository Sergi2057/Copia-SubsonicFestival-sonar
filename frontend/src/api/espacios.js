// src/api/espacios.js — llamadas a ms-espacios (a través del gateway).  Dueño: Pedro
// Rutas en docs/openapi/ms-espacios.yaml. Añade aquí las funciones que necesiten tus pantallas.
import { api } from './cliente';

/** Eventos del calendario. filtros = { pais, tag, desde, hasta, estado, limite, desplazamiento } (ver openapi) */
export const listarEventos = (filtros) => api('/eventos', { parametros: filtros, conTotal: true });

export const obtenerEvento = (eventoId) => api(`/eventos/${encodeURIComponent(eventoId)}`);
export const crearEvento = (datos) => api('/eventos', { metodo: 'POST', cuerpo: datos });
export const modificarEvento = (eventoId, datos) => api(`/eventos/${encodeURIComponent(eventoId)}`, {
  metodo: 'PUT', cuerpo: datos,
});
export const cambiarEstadoEvento = (eventoId, estado, motivo) => api(`/eventos/${encodeURIComponent(eventoId)}`, {
  metodo: 'PATCH', cuerpo: { estado, ...(motivo ? { motivo } : {}) },
});
export const eliminarEvento = (eventoId) => api(`/eventos/${encodeURIComponent(eventoId)}`, { metodo: 'DELETE' });

/** Lista espacios. filtros = { evento_id, tipo, disponible, limite, desplazamiento } */
export const listarEspacios = (filtros) => api('/espacios', { parametros: filtros, conTotal: true });
export const obtenerEspacio = (espacioId) => api(`/espacios/${encodeURIComponent(espacioId)}`);
export const crearEspacio = (datos) => api('/espacios', { metodo: 'POST', cuerpo: datos });
export const modificarEspacio = (espacioId, datos) => api(`/espacios/${encodeURIComponent(espacioId)}`, {
  metodo: 'PUT', cuerpo: datos,
});
export const eliminarEspacio = (espacioId) => api(`/espacios/${encodeURIComponent(espacioId)}`, { metodo: 'DELETE' });

export const listarTiposEspacio = () => api('/tipos-espacio');

/** Tarifas y disponibilidad de entradas de un evento. */
export const listarTarifas = (eventoId) => api(`/eventos/${encodeURIComponent(eventoId)}/tarifas`);
export const crearTarifa = (eventoId, datos) => api(`/eventos/${encodeURIComponent(eventoId)}/tarifas`, {
  metodo: 'POST', cuerpo: datos,
});
export const modificarTarifa = (eventoId, tarifaId, datos) => api(
  `/eventos/${encodeURIComponent(eventoId)}/tarifas/${encodeURIComponent(tarifaId)}`,
  { metodo: 'PUT', cuerpo: datos },
);
export const eliminarTarifa = (eventoId, tarifaId) => api(
  `/eventos/${encodeURIComponent(eventoId)}/tarifas/${encodeURIComponent(tarifaId)}`,
  { metodo: 'DELETE' },
);

export const listarRecintos = () => api('/recintos');
export const crearRecinto = (datos) => api('/recintos', { metodo: 'POST', cuerpo: datos });
export const modificarRecinto = (recintoId, datos) => api(`/recintos/${encodeURIComponent(recintoId)}`, {
  metodo: 'PUT', cuerpo: datos,
});
export const eliminarRecinto = (recintoId) => api(`/recintos/${encodeURIComponent(recintoId)}`, { metodo: 'DELETE' });

export const solicitarAlquiler = (espacioId, datos) => api(
  `/espacios/${encodeURIComponent(espacioId)}/alquileres`,
  { metodo: 'POST', cuerpo: datos },
);
export const listarAlquileres = (filtros) => api('/alquileres', { parametros: filtros, conTotal: true });
export const cambiarEstadoAlquiler = (alquilerId, estado, comentarios) => api(
  `/alquileres/${encodeURIComponent(alquilerId)}`,
  { metodo: 'PATCH', cuerpo: { estado, ...(comentarios ? { comentarios } : {}) } },
);
