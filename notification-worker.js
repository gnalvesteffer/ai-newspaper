// Notifications only: do not intercept or cache application/API requests.
self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('message', event => {
  if (event.data?.type !== 'TASK_NOTIFICATION' || !event.source?.id) return;
  event.waitUntil((async () => {
    const client = await self.clients.get(event.source.id);
    if (!client || (client.focused && client.visibilityState === 'visible')) return;
    const {title, options} = event.data;
    await self.registration.showNotification(title, {...options, data: {...options.data, clientId: client.id}});
  })());
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil((async () => {
    const client = await self.clients.get(event.notification.data?.clientId);
    if (client) {
      await client.focus();
      client.postMessage({type: 'OPEN_TASK', target: event.notification.data?.target, editionId: event.notification.data?.editionId});
    }
  })());
});
