// src/pages/Inicio/Inicio.jsx — Dueña: Paula (solo el orden de los bloques; cada bloque tiene su dueño)
// Los id (eventos, recomendaciones, musica) los usa la barra de navegación para bajar a cada bloque: no cambiarlos.
import BuscadorEventos from './BuscadorEventos';
import Musica from './Musica';
import Recomendaciones from './Recomendaciones';

export default function Inicio() {
  return (
    <main>
      <div id="eventos" style={{ paddingTop: '80px' }}><BuscadorEventos /></div>  {/* Pedro */}
      <div id="recomendaciones" className="bg-gradient"><Recomendaciones /></div>  {/* Paula */}
      <div id="musica" className="bg-gradient"><Musica /></div>                    {/* Sergio */}
    </main>
  );
}
