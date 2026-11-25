// Service worker de las notificaciones de usuarios. Dueño: Luis.
// Recibe únicamente la configuración PÚBLICA de la aplicación web, nunca la cuenta de servicio.
const parametros = new URL(self.location.href).searchParams;
const version = parametros.get('sdk');
const configuracion = JSON.parse(parametros.get('config'));
if (!/^\d+\.\d+\.\d+$/.test(version) || !configuracion?.projectId) throw new Error('Configuración de notificaciones inválida');
self.addEventListener('notificationclick', (evento) => {
  evento.notification.close();
  evento.stopImmediatePropagation();
  evento.waitUntil(self.clients.openWindow('/perfil'));
});
self.importScripts(`https://www.gstatic.com/firebasejs/${version}/firebase-app-compat.js`);
self.importScripts(`https://www.gstatic.com/firebasejs/${version}/firebase-messaging-compat.js`);
self.firebase.initializeApp(configuracion);
self.firebase.messaging().onBackgroundMessage((mensaje) => {
  // Los mensajes con notification ya los muestra el SDK; no duplicarlos.
  if (mensaje.notification) return;
  return self.registration.showNotification(mensaje.data?.titulo || 'Subsonic Festival', {
    body: mensaje.data?.cuerpo || 'Tienes novedades en tu perfil.',
    icon: '/SubsonicIcon.svg', tag: mensaje.messageId,
  });
});
