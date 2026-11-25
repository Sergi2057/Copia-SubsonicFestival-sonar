// src/perfiles/proveedor/PerfilProveedor.jsx — Dueña: Paula (solo la lista de pestañas; cada pestaña tiene su dueño)
import PanelPerfil from '../PanelPerfil';
import DatosPersonales from '../comun/DatosPersonales';
import Alquilar from './Alquilar';
import EspaciosRecomendados from './EspaciosRecomendados';
import MisAlquileres from './MisAlquileres';
import './PerfilProveedor.css';

const PESTANAS = [
  { id: 'alquileres', titulo: 'Mis Alquileres', icono: 'fa-boxes-stacked', Componente: MisAlquileres },    // Pedro
  { id: 'alquilar', titulo: 'Alquilar un Espacio', icono: 'fa-map-location-dot', Componente: Alquilar },    // Pedro
  { id: 'recomendados', titulo: 'Recomendados', icono: 'fa-star', Componente: EspaciosRecomendados },      // Paula
  { id: 'perfil', titulo: 'Perfil Empresarial', icono: 'fa-user-tie', Componente: DatosPersonales },       // Luis
];

export default function PerfilProveedor() {
  return <PanelPerfil clase="perfil-proveedor" icono="fa-shop" subtitulo="Proveedor" pestanas={PESTANAS} />;
}
