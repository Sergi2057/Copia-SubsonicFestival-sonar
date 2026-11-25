import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { validarEntrada } from '../../api/usuarios';
import { listarEventos } from '../../api/espacios';
import ValidarEntradas from './ValidarEntradas';

vi.mock('../../api/usuarios', () => ({ validarEntrada: vi.fn() }));
vi.mock('../../api/espacios', () => ({ listarEventos: vi.fn() }));
const resultado = { entrada_id: 'entrada-1', titular: 'David García', tipo_pase: 'VIP', validada_en: '2026-11-09T12:00:00Z' };
async function preparar() {
  render(<ValidarEntradas />);
  await userEvent.selectOptions(await screen.findByLabelText('Evento'), 'evento-1');
  await userEvent.type(screen.getByLabelText('Código QR'), 'SUBSONIC|entrada|evento|firma');
}
describe('Control de acceso', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listarEventos).mockResolvedValue({ datos: [{ id: 'evento-1', titulo: 'Subsonic' }], total: 1 });
    vi.mocked(validarEntrada).mockResolvedValue(resultado);
  });
  it('exige evento y QR, valida y muestra titular y pase', async () => {
    render(<ValidarEntradas />);
    expect(await screen.findByRole('button', { name: 'Validar entrada' })).toBeDisabled();
    await userEvent.selectOptions(screen.getByLabelText('Evento'), 'evento-1');
    await userEvent.type(screen.getByLabelText('Código QR'), 'QR-firmado');
    await userEvent.click(screen.getByRole('button', { name: 'Validar entrada' }));
    expect(validarEntrada).toHaveBeenCalledWith('QR-firmado', 'evento-1');
    expect(await screen.findByRole('status')).toHaveTextContent('Entrada válida');
    expect(screen.getByText('Titular: David García')).toBeInTheDocument();
    expect(screen.getByText('Pase: VIP')).toBeInTheDocument();
    expect(screen.getByLabelText('Código QR')).toHaveValue('');
  });
  it('un lector puede enviar el código con Enter', async () => {
    await preparar();
    await userEvent.type(screen.getByLabelText('Código QR'), '{enter}');
    expect(await screen.findByRole('status')).toHaveTextContent('Entrada válida');
    expect(validarEntrada).toHaveBeenCalledTimes(1);
  });
  it('muestra el rechazo de un QR usado o de otro evento', async () => {
    vi.mocked(validarEntrada).mockRejectedValue(new Error('La entrada ya se ha usado; acceso denegado'));
    await preparar();
    await userEvent.click(screen.getByRole('button', { name: 'Validar entrada' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('acceso denegado');
    expect(screen.queryByText('Entrada válida')).not.toBeInTheDocument();
  });
  it('muestra errores al cargar los eventos', async () => {
    vi.mocked(listarEventos).mockRejectedValue(new Error('No se pueden consultar los eventos'));
    render(<ValidarEntradas />);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pueden consultar los eventos');
    expect(validarEntrada).not.toHaveBeenCalled();
  });
});
