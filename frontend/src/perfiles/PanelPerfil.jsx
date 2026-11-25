// src/perfiles/PanelPerfil.jsx
// Esqueleto común de los perfiles: barra lateral con las pestañas y el contenido de la pestaña activa.
// Cada rol (PerfilCliente, PerfilAdmin…) solo indica sus pestañas; cada pestaña es un componente aparte
// con un único dueño, así nadie toca el archivo de otro.
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSesion } from '../sesion/SesionContext';

/**
 * pestanas = [{ id, titulo, icono: 'fa-ticket', Componente }]
 * Los componentes reciben { perfil } (el de GET /usuarios/me).
 */
export default function PanelPerfil({ clase, icono, subtitulo, pestanas }) {
  const { perfil, cerrarSesion } = useSesion();
  const [activa, setActiva] = useState(pestanas[0].id);
  const navigate = useNavigate();
  const { Componente } = pestanas.find((p) => p.id === activa);

  const salir = async () => {
    await cerrarSesion();
    navigate('/');
  };

  return (
    <main className={`dashboard-container ${clase}`}>
      <aside className="dashboard-sidebar">
        <div className="user-profile-summary">
          <div className="user-avatar"><i className={`fa-solid ${icono}`}></i></div>
          <h3>{perfil.nombre} {perfil.apellidos}</h3>
          <p className="user-role">{subtitulo}</p>
        </div>
        <div className="sidebar-nav">
          <ul>
            {pestanas.map((p) => (
              <li key={p.id}>
                <a href={`#${p.id}`} className={activa === p.id ? 'active' : ''}
                  onClick={(e) => { e.preventDefault(); setActiva(p.id); }}>
                  <i className={`fa-solid ${p.icono}`}></i> {p.titulo}
                </a>
              </li>
            ))}
          </ul>
        </div>
        <button className="btn-secondary" style={{ marginTop: 'auto', width: '100%' }} onClick={salir}>
          Cerrar Sesión
        </button>
      </aside>
      <section className="dashboard-content">
        <Componente perfil={perfil} />
      </section>
    </main>
  );
}
