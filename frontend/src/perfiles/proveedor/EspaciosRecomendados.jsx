// src/perfiles/proveedor/EspaciosRecomendados.jsx — Dueña: Paula
// Espacios de su tipo de servicio con mejor afluencia y precio, con el motivo de la recomendación.
// API: GET /recomendaciones/espacios (ms-analitica); eventos de GET /eventos (ms-espacios)
import { useState } from 'react';
import { obtenerEspaciosRecomendados } from '../../api/analitica';
import { Barra, Carga, SelectorEvento } from '../../analitica/Componentes';
import { euros, legible, numero, porcentaje } from '../../analitica/formato';
import { useDatos, useEventos } from '../../analitica/useDatos';

export default function EspaciosRecomendados() {
  const [eventoId, setEventoId] = useState(null);
  const eventos = useEventos();
  const espacios = useDatos(obtenerEspaciosRecomendados, eventoId);
  const tituloEvento = Object.fromEntries((eventos.datos || []).map((e) => [e.id, e.titulo]));

  return (
    <div className="dashboard-section active an-pantalla">
      <header className="section-header">
        <h2>Espacios recomendados</h2>
        <p>Los espacios de tu tipo de servicio con más público y mejor precio. Puedes alquilarlos en «Alquilar un Espacio».</p>
      </header>

      <div className="an-filtros">
        <SelectorEvento eventos={eventos} valor={eventoId} onCambiar={setEventoId} opcional="Todos los eventos" />
      </div>

      <Carga peticion={espacios} vacio="No hay espacios libres de tu tipo de servicio ahora mismo.">
        {(lista) => (
          <ol className="an-lista">
            {lista.map((e) => (
              <li key={e.espacio_id} className="an-item">
                <strong>{legible(e.tipo)} · {e.espacio_id}</strong>
                <span className="an-dato">{tituloEvento[e.evento_id] || e.evento_id}</span>
                {e.motivo && <span className="an-motivo">{e.motivo}</span>}
                <span className="an-dato">Alquiler: {euros(e.precio_alquiler)}</span>
                <span className="an-dato">Público estimado: {numero(e.afluencia_estimada)} personas</span>
                <span className="an-dato">Interés {porcentaje(e.puntuacion)}</span>
                <Barra fraccion={e.puntuacion} />
              </li>
            ))}
          </ol>
        )}
      </Carga>
    </div>
  );
}
