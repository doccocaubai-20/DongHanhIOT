'use strict';
// Service worker chỉ nhận thông báo đẩy; không lưu cache dữ liệu hay ảnh riêng tư.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));

self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch { data = {body: event.data ? event.data.text() : ''}; }
  const sos = data.level === 'sos';
  event.waitUntil(self.registration.showNotification(data.title || 'Đồng Hành', {
    body: data.body || '', tag: data.tag, renotify: true, requireInteraction: sos,
    icon: 'icon-192.png', badge: 'icon-192.png', vibrate: sos ? [400, 200, 400, 200, 400] : [200],
    data: {url: data.url || '/'},
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = new URL(event.notification.data?.url || '/', self.location.origin).href;
  event.waitUntil((async () => {
    for (const client of await self.clients.matchAll({type: 'window', includeUncontrolled: true})) {
      if (new URL(client.url).origin === self.location.origin) {
        await client.focus();
        if ('navigate' in client) await client.navigate(url);
        return;
      }
    }
    await self.clients.openWindow(url);
  })());
});
