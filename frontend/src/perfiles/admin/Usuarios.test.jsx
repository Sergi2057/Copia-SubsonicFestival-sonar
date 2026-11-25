import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarUsuarios, listarProveedores, modificarUsuario, validarProveedor } from '../../api/usuarios';
import Usuarios from './Usuarios';

vi.mock('../../api/usuarios', () => ({ listarUsuarios: vi.fn(), listarProveedores: vi.fn(), modificarUsuario: vi.fn(), validarProveedor: vi.fn() }));
vi.mock('../../sesion/SesionContext', () => ({ useSesion: () => ({ perfil: { id: 'admin-actual' } }) }));
const usuario = { id: 'u1', nombre: 'David', email: 'david@test.com', rol: 'CLIENTE', activo: true };
describe('Administración de usuarios y proveedores', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarUsuarios).mockResolvedValue({ datos: [usuario], total: 1 });
    vi.mocked(listarProveedores).mockResolvedValue({ datos: [{ ...usuario, rol: 'PROVEEDOR',
      proveedor: { nombre_comercial: 'Food Truck', validado: false } }], total: 1 });
  });
  it('muestra el usuario y guarda un nuevo rol', async () => {
    render(<Usuarios />);
    const selector = await screen.findByLabelText('Rol de David');
    await userEvent.selectOptions(selector, 'STAFF');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar rol' }));
    expect(modificarUsuario).toHaveBeenCalledWith('u1', { rol: 'STAFF' });
    expect(await screen.findByRole('status')).toHaveTextContent('Usuario actualizado');
  });
  it('desactiva una cuenta', async () => {
    render(<Usuarios />);
    await userEvent.click(await screen.findByRole('button', { name: 'Desactivar' }));
    expect(modificarUsuario).toHaveBeenCalledWith('u1', { activo: false });
  });
  it('permite validar proveedores', async () => {
    render(<Usuarios />);
    await userEvent.click(screen.getByRole('button', { name: 'Proveedores' }));
    expect(await screen.findByText('Food Truck')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Validar proveedor' }));
    expect(validarProveedor).toHaveBeenCalledWith('u1', true);
    expect(await screen.findByRole('status')).toHaveTextContent('Usuario actualizado');
  });
  it('pagina y vuelve al comienzo al aplicar filtros', async () => {
    vi.mocked(listarUsuarios).mockResolvedValue({ datos: [usuario], total: 21 });
    render(<Usuarios />);
    await userEvent.click(await screen.findByRole('button', { name: 'Siguiente' }));
    await waitFor(() => expect(listarUsuarios).toHaveBeenLastCalledWith(expect.objectContaining({ desplazamiento: 20 })));
    await userEvent.selectOptions(screen.getByLabelText('Rol', { exact: true }), 'STAFF');
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' }));
    await waitFor(() => expect(listarUsuarios).toHaveBeenLastCalledWith({ rol: 'STAFF', limite: 20, desplazamiento: 0 }));
  });
  it('muestra errores del backend al modificar sin anunciar éxito', async () => {
    vi.mocked(modificarUsuario).mockRejectedValue(new Error('Sin permiso'));
    render(<Usuarios />);
    await userEvent.click(await screen.findByRole('button', { name: 'Desactivar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Sin permiso');
    expect(screen.queryByText('Usuario actualizado.')).not.toBeInTheDocument();
  });
  it('ofrece reintentar si falla el listado', async () => {
    vi.mocked(listarUsuarios).mockRejectedValue(new Error('Servicio no disponible'));
    render(<Usuarios />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Servicio no disponible');
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument();
  });
});
