// src/pages/Evento/escaletaUtil.js — Dueño: Sergio
// Utilidades de la escaleta compartidas por el cartel del evento, la ficha del artista y el panel de admin.

/** Igual que ms-escaleta (HORA_CORTE_DIA): un pase a la 01:00 pertenece a la noche anterior. */
export const HORA_CORTE_DIA = 6;

export const ESTADOS_PASE = {
  PROGRAMADO: 'Programado',
  CONFIRMADO: 'Confirmado',
  EN_CURSO: 'En curso',
  FINALIZADO: 'Finalizado',
  CANCELADO: 'Cancelado',
};

/** Transiciones que admite ms-escaleta (PATCH /pases/{id}). */
export const TRANSICIONES_PASE = {
  PROGRAMADO: ['CONFIRMADO', 'CANCELADO'],
  CONFIRMADO: ['EN_CURSO', 'CANCELADO'],
  EN_CURSO: ['FINALIZADO'],
  FINALIZADO: [],
  CANCELADO: [],
};

export const FORMATOS_PASE = { DJ_SET: 'DJ set', LIVE: 'Live', B2B: 'B2B' };
export const TIPOS_SLOT = { ACTUACION: 'Actuación', CAMBIO_ESCENARIO: 'Cambio de escenario', DESCANSO: 'Descanso' };

export const hora = (iso) => new Date(iso).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });

export const fechaLarga = (fecha) => new Date(`${fecha}T12:00:00Z`).toLocaleDateString('es-ES', {
  weekday: 'long', day: 'numeric', month: 'long',
});

export const fechaHora = (iso) => new Date(iso).toLocaleString('es-ES', {
  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
});

/** ISO → valor de un <input type="datetime-local"> en la hora del navegador. */
export const aLocal = (iso) => {
  const fecha = new Date(iso);
  return new Date(fecha.getTime() - fecha.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};

/** Valor de datetime-local → ISO con zona (ms-escaleta exige la zona horaria). */
export const aIso = (local) => new Date(local).toISOString();

/** Día de festival (YYYY-MM-DD) de un pase, con el mismo corte que el backend. */
export function diaDeFestival(inicio) {
  return new Date(new Date(inicio).getTime() - HORA_CORTE_DIA * 3600 * 1000).toISOString().slice(0, 10);
}

/** Artistas distintos de la escaleta, por orden alfabético: [{ artista_id, artista }]. */
export function artistasDeEscaleta(escaleta) {
  const vistos = new Map();
  (escaleta?.dias || []).forEach((dia) => dia.escenarios.forEach((escenario) => escenario.pases.forEach((pase) => {
    if (!vistos.has(pase.artista_id)) vistos.set(pase.artista_id, { artista_id: pase.artista_id, artista: pase.artista });
  })));
  return [...vistos.values()].sort((a, b) => a.artista.localeCompare(b.artista, 'es'));
}

/**
 * Aplica a la escaleta un aviso del SSE (pase.modificado / pase.cancelado) sin volver a pedirla:
 * quita el pase de donde estuviera y lo coloca en su día y escenario nuevos. Devuelve una escaleta nueva.
 */
export function aplicarCambioPase(escaleta, pase) {
  if (!escaleta || !pase) return escaleta;
  const dias = escaleta.dias.map((dia) => ({
    ...dia,
    escenarios: dia.escenarios.map((e) => ({ ...e, pases: e.pases.filter((p) => p.pase_id !== pase.pase_id) })),
  }));
  const fecha = diaDeFestival(pase.inicio);
  let dia = dias.find((d) => d.fecha === fecha);
  if (!dia) {
    dia = { fecha, escenarios: [] };
    dias.push(dia);
    dias.sort((a, b) => a.fecha.localeCompare(b.fecha));
  }
  let escenario = dia.escenarios.find((e) => e.nombre === pase.escenario);
  if (!escenario) {
    escenario = { espacio_id: pase.escenario, nombre: pase.escenario, pases: [] };
    dia.escenarios.push(escenario);
    dia.escenarios.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  }
  escenario.pases = [...escenario.pases, pase].sort((a, b) => a.inicio.localeCompare(b.inicio));
  // Se quitan los escenarios y días que se hayan quedado vacíos
  return {
    ...escaleta,
    dias: dias
      .map((d) => ({ ...d, escenarios: d.escenarios.filter((e) => e.pases.length) }))
      .filter((d) => d.escenarios.length),
  };
}

/** URL para incrustar en un iframe un vídeo o playlist de YouTube (null si no se reconoce). */
export function urlIncrustada(video) {
  try {
    const url = new URL(video.url);
    const lista = url.searchParams.get('list');
    // Los identificadores vienen de YouTube: se codifican para que no puedan alterar la URL del iframe
    if (video.tipo === 'PLAYLIST' && lista) return `https://www.youtube.com/embed/videoseries?list=${encodeURIComponent(lista)}`;
    const v = url.searchParams.get('v');
    return v ? `https://www.youtube.com/embed/${encodeURIComponent(v)}` : null;
  } catch {
    return null;
  }
}
