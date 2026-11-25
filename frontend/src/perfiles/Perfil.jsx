// src/perfiles/Perfil.jsx — Dueña: Paula
// Página /perfil: muestra el perfil según el rol de la sesión.
import { Navigate } from 'react-router-dom';
import { useSesion } from '../sesion/SesionContext';
import CompletarRegistro from './CompletarRegistro';
import PerfilAdmin from './admin/PerfilAdmin';
import PerfilCliente from './cliente/PerfilCliente';
import PerfilProveedor from './proveedor/PerfilProveedor';
import PerfilStaff from './staff/PerfilStaff';
import './Perfil.css';

const PERFILES = { cliente: PerfilCliente, proveedor: PerfilProveedor, admin: PerfilAdmin, staff: PerfilStaff };

export default function Perfil() {
  const { autenticado, cargando, sinPerfil, rol, aviso } = useSesion();

  if (cargando) return <p className="perfil-estado">Cargando perfil...</p>;
  if (!autenticado) return <Navigate to="/" replace />;
  if (sinPerfil) return <CompletarRegistro />;

  const PerfilRol = PERFILES[rol];
  if (!PerfilRol) {
    return (
      <div className="perfil-estado">
        <h2 className="perfil-error-titulo">No se pudo cargar tu perfil</h2>
        <p>{aviso || 'Inténtalo de nuevo en unos segundos.'}</p>
      </div>
    );
  }
  return (
    <div className="dashboard-page" style={{ paddingTop: '73px', minHeight: '100vh', display: 'flex',
      flexDirection: 'column', width: '100%' }}>
      {aviso && <p className="auth-error" style={{ textAlign: 'center' }}>{aviso}</p>}
      <PerfilRol />
    </div>
  );
}
