// src/api/usuarios.js — llamadas a ms-usuarios (a través del gateway).  Dueño: Luis
// Rutas en docs/openapi/ms-usuarios.yaml. Las tres primeras las usa la sesión (no cambiar su firma).
import { api } from './cliente';

/** Perfil del usuario autenticado. ErrorApi 404 si aún no ha registrado su perfil. */
export const obtenerPerfil = () => api('/usuarios/me');

/** Registro del perfil tras crear la cuenta en Firebase. datos = { nombre, apellidos, rol, proveedor? } */
export const registrarPerfil = (datos) => api('/usuarios', { metodo: 'POST', cuerpo: datos });

export const modificarPerfil = (cambios) => api('/usuarios/me', { metodo: 'PATCH', cuerpo: cambios });

/** Favoritos del cliente. Compartidas con la ficha de artista y el cartel del evento. */
export const listarFavoritos = () => api('/usuarios/me/favoritos');
export const anadirFavorito = (artistaId) => api('/usuarios/me/favoritos', {
  metodo: 'POST', cuerpo: { artista_id: artistaId },
});
export const quitarFavorito = (artistaId) => api(`/usuarios/me/favoritos/${encodeURIComponent(artistaId)}`, {
  metodo: 'DELETE',
});

export const comprarEntrada = (datos) => api('/usuarios/me/entradas', { metodo: 'POST', cuerpo: datos });
export const listarMisEntradas = (estado) => api('/usuarios/me/entradas', { parametros: { estado } });
export const solicitarCancelacion = (entradaId, motivo) => api(
  `/usuarios/me/entradas/${encodeURIComponent(entradaId)}/cancelaciones`,
  { metodo: 'POST', cuerpo: { motivo } },
);

export const eliminarCuenta = () => api('/usuarios/me', { metodo: 'DELETE' });
export const obtenerPreferencias = () => api('/usuarios/me/preferencias-notificacion');
export const guardarPreferencias = (datos) => api('/usuarios/me/preferencias-notificacion', { metodo: 'PUT', cuerpo: datos });
export const registrarDispositivo = (fcmToken) => api('/usuarios/me/dispositivos', {
  metodo: 'POST', cuerpo: { fcm_token: fcmToken, plataforma: 'WEB' },
});
export const eliminarDispositivo = (fcmToken) => api(`/usuarios/me/dispositivos/${encodeURIComponent(fcmToken)}`, { metodo: 'DELETE' });

export const listarUsuarios = (filtros) => api('/usuarios', { parametros: filtros, conTotal: true });
export const modificarUsuario = (usuarioId, datos) => api(`/usuarios/${encodeURIComponent(usuarioId)}`, { metodo: 'PATCH', cuerpo: datos });
export const listarProveedores = (filtros) => api('/proveedores', { parametros: filtros, conTotal: true });
export const validarProveedor = (usuarioId, validado) => api(`/proveedores/${encodeURIComponent(usuarioId)}`, { metodo: 'PATCH', cuerpo: { validado } });
export const listarEntradasAdmin = (filtros) => api('/entradas', { parametros: filtros, conTotal: true });
export const resolverCancelacion = (entradaId, estado) => api(`/entradas/${encodeURIComponent(entradaId)}`, { metodo: 'PATCH', cuerpo: { estado } });
export const validarEntrada = (codigoQr, eventoId) => api('/entradas/validaciones', {
  metodo: 'POST', cuerpo: { codigo_qr: codigoQr, evento_id: eventoId },
});
