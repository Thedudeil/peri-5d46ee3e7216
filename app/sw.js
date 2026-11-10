// peri-v46: consent branch rebased onto origin/main 54c70e8 (peri-v45 / PT-056/057).
// OPT: files precached only if they exist. consent.js ships on this branch; a 404 inside
// cache.addAll would fail the whole install, so each OPT file is cached on its own and a failure is skipped.
const OPT=['../consent.js'];
const C='peri-v46',A=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png','icon-512-maskable.png','icon-180.png','../privacy.html','../health-data.html','../terms.html','../accessibility.html','fonts/fraunces-latin.woff2','fonts/nunito-latin.woff2'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(A).then(()=>Promise.all(OPT.map(u=>c.add(u).catch(()=>{}))))))});
self.addEventListener('message',e=>{if(e.data&&e.data.type==='SKIP_WAITING')self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x.startsWith('peri-')&&x!==C).map(x=>caches.delete(x)))));self.clients.claim()});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;{const u=new URL(e.request.url);if(u.origin!==location.origin)return}e.respondWith(fetch(e.request).then(r=>{const cp=r.clone();caches.open(C).then(c=>c.put(e.request,cp));return r}).catch(()=>caches.match(e.request,{ignoreSearch:true})))});
self.addEventListener('notificationclick',e=>{e.notification.close();e.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(l=>{for(const c of l){if('focus' in c)return c.focus()}return clients.openWindow('./')}))});
