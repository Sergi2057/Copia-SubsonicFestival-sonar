import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { eliminarCuenta, modificarPerfil } from '../../api/usuarios';
import { useSesion } from '../../sesion/SesionContext';
import DatosPersonales from './DatosPersonales';

vi.mock('../../api/usuarios', () => ({ eliminarCuenta: vi.fn(), modificarPerfil: vi.fn() }));
vi.mock('../../sesion/SesionContext', () => ({ useSesion: vi.fn() }));
const perfil = { id: 'u1', nombre: 'David', apellidos: 'García', email: 'david@example.com', rol: 'CLIENTE', activo: true };
const recargarPerfil = vi.fn();
const cerrarSesion = vi.fn();
describe('Datos personales', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useSesion).mockReturnValue({ perfil, recargarPerfil, cerrarSesion });
  });
  it('muestra el perfil y guarda los cambios recargando la sesión', async () => {
    render(<DatosPersonales perfil={perfil} />);
    expect(screen.getByLabelText('Email')).toHaveValue(perfil.email);
    await userEvent.clear(screen.getByLabelText('Nombre'));
    await userEvent.type(screen.getByLabelText('Nombre'), 'Luis');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Datos personales guardados');
    expect(modificarPerfil).toHaveBeenCalledWith(expect.objectContaining({ nombre: 'Luis' }));
    expect(recargarPerfil).toHaveBeenCalledTimes(1);
  });
  it('incluye los datos de empresa sin permitir validar al proveedor', async () => {
    render(<DatosPersonales perfil={{ ...perfil, rol: 'PROVEEDOR', proveedor: { nombre_comercial: 'Food', validado: false } }} />);
    await userEvent.type(screen.getByLabelText('CIF'), 'B12345678');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByRole('status')).toHaveTextContent('guardados');
    expect(modificarPerfil.mock.calls[0][0].proveedor).toEqual(expect.objectContaining({ nombre_comercial: 'Food', cif: 'B12345678' }));
    expect(modificarPerfil.mock.calls[0][0].proveedor).not.toHaveProperty('validado');
  });
  it('desactiva solo tras confirmar y cierra la sesión', async () => {
    render(<DatosPersonales perfil={perfil} />);
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar cuenta' }));
    expect(modificarPerfil).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar acción' }));
    expect(modificarPerfil).toHaveBeenCalledWith({ activo: false });
    expect(cerrarSesion).toHaveBeenCalledTimes(1);
  });
  it('exige confirmar el borrado y no cierra sesión ante un 409', async () => {
    vi.mocked(eliminarCuenta).mockRejectedValue(new Error('Tiene entradas activas'));
    render(<DatosPersonales perfil={perfil} />);
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar cuenta' }));
    expect(screen.getByRole('button', { name: 'Confirmar acción' })).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Confirmación'), 'ELIMINAR');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar acción' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Tiene entradas activas');
    expect(cerrarSesion).not.toHaveBeenCalled();
  });
  it('muestra el error de guardado', async () => {
    vi.mocked(modificarPerfil).mockRejectedValue(new Error('Datos no válidos'));
    render(<DatosPersonales perfil={perfil} />);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Datos no válidos');
  });
});
