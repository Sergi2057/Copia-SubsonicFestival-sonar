// src/perfiles/admin/estadisticas/Afluencia.jsx — Dueña: Paula
// Previsión de asistentes por escenario y actuación, con aviso cuando se acerca al aforo.
// API: GET /estadisticas/afluencia (ms-analitica)
import { useState } from 'react';
import { obtenerAfluencia } from '../../../api/analitica';
import { Barra, Carga } from '../../../analitica/Componentes';
import { hora, numero, porcentaje } from '../../../analitica/formato';
import { useDatos } from '../../../analitica/useDatos';

const CASI_LLENO = 0.9;

export default function Afluencia({ eventoId }) {
  const [fecha, setFecha] = useState('');
  const afluencia = useDatos(obtenerAfluencia, eventoId, fecha);

  return (
    <div className="an-apartado">
      <div className="an-filtros">
        <label className="an-campo">
          <span>Día (opcional)</span>
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
        </label>
      </div>

      <Carga peticion={afluencia} vacio="No hay actuaciones programadas para ese evento o día.">
        {(escenarios) => (
          <div className="an-escenarios">
            {escenarios.map((e) => (
              <article key={e.espacio_id} className="an-tarjeta">
                <h3>{e.escenario || e.espacio_id}</h3>
                {e.franjas?.length ? (
                  <div className="an-tabla-contenedor">
                    <table className="an-tabla">
                      <thead>
                        <tr>
                          <th>Hora</th>
                          <th>Artista</th>
                          <th className="an-num">Asistentes</th>
                          <th className="an-num">Aforo</th>
                        </tr>
                      </thead>
                      <tbody>
                        {e.franjas.map((f) => (
                          <tr key={`${f.inicio}-${f.artista}`}>
                            <td>{hora(f.inicio)}–{hora(f.fin)}</td>
                            <td>
                              {f.artista}
                              {f.porcentaje_aforo >= CASI_LLENO && <> <span className="an-chip">Casi lleno</span></>}
                            </td>
                            <td className="an-num">{numero(f.asistentes_estimados)}</td>
                            <td className="an-num">
                              {porcentaje(f.porcentaje_aforo)}
                              <Barra fraccion={f.porcentaje_aforo} aviso={CASI_LLENO} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <p className="an-subtitulo">Sin actuaciones.</p>}
              </article>
            ))}
          </div>
        )}
      </Carga>
    </div>
  );
}
