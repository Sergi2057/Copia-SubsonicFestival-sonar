// src/perfiles/staff/ValidarEntradas.jsx — Dueño: Luis
// Qué hacer: Elegir el evento y validar entradas escaneando o escribiendo el código QR; mostrar titular y tipo de pase o el motivo del rechazo.
// API: POST /entradas/validaciones (ms-usuarios); GET /eventos (ms-espacios, para elegir el evento)
// Referencia del monolito: Nueva (no existe en el monolito)
import { useRef, useState } from 'react';
import { validarEntrada } from '../../api/usuarios';
import { useEventos } from '../../analitica/useDatos';
import { AvisoUsuarios, CargaUsuarios } from '../comun/UsuariosUI';

export default function ValidarEntradas() {
  const eventos = useEventos();
  const [eventoId, setEventoId] = useState('');
  const [codigo, setCodigo] = useState('');
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  const [ocupado, setOcupado] = useState(false);
  const campoQr = useRef(null);
  const validar = async (e) => {
    e.preventDefault();
    if (ocupado || !eventoId || !codigo.trim()) return;
    setOcupado(true); setError(null); setResultado(null);
    try { setResultado(await validarEntrada(codigo.trim(), eventoId)); setCodigo(''); }
    catch (e) { setError(e); }
    finally { setOcupado(false); campoQr.current?.focus(); }
  };
  return <div className="us-panel"><h2>Control de acceso</h2>
    <CargaUsuarios peticion={eventos}>{(lista) => lista.length ? <form className="us-formulario" onSubmit={validar}>
      <fieldset disabled={ocupado}>
        <label className="us-campo">Evento<select required value={eventoId} onChange={(e) => {
          setEventoId(e.target.value); setCodigo(''); setResultado(null); setError(null);
        }}><option value="">Elige el evento del acceso</option>{lista.map((e) => <option key={e.id} value={e.id}>{e.titulo}</option>)}</select></label>
        <label className="us-campo">Código QR<input ref={campoQr} value={codigo} required autoComplete="off"
          onChange={(e) => setCodigo(e.target.value)} placeholder="SUBSONIC|entrada|evento|firma" /></label>
        <p className="us-ayuda">Pega el código o usa un lector de QR que escriba en este campo. Comprueba el evento antes de validar.</p>
        <button className="btn-primary" disabled={ocupado || !eventoId || !codigo.trim()}>{ocupado ? 'Validando…' : 'Validar entrada'}</button>
      </fieldset>
    </form> : <p>No hay eventos disponibles para validar entradas.</p>}</CargaUsuarios>
    <AvisoUsuarios error={error} />
    {resultado && <div className="us-exito" role="status"><h3>Entrada válida</h3>
      <p>Titular: {resultado.titular}</p><p>Pase: {resultado.tipo_pase}</p><p>{resultado.entrada_id}</p>
      <p>Validada: {new Date(resultado.validada_en).toLocaleString('es-ES')}</p>
    </div>}
  </div>;
}
