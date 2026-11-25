// src/pages/Evento/DetallesEvento.jsx — Dueño: Pedro
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { listarTarifas, obtenerEvento } from '../../api/espacios';
import { registrarInteraccion } from '../../analitica/interacciones';
import CartelEvento from './CartelEvento';
import ModalCheckout from './ModalCheckout';
import './DetallesEventos.css';

const fechasEvento = (evento) => evento.fecha_inicio === evento.fecha_fin
  ? evento.fecha_inicio : `${evento.fecha_inicio} – ${evento.fecha_fin}`;

export default function DetallesEvento() {
  const { id } = useParams();
  const [evento, setEvento] = useState(null);
  const [tarifas, setTarifas] = useState([]);
  const [tarifaElegida, setTarifaElegida] = useState(null);
  const [pestana, setPestana] = useState('servicios');
  const [eventoCargado, setEventoCargado] = useState(null);
  const [error, setError] = useState('');
  const [errorTarifas, setErrorTarifas] = useState('');
  const cargando = eventoCargado !== id;

  useEffect(() => {
    let cancelado = false;
    Promise.allSettled([obtenerEvento(id), listarTarifas(id)]).then(([resultadoEvento, resultadoTarifas]) => {
      if (cancelado) return;
      if (resultadoEvento.status === 'fulfilled') {
        setError('');
        setEvento(resultadoEvento.value);
        registrarInteraccion('VER_EVENTO', resultadoEvento.value.id);
      } else {
        setError(resultadoEvento.reason.message);
      }
      if (resultadoTarifas.status === 'fulfilled') {
        setErrorTarifas('');
        setTarifas(resultadoTarifas.value);
      } else {
        setErrorTarifas(resultadoTarifas.reason.message);
      }
    }).finally(() => {
      if (!cancelado) setEventoCargado(id);
    });
    return () => { cancelado = true; };
  }, [id]);

  if (cargando) return <main className="detalles-error" role="status">Cargando evento…</main>;
  if (error || !evento) return <main className="detalles-error" role="alert">{error || 'Evento no encontrado.'}</main>;

  const recinto = evento.recinto || {};
  const servicios = evento.servicios_generales || [];
  return (
    <main>
      <header className="detalles-hero" style={{ backgroundImage: evento.imagen_url ? `url("${evento.imagen_url}")` : undefined }}>
        <div className="detalles-hero-overlay">
          <h1 className="detalles-title">{evento.titulo}</h1>
          <p className="detalles-subtitle">{recinto.nombre || evento.pais} · {fechasEvento(evento)}</p>
        </div>
      </header>
      <section className="detalles-body">
        <div className="evento-tabs-header detalles-tabs-centered" aria-label="Información del evento">
          <button className={`tab-btn ${pestana === 'servicios' ? 'activo' : ''}`} onClick={() => setPestana('servicios')}>Servicios</button>
          <button className={`tab-btn ${pestana === 'pases' ? 'activo' : ''}`} onClick={() => setPestana('pases')}>Pases</button>
          <button className={`tab-btn ${pestana === 'cartel' ? 'activo' : ''}`} onClick={() => setPestana('cartel')}>Artistas y horarios</button>
        </div>
        {pestana === 'servicios' && (
          <div className="detalles-tab-content">
            <h2>{recinto.nombre || 'Recinto'}</h2>
            <p>{[recinto.direccion, recinto.ciudad, recinto.pais || evento.pais].filter(Boolean).join(', ')}</p>
            <p>{evento.descripcion}</p>
            <div className="detalles-servicios-grid">
              {servicios.length ? servicios.map((servicio) => (
                <div className="detalles-servicio-card" key={servicio}><span className="detalles-servicio-check">✓</span>
                  <span className="detalles-servicio-text">{servicio}</span></div>
              )) : <p>No hay servicios generales publicados.</p>}
            </div>
          </div>
        )}
        {pestana === 'pases' && (
          <div className="evento-tickets detalles-tickets-centered" aria-label="Tarifas">
            {errorTarifas && <p className="pe-error" role="alert">{errorTarifas}</p>}
            {!errorTarifas && tarifas.length === 0 && <p>No hay entradas configuradas para este evento.</p>}
            {tarifas.map((tarifa) => (
              <button className="ticket-box" key={tarifa.id} type="button" disabled={tarifa.disponibles <= 0}
                onClick={() => setTarifaElegida(tarifa)}>
                <span className="ticket-tipo">{tarifa.tipo_pase}</span>
                <span className="ticket-precio">{tarifa.precio} €</span>
                <span>{tarifa.disponibles} disponibles</span>
                <span>{tarifa.disponibles > 0 ? 'Comprar' : 'Agotado'}</span>
              </button>
            ))}
          </div>
        )}
        {pestana === 'cartel' && <CartelEvento eventoId={id} />}
        <div className="detalles-back-wrap">
          <Link to="/#eventos" className="btn-outline-small detalles-back-link">← Volver al inicio</Link>
        </div>
      </section>
      <ModalCheckout abierto={tarifaElegida !== null} onCerrar={() => setTarifaElegida(null)} eventoId={id}
        tarifa={tarifaElegida} eventoTitulo={evento.titulo} />
    </main>
  );
}
