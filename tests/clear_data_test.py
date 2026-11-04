# QA test: "Clear all data" removes everything except onb, lang, plus, t0 (Legal HIGH 1).
# Run: python3 -m http.server 8799 (in deploy/) then python3 tests/clear_data_test.py
from playwright.sync_api import sync_playwright
import json, sys
U = "http://localhost:8799/index.html"; fails = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept())
    pg.goto(U); pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(600)
    pg.evaluate("""S.onb=true;S.lang='en';S.t0='2026-10-01';S.plus='PLUS-TEST';S.me='Jane Doe';S.dr='Dr Smith';
      S.remOn=true;S.remT='20:00';S.e={'2026-10-02':{s:{hot:2}}};S.hrt=[{id:'h1',d:'2026-10-01',x:'Estradiol patch'}];
      S.mrs=[{d:'2026-10-02',a:[1,1,1,1,1,1,1,1,1,1,1]}];persist();scheduleReminder();""")
    pg.reload(); pg.wait_for_timeout(600)
    pg.evaluate("document.getElementById('clearBtn').click()"); pg.wait_for_timeout(300)
    s = pg.evaluate("JSON.parse(localStorage.getItem(KEY))")
    timer = pg.evaluate("remTimer")
    for k in ["dr", "me", "hrt", "mrs", "remT"]:
        if k in s: fails.append(f"{k} still present: {s[k]!r}")
    if s.get("e"): fails.append("entries not cleared")
    if s.get("remOn"): fails.append("remOn still on")
    if timer is not None: fails.append("reminder timer not cancelled")
    if s.get("t0") != "2026-10-01": fails.append(f"t0 changed: {s.get('t0')!r}")
    if s.get("plus") != "PLUS-TEST": fails.append("plus code not kept")
    if s.get("lang") is None or not s.get("onb"): fails.append("lang/onb not kept")
    if errs: fails.append("page errors: " + "; ".join(errs))
    print("state after clear:", json.dumps(s)); b.close()
print("PASS" if not fails else "FAIL\n" + "\n".join(fails)); sys.exit(1 if fails else 0)
