// src/perfiles/admin/estadisticas/ArtistasPopulares.jsx — Dueña: Paula
// Ranking de artistas por favoritos y visitas a su ficha, con la tendencia de la semana.
// API: GET /estadisticas/artistas-populares (ms-analitica)
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { obtenerArtistasPopulares } from '../../../api/analitica';
import { Carga } from '../../../analitica/Componentes';
import { numero, variacion } from '../../../analitica/formato';
import { useDatos } from '../../../analitica/useDatos';

export default function ArtistasPopulares({ eventoId }) {
  const [limite, setLimite] = useState(10);
  const ranking = useDatos(obtenerArtistasPopulares, { evento_id: eventoId, limite });

  return (
    <div className="an-apartado">
      <div className="an-filtros">
        <label className="an-campo">
          <span>Mostrar</span>
          <select value={limite} onChange={(e) => setLimite(Number(e.target.value))}>
            {[10, 20, 50].map((n) => <option key={n} value={n}>Top {n}</option>)}
          </select>
        </label>
      </div>

      <Carga peticion={ranking} vacio="Todavía no hay datos de artistas.">
        {(artistas) => (
          <div className="an-tabla-contenedor">
            <table className="an-tabla">
              <thead>
                <tr>
                  <th className="an-num">#</th>
                  <th>Artista</th>
                  <th className="an-num">Favoritos</th>
                  <th className="an-num">Visitas</th>
                  <th className="an-num">Últimos 7 días</th>
                </tr>
              </thead>
              <tbody>
                {artistas.map((a, i) => (
                  <tr key={a.artista_id}>
                    <td className="an-num">{i + 1}</td>
                    <td><Link to={`/artistas/${a.artista_id}`}>{a.artista}</Link></td>
                    <td className="an-num">{numero(a.favoritos)}</td>
                    <td className="an-num">{numero(a.visitas)}</td>
                    <td className={`an-num ${a.tendencia_7d > 0 ? 'an-sube' : a.tendencia_7d < 0 ? 'an-baja' : ''}`}>
                      {variacion(a.tendencia_7d)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Carga>
    </div>
  );
}
