# Migration test (landing-1104): app moves from / to /app/, landing page at /.
# 1) serve the OLD root-app build (f60b31d / peri-v27) at /, open it, let its root SW (scope /) install, seed data;
# 2) swap the served files to the NEW build (working tree) on the SAME origin;
# 3) check: landing renders at /, old root SW is retired and old peri-v27 cache deleted, data (same KEY) shows in /app/,
#    /app/ SW has scope /app/, standalone launches of / and ?source=pwa redirect to /app/, legal + /nights + /strong load,
#    no console errors. Run: python3 /workspace/peri-kit/app/tests/migration_test.py
from playwright.sync_api import sync_playwright
import sys, os, subprocess, time, shutil, tempfile, json
HERE = os.path.dirname(os.path.abspath(__file__))
DEPLOY = os.path.normpath(os.path.join(HERE, ".."))
OLD_REF = os.environ.get("OLD_REF", "f60b31d")  # last root-app build (peri-v27); origin/main is already /app/
PORT = int(os.environ.get("MIG_PORT", "8830")); BASE = f"http://localhost:{PORT}"
tmp = tempfile.mkdtemp(prefix="mig-"); SITE = os.path.join(tmp, "site"); os.makedirs(SITE)
def load_old():
    subprocess.run(f"git -C {DEPLOY} archive {OLD_REF} | tar -x -C {SITE}", shell=True, check=True)
def load_new():
    for n in os.listdir(SITE):
        q = os.path.join(SITE, n); shutil.rmtree(q) if os.path.isdir(q) else os.remove(q)
    shutil.copytree(DEPLOY, SITE, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
load_old()
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
fails = []; errs = []
def ck(c, m):
    if not c: fails.append(m)
def watch(pg, tag):
    pg.on("pageerror", lambda e: errs.append(f"[{tag}] pageerror {e}"))
    pg.on("console", lambda m: m.type == "error" and errs.append(f"[{tag}] console {m.text}"))
ENTRIES = {"2026-10-20": {"s": {"hot": 2, "sleep": 1}}, "2026-10-21": {"s": {"hot": 3}}, "2026-10-22": {"s": {"hot": 1, "mood": 2}}}
try:
  with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={"width": 390, "height": 844}); pg = ctx.new_page(); watch(pg, "old")
    # --- old live app at / ---
    pg.goto(BASE + "/"); pg.wait_for_function("navigator.serviceWorker.controller!==null || (location.reload(), false)", timeout=15000) if False else None
    pg.wait_for_function("navigator.serviceWorker.ready.then(()=>true)", timeout=15000)
    pg.reload(); pg.wait_for_function("!!navigator.serviceWorker.controller", timeout=15000)
    old_key = pg.evaluate("KEY"); ck(old_key == "periTracker.v1", f"old KEY unexpected: {old_key}")
    pg.evaluate("S.onb=true;S.lang='en';S.t0='2026-10-01';S.me='Mig Test';S.e=" + json.dumps(ENTRIES) + ";persist()")
    old_scope = pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>new URL(r.scope).pathname)")
    ck(old_scope == "/", f"old SW scope {old_scope}")
    ck(pg.evaluate("caches.keys()").count("peri-v27") == 1, "old peri-v27 cache missing before migration")
    seeded = pg.evaluate("localStorage.getItem('periTracker.v1')")
    # --- deploy new build on the same origin ---
    load_new()
    new_key = open(os.path.join(DEPLOY, "app", "index.html")).read()
    ck('const KEY="periTracker.v1";' in new_key, "new app KEY changed")
    pg.goto(BASE + "/"); pg.wait_for_timeout(1500); pg.goto(BASE + "/"); pg.wait_for_timeout(1500)
    ck(pg.locator("h1").inner_text().startswith("Less guessing."), "landing h1 not rendered at /")
    ck(pg.locator("#back").is_visible(), "returning-user 'Welcome back' link not shown")
    ck(pg.evaluate("typeof S") == "undefined", "old app still served at /")
    regs = pg.evaluate("navigator.serviceWorker.getRegistrations().then(rs=>rs.map(r=>new URL(r.scope).pathname))")
    ck("/" not in regs, f"root SW still registered: {regs}")
    ck("peri-v27" not in pg.evaluate("caches.keys()"), "old peri-v27 cache not deleted")
    now = json.loads(pg.evaluate("localStorage.getItem('periTracker.v1')") or "{}"); was = json.loads(seeded)
    ck(now.get("e") == was.get("e") and now.get("me") == was.get("me") and now.get("onb") == was.get("onb"), "stored data changed by landing / SW cleanup")
    # --- app at /app/ shows the data ---
    pg.goto(BASE + "/app/"); pg.wait_for_timeout(800)
    ck(pg.evaluate("KEY") == "periTracker.v1", "app KEY changed")
    ck(pg.evaluate("Object.keys(S.e).sort().join(',')") == ",".join(sorted(ENTRIES)), "seeded entries missing in /app/")
    ck(pg.evaluate("S.me") == "Mig Test" and pg.evaluate("S.onb") is True, "seeded settings missing in /app/")
    ck(pg.locator("#onb").count() == 0 or not pg.locator("#onb").is_visible(), "onboarding shown again in /app/")
    pg.wait_for_function("navigator.serviceWorker.getRegistration('/app/').then(r=>!!(r&&r.active))", timeout=15000)
    sc = pg.evaluate("navigator.serviceWorker.getRegistration('/app/').then(r=>new URL(r.scope).pathname)")
    ck(sc == "/app/", f"app SW scope {sc}")
    ck("peri-v47" in pg.evaluate("caches.keys()"), "peri-v47 cache not created")
    pg.reload(); pg.wait_for_timeout(800)
    ck(pg.evaluate("!!navigator.serviceWorker.controller"), "app not controlled by /app/ SW after reload")
    man = pg.evaluate("fetch('manifest.webmanifest').then(r=>r.json())")
    ck(man["start_url"] == "/app/" and man["scope"] == "/app/", f"manifest {man.get('start_url')} {man.get('scope')}")
    # landing again while /app/ SW exists: still landing, and app cache survives
    pg.goto(BASE + "/"); pg.wait_for_timeout(800)
    ck(pg.locator("h1").count() == 1 and pg.evaluate("typeof S") == "undefined", "landing not shown after /app/ visit")
    ck("peri-v47" in pg.evaluate("caches.keys()"), "landing cleanup deleted peri-v47")
    # --- standalone / PWA launches of the old start_url ---
    pg.goto(BASE + "/?source=pwa"); pg.wait_for_url("**/app/**", timeout=5000)
    ck(pg.evaluate("Object.keys(S.e).length") == 3, "?source=pwa did not land in app with data")
    for tag, init in [("display-mode", "const _m=window.matchMedia.bind(window);window.matchMedia=q=>/display-mode: *standalone/.test(q)?{matches:true,media:q,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}}:_m(q);"),
                      ("navigator.standalone", "Object.defineProperty(navigator,'standalone',{get:()=>true});")]:
        c2 = b.new_context(viewport={"width": 390, "height": 844}); c2.add_init_script(init); p2 = c2.new_page(); watch(p2, tag)
        p2.goto(BASE + "/"); p2.wait_for_url("**/app/**", timeout=5000)
        ck(p2.url.rstrip("/").endswith("/app"), f"{tag}: not redirected ({p2.url})"); c2.close()
    # --- other paths still work, legal pages link from footer ---
    for path in ["/nights/", "/strong/", "/privacy.html", "/health-data.html", "/terms.html", "/accessibility.html", "/manifest.webmanifest", "/sw.js", "/app/sw.js", "/app/manifest.webmanifest"]:
        r = pg.request.get(BASE + path); ck(r.status == 200, f"{path} -> {r.status}")
    pg.goto(BASE + "/")
    hrefs = pg.evaluate("[...document.querySelectorAll('footer a')].map(a=>a.getAttribute('href'))")
    for h in ["/privacy.html", "/health-data.html", "/terms.html", "/accessibility.html", "/app/"]:
        ck(h in hrefs, f"footer missing {h}")
    imgs = pg.evaluate("Promise.all([...document.images].map(i=>(i.loading='eager',i.decode().then(()=>i.naturalWidth).catch(()=>0))))")
    ck(all(imgs), f"broken landing images: {imgs}")
    html = pg.content().lower(); text = pg.locator("body").inner_text().lower()
    for bad in ["free forever", "nothing uploaded", "checkout", "whop.com", "$", "gtag", "fbq(", "pixel.", "googletagmanager"]:
        ck(bad not in (text if bad == "$" else html), f"landing contains forbidden '{bad}'")
    # legal page 'Open the app' goes to /app/
    pg.goto(BASE + "/privacy.html"); pg.reload(); ck(  # reload: revalidate the HTTP-cached pre-migration copy
        pg.evaluate("[...document.querySelectorAll('footer a')].some(a=>a.textContent==='Open the app'&&new URL(a.href).pathname==='/app/')"), "privacy 'Open the app' not /app/")
    pg.goto(BASE + "/app/"); pg.wait_for_timeout(500)
    links = pg.evaluate("[...document.querySelectorAll('ul.legal a')].map(a=>new URL(a.href).pathname)")
    for l in links:
        ck(pg.request.get(BASE + l).status == 200, f"app legal link {l} broken")
    ck(len(links) == 4, f"app legal links {links}")
    b.close()
finally:
    srv.terminate(); shutil.rmtree(tmp, ignore_errors=True)
if errs: fails.append("console/page errors:\n  " + "\n  ".join(errs))
print("PASS" if not fails else "FAIL\n" + "\n".join(fails)); sys.exit(1 if fails else 0)
