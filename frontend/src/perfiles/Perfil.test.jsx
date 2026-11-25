// src/perfiles/Perfil.test.jsx
// Ejemplo de test de pantalla: se simula Firebase y la API, se pinta la página y se comprueba lo que ve el usuario.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../firebase/firebaseConfig', () => ({ auth: {}, googleProvider: {} }));
vi.mock('firebase/auth', () => ({
  onAuthStateChanged: (_auth, alCambiar) => { alCambiar(null); return () => {}; },  // nadie con Firebase
  signOut: vi.fn(),
}));
vi.mock('../sesion/usuariosPrueba', async (original) => ({ ...(await original()), MODO_DESARROLLO: true }));
vi.mock('../api/usuarios', () => ({ obtenerPerfil: vi.fn(), registrarPerfil: vi.fn() }));

const { obtenerPerfil, registrarPerfil } = await import('../api/usuarios');
const { SesionProvider, alCerrarSesion } = await import('../sesion/SesionContext');
const { default: Perfil } = await import('./Perfil');
const { USUARIOS_PRUEBA } = await import('../sesion/usuariosPrueba');

function pintarPerfil() {
  render(
    <SesionProvider>
      <MemoryRouter initialEntries={['/perfil']}>
        <Routes>
          <Route path="/" element={<p>Portada</p>} />
          <Route path="/perfil" element={<Perfil />} />
        </Routes>
      </MemoryRouter>
    </SesionProvider>,
  );
}

function entrarComo(uid) {
  sessionStorage.setItem('subsonic.usuarioPrueba', JSON.stringify(USUARIOS_PRUEBA.find((u) => u.uid === uid)));
}

describe('Perfil', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.mocked(obtenerPerfil).mockReset();
  });

  it('sin sesión vuelve a la portada', async () => {
    pintarPerfil();

    expect(await screen.findByText('Portada')).toBeInTheDocument();
  });

  it.each([
    ['uid-cliente-david', 'CLIENTE', 'Mis Entradas'],
    ['uid-proveedor-ana', 'PROVEEDOR', 'Mis Alquileres'],
    ['uid-admin-jose', 'ADMIN', 'Eventos y Recintos'],
    ['uid-staff-lucia', 'STAFF', 'Control de Acceso'],
  ])('%s ve el panel de su rol (%s)', async (uid, rol, pestana) => {
    entrarComo(uid);
    vi.mocked(obtenerPerfil).mockResolvedValue({ id: uid, nombre: 'Nombre', apellidos: 'Apellidos', rol });

    pintarPerfil();

    expect(await screen.findByText(pestana)).toBeInTheDocument();
    expect(screen.getByText('Nombre Apellidos')).toBeInTheDocument();
  });

  it('un usuario sin perfil (404) ve el formulario para completar el registro', async () => {
    entrarComo('uid-cliente-david');
    vi.mocked(obtenerPerfil).mockRejectedValue(Object.assign(new Error('Sin perfil'), { status: 404 }));

    pintarPerfil();

    expect(await screen.findByText('COMPLETA TU REGISTRO')).toBeInTheDocument();
    expect(registrarPerfil).not.toHaveBeenCalled();
  });
  it('al cerrar sesión ejecuta las limpiezas apuntadas con la sesión aún abierta', async () => {
    entrarComo('uid-cliente-david');
    vi.mocked(obtenerPerfil).mockResolvedValue({ id: 'uid-cliente-david', nombre: 'David', apellidos: 'G', rol: 'CLIENTE' });
    let sesionAbiertaAlLimpiar = null;
    const quitar = alCerrarSesion(() => { sesionAbiertaAlLimpiar = sessionStorage.getItem('subsonic.usuarioPrueba') !== null; });
    pintarPerfil();

    await userEvent.click(await screen.findByRole('button', { name: 'Cerrar Sesión' }));

    expect(await screen.findByText('Portada')).toBeInTheDocument();
    expect(sesionAbiertaAlLimpiar).toBe(true);
    quitar();
  });

  it('si una limpieza falla, la sesión se cierra igualmente', async () => {
    entrarComo('uid-cliente-david');
    vi.mocked(obtenerPerfil).mockResolvedValue({ id: 'uid-cliente-david', nombre: 'David', apellidos: 'G', rol: 'CLIENTE' });
    const quitar = alCerrarSesion(() => { throw new Error('sin red'); });
    pintarPerfil();

    await userEvent.click(await screen.findByRole('button', { name: 'Cerrar Sesión' }));

    expect(await screen.findByText('Portada')).toBeInTheDocument();
    expect(sessionStorage.getItem('subsonic.usuarioPrueba')).toBeNull();
    quitar();
  });
});
