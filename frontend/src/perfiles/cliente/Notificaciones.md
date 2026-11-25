# Notificaciones · Luis

Las preferencias y el alta/baja del dispositivo usan exclusivamente `src/api/usuarios.js`.
El botón de prueba permite comprobar el flujo con David y los avisos del backend local sin Firebase.

Para el registro real del navegador, añadir en el `.env` local la clave **pública** web push del proyecto:

```dotenv
VITE_FIREBASE_VAPID_KEY=clave_publica_del_proyecto
```

Reiniciar Vite después de cambiar `.env`. No se usa aquí `firebase-claves.json` ni ninguna clave privada.
La pantalla pide permiso, registra `public/usuarios-notificaciones-sw.js` y obtiene el token con Firebase
Cloud Messaging. La configuración pública y la versión del SDK se toman de la aplicación ya inicializada
por Paula. El service worker no duplica las notificaciones que el SDK muestra automáticamente.

El registro instala la limpieza mediante `alCerrarSesion` de Paula, antes de borrar el token de sesión.
La baja manual o el cambio de token desapuntan la limpieza anterior para no repetirla.
Tras recargar, la limpieza se recupera del registro local y comprueba la identidad de la sesión.
Si falla la baja, se conserva el registro para poder reintentar; el enganche de sesión limita la espera a 3 s.
La función se puede probar con `dispositivoPush.test.js`. Registrar un navegador no activa por sí mismo
el envío FCM del backend: ese envío sigue dependiendo de la configuración del microservicio.
