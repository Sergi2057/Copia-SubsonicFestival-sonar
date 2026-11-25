// src/pages/Inicio/Recomendaciones.jsx — Dueña: Paula
// Bloque de la portada: si hay sesión de cliente, eventos y artistas recomendados para él;
// si no (o aún no tiene favoritos), lo más popular del festival.
// API: GET /recomendaciones/me, GET /recomendaciones/populares (ms-analitica)
import { obtenerMisRecomendaciones, obtenerRecomendacionesPopulares } from '../../api/analitica';
import { Carga } from '../../analitica/Componentes';
import { ListaArtistas, ListaEventos } from '../../analitica/Listas';
import { useDatos } from '../../analitica/useDatos';
import { useSesion } from '../../sesion/SesionContext';

/** Personalizadas; si no hay ninguna (cliente sin favoritos) o el token aún no lleva el rol, las populares. */
async function cargarParaCliente() {
  try {
    const mias = await obtenerMisRecomendaciones();
    if (mias.eventos?.length || mias.artistas?.length) return { ...mias, personalizadas: true };
  } catch (error) {
    if (error.status !== 403) throw error;
  }
  return { ...(await obtenerRecomendacionesPopulares()), personalizadas: false };
}

const cargarPopulares = () => obtenerRecomendacionesPopulares().then((r) => ({ ...r, personalizadas: false }));

export default function Recomendaciones() {
  const { rol, cargando: cargandoSesion } = useSesion();
  const funcion = cargandoSesion ? null : rol === 'cliente' ? cargarParaCliente : cargarPopulares;
  const peticion = useDatos(funcion);

  return (
    <section className="an-pantalla an-inicio" aria-labelledby="titulo-recomendaciones">
      <header>
        <div className="section-label">{peticion.datos?.personalizadas ? 'Para ti' : 'Tendencias'}</div>
        <h2 id="titulo-recomendaciones">
          {peticion.datos?.personalizadas ? 'Recomendado para ti' : 'Lo más popular'}
        </h2>
        <p className="an-subtitulo">
          {peticion.datos?.personalizadas
            ? 'Según tus artistas favoritos y los de gente con gustos parecidos.'
            : 'Los eventos y artistas que más interesan estos días.'}
        </p>
      </header>
      <Carga peticion={{ ...peticion, cargando: peticion.cargando || cargandoSesion }}
        vacio="Todavía no hay recomendaciones.">
        {(datos) => (
          <>
            {datos.eventos?.length > 0 && (
              <div>
                <h3>Eventos</h3>
                <ListaEventos eventos={datos.eventos} personalizadas={datos.personalizadas} />
              </div>
            )}
            {datos.artistas?.length > 0 && (
              <div>
                <h3>Artistas</h3>
                <ListaArtistas artistas={datos.artistas} />
              </div>
            )}
            {!datos.eventos?.length && !datos.artistas?.length && (
              <p className="an-aviso">Todavía no hay recomendaciones.</p>
            )}
          </>
        )}
      </Carga>
    </section>
  );
}
