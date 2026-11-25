// src/pages/Calendario/Calendario.jsx — Dueño: Pedro
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listarEventos } from '../../api/espacios';
import './CalendarioEventos.css';

const fechaLocal = (fecha) => new Date(`${fecha}T00:00:00`);
const etiquetaMes = (fecha) => new Intl.DateTimeFormat('es', { month: 'long', year: 'numeric' }).format(fecha);
const mostrarFechas = (evento) => evento.fecha_inicio === evento.fecha_fin
  ? evento.fecha_inicio : `${evento.fecha_inicio} – ${evento.fecha_fin}`;

export default function Calendario() {
  const [eventos, setEventos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelado = false;
    listarEventos({ estado: 'PUBLICADO' })
      .then(({ datos }) => {
        if (!cancelado) setEventos([...datos].sort((a, b) => a.fecha_inicio.localeCompare(b.fecha_inicio)));
      })
      .catch((e) => {
        if (!cancelado) setError(e.message);
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => { cancelado = true; };
  }, []);

  const grupos = eventos.reduce((resultado, evento) => {
    const mes = etiquetaMes(fechaLocal(evento.fecha_inicio));
    resultado.set(mes, [...(resultado.get(mes) || []), evento]);
    return resultado;
  }, new Map());

  return (
    <main className="calendario-page">
      <section>
        <div className="section-label">Agenda global</div>
        <h1>Calendario de eventos</h1>
        {cargando && <p role="status">Cargando calendario…</p>}
        {error && <p role="alert">{error}</p>}
        {!cargando && !error && eventos.length === 0 && <p>No hay eventos publicados por el momento.</p>}
        {[...grupos].map(([mes, lista]) => (
          <div role="region" aria-label={mes} key={mes}>
            <h2>{mes}</h2>
            <div className="calendario-lista">
              {lista.map((evento) => (
                <article className="calendario-card" key={evento.id}>
                  <div className="calendario-card-main">
                    <div className="calendario-fecha-box">
                      <div className="calendario-mes">FECHAS</div>
                      <div className="calendario-dia">{mostrarFechas(evento)}</div>
                    </div>
                    <div>
                      <h3 className="calendario-evento">{evento.titulo}</h3>
                      <p className="calendario-lugar">{evento.pais}</p>
                    </div>
                  </div>
                  <Link className="calendario-estado ok" to={`/evento/${encodeURIComponent(evento.id)}`}>
                    Ver evento
                  </Link>
                </article>
              ))}
            </div>
          </div>
        ))}
        <div className="calendario-back">
          <Link to="/#eventos" className="btn-outline-small calendario-back-link">← Volver al inicio</Link>
        </div>
      </section>
    </main>
  );
}
