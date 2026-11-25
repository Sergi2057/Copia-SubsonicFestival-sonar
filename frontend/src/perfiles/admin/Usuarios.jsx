// src/perfiles/admin/Usuarios.jsx — Dueño: Luis
// Qué hacer: Lista de usuarios con filtro por rol, cambiar rol y activar/desactivar; control de proveedores y validarlos.
// API: GET /usuarios, PATCH /usuarios/{id}, GET /proveedores, PATCH /proveedores/{id} (ms-usuarios)
// Referencia del monolito: legado/components/PerfilAdmin/PerfilAdmin.jsx (secciones 'usuarios' y 'proveedores')
import { useState } from 'react';
import { listarUsuarios, modificarUsuario, listarProveedores, validarProveedor } from '../../api/usuarios';
import { useDatos } from '../../analitica/useDatos';
import { useSesion } from '../../sesion/SesionContext';
import { AvisoUsuarios, CargaUsuarios, PaginasUsuarios } from '../comun/UsuariosUI';

const ROLES = ['CLIENTE', 'PROVEEDOR', 'ADMIN', 'STAFF'];

export default function Usuarios() {
  const [modo, setModo] = useState('usuarios');
  const { perfil } = useSesion();
  return <div className="us-panel"><h2>Usuarios y proveedores</h2>
    <div className="us-acciones" role="group" aria-label="Tipo de listado">
      <button className="btn-secondary" aria-pressed={modo === 'usuarios'} onClick={() => setModo('usuarios')}>Usuarios</button>
      <button className="btn-secondary" aria-pressed={modo === 'proveedores'} onClick={() => setModo('proveedores')}>Proveedores</button>
    </div>
    <Listado key={modo} modo={modo} propioId={perfil?.id} />
  </div>;
}

function Listado({ modo, propioId }) {
  const [borrador, setBorrador] = useState({});
  const [filtros, setFiltros] = useState({});
  const [pagina, setPagina] = useState(0);
  const [mensaje, setMensaje] = useState('');
  const proveedores = modo === 'proveedores';
  const peticion = useDatos(proveedores ? listarProveedores : listarUsuarios, { ...filtros, limite: 20, desplazamiento: pagina * 20 });
  const cambiar = (clave, valor) => setBorrador({ ...borrador, [clave]: valor });
  return <>
    <form className="us-filtros" onSubmit={(e) => { e.preventDefault(); setFiltros(borrador); setPagina(0); }}>
      {proveedores ? <>
        <label className="us-campo">Validación<select value={borrador.validado ?? ''} onChange={(e) => cambiar('validado', e.target.value)}>
          <option value="">Todos</option><option value="true">Validados</option><option value="false">Pendientes</option>
        </select></label>
        <label className="us-campo">Tipo de servicio<input value={borrador.tipo_servicio || ''} onChange={(e) => cambiar('tipo_servicio', e.target.value)} /></label>
      </> : <>
        <label className="us-campo">Buscar usuario<input value={borrador.q || ''} onChange={(e) => cambiar('q', e.target.value)} placeholder="Nombre o email" /></label>
        <label className="us-campo">Rol<select value={borrador.rol || ''} onChange={(e) => cambiar('rol', e.target.value)}>
          <option value="">Todos</option>{ROLES.map((rol) => <option key={rol}>{rol}</option>)}
        </select></label>
        <label className="us-campo">Cuenta<select value={borrador.activo ?? ''} onChange={(e) => cambiar('activo', e.target.value)}>
          <option value="">Todas</option><option value="true">Activas</option><option value="false">Desactivadas</option>
        </select></label>
      </>}
      <button className="btn-secondary">Aplicar filtros</button>
    </form>
    <AvisoUsuarios mensaje={mensaje} />
    <CargaUsuarios peticion={peticion}>{({ datos, total }) => <>
      {datos.length ? <div className="us-tabla-scroll"><table className="us-tabla">
        <caption>{proveedores ? 'Control de proveedores' : 'Administración de usuarios'}</caption>
        <thead><tr><th scope="col">Usuario</th><th scope="col">{proveedores ? 'Empresa' : 'Rol'}</th>
          <th scope="col">Estado</th><th scope="col">Acciones</th></tr></thead>
        <tbody>{datos.map((u) => <Fila key={u.id} usuario={u} proveedores={proveedores} propio={u.id === propioId}
          alCambiar={() => { setMensaje('Usuario actualizado.'); peticion.recargar(); }} />)}</tbody>
      </table></div> : <p className="us-ayuda">No hay usuarios con estos filtros.</p>}
      <PaginasUsuarios pagina={pagina} total={total} alCambiar={setPagina} />
    </>}</CargaUsuarios>
  </>;
}

function Fila({ usuario, proveedores, propio, alCambiar }) {
  const [rol, setRol] = useState(usuario.rol);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState(null);
  const ejecutar = async (accion) => {
    if (ocupado) return;
    setOcupado(true); setError(null);
    try { await accion(); alCambiar(); }
    catch (e) { setError(e); }
    finally { setOcupado(false); }
  };
  return <tr>
    <td>{usuario.nombre} {usuario.apellidos}<p className="us-ayuda">{usuario.email}</p></td>
    <td>{proveedores ? <>{usuario.proveedor?.nombre_comercial || 'Sin nombre comercial'}
      <p>{usuario.proveedor?.tipo_servicio}</p><p>{usuario.proveedor?.cif}</p></> :
      <label className="us-campo">Rol de {usuario.nombre || usuario.email}
        <select disabled={ocupado || propio} value={rol} onChange={(e) => setRol(e.target.value)}>
          {ROLES.map((r) => <option key={r}>{r}</option>)}
        </select>
      </label>}</td>
    <td>{usuario.activo ? 'Activa' : 'Desactivada'}
      {proveedores && <p>{usuario.proveedor?.validado ? 'Validado' : 'Pendiente de validar'}</p>}</td>
    <td>
      {propio ? <p>Tu cuenta se gestiona en Datos personales.</p> : <div className="us-acciones">
        {!proveedores && <button className="btn-secondary" disabled={ocupado || rol === usuario.rol}
          onClick={() => ejecutar(() => modificarUsuario(usuario.id, { rol }))}>Guardar rol</button>}
        <button className="btn-secondary" disabled={ocupado}
          onClick={() => ejecutar(() => modificarUsuario(usuario.id, { activo: !usuario.activo }))}>
          {usuario.activo ? 'Desactivar' : 'Activar'}</button>
        {proveedores && <button className="btn-secondary" disabled={ocupado}
          onClick={() => ejecutar(() => validarProveedor(usuario.id, !usuario.proveedor?.validado))}>
          {usuario.proveedor?.validado ? 'Retirar validación' : 'Validar proveedor'}</button>}
      </div>}
      <AvisoUsuarios error={error} />
    </td>
  </tr>;
}
