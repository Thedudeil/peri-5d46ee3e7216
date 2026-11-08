// Root service worker, retired in peri-v29 (Nov 2026). The app moved to /app/ (its own SW, scope /app/).
// Older installs registered this file with scope "/" and would keep serving the old app over the landing page.
// This version: takes over at once, deletes old root app caches, unregisters itself, and reloads open windows
// so they get the network copy (landing page, which sends home-screen launches on to /app/).
// It never touches localStorage, so her entries (key periTracker.v1, same origin) are untouched.
const KEEP=['peri-v29'];// the /app/ SW's cache; nights-*/strong-* are not peri-* so untouched
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>{e.waitUntil((async()=>{
 const k=await caches.keys();await Promise.all(k.filter(x=>x.startsWith('peri-')&&!KEEP.includes(x)).map(x=>caches.delete(x)));
 await self.registration.unregister();
 const cs=await self.clients.matchAll({type:'window'});
 for(const c of cs){try{const u=new URL(c.url);if(!u.pathname.startsWith('/app/')&&!u.pathname.startsWith('/nights/')&&!u.pathname.startsWith('/strong/'))c.navigate(c.url)}catch(x){}}
})())});
// No fetch handler: everything goes to the network.
