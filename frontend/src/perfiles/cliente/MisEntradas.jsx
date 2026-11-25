// src/perfiles/cliente/MisEntradas.jsx — Dueño: Luis
// Qué hacer: Entradas del cliente con su QR (react-qr-code con entrada.codigo_qr) y solicitud de cancelación con motivo.
// API: GET /usuarios/me/entradas, POST /usuarios/me/entradas/{id}/cancelaciones (ms-usuarios)
// Referencia del monolito: legado/components/PerfilCliente/PerfilCliente.jsx (sección 'mis-entradas')
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { listarMisEntradas, solicitarCancelacion } from '../../api/usuarios';
import { useDatos } from '../../analitica/useDatos';
import { AvisoUsuarios, CargaUsuarios, EntradaQR } from '../comun/UsuariosUI';

export default function MisEntradas() {
  const peticion = useDatos(listarMisEntradas);
  const [mensaje, setMensaje] = useState('');
  return <div className="us-panel"><h2>Mis entradas</h2>
    <AvisoUsuarios mensaje={mensaje} />
    <CargaUsuarios peticion={peticion}>{(entradas) => entradas.length ? <div className="us-grid">
      {entradas.map((entrada) => <TarjetaEntrada key={entrada.id} entrada={entrada} alSolicitar={() => {
        setMensaje('Solicitud de cancelación enviada. Un administrador revisará el reembolso.'); peticion.recargar();
      }} />)}
    </div> : <p>No tienes entradas. <Link to="/calendario">Consulta los próximos eventos</Link>.</p>}</CargaUsuarios>
  </div>;
}

function TarjetaEntrada({ entrada, alSolicitar }) {
  const [qr, setQr] = useState(false);
  const [cancelar, setCancelar] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState(null);
  const solicitar = async (e) => {
    e.preventDefault();
    if (ocupado || motivo.trim().length < 5) return;
    setOcupado(true); setError(null);
    try { await solicitarCancelacion(entrada.id, motivo.trim()); setCancelar(false); alSolicitar(); }
    catch (e) { setError(e); }
    finally { setOcupado(false); }
  };
  return <article className="us-tarjeta" aria-label={`Entrada ${entrada.id}`}>
    <span className="us-estado">{entrada.estado.replaceAll('_', ' ')}</span>
    <h3>{entrada.evento_titulo || entrada.evento_id}</h3>
    <p>{entrada.evento_fechas}</p><p>{entrada.tipo_pase} · {entrada.precio_pagado} €</p>
    <p className="us-ayuda">{entrada.id}</p>
    {entrada.motivo_cancelacion && <p>Motivo: {entrada.motivo_cancelacion}</p>}
    {entrada.estado === 'ACTIVA' && <div className="us-acciones">
      <button className="btn-secondary" onClick={() => setQr(!qr)} aria-expanded={qr}>{qr ? 'Ocultar QR' : 'Mostrar QR'}</button>
      <button className="btn-secondary" onClick={() => setCancelar(!cancelar)} disabled={ocupado} aria-expanded={cancelar}>Solicitar cancelación</button>
    </div>}
    {qr && entrada.estado === 'ACTIVA' && <EntradaQR entrada={entrada} />}
    {cancelar && entrada.estado === 'ACTIVA' && <form onSubmit={solicitar}>
      <label className="us-campo">Motivo de cancelación<textarea required minLength={5} value={motivo}
        onChange={(e) => setMotivo(e.target.value)} disabled={ocupado} /></label>
      <p className="us-ayuda">Mínimo 5 caracteres. La cancelación necesita aprobación.</p>
      <button className="btn-primary" disabled={ocupado || motivo.trim().length < 5}>{ocupado ? 'Enviando…' : 'Enviar solicitud'}</button>
    </form>}
    <AvisoUsuarios error={error} />
  </article>;
}
