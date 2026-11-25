// src/perfiles/cliente/Notificaciones.jsx — Dueño: Luis
// Qué hacer: Preferencias push/email y registro de este navegador para notificaciones push (Firebase Cloud Messaging). Al cerrar sesión, dar de baja el dispositivo.
// API: GET/PUT /usuarios/me/preferencias-notificacion, POST /usuarios/me/dispositivos, DELETE /usuarios/me/dispositivos/{fcm_token}
// Referencia del monolito: Nueva (no existe en el monolito)
import { useState } from 'react';
import { obtenerPreferencias, guardarPreferencias } from '../../api/usuarios';
import { useDatos } from '../../analitica/useDatos';
import { useSesion } from '../../sesion/SesionContext';
import { MODO_DESARROLLO } from '../../sesion/usuariosPrueba';
import { AvisoUsuarios, CargaUsuarios } from '../comun/UsuariosUI';
import { activarPush, desactivarPush, dispositivoActual } from './dispositivoPush';

export default function Notificaciones({ perfil }) {
  const sesion = useSesion();
  const actual = perfil || sesion.perfil;
  const peticion = useDatos(obtenerPreferencias);
  return <div className="us-panel"><h2>Notificaciones</h2>
    <CargaUsuarios peticion={peticion}>{(preferencias) => <Preferencias key={actual?.id} usuarioId={actual?.id}
      preferencias={preferencias} />}</CargaUsuarios>
  </div>;
}

function Preferencias({ usuarioId, preferencias }) {
  const [canales, setCanales] = useState(preferencias);
  const [dispositivo, setDispositivo] = useState(() => dispositivoActual(usuarioId));
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState(null);
  const [mensaje, setMensaje] = useState('');
  const ejecutar = async (tarea, texto) => {
    if (ocupado) return;
    setOcupado(true); setError(null); setMensaje('');
    try { await tarea(); setMensaje(texto); }
    catch (e) { setError(e); }
    finally { setOcupado(false); }
  };
  const registrar = (prueba) => ejecutar(async () => setDispositivo(await activarPush(usuarioId, prueba)), 'Navegador registrado.');
  return <>
    <form onSubmit={(e) => { e.preventDefault(); ejecutar(async () => {
      await guardarPreferencias(canales);
      if (!canales.push && dispositivo) { await desactivarPush(usuarioId); setDispositivo(null); }
    }, 'Preferencias guardadas.'); }}>
      <fieldset disabled={ocupado}>
        <label className="us-check"><input type="checkbox" checked={canales.push}
          onChange={(e) => setCanales({ ...canales, push: e.target.checked })} />Notificaciones push</label>
        <label className="us-check"><input type="checkbox" checked={canales.email}
          onChange={(e) => setCanales({ ...canales, email: e.target.checked })} />Notificaciones por email</label>
        <button className="btn-primary" disabled={ocupado}>Guardar preferencias</button>
      </fieldset>
    </form>
    <div className="us-peligros"><h3>Este navegador</h3>
      <p>{dispositivo ? `Registrado${dispositivo.prueba ? ' para pruebas' : ' con Firebase Cloud Messaging'}.` : 'No está registrado para notificaciones push.'}</p>
      <p className="us-ayuda">La preferencia push necesita un dispositivo registrado y permiso del navegador.</p>
      <div className="us-acciones">
        {!dispositivo ? <>
          <button className="btn-secondary" disabled={ocupado || !usuarioId} onClick={() => registrar(false)}>Activar en este navegador</button>
          {MODO_DESARROLLO && <button className="btn-secondary" disabled={ocupado || !usuarioId} onClick={() => registrar(true)}>Registrar navegador de prueba</button>}
        </> : <button className="btn-secondary" disabled={ocupado} onClick={() => ejecutar(async () => {
          await desactivarPush(usuarioId); setDispositivo(null);
        }, 'Navegador dado de baja.')}>Dar de baja este navegador</button>}
      </div>
      {MODO_DESARROLLO && <p className="us-ayuda">El registro de prueba comprueba los avisos del entorno local sin solicitar permisos ni contactar con Firebase.</p>}
    </div>
    <AvisoUsuarios error={error} mensaje={mensaje} />
  </>;
}
