// src/sesion/usuariosPrueba.js
// Usuarios de los datos de prueba (scripts/poblar_bd.py de ms-usuarios) para "Entrar como…" en desarrollo.
// Usan tokens dev:<uid>:<ROL>:<email>, que el gateway solo acepta con MODO_AUTENTICACION=desarrollo.

export const MODO_DESARROLLO = import.meta.env.VITE_MODO_DESARROLLO === 'true';

export const USUARIOS_PRUEBA = [
  { uid: 'uid-cliente-david', rol: 'CLIENTE', email: 'cliente@subsonic.com', nombre: 'David (cliente)' },
  { uid: 'uid-proveedor-ana', rol: 'PROVEEDOR', email: 'proveedor@subsonic.com', nombre: 'Ana (proveedora)' },
  { uid: 'uid-admin-jose', rol: 'ADMIN', email: 'admin@subsonic.com', nombre: 'José (administrador)' },
  { uid: 'uid-staff-lucia', rol: 'STAFF', email: 'staff@subsonic.com', nombre: 'Lucía (staff de acceso)' },
];

export function tokenDesarrollo({ uid, rol, email }) {
  return `dev:${uid}:${rol}:${email}`;
}
