// src/sesion/SesionContext.jsx
// Sesión del usuario para toda la app: quién es, su perfil de ms-usuarios y su rol.
//
//   const { perfil, rol, cargando, entrarComoPrueba, registrar, cerrarSesion } = useSesion();
//
// rol va en minúsculas ('cliente', 'proveedor', 'admin', 'staff') o null si no hay sesión o falta el perfil.
//
// Si al cerrar sesión hay que avisar al backend (p. ej. dar de baja el móvil para el push), desde tu archivo:
//   const quitar = alCerrarSesion(() => quitarDispositivo(tokenFcm));   // quitar() la desapunta
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from '../firebase/firebaseConfig';
import { configurarToken } from '../api/cliente';
import { obtenerPerfil, registrarPerfil } from '../api/usuarios';
import { MODO_DESARROLLO, tokenDesarrollo } from './usuariosPrueba';

const SesionContext = createContext(null);
const CLAVE_PRUEBA = 'subsonic.usuarioPrueba';  // sessionStorage: el usuario de prueba sobrevive a recargar
const ESPERA_LIMPIEZA_MS = 3000;                // cerrar sesión nunca espera más que esto a las limpiezas

const limpiezasAlCerrar = new Set();

/**
 * Apunta una función que se ejecuta al cerrar sesión, ANTES de borrar el token (puede llamar a la API).
 * Si falla o tarda más de 3 s, la sesión se cierra igualmente. Devuelve una función para desapuntarla.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function alCerrarSesion(funcion) {
  limpiezasAlCerrar.add(funcion);
  return () => limpiezasAlCerrar.delete(funcion);
}

async function ejecutarLimpiezas() {
  const todas = Promise.allSettled([...limpiezasAlCerrar].map((f) => Promise.resolve().then(f)));
  let temporizador;
  const limite = new Promise((resolver) => { temporizador = setTimeout(resolver, ESPERA_LIMPIEZA_MS); });
  await Promise.race([todas, limite]);
  clearTimeout(temporizador);
}

function leerUsuarioPrueba() {
  if (!MODO_DESARROLLO) return null;
  try {
    return JSON.parse(sessionStorage.getItem(CLAVE_PRUEBA));
  } catch {
    return null;
  }
}

export function SesionProvider({ children }) {
  const [usuarioFirebase, setUsuarioFirebase] = useState(null);
  const [usuarioPrueba, setUsuarioPrueba] = useState(leerUsuarioPrueba);
  const [perfil, setPerfil] = useState(null);
  const [sinPerfil, setSinPerfil] = useState(false);  // autenticado en Firebase pero sin registrar en ms-usuarios
  const [aviso, setAviso] = useState('');
  const [firebaseListo, setFirebaseListo] = useState(false);
  // De quién es el perfil cargado: mientras no sea el usuario actual, la sesión está "cargando"
  const [perfilCargadoDe, setPerfilCargadoDe] = useState(undefined);
  const usuarioActual = usuarioPrueba?.uid ?? usuarioFirebase?.uid ?? null;

  useEffect(() => onAuthStateChanged(auth, (usuario) => {
    setUsuarioFirebase(usuario);
    setFirebaseListo(true);
  }), []);

  // El cliente HTTP pide el token a la sesión en cada petición
  useEffect(() => {
    configurarToken(async (forzar) => {
      if (usuarioPrueba) return tokenDesarrollo(usuarioPrueba);
      if (usuarioFirebase) return usuarioFirebase.getIdToken(forzar);
      return null;
    });
  }, [usuarioFirebase, usuarioPrueba]);

  const aplicarPerfil = useCallback(({ datos, falta, mensaje }) => {
    setPerfil(datos);
    setSinPerfil(falta);
    setAviso(mensaje);
    setPerfilCargadoDe(usuarioActual);
  }, [usuarioActual]);

  const cargarPerfil = useCallback(
    async () => aplicarPerfil(await leerPerfil(usuarioActual, usuarioPrueba ? null : usuarioFirebase)),
    [aplicarPerfil, usuarioActual, usuarioFirebase, usuarioPrueba],
  );

  useEffect(() => {
    if (!firebaseListo) return undefined;
    let vigente = true;  // si cambia el usuario antes de que llegue la respuesta, se descarta
    leerPerfil(usuarioActual, usuarioPrueba ? null : usuarioFirebase).then((r) => vigente && aplicarPerfil(r));
    return () => { vigente = false; };
  }, [firebaseListo, usuarioActual, usuarioFirebase, usuarioPrueba, aplicarPerfil]);

  const cargando = !firebaseListo || perfilCargadoDe !== usuarioActual;

  const entrarComoPrueba = useCallback((usuario) => {
    sessionStorage.setItem(CLAVE_PRUEBA, JSON.stringify(usuario));
    setUsuarioPrueba(usuario);
  }, []);

  /** Crea el perfil en ms-usuarios y renueva el token para que lleve el rol recién asignado. */
  const registrar = useCallback(async (datos) => {
    await registrarPerfil(datos);
    if (usuarioFirebase) await usuarioFirebase.getIdToken(true);
    await cargarPerfil();
  }, [usuarioFirebase, cargarPerfil]);

  const cerrarSesion = useCallback(async () => {
    await ejecutarLimpiezas();  // con el token todavía válido
    sessionStorage.removeItem(CLAVE_PRUEBA);
    setUsuarioPrueba(null);
    setPerfil(null);
    if (auth.currentUser) await signOut(auth);
  }, []);

  const valor = useMemo(() => ({
    perfil,
    rol: perfil?.rol ? perfil.rol.toLowerCase() : null,
    autenticado: Boolean(usuarioPrueba || usuarioFirebase),
    sinPerfil,
    aviso,
    cargando,
    usuarioPrueba,
    entrarComoPrueba,
    registrar,
    recargarPerfil: cargarPerfil,
    cerrarSesion,
  }), [perfil, usuarioPrueba, usuarioFirebase, sinPerfil, aviso, cargando, entrarComoPrueba, registrar,
    cargarPerfil, cerrarSesion]);

  return <SesionContext.Provider value={valor}>{children}</SesionContext.Provider>;
}

/** Perfil de ms-usuarios del usuario actual. falta = autenticado pero sin perfil registrado (404). */
async function leerPerfil(usuarioActual, usuarioFirebase) {
  if (!usuarioActual) return { datos: null, falta: false, mensaje: '' };
  try {
    const datos = await obtenerPerfil();
    const mensaje = usuarioFirebase ? await comprobarRolEnToken(usuarioFirebase, datos.rol) : '';
    return { datos, falta: false, mensaje };
  } catch (error) {
    return { datos: null, falta: error.status === 404, mensaje: error.status === 404 ? '' : error.message };
  }
}

/** El rol solo llega al token cuando se renueva; si sigue sin estar, el resto de servicios responderán 401. */
async function comprobarRolEnToken(usuario, rolPerfil) {
  let claims = (await usuario.getIdTokenResult()).claims;
  if (claims.rol !== rolPerfil) claims = (await usuario.getIdTokenResult(true)).claims;
  if (claims.rol === rolPerfil) return '';
  return 'Tu token de Firebase todavía no incluye tu rol. Si estás en local, ms-usuarios necesita '
    + 'firebase-claves.json (ver infra/README.md); si un administrador te cambió el rol, vuelve a iniciar sesión.';
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSesion() {
  const sesion = useContext(SesionContext);
  if (!sesion) throw new Error('useSesion() debe usarse dentro de <SesionProvider>');
  return sesion;
}
