// src/perfiles/cliente/Resumen.jsx — Dueña: Paula
// Recomendaciones personalizadas (eventos y artistas) y «mi escaleta»: los pases de sus artistas
// favoritos ordenados por hora, con los que coinciden en horario marcados.
// API: GET /recomendaciones/me (ms-analitica); eventos de GET /eventos (ms-espacios)
import { useState } from 'react';
import { obtenerMisRecomendaciones } from '../../api/analitica';
import { Carga, SelectorEvento } from '../../analitica/Componentes';
import { dia, hora } from '../../analitica/formato';
import { useDatos, useEventos } from '../../analitica/useDatos';
import { ListaArtistas, ListaEventos } from '../../analitica/Listas';

/** Agrupa los pases por día: [[«sábado, 18 de julio», [pase, …]], …] */
function porDia(pases) {
  const grupos = new Map();
  [...pases].sort((a, b) => new Date(a.inicio) - new Date(b.inicio)).forEach((p) => {
    const clave = dia(p.inicio);
    grupos.set(clave, [...(grupos.get(clave) || []), p]);
  });
  return [...grupos.entries()];
}

export function MiEscaleta({ pases }) {
  if (!pases?.length) {
    return <p className="an-aviso">Añade artistas a «Artistas Favoritos» y aquí verás cuándo y dónde tocan.</p>;
  }
  const nombre = Object.fromEntries(pases.map((p) => [p.pase_id, p.artista]));
  const solapados = pases.filter((p) => p.solapa_con?.length).length;
  return (
    <>
      {solapados > 0 && (
        <p className="an-subtitulo">
          <span className="an-chip">{solapados} pases coinciden en horario</span> Tendrás que elegir entre ellos.
        </p>
      )}
      {porDia(pases).map(([fecha, delDia]) => (
        <div key={fecha}>
          <h4 className="an-escaleta-dia">{fecha}</h4>
          <div className="an-tabla-contenedor">
            <table className="an-tabla">
              <thead>
                <tr><th>Hora</th><th>Artista</th><th>Escenario</th><th>Coincide con</th></tr>
              </thead>
              <tbody>
                {delDia.map((p) => (
                  <tr key={p.pase_id} className={p.solapa_con?.length ? 'an-solapa' : undefined}>
                    <td>{hora(p.inicio)}–{hora(p.fin)}</td>
                    <td>{p.artista}</td>
                    <td>{p.escenario}</td>
                    <td>
                      {p.solapa_con?.length
                        ? <span className="an-chip">{p.solapa_con.map((id) => nombre[id] || 'otro favorito').join(', ')}</span>
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </>
  );
}

export default function Resumen({ perfil }) {
  const [eventoId, setEventoId] = useState(null);
  const eventos = useEventos();
  const recomendaciones = useDatos(obtenerMisRecomendaciones, eventoId);

  return (
    <div className="dashboard-section active an-pantalla">
      <header className="section-header">
        <h2>Hola{perfil?.nombre ? `, ${perfil.nombre}` : ''}</h2>
        <p>Lo que te recomendamos y tu escaleta del festival.</p>
      </header>

      <div className="an-filtros">
        <SelectorEvento eventos={eventos} valor={eventoId} onCambiar={setEventoId} opcional="Todos los eventos" />
      </div>

      <Carga peticion={recomendaciones} vacio="Todavía no hay recomendaciones para ti.">
        {(r) => (
          <>
            <div>
              <h3>Mi escaleta</h3>
              <MiEscaleta pases={r.mi_escaleta} />
            </div>
            <div>
              <h3>Eventos recomendados</h3>
              {r.eventos?.length
                ? <ListaEventos eventos={r.eventos} personalizadas />
                : <p className="an-aviso">Cuando tengas artistas favoritos te recomendaremos eventos.</p>}
            </div>
            <div>
              <h3>Artistas que te pueden gustar</h3>
              {r.artistas?.length
                ? <ListaArtistas artistas={r.artistas} />
                : <p className="an-aviso">Aún no tenemos sugerencias de artistas para ti.</p>}
            </div>
          </>
        )}
      </Carga>
    </div>
  );
}
