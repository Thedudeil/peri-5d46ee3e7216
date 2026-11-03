const C='nights-v3',A=['./','index.html','manifest.webmanifest','icon.svg','icon-180.png','icon-192.png','icon-512.png','privacy.html','terms.html','fonts/fraunces-latin.woff2','fonts/caveat-latin.woff2','fonts/nunito-latin.woff2'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(A)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x.startsWith('nights-')&&x!==C).map(x=>caches.delete(x)))));self.clients.claim()});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)))});
