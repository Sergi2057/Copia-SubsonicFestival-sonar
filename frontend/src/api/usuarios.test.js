import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './cliente';
import { anadirFavorito, listarFavoritos, quitarFavorito, eliminarDispositivo, comprarEntrada,
  solicitarCancelacion } from './usuarios';

vi.mock('./cliente', () => ({ api: vi.fn() }));

describe('API de favoritos compartida con cartel y artistas', () => {
  beforeEach(() => vi.mocked(api).mockReset());

  it('devuelve los favoritos del usuario autenticado', async () => {
    const favoritos = [{ artista_id: 'artista-1', artista_nombre: 'Artista' }];
    vi.mocked(api).mockResolvedValue(favoritos);
    expect(await listarFavoritos()).toEqual(favoritos);
    expect(api).toHaveBeenCalledWith('/usuarios/me/favoritos');
  });

  it('añade por ID usando el cuerpo del contrato', async () => {
    await anadirFavorito('artista-1');
    expect(api).toHaveBeenCalledWith('/usuarios/me/favoritos', {
      metodo: 'POST', cuerpo: { artista_id: 'artista-1' },
    });
  });

  it('quita un favorito y admite la respuesta 204 del cliente HTTP', async () => {
    vi.mocked(api).mockResolvedValue(null);
    expect(await quitarFavorito('artista/1')).toBeNull();
    expect(api).toHaveBeenCalledWith('/usuarios/me/favoritos/artista%2F1', { metodo: 'DELETE' });
  });

  it('propaga los errores del gateway a la pantalla', async () => {
    const error = Object.assign(new Error('Ya está en favoritos'), { status: 409 });
    vi.mocked(api).mockRejectedValue(error);
    await expect(anadirFavorito('artista-1')).rejects.toBe(error);
  });
});

describe('Contratos de entradas y dispositivos', () => {
  it('codifica el token FCM en el segmento de ruta de la baja', async () => {
    vi.mocked(api).mockReset();
    await eliminarDispositivo('navegador:token/con+simbolos');
    expect(api).toHaveBeenCalledWith('/usuarios/me/dispositivos/navegador%3Atoken%2Fcon%2Bsimbolos', { metodo: 'DELETE' });
  });
  it('envía el token de pago y el motivo de la cancelación al gateway', async () => {
    vi.mocked(api).mockReset();
    const datos = { evento_id: 'evento-1', tipo_pase: 'DAY', token_pago: 'tok_ok' };
    await comprarEntrada(datos);
    expect(api).toHaveBeenCalledWith('/usuarios/me/entradas', { metodo: 'POST', cuerpo: datos });
    await solicitarCancelacion('entrada-1', 'No puedo asistir');
    expect(api).toHaveBeenCalledWith('/usuarios/me/entradas/entrada-1/cancelaciones', {
      metodo: 'POST', cuerpo: { motivo: 'No puedo asistir' },
    });
  });
});
