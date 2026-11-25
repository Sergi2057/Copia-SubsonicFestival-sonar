// src/perfiles/admin/Entradas.jsx — Dueño: Luis
// Qué hacer: Listado de entradas con filtros y resolución de las solicitudes de cancelación (aceptar → CANCELADA, rechazar → ACTIVA).
// API: GET /entradas, PATCH /entradas/{id} (ms-usuarios)
// Referencia del monolito: Nueva (no existe en el monolito)
import { useState } from 'react';
import { listarEntradasAdmin, resolverCancelacion } from '../../api/usuarios';
import { useDatos, useEventos } from '../../analitica/useDatos';
import { AvisoUsuarios, CargaUsuarios, PaginasUsuarios } from '../comun/UsuariosUI';

export default function Entradas() {
  const eventos = useEventos();
  const [borrador, setBorrador] = useState({ estado: 'CANCELACION_SOLICITADA', evento_id: '' });
  const [filtros, setFiltros] = useState(borrador);
  const [pagina, setPagina] = useState(0);
  const [ocupado, setOcupado] = useState(null);
  const [error, setError] = useState(null);
  const [mensaje, setMensaje] = useState('');
  const peticion = useDatos(listarEntradasAdmin, { ...filtros, limite: 20, desplazamiento: pagina * 20 });
  const resolver = async (id, estado) => {
    if (ocupado) return;
    setOcupado(id); setError(null); setMensaje('');
    try {
      await resolverCancelacion(id, estado);
      setMensaje(estado === 'CANCELADA' ? 'Cancelación aceptada y reembolso tramitado.' : 'Solicitud rechazada; la entrada vuelve a estar activa.');
      peticion.recargar();
    } catch (e) { setError(e); }
    finally { setOcupado(null); }
  };
  return <div className="us-panel"><h2>Entradas y cancelaciones</h2>
    <form className="us-filtros" onSubmit={(e) => { e.preventDefault(); setFiltros(borrador); setPagina(0); }}>
      <label className="us-campo">Estado<select value={borrador.estado} onChange={(e) => setBorrador({ ...borrador, estado: e.target.value })}>
        <option value="">Todos</option>{['ACTIVA', 'CANCELACION_SOLICITADA', 'CANCELADA', 'USADA'].map((s) => <option key={s} value={s}>{s.replaceAll('_', ' ')}</option>)}
      </select></label>
      <CargaUsuarios peticion={eventos}>{(lista) => <label className="us-campo">Evento
        <select value={borrador.evento_id} onChange={(e) => setBorrador({ ...borrador, evento_id: e.target.value })}>
          <option value="">Todos los eventos</option>
          {lista.map((e) => <option key={e.id} value={e.id}>{e.titulo}</option>)}
        </select>
      </label>}</CargaUsuarios>
      <button className="btn-secondary">Aplicar filtros</button>
    </form>
    <AvisoUsuarios error={error} mensaje={mensaje} />
    <CargaUsuarios peticion={peticion}>{({ datos, total }) => <>
      {datos.length ? <div className="us-tabla-scroll"><table className="us-tabla">
        <caption>Entradas del festival</caption>
        <thead><tr><th scope="col">Entrada</th><th scope="col">Evento</th><th scope="col">Pase / importe</th>
          <th scope="col">Estado / motivo</th><th scope="col">Resolución</th></tr></thead>
        <tbody>{datos.map((e) => <tr key={e.id}><td>{e.id}</td><td>{e.evento_titulo || e.evento_id}</td>
          <td>{e.tipo_pase}<p>{e.precio_pagado} €</p></td><td>{e.estado.replaceAll('_', ' ')}<p>{e.motivo_cancelacion}</p></td>
          <td>{e.estado === 'CANCELACION_SOLICITADA' ? <div className="us-acciones">
            <button className="btn-secondary" disabled={ocupado !== null} onClick={() => resolver(e.id, 'CANCELADA')}>Aceptar cancelación</button>
            <button className="btn-secondary" disabled={ocupado !== null} onClick={() => resolver(e.id, 'ACTIVA')}>Rechazar solicitud</button>
          </div> : 'Sin solicitud pendiente'}</td></tr>)}</tbody>
      </table></div> : <p className="us-ayuda">No hay entradas con estos filtros.</p>}
      <PaginasUsuarios pagina={pagina} total={total} alCambiar={setPagina} />
    </>}</CargaUsuarios>
  </div>;
}
