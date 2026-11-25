// src/perfiles/admin/estadisticas/VentasTienda.jsx — Dueña: Paula
// Ventas de merchandising por producto y talla, y tallas a punto de agotarse.
// API: GET /estadisticas/tienda (ms-analitica)
import { useState } from 'react';
import { obtenerEstadisticasTienda } from '../../../api/analitica';
import { Carga } from '../../../analitica/Componentes';
import { euros, numero } from '../../../analitica/formato';
import { useDatos } from '../../../analitica/useDatos';

const suma = (filas, campo) => filas.reduce((total, f) => total + (Number(f[campo]) || 0), 0);

export default function VentasTienda() {
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const fechasMal = desde && hasta && desde > hasta;
  const tienda = useDatos(fechasMal ? null : obtenerEstadisticasTienda, { desde, hasta });

  return (
    <div className="an-apartado">
      <div className="an-filtros">
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
        <Carga peticion={tienda} vacio="No hay datos de la tienda.">
          {({ ventas = [], stock_bajo: stockBajo = [] }) => (
            <>
              <div>
                <h3>Tallas a punto de agotarse</h3>
                {stockBajo.length === 0 ? <p className="an-aviso">Ninguna talla tiene poco stock.</p> : (
                  <ul className="an-lista">
                    {stockBajo.map((s) => (
                      <li key={`${s.producto_id}-${s.talla}`} className="an-item">
                        <strong>{s.producto_id}</strong>
                        <span className="an-dato">Talla {s.talla}</span>
                        <span className="an-chip">Quedan {numero(s.stock)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <h3>Ventas por producto y talla</h3>
                {ventas.length === 0 ? <p className="an-aviso">No hay ventas en ese periodo.</p> : (
                  <div className="an-tabla-contenedor">
                    <table className="an-tabla">
                      <thead>
                        <tr>
                          <th>Producto</th>
                          <th>Talla</th>
                          <th className="an-num">Unidades</th>
                          <th className="an-num">Ingresos</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ventas.map((v) => (
                          <tr key={`${v.producto_id}-${v.talla}`}>
                            <td>{v.producto_id}</td>
                            <td>{v.talla}</td>
                            <td className="an-num">{numero(v.unidades)}</td>
                            <td className="an-num">{euros(v.ingresos)}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr>
                          <td colSpan={2}>Total</td>
                          <td className="an-num">{numero(suma(ventas, 'unidades'))}</td>
                          <td className="an-num">{euros(suma(ventas, 'ingresos'))}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </Carga>
      )}
    </div>
  );
}
