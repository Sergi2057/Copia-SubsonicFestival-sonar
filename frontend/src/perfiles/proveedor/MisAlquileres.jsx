// src/perfiles/proveedor/MisAlquileres.jsx — Dueño: Pedro
import { useCallback, useEffect, useState } from 'react';
import { cambiarEstadoAlquiler, listarAlquileres } from '../../api/espacios';
import { useEventos } from '../../analitica/useDatos';
import '../espacios.css';

const lista = (respuesta) => respuesta?.datos || respuesta || [];

export default function MisAlquileres() {
  const [alquileres, setAlquileres] = useState([]);
  const [estado, setEstado] = useState('');
  const [cargando, setCargando] = useState(true);
  const [ocupado, setOcupado] = useState(null);
  const [error, setError] = useState('');
  const { datos: eventos, error: errorEventos } = useEventos();

  const cargar = useCallback(async () => {
    setCargando(true);
    setError('');
    try {
      setAlquileres(lista(await listarAlquileres({ estado: estado || undefined })));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }, [estado]);

  useEffect(() => { cargar(); }, [cargar]);

  const actualizar = async (alquiler, nuevoEstado) => {
    setOcupado(alquiler.id);
    setError('');
    try {
      await cambiarEstadoAlquiler(alquiler.id, nuevoEstado);
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setOcupado(null);
    }
  };

  return (
    <div className="pe-panel" aria-labelledby="pe-mis-alquileres-title">
      <header className="pe-panel-heading"><h2 id="pe-mis-alquileres-title">Mis alquileres</h2>
        <p>Consulta tus solicitudes, alquileres activos e historial.</p></header>
      <label className="pe-filter-single">Estado
        <select value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos</option>
          {['PENDIENTE', 'APROBADO', 'ACTIVO', 'RECHAZADO', 'CANCELADO', 'FINALIZADO'].map((opcion) => (
            <option key={opcion} value={opcion}>{opcion}</option>
          ))}
        </select>
      </label>
      {error && <p className="pe-error" role="alert">{error}</p>}
      {errorEventos && <p className="pe-error" role="alert">{errorEventos.message}</p>}
      {cargando && <p role="status">Cargando alquileres…</p>}
      {!cargando && !error && alquileres.length === 0 && <p>No tienes alquileres en este estado.</p>}
      <div className="pe-cards">
        {alquileres.map((alquiler) => (
          <article className="pe-card" key={alquiler.id}>
            <span className="pe-badge">{alquiler.estado}</span>
            <h3>{alquiler.espacio?.nombre || alquiler.espacio_id}</h3>
            <p>Evento: {eventos?.find((evento) => evento.id === alquiler.evento_id)?.titulo || alquiler.evento_id}</p>
            <p>{alquiler.fecha_inicio} – {alquiler.fecha_fin}</p>
            <p>Importe: {alquiler.importe} €</p>
            {alquiler.comentarios && <p>{alquiler.comentarios}</p>}
            {alquiler.estado === 'PENDIENTE' && <button className="btn-secondary" type="button"
              disabled={ocupado !== null} onClick={() => actualizar(alquiler, 'CANCELADO')}>
              {ocupado === alquiler.id ? 'Actualizando…' : 'Cancelar solicitud'}
            </button>}
            {alquiler.estado === 'ACTIVO' && <button className="btn-primary" type="button"
              disabled={ocupado !== null} onClick={() => actualizar(alquiler, 'FINALIZADO')}>
              {ocupado === alquiler.id ? 'Actualizando…' : 'Finalizar alquiler'}
            </button>}
          </article>
        ))}
      </div>
    </div>
  );
}
