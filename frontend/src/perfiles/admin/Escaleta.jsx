// src/perfiles/admin/Escaleta.jsx — Dueño: Sergio
// Escaleta y artistas: programa de cada evento (slots, pases, publicación) y catálogo de artistas.
// Cada parte está en perfiles/admin/escaleta/.
import { useState } from 'react';
import { useEventos } from '../../analitica/useDatos';
import Artistas from './escaleta/Artistas';
import Programa from './escaleta/Programa';
import '../escaletaTienda.css';

const PESTANAS = [['programa', 'Escaleta por evento'], ['artistas', 'Artistas']];

export default function Escaleta() {
  const [pestana, setPestana] = useState('programa');
  const eventos = useEventos();
  const [aviso, setAviso] = useState({ error: '', mensaje: '' });
  const avisar = (error, mensaje) => setAviso({ error, mensaje });

  return (
    <div className="et-panel" aria-labelledby="et-escaleta-titulo">
      <header className="et-panel-heading">
        <h2 id="et-escaleta-titulo">Escaleta y artistas</h2>
        <p>Programa de cada escenario, cambios en directo y publicación del cartel.</p>
      </header>
      <div className="et-tabs" role="tablist">
        {PESTANAS.map(([id, titulo]) => (
          <button key={id} type="button" role="tab" aria-selected={pestana === id} className={pestana === id ? 'activo' : ''}
            onClick={() => { setPestana(id); avisar('', ''); }}>
            {titulo}
          </button>
        ))}
      </div>
      {aviso.error && <p className="et-error" role="alert">{aviso.error}</p>}
      {aviso.mensaje && <p className="et-ok" role="status">{aviso.mensaje}</p>}
      {pestana === 'programa' ? <Programa eventos={eventos} avisar={avisar} /> : <Artistas avisar={avisar} />}
    </div>
  );
}
