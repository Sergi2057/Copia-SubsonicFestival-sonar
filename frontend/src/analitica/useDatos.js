// src/analitica/useDatos.js — Dueña: Paula
// Carga datos de la API al pintar la pantalla y cada vez que cambian los argumentos.
//
//   const ventas = useDatos(obtenerVentas, { evento_id, agrupar_por });
//   ventas.cargando · ventas.error (ErrorApi) · ventas.datos · ventas.recargar()
//
// funcion debe ser estable (importada de src/api/… o definida fuera del componente).
// Si funcion es null no se pide nada (p. ej. mientras no hay evento elegido).
import { useEffect, useState } from 'react';
import { listarEventos } from '../api/espacios';

export function useDatos(funcion, ...argumentos) {
  const [intento, setIntento] = useState(0);
  const [resultado, setResultado] = useState({ clave: null, datos: null, error: null });
  // La clave identifica la petición: si cambia, lo guardado es de otra petición y se está cargando
  const clave = JSON.stringify([argumentos, intento]);

  useEffect(() => {
    if (!funcion) return undefined;
    let vigente = true;
    const [args] = JSON.parse(clave);
    funcion(...args).then(
      (datos) => vigente && setResultado({ clave, datos, error: null }),
      (error) => vigente && setResultado({ clave, datos: null, error }),
    );
    return () => { vigente = false; };
  }, [funcion, clave]);

  const actual = funcion !== null && resultado.clave === clave;
  return {
    cargando: funcion !== null && !actual,
    datos: actual ? resultado.datos : null,
    error: actual ? resultado.error : null,
    recargar: () => setIntento((n) => n + 1),
  };
}

const cargarEventos = () => listarEventos({ limite: 100 }).then(({ datos }) => datos);

/** Eventos de ms-espacios para los selectores: { cargando, error, datos: [{ id, titulo, … }] }. activo=false: no los pide. */
export const useEventos = (activo = true) => useDatos(activo ? cargarEventos : null);
