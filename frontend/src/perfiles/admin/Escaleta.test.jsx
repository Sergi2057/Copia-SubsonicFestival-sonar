import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorApi } from '../../api/cliente';
import {
  crearArtista, crearPase, crearSlot, eliminarArtista, listarArtistas, listarPublicaciones, listarSlots, modificarPase,
  publicarEscaleta,
} from '../../api/escaleta';
import { listarEspacios, listarEventos } from '../../api/espacios';
import { aIso } from '../../pages/Evento/escaletaUtil';
import Escaleta from './Escaleta';

vi.mock('../../api/escaleta', () => ({
  listarArtistas: vi.fn(), crearArtista: vi.fn(), modificarArtista: vi.fn(), eliminarArtista: vi.fn(),
  listarSlots: vi.fn(), crearSlot: vi.fn(), eliminarSlot: vi.fn(), crearPase: vi.fn(), modificarPase: vi.fn(),
  eliminarPase: vi.fn(), listarPublicaciones: vi.fn(), publicarEscaleta: vi.fn(),
}));
vi.mock('../../api/espacios', () => ({ listarEventos: vi.fn(), listarEspacios: vi.fn() }));

const ARTISTAS = [{ id: 'a1', nombre: 'Armin van Buuren', generos: ['trance'], pais: 'Países Bajos', redes: {} },
  { id: 'a2', nombre: 'Tiësto', generos: ['house'], pais: null, redes: {} }];
const SLOTS = [
  { id: 's1', evento_id: 'evento-belgium', espacio_id: 'esp-main', inicio: '2026-07-18T20:00:00Z', fin: '2026-07-18T22:00:00Z',
    tipo: 'ACTUACION', pase: { id: 'p1', slot_id: 's1', artista_id: 'a1', artista_nombre: 'Armin van Buuren', formato: 'DJ_SET',
      estado: 'PROGRAMADO', notas_tecnicas: null, version: 4 } },
  { id: 's2', evento_id: 'evento-belgium', espacio_id: 'esp-main', inicio: '2026-07-18T22:00:00Z', fin: '2026-07-19T00:00:00Z',
    tipo: 'ACTUACION', pase: null },
];

async function elegirEvento() {
  render(<MemoryRouter><Escaleta /></MemoryRouter>);
  await screen.findByRole('option', { name: 'Subsonic Belgium' });
  await userEvent.selectOptions(screen.getByLabelText('Evento'), 'evento-belgium');
  await screen.findByRole('heading', { name: 'Main Stage' });
}

describe('admin · Escaleta', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    vi.mocked(listarEventos).mockResolvedValue({ datos: [{ id: 'evento-belgium', titulo: 'Subsonic Belgium' }], total: 1 });
    vi.mocked(listarEspacios).mockResolvedValue({ datos: [{ id: 'esp-main', nombre: 'Main Stage', tipo: 'ESCENARIO' }], total: 1 });
    vi.mocked(listarArtistas).mockResolvedValue({ datos: ARTISTAS, total: 2 });
    vi.mocked(listarSlots).mockResolvedValue(SLOTS);
    vi.mocked(listarPublicaciones).mockResolvedValue([
      { evento_id: 'evento-belgium', version: 2, publicada_en: '2026-07-01T10:00:00Z', publicada_por: 'uid-admin-jose' },
      { evento_id: 'evento-belgium', version: 1, publicada_en: '2026-06-01T10:00:00Z', publicada_por: 'seed' },
    ]);
  });

  it('pinta los slots del evento por escenario y la última publicación', async () => {
    await elegirEvento();
    expect(listarEspacios).toHaveBeenCalledWith({ evento_id: 'evento-belgium', tipo: 'ESCENARIO', limite: 100 });
    expect(within(screen.getByTestId('slot-s1')).getByText('Armin van Buuren')).toBeInTheDocument();
    expect(within(screen.getByTestId('slot-s1')).getByText(/v4/)).toBeInTheDocument();
    expect(screen.getByText(/Última versión publicada: v2/)).toBeInTheDocument();
  });

  it('asigna un artista a un slot libre', async () => {
    await elegirEvento();
    const libre = screen.getByTestId('slot-s2');
    await userEvent.selectOptions(within(libre).getByLabelText('Artista'), 'a2');
    await userEvent.selectOptions(within(libre).getByLabelText('Formato'), 'B2B');
    await userEvent.click(within(libre).getByRole('button', { name: 'Asignar' }));
    expect(crearPase).toHaveBeenCalledWith('s2', { artista_id: 'a2', formato: 'B2B' });
    expect(await screen.findByRole('status')).toHaveTextContent('Artista asignado');
  });

  it('cambia el estado de un pase enviando su version y avisa si otro admin lo cambió antes', async () => {
    await elegirEvento();
    await userEvent.click(within(screen.getByTestId('slot-s1')).getByRole('button', { name: 'Marcar confirmado' }));
    expect(modificarPase).toHaveBeenCalledWith('p1', { version: 4, estado: 'CONFIRMADO' });

    vi.mocked(modificarPase).mockRejectedValue(new ErrorApi(409, 'VERSION_OBSOLETA', 'Otro administrador ha modificado el pase'));
    await userEvent.click(within(await screen.findByTestId('slot-s1')).getByRole('button', { name: 'Cancelar pase' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Otro administrador ha cambiado este pase');
  });

  it('reprograma un pase con su motivo', async () => {
    await elegirEvento();
    const slot = screen.getByTestId('slot-s1');
    await userEvent.click(within(slot).getByRole('button', { name: 'Cambiar horario' }));
    const form = within(slot).getByRole('form', { name: 'Cambiar horario de Armin van Buuren' });
    const inicio = within(form).getByLabelText('Inicio');
    await userEvent.clear(inicio);
    await userEvent.type(inicio, '2026-07-18T23:30');
    await userEvent.type(within(form).getByLabelText(/Motivo/), 'Retraso técnico');
    await userEvent.click(within(form).getByRole('button', { name: 'Guardar' }));
    expect(modificarPase).toHaveBeenCalledWith('p1', { version: 4, inicio: aIso('2026-07-18T23:30'), motivo: 'Retraso técnico' });
  });

  it('crea un slot con fechas con zona horaria', async () => {
    await elegirEvento();
    const form = screen.getByRole('form', { name: 'Nuevo slot' });
    await userEvent.selectOptions(within(form).getByLabelText('Escenario'), 'esp-main');
    await userEvent.type(within(form).getByLabelText('Inicio'), '2026-07-19T00:00');
    await userEvent.type(within(form).getByLabelText('Fin'), '2026-07-19T02:00');
    await userEvent.selectOptions(within(form).getByLabelText('Tipo'), 'DESCANSO');
    await userEvent.click(within(form).getByRole('button', { name: 'Crear slot' }));
    expect(crearSlot).toHaveBeenCalledWith('evento-belgium', { espacio_id: 'esp-main', tipo: 'DESCANSO',
      inicio: aIso('2026-07-19T00:00'), fin: aIso('2026-07-19T02:00') });
  });

  it('publica la escaleta y explica cuándo no hay cambios', async () => {
    await elegirEvento();
    await userEvent.click(screen.getByRole('button', { name: 'Publicar escaleta' }));
    expect(publicarEscaleta).toHaveBeenCalledWith('evento-belgium');
    expect(await screen.findByRole('status')).toHaveTextContent('Escaleta publicada');

    vi.mocked(publicarEscaleta).mockRejectedValue(new ErrorApi(409, 'SIN_CAMBIOS', 'No hay cambios'));
    await userEvent.click(screen.getByRole('button', { name: 'Publicar escaleta' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No hay cambios desde la última publicación.');
  });

  it('da de alta un artista y no deja borrar uno con pases', async () => {
    vi.mocked(crearArtista).mockResolvedValue({});
    vi.mocked(eliminarArtista).mockRejectedValue(new ErrorApi(409, 'ARTISTA_CON_PASES', 'El artista tiene pases asignados'));
    render(<MemoryRouter><Escaleta /></MemoryRouter>);
    await userEvent.click(screen.getByRole('tab', { name: 'Artistas' }));
    const form = await screen.findByRole('form', { name: 'Nuevo artista' });
    await userEvent.type(within(form).getByLabelText('Nombre'), 'Charlotte de Witte');
    await userEvent.type(within(form).getByLabelText(/Géneros/), 'Techno, Acid');
    await userEvent.type(within(form).getByLabelText('País'), 'Bélgica');
    await userEvent.click(within(form).getByRole('button', { name: 'Dar de alta' }));
    expect(crearArtista).toHaveBeenCalledWith({ nombre: 'Charlotte de Witte', generos: ['techno', 'acid'], pais: 'Bélgica',
      biografia: null, imagen_url: null, youtube_channel_id: null, redes: {} });

    await userEvent.click(await screen.findByRole('button', { name: 'Eliminar a Armin van Buuren' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Armin van Buuren tiene pases en alguna escaleta');
  });
});
