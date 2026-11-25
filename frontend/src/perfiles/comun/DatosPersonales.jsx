// src/perfiles/comun/DatosPersonales.jsx — Dueño: Luis
// Qué hacer: Ver y modificar el perfil (nombre, apellidos, teléfono, dirección; datos de empresa si es proveedor), desactivar y eliminar la cuenta. La usan cliente, proveedor, admin y staff.
// API: GET/PATCH/DELETE /usuarios/me (ms-usuarios). Tras eliminar o desactivar: useSesion().cerrarSesion()
// Referencia del monolito: legado/components/PerfilCliente/PerfilCliente.jsx (sección 'datos-personales') y PerfilProveedor.jsx ('perfil')
import { useState } from 'react';
import { modificarPerfil, eliminarCuenta } from '../../api/usuarios';
import { useSesion } from '../../sesion/SesionContext';
import { AvisoUsuarios, ModalUsuarios } from './UsuariosUI';

export default function DatosPersonales({ perfil }) {
  const sesion = useSesion();
  const actual = perfil || sesion.perfil;
  return actual ? <Formulario key={actual.id} perfil={actual} sesion={sesion} /> : <p role="status">Cargando perfil…</p>;
}

const CAMPOS = [['nombre', 'Nombre'], ['apellidos', 'Apellidos'], ['telefono', 'Teléfono'], ['direccion', 'Dirección']];
const EMPRESA = [['nombre_comercial', 'Nombre comercial'], ['cif', 'CIF'], ['tipo_servicio', 'Tipo de servicio'], ['descripcion_servicio', 'Descripción del servicio']];
const valores = (datos, campos) => Object.fromEntries(campos.map(([clave]) => [clave, datos?.[clave] || '']));

function Formulario({ perfil, sesion }) {
  const [datos, setDatos] = useState(() => valores(perfil, CAMPOS));
  const [empresa, setEmpresa] = useState(() => valores(perfil.proveedor, EMPRESA));
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState(null);
  const [mensaje, setMensaje] = useState('');
  const [accion, setAccion] = useState(null);
  const [confirmacion, setConfirmacion] = useState('');
  const guardar = async (e) => {
    e.preventDefault(); setOcupado(true); setError(null); setMensaje('');
    try {
      await modificarPerfil({ ...datos, nombre: datos.nombre.trim(), ...(perfil.rol === 'PROVEEDOR' ? { proveedor: empresa } : {}) });
      await sesion.recargarPerfil(); setMensaje('Datos personales guardados.');
    } catch (e) { setError(e); }
    finally { setOcupado(false); }
  };
  const confirmar = async () => {
    if (ocupado || (accion === 'eliminar' && confirmacion !== 'ELIMINAR')) return;
    setOcupado(true); setError(null);
    try {
      if (accion === 'eliminar') await eliminarCuenta();
      else await modificarPerfil({ activo: false });
      await sesion.cerrarSesion();
    } catch (e) { setError(e); }
    finally { setOcupado(false); }
  };
  return <div className="us-panel"><h2>Datos personales</h2>
    {!accion && <AvisoUsuarios error={error} mensaje={mensaje} />}
    <form className="us-formulario" onSubmit={guardar}>
      <fieldset disabled={ocupado}>
        <label className="us-campo">Email<input type="email" value={perfil.email} readOnly /></label>
        <div className="us-form-grid">{CAMPOS.map(([clave, texto]) => <label className="us-campo" key={clave}>{texto}
          <input value={datos[clave]} required={clave === 'nombre'} maxLength={clave === 'telefono' ? 20 : clave === 'nombre' ? 100 : 255}
            type={clave === 'telefono' ? 'tel' : 'text'} onChange={(e) => setDatos({ ...datos, [clave]: e.target.value })} />
        </label>)}</div>
        {perfil.rol === 'PROVEEDOR' && <>
          <h3>Datos de empresa</h3><p>Proveedor {perfil.proveedor?.validado ? 'validado' : 'pendiente de validar'}</p>
          <div className="us-form-grid">{EMPRESA.map(([clave, texto]) => <label className="us-campo" key={clave}>{texto}
            <input value={empresa[clave]} maxLength={clave === 'cif' ? 20 : undefined}
              onChange={(e) => setEmpresa({ ...empresa, [clave]: e.target.value })} />
          </label>)}</div>
        </>}
        <button className="btn-primary" disabled={ocupado || !datos.nombre.trim()}>{ocupado ? 'Guardando…' : 'Guardar cambios'}</button>
      </fieldset>
    </form>
    <div className="us-peligros"><h3>Gestión de la cuenta</h3>
      <p>La cuenta desactivada solo puede reactivarla un administrador. El borrado elimina tus datos personales y conserva el histórico anonimizado.</p>
      <div className="us-acciones">{['desactivar', 'eliminar'].map((tipo) => <button key={tipo} className="us-peligro" disabled={ocupado}
        onClick={() => { setAccion(tipo); setConfirmacion(''); setError(null); }}>
        {tipo === 'desactivar' ? 'Desactivar cuenta' : 'Eliminar cuenta'}</button>)}</div>
    </div>
    {accion && <ModalUsuarios titulo={accion === 'eliminar' ? 'Confirmar borrado de cuenta' : 'Confirmar desactivación'}
      onCerrar={() => setAccion(null)} ocupado={ocupado}>
      <p>{accion === 'eliminar' ? 'Esta acción elimina tu cuenta y no se puede deshacer. Escribe ELIMINAR para continuar.' : 'Se cerrará tu sesión. Para reactivar la cuenta tendrás que contactar con un administrador.'}</p>
      {accion === 'eliminar' && <label className="us-campo">Confirmación<input value={confirmacion} onChange={(e) => setConfirmacion(e.target.value)} /></label>}
      <AvisoUsuarios error={error} />
      <div className="us-acciones"><button className="btn-secondary" disabled={ocupado} onClick={() => setAccion(null)}>Volver</button>
        <button className="us-peligro" disabled={ocupado || (accion === 'eliminar' && confirmacion !== 'ELIMINAR')} onClick={confirmar}>
          {ocupado ? 'Procesando…' : 'Confirmar acción'}</button></div>
    </ModalUsuarios>}
  </div>;
}
