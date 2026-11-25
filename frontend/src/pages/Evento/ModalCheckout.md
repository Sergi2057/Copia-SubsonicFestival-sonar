# Compra de entradas · integración con la ficha del evento

`ModalCheckout` conserva `abierto`, `onCerrar`, `eventoId` y `tarifa`. Acepta además
`eventoTitulo`, opcional, para mostrar el nombre en el resumen antes de comprar:

```jsx
<ModalCheckout
  abierto={tarifaElegida !== null}
  onCerrar={() => setTarifaElegida(null)}
  eventoId={id}
  eventoTitulo={evento.titulo}
  tarifa={tarifaElegida}
/>
```

La ficha de Pedro puede pasar ese título cuando tenga cargado el evento. Si no lo
pasa, sigue mostrándose `eventoId`. La petición de compra siempre usa `eventoId`;
en la confirmación se da prioridad al título que devuelve el backend.
