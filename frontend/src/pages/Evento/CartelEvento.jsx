// src/pages/Evento/CartelEvento.jsx — Dueño: Sergio
// Pestañas Artistas y Horarios de la ficha del evento: escaleta publicada por día y escenario,
// actualizada en directo por SSE, con botón de favorito para los clientes.
// API: GET /escaletas/{evento_id}, SSE /escaletas/{evento_id}/cambios (ms-escaleta); favoritos (ms-usuarios)
// Uso (Pedro, en DetallesEvento): <CartelEvento eventoId={id} />
import { useEffect, useEffectEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { escucharCambios, obtenerEscaleta } from '../../api/escaleta';
import { anadirFavorito, listarFavoritos, quitarFavorito } from '../../api/usuarios';
import { useDatos } from '../../analitica/useDatos';
import { useSesion } from '../../sesion/SesionContext';
import { ESTADOS_PASE, aplicarCambioPase, artistasDeEscaleta, fechaLarga, hora } from './escaletaUtil';
import './CartelEvento.css';

const sinCambios = (eventoId) => ({ eventoId, pases: new Map() });

export default function CartelEvento({ eventoId }) {
  const { rol } = useSesion();
  const esCliente = rol === 'cliente';
  const [pestana, setPestana] = useState('artistas');
  const peticion = useDatos(obtenerEscaleta, eventoId);
  // Pases que han cambiado en directo desde la última carga (pase_id -> pase), del evento actual
  const [cambios, setCambios] = useState(() => sinCambios(eventoId));
  const [favoritos, setFavoritos] = useState(new Set());
  const [aviso, setAviso] = useState('');
  const [errorFavorito, setErrorFavorito] = useState('');

  // Cambios en directo: un pase modificado se aplica tal cual; una publicación nueva se vuelve a pedir
  const alCambiar = useEffectEvent((cambio) => {
    if (cambio.tipo === 'escaleta.publicada') {
      setAviso(`Se ha publicado una nueva versión del cartel (v${cambio.version}).`);
      setCambios(sinCambios(eventoId));
      peticion.recargar();
      return;
    }
    if (!cambio.pase) return;
    const { pase } = cambio;
    setCambios((actual) => {
      const pases = new Map(actual.eventoId === eventoId ? actual.pases : []);
      pases.set(pase.pase_id, pase);
      return { eventoId, pases };
    });
    setAviso(cambio.tipo === 'pase.cancelado'
      ? `Cancelado: ${pase.artista} en ${pase.escenario}.`
      : `Cambio de horario: ${pase.artista} actúa a las ${hora(pase.inicio)} en ${pase.escenario}.`);
  });
  useEffect(() => escucharCambios(eventoId, alCambiar), [eventoId]);

  useEffect(() => {
    if (!esCliente) return undefined;
    let vigente = true;
    listarFavoritos()
      .then((lista) => vigente && setFavoritos(new Set(lista.map((f) => f.artista_id))))
      .catch(() => {});   // sin favoritos no se rompe el cartel
    return () => { vigente = false; };
  }, [esCliente]);

  const alternarFavorito = async (artistaId) => {
    setErrorFavorito('');
    if (!esCliente) {
      setErrorFavorito('Inicia sesión como cliente para guardar artistas favoritos.');
      return;
    }
    const eraFavorito = favoritos.has(artistaId);
    try {
      if (eraFavorito) await quitarFavorito(artistaId);
      else await anadirFavorito(artistaId);
      setFavoritos((actual) => {
        const nuevo = new Set(actual);
        if (eraFavorito) nuevo.delete(artistaId); else nuevo.add(artistaId);
        return nuevo;
      });
    } catch (e) {
      setErrorFavorito(e.message);
    }
  };

  if (peticion.error?.status === 404) {
    return <div className="detalles-tab-content sin-datos-aviso">El cartel de este evento todavía no se ha publicado.</div>;
  }
  if (peticion.error) {
    return <div className="detalles-tab-content"><p className="cartel-error" role="alert">{peticion.error.message}</p></div>;
  }
  if (peticion.cargando) return <div className="detalles-tab-content" role="status">Cargando cartel…</div>;

  const cambiados = cambios.eventoId === eventoId ? cambios.pases : new Map();
  const escaleta = [...cambiados.values()].reduce(aplicarCambioPase, peticion.datos);
  const artistas = artistasDeEscaleta(escaleta);
  const esFavorito = (artistaId) => esCliente && favoritos.has(artistaId);
  return (
    <div className="detalles-tab-content cartel">
      <div className="evento-tabs-header cartel-subtabs" role="tablist" aria-label="Cartel del evento">
        <button type="button" role="tab" aria-selected={pestana === 'artistas'}
          className={`tab-btn ${pestana === 'artistas' ? 'activo' : ''}`} onClick={() => setPestana('artistas')}>
          Artistas
        </button>
        <button type="button" role="tab" aria-selected={pestana === 'horarios'}
          className={`tab-btn ${pestana === 'horarios' ? 'activo' : ''}`} onClick={() => setPestana('horarios')}>
          Horarios
        </button>
      </div>

      <p className="cartel-directo"><span className="cartel-punto" aria-hidden="true" /> En directo · versión {escaleta.version}</p>
      {aviso && <p className="cartel-aviso" role="status">{aviso}</p>}
      {errorFavorito && <p className="cartel-error" role="alert">{errorFavorito}</p>}

      {pestana === 'artistas' && (
        <div className="artistas-container-nuevo">
          {artistas.length === 0 && <div className="sin-datos-aviso">No hay artistas confirmados todavía.</div>}
          {artistas.map(({ artista_id: artistaId, artista }) => {
            const favorito = esFavorito(artistaId);
            return (
              <div className="artista-badge" key={artistaId}>
                <Link to={`/artistas/${encodeURIComponent(artistaId)}`} className="cartel-artista">{artista}</Link>
                <button type="button" className={`btn-favorito ${favorito ? 'favorito-activo' : ''}`}
                  aria-pressed={favorito} onClick={() => alternarFavorito(artistaId)}
                  aria-label={favorito ? `Quitar a ${artista} de favoritos` : `Añadir a ${artista} a favoritos`}>
                  <i className={`fa-${favorito ? 'solid' : 'regular'} fa-heart`} aria-hidden="true" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {pestana === 'horarios' && (
        <div className="horarios-list">
          {escaleta.dias.length === 0 && <div className="sin-datos-aviso">No hay pases publicados.</div>}
          {escaleta.dias.map((dia) => (
            <div key={dia.fecha} className="cartel-dia">
              <h3 className="cartel-dia-titulo">{fechaLarga(dia.fecha)}</h3>
              {dia.escenarios.map((escenario) => (
                <div key={escenario.espacio_id} className="detalles-stage-card">
                  <h4 className="detalles-stage-title">{escenario.nombre}</h4>
                  {escenario.pases.map((pase) => (
                    <div key={pase.pase_id} data-testid={`pase-${pase.pase_id}`}
                      className={`horario-row ${pase.estado === 'CANCELADO' ? 'cartel-cancelado' : ''} ${cambiados.has(pase.pase_id) ? 'cartel-cambiado' : ''}`}>
                      <div className="horario-artista">
                        <Link to={`/artistas/${encodeURIComponent(pase.artista_id)}`}><strong>{pase.artista}</strong></Link>
                        {pase.estado !== 'CONFIRMADO' && pase.estado !== 'PROGRAMADO' && (
                          <span className="cartel-estado">{ESTADOS_PASE[pase.estado] || pase.estado}</span>
                        )}
                      </div>
                      <div className="horario-hora">{hora(pase.inicio)} – {hora(pase.fin)}</div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
