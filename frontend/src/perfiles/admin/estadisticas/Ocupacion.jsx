// src/perfiles/admin/estadisticas/Ocupacion.jsx — Dueña: Paula
// Espacios alquilados frente a los disponibles, por tipo de espacio, de un evento.
// API: GET /estadisticas/ocupacion (ms-analitica)
import { obtenerOcupacion } from '../../../api/analitica';
import { Barra, Carga } from '../../../analitica/Componentes';
import { euros, legible, numero, porcentaje } from '../../../analitica/formato';
import { useDatos } from '../../../analitica/useDatos';

const suma = (filas, campo) => filas.reduce((total, f) => total + (Number(f[campo]) || 0), 0);

export default function Ocupacion({ eventoId }) {
  const ocupacion = useDatos(obtenerOcupacion, eventoId);

  return (
    <Carga peticion={ocupacion} vacio="Este evento aún no tiene espacios alquilables.">
      {(filas) => {
        const total = suma(filas, 'total');
        const alquilados = suma(filas, 'alquilados');
        return (
          <div className="an-tabla-contenedor">
            <table className="an-tabla">
              <thead>
                <tr>
                  <th>Tipo de espacio</th>
                  <th className="an-num">Alquilados</th>
                  <th className="an-num">Ocupación</th>
                  <th aria-hidden="true"></th>
                  <th className="an-num">Ingresos</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((f) => {
                  const fraccion = f.total ? f.alquilados / f.total : 0;
                  return (
                    <tr key={f.tipo_espacio}>
                      <td>{legible(f.tipo_espacio)}</td>
                      <td className="an-num">{numero(f.alquilados)} / {numero(f.total)}</td>
                      <td className="an-num">{porcentaje(fraccion)}</td>
                      <td className="an-ancho"><Barra fraccion={fraccion} /></td>
                      <td className="an-num">{euros(f.ingresos_alquiler)}</td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr>
                  <td>Total</td>
                  <td className="an-num">{numero(alquilados)} / {numero(total)}</td>
                  <td className="an-num">{porcentaje(total ? alquilados / total : 0)}</td>
                  <td></td>
                  <td className="an-num">{euros(suma(filas, 'ingresos_alquiler'))}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        );
      }}
    </Carga>
  );
}
