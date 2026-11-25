// src/perfiles/admin/escaleta/Programa.jsx — Dueño: Sergio
// Escaleta de un evento (borrador): slots por escenario, asignar artistas (pases), cambiar horario o estado de
// los pases (con su version), publicar la escaleta e historial de publicaciones.
// API: /escaletas/{evento_id}/slots, /slots/{id}, /slots/{id}/pases, /pases/{id}, /escaletas/{evento_id}/publicaciones
//      (ms-escaleta); GET /espacios?tipo=ESCENARIO (ms-espacios)
import { useState } from 'react';
import {
  crearPase, crearSlot, eliminarPase, eliminarSlot, listarArtistas, listarPublicaciones, listarSlots, modificarPase,
  publicarEscaleta,
} from '../../../api/escaleta';
import { listarEspacios } from '../../../api/espacios';
import { useDatos } from '../../../analitica/useDatos';
import { useDatosRecargables } from '../../useDatosRecargables';
import {
  ESTADOS_PASE, FORMATOS_PASE, TIPOS_SLOT, TRANSICIONES_PASE, aIso, aLocal, fechaHora, hora,
} from '../../../pages/Evento/escaletaUtil';

const cargarEscenarios = (eventoId) => listarEspacios({ evento_id: eventoId, tipo: 'ESCENARIO', limite: 100 })
  .then((r) => r?.datos || r || []);
const cargarArtistas = () => listarArtistas({ limite: 100 }).then(({ datos }) => datos);
const cargarSlots = (eventoId) => listarSlots(eventoId);
const cargarPublicaciones = (eventoId) => listarPublicaciones(eventoId);

function mensaje(error) {
  switch (error.codigo) {
    case 'VERSION_OBSOLETA': return 'Otro administrador ha cambiado este pase. Se han recargado los datos: revisa y repite el cambio.';
    case 'SIN_CAMBIOS': return 'No hay cambios desde la última publicación.';
    case 'EVENTO_NO_ADMITE_ESCALETA': return `${error.message}. Solo se pueden programar eventos publicados.`;
    default: return error.message;
  }
}

function NuevoSlot({ escenarios, ocupado, alCrear }) {
  const [datos, setDatos] = useState({ espacio_id: '', inicio: '', fin: '', tipo: 'ACTUACION' });
  const campo = (clave) => ({ value: datos[clave], onChange: (e) => setDatos({ ...datos, [clave]: e.target.value }) });
  const enviar = async (e) => {
    e.preventDefault();
    if (await alCrear({ ...datos, inicio: aIso(datos.inicio), fin: aIso(datos.fin) })) {
      setDatos({ ...datos, inicio: datos.fin, fin: '' });   // la siguiente franja suele empezar donde acaba esta
    }
  };
  return (
    <form className="et-form" onSubmit={enviar} aria-label="Nuevo slot">
      <h3>Nuevo slot</h3>
      <div className="et-form-grid">
        <label>Escenario
          <select required {...campo('espacio_id')}>
            <option value="">Elige un escenario</option>
            {escenarios.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
          </select>
        </label>
        <label>Inicio<input required type="datetime-local" {...campo('inicio')} /></label>
        <label>Fin<input required type="datetime-local" min={datos.inicio || undefined} {...campo('fin')} /></label>
        <label>Tipo
          <select {...campo('tipo')}>
            {Object.entries(TIPOS_SLOT).map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>
      </div>
      <div className="et-acciones">
        <button type="submit" className="btn-primary" disabled={ocupado}>Crear slot</button>
      </div>
    </form>
  );
}

function Slot({ slot, escenarios, artistas, ocupado, ejecutar }) {
  const [artistaId, setArtistaId] = useState('');
  const [formato, setFormato] = useState('DJ_SET');
  const [reprogramando, setReprogramando] = useState(false);
  const [cambio, setCambio] = useState({ inicio: aLocal(slot.inicio), fin: aLocal(slot.fin), espacio_id: slot.espacio_id, motivo: '' });
  const { pase } = slot;
  const titulo = pase ? pase.artista_nombre || pase.artista_id : TIPOS_SLOT[slot.tipo];

  const reprogramar = async (e) => {
    e.preventDefault();
    const cambios = { version: pase.version, motivo: cambio.motivo.trim() || undefined };
    if (aIso(cambio.inicio) !== new Date(slot.inicio).toISOString()) cambios.inicio = aIso(cambio.inicio);
    if (aIso(cambio.fin) !== new Date(slot.fin).toISOString()) cambios.fin = aIso(cambio.fin);
    if (cambio.espacio_id !== slot.espacio_id) cambios.espacio_id = cambio.espacio_id;
    if (await ejecutar(() => modificarPase(pase.id, cambios), `Pase de ${titulo} reprogramado.`)) setReprogramando(false);
  };

  return (
    <div className={`et-slot ${pase?.estado === 'CANCELADO' ? 'et-slot-cancelado' : ''}`} data-testid={`slot-${slot.id}`}>
      <div>
        <div className="et-slot-hora">{hora(slot.inicio)} – {hora(slot.fin)}</div>
        <div className="et-apagado">{fechaHora(slot.inicio).split(',')[0]} · {TIPOS_SLOT[slot.tipo]}</div>
      </div>

      <div className="et-slot-pase">
        {pase ? (
          <>
            <div>
              <strong className="et-slot-artista">{titulo}</strong>{' '}
              <span className="et-apagado">{FORMATOS_PASE[pase.formato]} · v{pase.version}</span>{' '}
              <span className="et-insignia">{ESTADOS_PASE[pase.estado]}</span>
            </div>
            <div className="et-acciones et-acciones-izq" style={{ marginTop: 0 }}>
              {TRANSICIONES_PASE[pase.estado].map((estado) => (
                <button key={estado} type="button" disabled={ocupado}
                  className={estado === 'CANCELADO' ? 'et-peligro' : 'et-boton'}
                  onClick={() => ejecutar(() => modificarPase(pase.id, { version: pase.version, estado }),
                    `${titulo}: ${ESTADOS_PASE[estado].toLowerCase()}.`, estado === 'CANCELADO' ? `¿Cancelar el pase de ${titulo}?` : null)}>
                  {estado === 'CANCELADO' ? 'Cancelar pase' : `Marcar ${ESTADOS_PASE[estado].toLowerCase()}`}
                </button>
              ))}
              {!['FINALIZADO', 'CANCELADO'].includes(pase.estado) && (
                <button type="button" className="et-boton" onClick={() => setReprogramando(!reprogramando)}>
                  {reprogramando ? 'Cerrar' : 'Cambiar horario'}
                </button>
              )}
            </div>
            {reprogramando && (
              <form className="et-mini-form" onSubmit={reprogramar} aria-label={`Cambiar horario de ${titulo}`}>
                <label>Inicio<input type="datetime-local" required value={cambio.inicio}
                  onChange={(e) => setCambio({ ...cambio, inicio: e.target.value })} /></label>
                <label>Fin<input type="datetime-local" required value={cambio.fin}
                  onChange={(e) => setCambio({ ...cambio, fin: e.target.value })} /></label>
                <label>Escenario
                  <select value={cambio.espacio_id} onChange={(e) => setCambio({ ...cambio, espacio_id: e.target.value })}>
                    {escenarios.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
                  </select>
                </label>
                <label>Motivo (se avisa al público)<input value={cambio.motivo} placeholder="Retraso técnico"
                  onChange={(e) => setCambio({ ...cambio, motivo: e.target.value })} /></label>
                <button type="submit" className="btn-primary" disabled={ocupado}>Guardar</button>
              </form>
            )}
          </>
        ) : slot.tipo === 'ACTUACION' ? (
          <form className="et-mini-form" aria-label="Asignar artista"
            onSubmit={(e) => {
              e.preventDefault();
              ejecutar(() => crearPase(slot.id, { artista_id: artistaId, formato }), 'Artista asignado al slot.');
            }}>
            <label>Artista
              <select required value={artistaId} onChange={(e) => setArtistaId(e.target.value)}>
                <option value="">Elige un artista</option>
                {artistas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
              </select>
            </label>
            <label>Formato
              <select value={formato} onChange={(e) => setFormato(e.target.value)}>
                {Object.entries(FORMATOS_PASE).map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
              </select>
            </label>
            <button type="submit" className="btn-primary" disabled={ocupado}>Asignar</button>
          </form>
        ) : <span className="et-apagado">{titulo}</span>}
      </div>

      <div className="et-acciones" style={{ marginTop: 0, flexDirection: 'column', alignItems: 'stretch' }}>
        {pase && (
          <button type="button" className="et-boton" disabled={ocupado}
            onClick={() => ejecutar(() => eliminarPase(pase.id), `${titulo} quitado del slot.`, `¿Quitar a ${titulo} de este slot?`)}>
            Quitar artista
          </button>
        )}
        <button type="button" className="et-peligro" disabled={ocupado}
          onClick={() => ejecutar(() => eliminarSlot(slot.id), 'Slot eliminado.', '¿Eliminar este slot (y su pase, si lo tiene)?')}>
          Eliminar slot
        </button>
      </div>
    </div>
  );
}

export default function Programa({ eventos, avisar }) {
  const [eventoId, setEventoId] = useState('');
  const escenarios = useDatos(eventoId ? cargarEscenarios : null, eventoId);
  const artistas = useDatos(cargarArtistas);
  const slots = useDatosRecargables(eventoId ? cargarSlots : null, eventoId);
  const publicaciones = useDatosRecargables(eventoId ? cargarPublicaciones : null, eventoId);
  const [ocupado, setOcupado] = useState(false);

  /** Ejecuta una acción, muestra el resultado y recarga. Devuelve true si ha ido bien. */
  const ejecutar = async (accion, textoOk, confirmacion = null) => {
    if (confirmacion && !window.confirm(confirmacion)) return false;
    setOcupado(true);
    avisar('', '');
    try {
      await accion();
      avisar('', textoOk);
      return true;
    } catch (e) {
      avisar(mensaje(e), '');
      return false;
    } finally {
      setOcupado(false);
      slots.recargar();
      publicaciones.recargar();
    }
  };

  const listaEscenarios = escenarios.datos || [];
  const nombreEscenario = (id) => listaEscenarios.find((e) => e.id === id)?.nombre || id;
  const porEscenario = new Map();
  [...(slots.datos || [])].sort((a, b) => a.inicio.localeCompare(b.inicio)).forEach((slot) => {
    if (!porEscenario.has(slot.espacio_id)) porEscenario.set(slot.espacio_id, []);
    porEscenario.get(slot.espacio_id).push(slot);
  });
  const ultima = publicaciones.datos?.[0];

  return (
    <>
      <div className="et-filtros">
        <label>Evento
          <select value={eventoId} onChange={(e) => { setEventoId(e.target.value); avisar('', ''); }}>
            <option value="">Elige un evento</option>
            {(eventos.datos || []).map((ev) => <option key={ev.id} value={ev.id}>{ev.titulo}</option>)}
          </select>
        </label>
        {eventos.error && <p className="et-error" role="alert">{eventos.error.message}</p>}
      </div>

      {!eventoId ? <p>Elige un evento para ver y editar su escaleta.</p> : (
        <>
          <div className="et-form">
            <div className="et-tarjeta-cabecera">
              <div>
                <h3>Publicación</h3>
                <p className="et-apagado">
                  Los cambios de slots y pases son un borrador hasta que publicas. Los cambios de horario y las
                  cancelaciones de un pase se avisan al momento al público que está viendo el cartel.
                </p>
                <p>{ultima ? `Última versión publicada: v${ultima.version} (${fechaHora(ultima.publicada_en)})` : 'Todavía no se ha publicado.'}</p>
              </div>
              <button type="button" className="btn-primary" disabled={ocupado}
                onClick={() => ejecutar(() => publicarEscaleta(eventoId), 'Escaleta publicada: el público ya ve la versión nueva.')}>
                Publicar escaleta
              </button>
            </div>
            {publicaciones.datos?.length > 1 && (
              <details>
                <summary>Historial ({publicaciones.datos.length} versiones)</summary>
                <ul className="et-lista">
                  {publicaciones.datos.map((p) => (
                    <li key={p.version}><span>v{p.version}</span><span>{fechaHora(p.publicada_en)}</span>
                      <span className="et-apagado">{p.publicada_por}</span></li>
                  ))}
                </ul>
              </details>
            )}
          </div>

          {escenarios.error && <p className="et-error" role="alert">{escenarios.error.message}</p>}
          {escenarios.datos && listaEscenarios.length === 0 && (
            <p className="et-error" role="alert">Este evento no tiene escenarios. Créalos en «Espacios y Alquileres» (tipo ESCENARIO).</p>
          )}
          {listaEscenarios.length > 0 && <NuevoSlot escenarios={listaEscenarios} ocupado={ocupado}
            alCrear={(datos) => ejecutar(() => crearSlot(eventoId, datos), 'Slot creado.')} />}

          {slots.cargando && !slots.datos && <p role="status">Cargando escaleta…</p>}
          {slots.error && <p className="et-error" role="alert">{slots.error.message}</p>}
          {slots.datos?.length === 0 && <p>Todavía no hay slots en este evento.</p>}
          {[...porEscenario.entries()].map(([espacioId, lista]) => (
            <div key={espacioId} className="et-escenario">
              <h3>{nombreEscenario(espacioId)}</h3>
              {lista.map((slot) => (
                <Slot key={`${slot.id}-${slot.pase?.version ?? 0}-${slot.inicio}-${slot.fin}`} slot={slot}
                  escenarios={listaEscenarios} artistas={artistas.datos || []} ocupado={ocupado} ejecutar={ejecutar} />
              ))}
            </div>
          ))}
        </>
      )}
    </>
  );
}
