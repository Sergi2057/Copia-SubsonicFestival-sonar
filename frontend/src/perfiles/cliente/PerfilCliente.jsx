// src/perfiles/cliente/PerfilCliente.jsx — Dueña: Paula (solo la lista de pestañas; cada pestaña tiene su dueño)
import PanelPerfil from '../PanelPerfil';
import DatosPersonales from '../comun/DatosPersonales';
import Favoritos from './Favoritos';
import MisEntradas from './MisEntradas';
import MisPedidos from './MisPedidos';
import Notificaciones from './Notificaciones';
import Resumen from './Resumen';
import './PerfilCliente.css';

const PESTANAS = [
  { id: 'inicio', titulo: 'Inicio', icono: 'fa-home', Componente: Resumen },                         // Paula
  { id: 'entradas', titulo: 'Mis Entradas', icono: 'fa-ticket', Componente: MisEntradas },           // Luis
  { id: 'favoritos', titulo: 'Artistas Favoritos', icono: 'fa-heart', Componente: Favoritos },       // Luis
  { id: 'pedidos', titulo: 'Mis Pedidos', icono: 'fa-bag-shopping', Componente: MisPedidos },        // Sergio
  { id: 'notificaciones', titulo: 'Notificaciones', icono: 'fa-bell', Componente: Notificaciones }, // Luis
  { id: 'datos', titulo: 'Datos Personales', icono: 'fa-user-gear', Componente: DatosPersonales },  // Luis
];

export default function PerfilCliente() {
  return <PanelPerfil clase="perfil-cliente" icono="fa-user" subtitulo="Cliente" pestanas={PESTANAS} />;
}
