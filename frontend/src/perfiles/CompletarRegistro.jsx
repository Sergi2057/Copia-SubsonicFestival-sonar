// src/perfiles/CompletarRegistro.jsx — Dueña: Paula
// Para quien ya tiene cuenta en Firebase (p. ej. entró con Google) pero aún no tiene perfil en ms-usuarios.
import { useState } from 'react';
import { useSesion } from '../sesion/SesionContext';

export default function CompletarRegistro() {
  const { registrar, cerrarSesion } = useSesion();
  const [datos, setDatos] = useState({ nombre: '', apellidos: '', rol: 'CLIENTE', nombre_comercial: '',
    tipo_servicio: '' });
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  const cambiar = (campo) => (e) => setDatos({ ...datos, [campo]: e.target.value });

  const enviar = async (e) => {
    e.preventDefault();
    setError('');
    setEnviando(true);
    const { nombre_comercial, tipo_servicio, ...perfil } = datos;
    try {
      await registrar(datos.rol === 'PROVEEDOR' ? { ...perfil, proveedor: { nombre_comercial, tipo_servicio } } : perfil);
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="perfil-estado">
      <div className="modal" style={{ margin: '0 auto' }}>
        <h3>COMPLETA TU REGISTRO</h3>
        <p>Tu cuenta ya existe; solo faltan tus datos para crear tu perfil.</p>
        <form onSubmit={enviar}>
          <div className="campo">
            <label htmlFor="registro-nombre">Nombre</label>
            <input id="registro-nombre" value={datos.nombre} onChange={cambiar('nombre')} required />
          </div>
          <div className="campo">
            <label htmlFor="registro-apellidos">Apellidos</label>
            <input id="registro-apellidos" value={datos.apellidos} onChange={cambiar('apellidos')} required />
          </div>
          <div className="campo">
            <label htmlFor="registro-rol">Tipo de cuenta</label>
            <select id="registro-rol" value={datos.rol} onChange={cambiar('rol')}>
              <option value="CLIENTE">Cliente</option>
              <option value="PROVEEDOR">Proveedor</option>
            </select>
          </div>
          {datos.rol === 'PROVEEDOR' && (
            <>
              <div className="campo">
                <label htmlFor="registro-comercial">Nombre comercial</label>
                <input id="registro-comercial" value={datos.nombre_comercial} onChange={cambiar('nombre_comercial')}
                  required />
              </div>
              <div className="campo">
                <label htmlFor="registro-servicio">Tipo de servicio</label>
                <input id="registro-servicio" placeholder="Comida, bebida, merchandising…" value={datos.tipo_servicio}
                  onChange={cambiar('tipo_servicio')} required />
              </div>
            </>
          )}
          <div className="modal-btns">
            <button type="button" className="btn-cerrar" onClick={cerrarSesion} disabled={enviando}>Salir</button>
            <button type="submit" className="btn-login" disabled={enviando}>
              {enviando ? 'Guardando...' : 'Crear perfil'}
            </button>
          </div>
        </form>
        {error && <p className="auth-error">{error}</p>}
      </div>
    </div>
  );
}
