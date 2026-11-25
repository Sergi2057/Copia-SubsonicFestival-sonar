// src/perfiles/useDatosRecargables.js — Dueño: Sergio
// Como useDatos (src/analitica/useDatos.js), pero al recargar conserva los datos anteriores hasta que
// llegan los nuevos: las listas de los paneles no parpadean ni pierden el foco tras guardar algo.
//
//   const productos = useDatosRecargables(cargarProductos, filtro);
//   productos.datos (los últimos que llegaron) · productos.cargando · productos.error · productos.recargar()
//
// funcion debe ser estable (definida fuera del componente). null = no pedir nada.
import { useEffect, useState } from 'react';

export function useDatosRecargables(funcion, ...argumentos) {
  const [intento, setIntento] = useState(0);
  const [resultado, setResultado] = useState({ clave: null, datos: null, error: null });
  const clave = JSON.stringify([argumentos, intento]);

  useEffect(() => {
    if (!funcion) return undefined;
    let vigente = true;
    const [args] = JSON.parse(clave);
    funcion(...args).then(
      (datos) => vigente && setResultado({ clave, datos, error: null }),
      (error) => vigente && setResultado((anterior) => ({ clave, datos: anterior.datos, error })),
    );
    return () => { vigente = false; };
  }, [funcion, clave]);

  const actual = funcion !== null && resultado.clave === clave;
  return {
    cargando: funcion !== null && !actual,
    datos: resultado.datos,
    error: actual ? resultado.error : null,
    recargar: () => setIntento((n) => n + 1),
  };
}
