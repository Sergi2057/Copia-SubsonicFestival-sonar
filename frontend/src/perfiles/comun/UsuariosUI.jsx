// Piezas de las pantallas de usuarios. Dueño: Luis.
import { useEffect, useId, useRef } from 'react';
import QRCode from 'react-qr-code';
import './UsuariosUI.css';

export function AvisoUsuarios({ error, mensaje }) {
  if (error) return <p className="us-error" role="alert">{error.message || error}</p>;
  return mensaje ? <p className="us-exito" role="status">{mensaje}</p> : null;
}

export function CargaUsuarios({ peticion, children }) {
  if (peticion.cargando) return <p role="status">Cargando…</p>;
  if (peticion.error) return <div className="us-error" role="alert">
    <p>{peticion.error.message}</p>
    <button type="button" className="btn-secondary" onClick={peticion.recargar}>Reintentar</button>
  </div>;
  return children(peticion.datos);
}

export function EntradaQR({ entrada }) {
  return <div className="us-qr">
    <QRCode value={entrada.codigo_qr} size={192} title={`QR de la entrada ${entrada.id}`} />
    <p>{entrada.id}</p>
    <small>Presenta este QR en el control de acceso. No lo compartas.</small>
  </div>;
}

export function PaginasUsuarios({ pagina, total, alCambiar, tamano = 20 }) {
  return <div className="us-paginacion" aria-label="Paginación">
    <button className="btn-secondary" disabled={pagina === 0} onClick={() => alCambiar(pagina - 1)}>Anterior</button>
    <span>Página {pagina + 1} · {total} resultados</span>
    <button className="btn-secondary" disabled={(pagina + 1) * tamano >= total} onClick={() => alCambiar(pagina + 1)}>Siguiente</button>
  </div>;
}

export function ModalUsuarios({ titulo, onCerrar, ocupado = false, children }) {
  const tituloId = useId();
  const modal = useRef(null);
  useEffect(() => {
    const anterior = document.activeElement;
    modal.current?.focus();
    return () => anterior?.focus();
  }, []);
  useEffect(() => {
    const teclado = (evento) => {
      if (evento.key === 'Escape' && !ocupado) onCerrar();
      if (evento.key !== 'Tab') return;
      const campos = modal.current?.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled)');
      if (!campos?.length) { evento.preventDefault(); return; }
      const primero = campos[0];
      const ultimo = campos[campos.length - 1];
      if (evento.shiftKey && (document.activeElement === primero || document.activeElement === modal.current)) {
        evento.preventDefault(); ultimo.focus();
      } else if (!evento.shiftKey && (document.activeElement === ultimo || document.activeElement === modal.current)) {
        evento.preventDefault(); primero.focus();
      }
    };
    document.addEventListener('keydown', teclado);
    return () => document.removeEventListener('keydown', teclado);
  }, [ocupado, onCerrar]);
  return <div className="us-modal-fondo" onClick={(e) => {
    if (e.target === e.currentTarget && !ocupado) onCerrar();
  }}>
    <div className="us-modal us-panel" role="dialog" aria-modal="true" aria-labelledby={tituloId}
      tabIndex={-1} ref={modal} aria-busy={ocupado}>
      <div className="us-cabecera"><h2 id={tituloId}>{titulo}</h2>
        <button className="btn-secondary" onClick={onCerrar} disabled={ocupado} aria-label="Cerrar ventana">×</button>
      </div>
      {children}
    </div>
  </div>;
}
