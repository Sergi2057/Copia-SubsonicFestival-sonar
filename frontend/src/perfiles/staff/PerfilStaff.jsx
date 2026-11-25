// src/perfiles/staff/PerfilStaff.jsx — Dueña: Paula (solo la lista de pestañas; cada pestaña tiene su dueño)
import PanelPerfil from '../PanelPerfil';
import DatosPersonales from '../comun/DatosPersonales';
import ValidarEntradas from './ValidarEntradas';
import '../admin/PerfilAdmin.css';

const PESTANAS = [
  { id: 'validar', titulo: 'Control de Acceso', icono: 'fa-qrcode', Componente: ValidarEntradas },  // Luis
  { id: 'datos', titulo: 'Datos Personales', icono: 'fa-user-gear', Componente: DatosPersonales },  // Luis
];

export default function PerfilStaff() {
  return <PanelPerfil clase="perfil-admin" icono="fa-id-badge" subtitulo="Staff de acceso" pestanas={PESTANAS} />;
}
