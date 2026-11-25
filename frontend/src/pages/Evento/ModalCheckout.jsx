// src/pages/Evento/ModalCheckout.jsx — Dueño: Luis
// Props: { abierto, onCerrar, eventoId, tarifa, eventoTitulo? }. El título es opcional para mostrar el resumen; la compra usa eventoId.
// API: POST /usuarios/me/entradas (ms-usuarios)
// Referencia del monolito: legado/components/ModalCheckout.jsx
import { useState } from 'react';
import { comprarEntrada } from '../../api/usuarios';
import { useSesion } from '../../sesion/SesionContext';
import { AvisoUsuarios, EntradaQR, ModalUsuarios } from '../../perfiles/comun/UsuariosUI';

export default function ModalCheckout({ abierto, onCerrar, eventoId, tarifa, eventoTitulo }) {
  if (!abierto) return null;
  return <Compra key={`${eventoId}-${tarifa?.id || tarifa?.tipo_pase}`} onCerrar={onCerrar}
    eventoId={eventoId} tarifa={tarifa} eventoTitulo={eventoTitulo} />;
}

function Compra({ onCerrar, eventoId, tarifa, eventoTitulo }) {
  const { perfil, rol, cargando } = useSesion();
  const [token, setToken] = useState('tok_ok');
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState(null);
  const [entrada, setEntrada] = useState(null);
  const puedeComprar = rol === 'cliente' && perfil?.activo !== false && tarifa && eventoId && tarifa.disponibles > 0;
  const comprar = async (e) => {
    e.preventDefault();
    if (ocupado || entrada || !puedeComprar) return;
    setError(null); setOcupado(true);
    try {
      setEntrada(await comprarEntrada({ evento_id: eventoId, tipo_pase: tarifa.tipo_pase, token_pago: token.trim() }));
    } catch (e) { setError(e); }
    finally { setOcupado(false); }
  };
  return <ModalUsuarios titulo={entrada ? 'Entrada comprada' : 'Comprar entrada'} onCerrar={onCerrar} ocupado={ocupado}>
    {entrada ? <>
      <p role="status">Tu compra se ha completado. También puedes consultar el QR en Mis entradas.</p>
      <h3>{entrada.evento_titulo || eventoTitulo || eventoId}</h3><p>{entrada.evento_fechas} · {entrada.tipo_pase}</p>
      <p>Importe pagado: {entrada.precio_pagado} €</p>
      <EntradaQR entrada={entrada} />
      <button className="btn-primary" onClick={onCerrar}>Terminar</button>
    </> : <>
      <dl className="us-resumen"><dt>Evento</dt><dd>{eventoTitulo || eventoId}</dd>
        <dt>Pase</dt><dd>{tarifa?.tipo_pase || 'Sin seleccionar'}</dd>
        <dt>Total</dt><dd>{tarifa?.precio ?? '—'} €</dd></dl>
      {cargando ? <p role="status">Cargando sesión…</p> : rol !== 'cliente'
        ? <p role="alert">Inicia sesión como cliente desde MI PERFIL para comprar una entrada.</p>
        : perfil?.activo === false ? <p role="alert">Tu cuenta está desactivada.</p>
          : !puedeComprar && <p role="alert">No quedan entradas de esta tarifa o no se ha seleccionado un pase.</p>}
      <form onSubmit={comprar}>
        <label className="us-campo">Token de pago<input required value={token}
          onChange={(e) => setToken(e.target.value)} disabled={ocupado || !puedeComprar} /></label>
        <p className="us-ayuda">Pago de prueba: usa tok_ok para aceptar o tok_rechazado para simular un rechazo. No introduzcas datos de tarjeta.</p>
        <AvisoUsuarios error={error} />
        <button className="btn-primary" disabled={ocupado || cargando || !puedeComprar || !token.trim()}>
          {ocupado ? 'Procesando compra…' : 'Confirmar compra'}
        </button>
      </form>
    </>}
  </ModalUsuarios>;
}
