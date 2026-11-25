// src/components/Pendiente.jsx
// Marcador de una pantalla que aún no se ha pasado a los microservicios. Cada dueño lo sustituye por la suya.
export default function Pendiente({ titulo, dueno, children }) {
  return (
    <div className="dashboard-section active" data-testid="pendiente">
      <header className="section-header">
        <h2>{titulo}</h2>
        <p>Pendiente de pasar a los microservicios · <strong>{dueno}</strong></p>
      </header>
      {children && <div style={{ opacity: 0.8 }}>{children}</div>}
    </div>
  );
}
