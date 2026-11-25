// src/api/cliente.js
// Única forma de llamar al backend: todas las peticiones van al API Gateway con el token del usuario.
// Cada servicio tiene su archivo (espacios.js, usuarios.js…) con funciones que usan api().

export const URL_API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// La sesión (src/sesion/SesionContext.jsx) indica cómo obtener el token. forzar = pedir uno nuevo a Firebase.
let obtenerToken = async () => null;

export function configurarToken(funcion) {
  obtenerToken = funcion;
}

/** Error con el formato común del backend: { codigo, mensaje, detalles, correlation_id }. */
export class ErrorApi extends Error {
  constructor(status, codigo, mensaje, detalles = null) {
    super(mensaje);
    this.status = status;
    this.codigo = codigo;
    this.detalles = detalles;
  }
}

function construirUrl(ruta, parametros) {
  const url = new URL(`${URL_API}${ruta}`);
  Object.entries(parametros || {}).forEach(([clave, valor]) => {
    if (valor === undefined || valor === null || valor === '') return;
    (Array.isArray(valor) ? valor : [valor]).forEach((v) => url.searchParams.append(clave, v));
  });
  return url.toString();
}

async function enviar(url, metodo, cuerpo, forzarToken) {
  const token = await obtenerToken(forzarToken);
  const cabeceras = {};
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json';
  if (token) cabeceras.Authorization = `Bearer ${token}`;
  return fetch(url, {
    method: metodo,
    headers: cabeceras,
    body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
  });
}

/**
 * Llama a una ruta del gateway y devuelve el JSON de la respuesta (null si no tiene cuerpo).
 *
 *   await api('/eventos', { parametros: { pais: 'Bélgica' } })
 *   await api('/pedidos', { metodo: 'POST', cuerpo: { lineas, entrega, token_pago } })
 *   const { datos, total } = await api('/productos', { parametros: { limite: 20 }, conTotal: true })
 *
 * Si el backend responde con error, lanza ErrorApi (error.status, error.codigo, error.message).
 */
export async function api(ruta, { metodo = 'GET', cuerpo, parametros, conTotal = false } = {}) {
  const url = construirUrl(ruta, parametros);
  let respuesta;
  try {
    respuesta = await enviar(url, metodo, cuerpo, false);
    // Token caducado: se pide uno nuevo una sola vez
    if (respuesta.status === 401) respuesta = await enviar(url, metodo, cuerpo, true);
  } catch {
    throw new ErrorApi(0, 'SIN_CONEXION', 'No se puede conectar con el servidor. ¿Está arrancado el gateway?');
  }

  if (!respuesta.ok) {
    const error = await respuesta.json().catch(() => ({}));
    throw new ErrorApi(respuesta.status, error.codigo || 'ERROR', error.mensaje || 'Error al procesar la solicitud',
      error.detalles || null);
  }
  // 204, o 201/202 sin cuerpo (p. ej. POST /usuarios/me/dispositivos): null
  const texto = respuesta.status === 204 ? '' : await respuesta.text();
  const datos = texto ? JSON.parse(texto) : null;
  return conTotal ? { datos, total: Number(respuesta.headers.get('X-Total-Count') ?? 0) } : datos;
}

/** URL completa de una ruta, para lo que no usa fetch (EventSource del SSE, enlaces…). */
export function urlApi(ruta) {
  return `${URL_API}${ruta}`;
}
