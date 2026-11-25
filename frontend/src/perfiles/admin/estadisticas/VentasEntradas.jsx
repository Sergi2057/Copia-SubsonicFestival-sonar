// src/perfiles/admin/estadisticas/VentasEntradas.jsx — Dueña: Paula
// Serie de ventas de entradas agrupada por día, semana o tipo de pase.
// API: GET /estadisticas/ventas (ms-analitica)
import { useState } from 'react';
import { obtenerVentas } from '../../../api/analitica';
import { Barra, Carga } from '../../../analitica/Componentes';
import { euros, legible, numero } from '../../../analitica/formato';
import { useDatos } from '../../../analitica/useDatos';

const AGRUPACIONES = { DIA: 'Día', SEMANA: 'Semana', TIPO_PASE: 'Tipo de pase' };

const suma = (filas, campo) => filas.reduce((total, f) => total + (Number(f[campo]) || 0), 0);

export default function VentasEntradas({ eventoId, eventos = [] }) {
  const titulo = Object.fromEntries(eventos.map((e) => [e.id, e.titulo]));
  const [agruparPor, setAgruparPor] = useState('DIA');
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const fechasMal = desde && hasta && desde > hasta;
  const ventas = useDatos(fechasMal ? null : obtenerVentas,
    { evento_id: eventoId, desde, hasta, agrupar_por: agruparPor });

  return (
    <div className="an-apartado">
      <div className="an-filtros">
        <label className="an-campo">
          <span>Agrupar por</span>
          <select value={agruparPor} onChange={(e) => setAgruparPor(e.target.value)}>
            {Object.entries(AGRUPACIONES).map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>
        <label className="an-campo">
          <span>Desde</span>
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label className="an-campo">
          <span>Hasta</span>
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </label>
      </div>

      {fechasMal ? <p className="an-error" role="alert">La fecha «desde» no puede ser posterior a «hasta».</p> : (
        <Carga peticion={ventas} vacio="No hay ventas en ese periodo.">
          {(filas) => {
            const maximo = Math.max(...filas.map((f) => Number(f.ingresos) || 0), 1);
            return (
              <div className="an-tabla-contenedor">
                <table className="an-tabla">
                  <thead>
                    <tr>
                      <th>{AGRUPACIONES[agruparPor]}</th>
                      {!eventoId && <th>Evento</th>}
                      <th className="an-num">Entradas</th>
                      <th className="an-num">Cancelaciones</th>
                      <th className="an-num">Ingresos</th>
                      <th aria-hidden="true"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filas.map((f, i) => (
                      <tr key={`${f.evento_id}-${f.periodo}-${f.tipo_pase}-${i}`}>
                        <td>{agruparPor === 'TIPO_PASE' ? legible(f.tipo_pase || f.periodo) : f.periodo}</td>
                        {!eventoId && <td>{titulo[f.evento_id] || f.evento_id}</td>}
                        <td className="an-num">{numero(f.entradas)}</td>
                        <td className="an-num">{numero(f.cancelaciones)}</td>
                        <td className="an-num">{euros(f.ingresos)}</td>
                        <td className="an-ancho"><Barra fraccion={(Number(f.ingresos) || 0) / maximo} /></td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td>Total</td>
                      {!eventoId && <td></td>}
                      <td className="an-num">{numero(suma(filas, 'entradas'))}</td>
                      <td className="an-num">{numero(suma(filas, 'cancelaciones'))}</td>
                      <td className="an-num">{euros(suma(filas, 'ingresos'))}</td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            );
          }}
        </Carga>
      )}
    </div>
  );
}
