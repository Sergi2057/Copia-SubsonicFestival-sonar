// src/perfiles/admin/Estadisticas.jsx — Dueña: Paula
// Ventas por evento y día, ocupación de espacios, previsión de afluencia por escenario,
// ventas de la tienda y artistas populares. Cada apartado está en ./estadisticas/.
// API: GET /estadisticas/ventas, /ocupacion, /afluencia, /tienda, /artistas-populares (ms-analitica)
import { useState } from 'react';
import { SelectorEvento } from '../../analitica/Componentes';
import { useEventos } from '../../analitica/useDatos';
import Afluencia from './estadisticas/Afluencia';
import ArtistasPopulares from './estadisticas/ArtistasPopulares';
import Ocupacion from './estadisticas/Ocupacion';
import VentasEntradas from './estadisticas/VentasEntradas';
import VentasTienda from './estadisticas/VentasTienda';

// porEvento: el apartado usa el evento elegido arriba (obligatorio si «requiereEvento»)
const APARTADOS = [
  { id: 'ventas', titulo: 'Venta de entradas', Componente: VentasEntradas, porEvento: true },
  { id: 'ocupacion', titulo: 'Ocupación de espacios', Componente: Ocupacion, porEvento: true, requiereEvento: true },
  { id: 'afluencia', titulo: 'Previsión de afluencia', Componente: Afluencia, porEvento: true, requiereEvento: true },
  { id: 'tienda', titulo: 'Tienda', Componente: VentasTienda },
  { id: 'artistas', titulo: 'Artistas populares', Componente: ArtistasPopulares, porEvento: true },
];

export default function Estadisticas() {
  const [activo, setActivo] = useState(APARTADOS[0].id);
  const [eventoId, setEventoId] = useState(null);
  const eventos = useEventos();
  const apartado = APARTADOS.find((a) => a.id === activo);
  const { Componente } = apartado;

  return (
    <div className="dashboard-section active an-pantalla">
      <header className="section-header">
        <h2>Estadísticas</h2>
        <p>Ventas, ocupación y previsiones del festival.</p>
      </header>

      <div className="an-pestanas" role="group" aria-label="Apartados de estadísticas">
        {APARTADOS.map((a) => (
          <button key={a.id} type="button" aria-pressed={a.id === activo} onClick={() => setActivo(a.id)}>
            {a.titulo}
          </button>
        ))}
      </div>

      {apartado.porEvento && (
        <div className="an-filtros">
          <SelectorEvento eventos={eventos} valor={eventoId} onCambiar={setEventoId}
            opcional={apartado.requiereEvento ? undefined : 'Todos los eventos'} />
        </div>
      )}

      {apartado.requiereEvento && !eventoId
        ? <p className="an-aviso">Elige un evento para ver {apartado.titulo.toLowerCase()}.</p>
        : <Componente eventoId={eventoId} eventos={eventos.datos || []} />}
    </div>
  );
}
