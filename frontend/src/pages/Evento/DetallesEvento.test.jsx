import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listarTarifas, obtenerEvento } from '../../api/espacios';
import { registrarInteraccion } from '../../analitica/interacciones';
import DetallesEvento from './DetallesEvento';

vi.mock('../../api/espacios', () => ({ listarTarifas: vi.fn(), obtenerEvento: vi.fn() }));
vi.mock('../../analitica/interacciones', () => ({ registrarInteraccion: vi.fn() }));
vi.mock('./CartelEvento', () => ({ default: ({ eventoId }) => <p>Cartel {eventoId}</p> }));
vi.mock('./ModalCheckout', () => ({ default: ({ abierto, tarifa }) => (
  abierto ? <p role="status">Checkout {tarifa.tipo_pase}</p> : null
) }));

const pintar = () => render(<MemoryRouter initialEntries={['/evento/evento-1']}>
  <Routes><Route path="/evento/:id" element={<DetallesEvento />} /></Routes>
</MemoryRouter>);

describe('Ficha del evento', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(obtenerEvento).mockResolvedValue({
      id: 'evento-1', titulo: 'Subsonic Belgium', pais: 'Bélgica',
      fecha_inicio: '2026-07-18', fecha_fin: '2026-07-27',
      recinto: { nombre: 'Dreamville Grounds', ciudad: 'Boom' },
      servicios_generales: ['Zona de acampada'],
    });
    vi.mocked(listarTarifas).mockResolvedValue([
      { id: 'tarifa-1', tipo_pase: 'DAY', precio: 89, disponibles: 10 },
    ]);
  });

  it('muestra datos del evento, cartel, servicios y abre la compra con la tarifa', async () => {
    pintar();
    expect(await screen.findByRole('heading', { name: 'Subsonic Belgium' })).toBeInTheDocument();
    expect(screen.getByText('Dreamville Grounds · 2026-07-18 – 2026-07-27')).toBeInTheDocument();
    expect(screen.getByText('Zona de acampada')).toBeInTheDocument();
    expect(registrarInteraccion).toHaveBeenCalledWith('VER_EVENTO', 'evento-1');
    fireEvent.click(screen.getByRole('button', { name: 'Artistas y horarios' }));
    expect(screen.getByText('Cartel evento-1')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Pases' }));
    fireEvent.click(screen.getByRole('button', { name: /DAY.*89.*10 disponibles/i }));
    expect(screen.getByRole('status')).toHaveTextContent('Checkout DAY');
  });

  it('muestra el error de evento del gateway', async () => {
    vi.mocked(obtenerEvento).mockRejectedValue(new Error('Evento no encontrado'));
    pintar();
    expect(await screen.findByRole('alert')).toHaveTextContent('Evento no encontrado');
  });
});
