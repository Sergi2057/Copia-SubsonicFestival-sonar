// src/perfiles/admin/PerfilAdmin.jsx — Dueña: Paula (solo la lista de pestañas; cada pestaña tiene su dueño)
import PanelPerfil from '../PanelPerfil';
import Entradas from './Entradas';
import Escaleta from './Escaleta';
import Espacios from './Espacios';
import Estadisticas from './Estadisticas';
import Eventos from './Eventos';
import Resumen from './Resumen';
import Tienda from './Tienda';
import Usuarios from './Usuarios';
import './PerfilAdmin.css';

const PESTANAS = [
  { id: 'resumen', titulo: 'Visión General', icono: 'fa-chart-line', Componente: Resumen },              // Paula
  { id: 'eventos', titulo: 'Eventos y Recintos', icono: 'fa-calendar-days', Componente: Eventos },       // Pedro
  { id: 'espacios', titulo: 'Espacios y Alquileres', icono: 'fa-map-location-dot', Componente: Espacios }, // Pedro
  { id: 'escaleta', titulo: 'Escaleta y Artistas', icono: 'fa-music', Componente: Escaleta },            // Sergio
  { id: 'usuarios', titulo: 'Usuarios y Proveedores', icono: 'fa-users', Componente: Usuarios },         // Luis
  { id: 'entradas', titulo: 'Entradas', icono: 'fa-ticket', Componente: Entradas },                      // Luis
  { id: 'tienda', titulo: 'Tienda', icono: 'fa-shirt', Componente: Tienda },                             // Sergio
  { id: 'estadisticas', titulo: 'Estadísticas', icono: 'fa-vault', Componente: Estadisticas },           // Paula
];

export default function PerfilAdmin() {
  return <PanelPerfil clase="perfil-admin" icono="fa-crown" subtitulo="Administrador" pestanas={PESTANAS} />;
}
