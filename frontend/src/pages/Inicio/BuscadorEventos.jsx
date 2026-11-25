// src/pages/Inicio/BuscadorEventos.jsx — Dueño: Pedro
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { listarEventos } from '../../api/espacios';
import { registrarInteraccion } from '../../analitica/interacciones';
import './BuscadorEventos.css';

function fechasEvento(evento) {
  if (evento.fecha_inicio === evento.fecha_fin) return evento.fecha_inicio;
  return `${evento.fecha_inicio} – ${evento.fecha_fin}`;
}

export default function BuscadorEventos() {
  const [eventos, setEventos] = useState([]);
  const [paises, setPaises] = useState([]);
  const [texto, setTexto] = useState('');
  const [pais, setPais] = useState('');
  const [desde, setDesde] = useState('');
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelado = false;
    listarEventos({ estado: 'PUBLICADO' })
      .then(({ datos }) => {
        if (!cancelado) {
          setEventos(datos);
          setPaises([...new Set(datos.map((evento) => evento.pais).filter(Boolean))].sort());
        }
      })
      .catch((e) => {
        if (!cancelado) setError(e.message);
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => { cancelado = true; };
  }, []);

  const visibles = useMemo(() => {
    const consulta = texto.trim().toLocaleLowerCase();
    return eventos.filter((evento) => {
      const coincideTexto = !consulta || [evento.titulo, evento.pais, ...(evento.tags || [])]
        .some((valor) => valor?.toLocaleLowerCase().includes(consulta));
      const coincidePais = !pais || evento.pais === pais;
      const coincideFecha = !desde || evento.fecha_fin >= desde;
      return coincideTexto && coincidePais && coincideFecha;
    });
  }, [eventos, texto, pais, desde]);

  const buscar = async (event) => {
    event.preventDefault();
    const consulta = texto.trim() || pais || desde;
    if (consulta) registrarInteraccion('BUSCAR', consulta);
    setCargando(true);
    setError('');
    try {
      const resultado = await listarEventos({
        estado: 'PUBLICADO',
        pais: pais || undefined,
        desde: desde || undefined,
      });
      setEventos(resultado.datos);
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="pe-home" aria-labelledby="pe-home-title">
      <header className="pe-home-hero">
        <p className="pe-eyebrow">Festivales de música electrónica</p>
        <h1 id="pe-home-title">Subsonic Festival</h1>
        <p>Encuentra tu próximo festival.</p>
        <form className="pe-search" onSubmit={buscar}>
          <label>
            Buscar eventos
            <input value={texto} onChange={(event) => setTexto(event.target.value)}
              placeholder="Nombre, país o género" />
          </label>
          <label>
            País
            <select value={pais} onChange={(event) => setPais(event.target.value)}>
              <option value="">Todos los países</option>
              {paises.map((opcion) => <option key={opcion} value={opcion}>{opcion}</option>)}
            </select>
          </label>
          <label>
            Desde
            <input type="date" value={desde} onChange={(event) => setDesde(event.target.value)} />
          </label>
          <button className="btn-primary" type="submit">Buscar eventos</button>
        </form>
      </header>

      <div className="pe-eventos">
        <div className="pe-section-heading">
          <div><p className="pe-eyebrow">Próximos festivales</p><h2>Eventos publicados</h2></div>
          <Link className="btn-outline-small" to="/calendario">Ver calendario</Link>
        </div>
        {cargando && <p role="status">Cargando eventos…</p>}
        {error && <p className="pe-error" role="alert">{error}</p>}
        {!cargando && !error && visibles.length === 0 && <p>No hay eventos que coincidan con la búsqueda.</p>}
        <div className="pe-event-grid">
          {visibles.map((evento) => (
            <article className="pe-event-card" key={evento.id}>
              {evento.imagen_url && <img src={evento.imagen_url} alt="" />}
              <div>
                <p className="pe-eyebrow">{fechasEvento(evento)}</p>
                <h3>{evento.titulo}</h3>
                <p>{evento.pais}</p>
                <Link to={`/evento/${encodeURIComponent(evento.id)}`}>Ver evento</Link>
              </div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
