// src/perfiles/admin/Resumen.jsx — Dueña: Paula
// Indicadores principales: entradas vendidas, ingresos (entradas, alquileres, tienda), usuarios,
// ocupación de espacios y asistentes hoy. De todo el festival o de un evento.
// API: GET /estadisticas/resumen (ms-analitica); eventos de GET /eventos (ms-espacios)
import { useState } from 'react';
import { obtenerResumen } from '../../api/analitica';
import { Barra, Carga, SelectorEvento } from '../../analitica/Componentes';
import { euros, hora, numero, porcentaje } from '../../analitica/formato';
import { useDatos, useEventos } from '../../analitica/useDatos';

function Tarjeta({ titulo, valor, detalle, children }) {
  return (
    <div className="an-tarjeta">
      <span className="an-tarjeta-titulo">{titulo}</span>
      <span className="an-tarjeta-numero">{valor}</span>
      {children}
      {detalle && <span className="an-tarjeta-detalle">{detalle}</span>}
    </div>
  );
}

export default function Resumen() {
  const [eventoId, setEventoId] = useState(null);
  const eventos = useEventos();
  const resumen = useDatos(obtenerResumen, eventoId);

  return (
    <div className="dashboard-section active an-pantalla">
      <header className="section-header">
        <h2>Visión General</h2>
        <p>Las cifras se recalculan cada minuto.</p>
      </header>

      <div className="an-filtros">
        <SelectorEvento eventos={eventos} valor={eventoId} onCambiar={setEventoId} opcional="Todo el festival" />
        <button type="button" className="btn-secondary" onClick={resumen.recargar} disabled={resumen.cargando}>
          <i className="fa-solid fa-rotate"></i> Actualizar
        </button>
      </div>

      <Carga peticion={resumen} vacio="Todavía no hay datos.">
        {(r) => {
          const ingresos = (r.ingresos_entradas || 0) + (r.ingresos_alquileres || 0) + (r.ingresos_tienda || 0);
          return (
            <>
              <div className="an-indicadores">
                <Tarjeta titulo="Entradas vendidas" valor={numero(r.entradas_vendidas)} detalle="Sin contar las canceladas" />
                <Tarjeta titulo="Ingresos totales" valor={euros(ingresos)}
                  detalle={`Entradas ${euros(r.ingresos_entradas)} · Alquileres ${euros(r.ingresos_alquileres)} · Tienda ${euros(r.ingresos_tienda)}`} />
                <Tarjeta titulo="Usuarios registrados" valor={numero(r.usuarios_registrados)} />
                <Tarjeta titulo="Ocupación de espacios" valor={porcentaje(r.ocupacion_espacios)}
                  detalle="Espacios alquilables ya alquilados">
                  <Barra fraccion={r.ocupacion_espacios} />
                </Tarjeta>
                <Tarjeta titulo="Asistentes hoy" valor={numero(r.asistentes_hoy)} detalle="Entradas validadas en la puerta" />
              </div>
              {r.actualizado_en && <p className="an-subtitulo">Datos de las {hora(r.actualizado_en)}.</p>}
            </>
          );
        }}
      </Carga>
    </div>
  );
}
