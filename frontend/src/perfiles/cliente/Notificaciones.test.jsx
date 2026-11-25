import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { guardarPreferencias, obtenerPreferencias } from '../../api/usuarios';
import { activarPush, desactivarPush, dispositivoActual } from './dispositivoPush';
import Notificaciones from './Notificaciones';

vi.mock('../../api/usuarios', () => ({ guardarPreferencias: vi.fn(), obtenerPreferencias: vi.fn() }));
vi.mock('../../sesion/SesionContext', () => ({ useSesion: () => ({ perfil: { id: 'u1' } }) }));
vi.mock('../../sesion/usuariosPrueba', () => ({ MODO_DESARROLLO: true }));
vi.mock('./dispositivoPush', () => ({ activarPush: vi.fn(), desactivarPush: vi.fn(), dispositivoActual: vi.fn() }));
describe('Notificaciones', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(obtenerPreferencias).mockResolvedValue({ push: true, email: true });
    vi.mocked(dispositivoActual).mockReturnValue(null);
  });
  it('muestra y guarda los canales elegidos', async () => {
    render(<Notificaciones />);
    await userEvent.click(await screen.findByLabelText('Notificaciones push'));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar preferencias' }));
    expect(guardarPreferencias).toHaveBeenCalledWith({ push: false, email: true });
    expect(await screen.findByRole('status')).toHaveTextContent('Preferencias guardadas');
  });
  it('registra este navegador en modo de prueba', async () => {
    vi.mocked(activarPush).mockResolvedValue({ usuarioId: 'u1', token: 't1', prueba: true });
    render(<Notificaciones />);
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar navegador de prueba' }));
    expect(activarPush).toHaveBeenCalledWith('u1', true);
    expect(await screen.findByText('Registrado para pruebas.')).toBeInTheDocument();
  });
  it('da de baja el dispositivo registrado', async () => {
    vi.mocked(dispositivoActual).mockReturnValue({ token: 't1', prueba: true });
    render(<Notificaciones />);
    await userEvent.click(await screen.findByRole('button', { name: 'Dar de baja este navegador' }));
    expect(desactivarPush).toHaveBeenCalledWith('u1');
    expect(await screen.findByRole('status')).toHaveTextContent('Navegador dado de baja');
  });
  it('da de baja el navegador al desactivar la preferencia push', async () => {
    vi.mocked(dispositivoActual).mockReturnValue({ token: 't1', prueba: true });
    render(<Notificaciones />);
    await userEvent.click(await screen.findByLabelText('Notificaciones push'));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar preferencias' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Preferencias guardadas');
    expect(desactivarPush).toHaveBeenCalledWith('u1');
    expect(screen.queryByRole('button', { name: 'Dar de baja este navegador' })).not.toBeInTheDocument();
  });
  it('muestra los errores del backend al guardar', async () => {
    vi.mocked(guardarPreferencias).mockRejectedValue(new Error('No se han podido guardar'));
    render(<Notificaciones />);
    await userEvent.click(await screen.findByRole('button', { name: 'Guardar preferencias' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se han podido guardar');
  });
  it('muestra un permiso de navegador rechazado', async () => {
    vi.mocked(activarPush).mockRejectedValue(new Error('Permiso denegado'));
    render(<Notificaciones />);
    await userEvent.click(await screen.findByRole('button', { name: 'Activar en este navegador' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Permiso denegado');
  });
});
