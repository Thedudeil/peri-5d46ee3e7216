"""Reminder discovery offer and missed-today banner (reminder-offer-1113).

Covers: offer after the first successful save; no reappearance after
dismissal; at-most-one re-offer on the 3rd check-in day; Notification
granted / denied / unsupported (mocked); missed-today banner show/hide;
Hebrew RTL. Run: python3 tests/reminder_offer_test.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import subprocess, sys, time, json

ROOT = Path(__file__).resolve().parents[1]
PORT = 8871
BASE = f"http://127.0.0.1:{PORT}"
fails = []

def ck(c, m):
    if not c:
        fails.append(m)
        print("  FAIL", m)
    else:
        print("  PASS", m)

NOTIF_INIT = """
window.__notif = {permission: window.__notifPerm || 'default', next: window.__notifNext || 'granted'};
class MockN {
  constructor(title, opts){ MockN.last = {title, opts}; }
  static get permission(){ return window.__notif.permission; }
  static requestPermission(){
    return Promise.resolve(window.__notif.next).then(p => { window.__notif.permission = p; return p; });
  }
}
window.Notification = MockN;
"""

UNSUP_INIT = """
window.Notification = undefined;
"""

def evening(hour=21, minute=0):
    return f"""(() => {{
      const d = new Date();
      d.setHours({hour},{minute},0,0);
      window.__remNow = d.getTime();
    }})()"""

def boot(pg, extra=""):
    pg.evaluate(f"""() => {{
      S.onb = true; S.instSeen = true; S.lang = 'en'; S.remOn = false;
      delete S.remOffer; delete S.remBanDis; delete S.remT; delete S.remLast;
      S.e = {{}};
      {extra}
      persist();
    }}""")
    pg.reload(wait_until="domcontentloaded")
    pg.wait_for_timeout(250)

def save_today(pg):
    pg.evaluate("cur = today(); show('today')")
    pg.wait_for_timeout(100)
    pg.locator("#saveBtn").click()
    pg.wait_for_timeout(300)

def offer_visible(pg):
    return pg.locator("#remOffer").count() > 0

def banner_visible(pg):
    return pg.locator("#missedBan").count() > 0

srv = subprocess.Popen(
    [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
    cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
time.sleep(0.6)

try:
    with sync_playwright() as p:
        b = p.chromium.launch()

        # ---- 1. Offer after first save; not before ----
        print("======= first save =======")
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        ctx.add_init_script(NOTIF_INIT)
        pg = ctx.new_page()
        pg.goto(BASE + "/app/", wait_until="domcontentloaded")
        boot(pg)
        ck(not offer_visible(pg), "no offer before any save")
        save_today(pg)
        ck(offer_visible(pg), "offer appears after first save")
        ck(pg.locator("#remOfferT").inner_text() == "Want a gentle reminder each evening?",
           "offer title EN: " + pg.locator("#remOfferT").inner_text() if offer_visible(pg) else "missing")
        ck(pg.locator("#remOfferOn").inner_text() == "Turn on reminder", "primary button EN")
        ck(pg.locator("#remOfferIcs").inner_text() == "Add to my calendar instead", "ICS button EN")
        ck(pg.locator("#remOfferNo").inner_text() == "No thanks", "No thanks EN")
        ck("Home Screen" in pg.locator("#remOfferNote").inner_text() and "16.4" in pg.locator("#remOfferNote").inner_text(),
           "short honest note mentions Home Screen and iOS 16.4")
        ck(pg.locator("#remOfferTime").input_value() == "20:30", "time defaults to 20:30")
        ck(pg.evaluate("S.remOffer") in (None, "undefined") or pg.evaluate("S.remOffer") is None,
           "dismissal not stored until she answers: " + str(pg.evaluate("S.remOffer")))

        # ---- 2. Dismissal: No thanks, does not reappear same / second day ----
        print("======= first dismissal =======")
        pg.locator("#remOfferNo").click()
        pg.wait_for_timeout(200)
        ck(not offer_visible(pg), "offer hides after No thanks")
        ck(pg.evaluate("S.remOffer") == "later", "first No thanks stores remOffer=later")
        pg.evaluate("show('today')")
        pg.wait_for_timeout(150)
        ck(not offer_visible(pg), "offer does not return on same day after No thanks")
        # second check-in day
        pg.evaluate("() => { const d = addD(today(), -1); S.e[d] = {s:{}, bleed:'none', trig:[], meds:[], notes:'', saved:true}; persist(); show('today') }")
        pg.wait_for_timeout(150)
        ck(pg.evaluate("realDays().length") == 2, "two saved days")
        ck(not offer_visible(pg), "no offer on the 2nd check-in day")

        # ---- 3. Re-offer on 3rd day, then never again ----
        print("======= day-3 re-offer =======")
        pg.evaluate("() => { const d = addD(today(), -2); S.e[d] = {s:{}, bleed:'none', trig:[], meds:[], notes:'', saved:true}; persist(); show('today') }")
        pg.wait_for_timeout(200)
        ck(pg.evaluate("realDays().length") >= 3, "three saved days")
        ck(offer_visible(pg), "offer returns after the 3rd check-in day")
        pg.locator("#remOfferNo").click()
        pg.wait_for_timeout(200)
        ck(not offer_visible(pg), "offer hides after second No thanks")
        ck(pg.evaluate("S.remOffer") == "done", "second No thanks stores remOffer=done")
        pg.evaluate("() => { const d = addD(today(), -3); S.e[d] = {s:{}, bleed:'none', trig:[], meds:[], notes:'', saved:true}; persist(); show('today') }")
        pg.wait_for_timeout(150)
        ck(not offer_visible(pg), "no offer on a 4th day after final dismissal")
        ctx.close()

        # ---- 4. Permission granted ----
        print("======= permission granted =======")
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        ctx.add_init_script(NOTIF_INIT)
        pg = ctx.new_page()
        pg.goto(BASE + "/app/", wait_until="domcontentloaded")
        boot(pg)
        save_today(pg)
        ck(offer_visible(pg), "offer present for grant path")
        pg.locator("#remOfferTime").fill("21:15")
        pg.locator("#remOfferOn").click()
        pg.wait_for_timeout(400)
        state = pg.evaluate("() => ({on:S.remOn, t:S.remT, offer:S.remOffer, vis:!!document.getElementById('remOffer'), perm:Notification.permission})")
        ck(state["on"] is True, f"remOn true after grant: {state}")
        ck(state["t"] == "21:15", f"time saved from picker: {state}")
        ck(state["offer"] == "done", f"offer marked done after grant: {state}")
        ck(not state["vis"], "offer hidden after grant")
        # does not reappear
        pg.evaluate("show('today')")
        pg.wait_for_timeout(100)
        ck(not offer_visible(pg), "no offer after reminder is on")
        ctx.close()

        # ---- 5. Permission denied: calendar-only + remDenied ----
        print("======= permission denied =======")
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        ctx.add_init_script("window.__notifPerm='default'; window.__notifNext='denied';")
        ctx.add_init_script(NOTIF_INIT)
        pg = ctx.new_page()
        pg.goto(BASE + "/app/", wait_until="domcontentloaded")
        boot(pg)
        save_today(pg)
        ck(pg.locator("#remOfferOn").count() == 1, "Turn on is shown while permission is still default")
        pg.locator("#remOfferOn").click()
        pg.wait_for_timeout(400)
        st = pg.evaluate("""() => ({
          on:S.remOn, offer:S.remOffer, vis:!!document.getElementById('remOffer'),
          hasOn:!!document.getElementById('remOfferOn'),
          hasIcs:!!document.getElementById('remOfferIcs'),
          note:(document.getElementById('remOfferNote')||{}).innerText||'',
          perm:Notification.permission
        })""")
        ck(st["on"] is False, f"remOn stays false when denied: {st}")
        ck(st["vis"] and not st["hasOn"] and st["hasIcs"], f"calendar-only after deny: {st}")
        ck("blocked" in st["note"].lower() or "allow them" in st["note"].lower(),
           f"remDenied text shown: {st['note'][:120]}")
        ck(st["offer"] != "done", "denying the prompt does not dismiss the offer for good")
        ctx.close()

        # ---- 6. Unsupported: calendar-only + remUnsup, no Turn on ----
        print("======= unsupported =======")
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        ctx.add_init_script(UNSUP_INIT)
        pg = ctx.new_page()
        pg.goto(BASE + "/app/", wait_until="domcontentloaded")
        boot(pg)
        save_today(pg)
        st = pg.evaluate("""() => ({
          vis:!!document.getElementById('remOffer'),
          hasOn:!!document.getElementById('remOfferOn'),
          hasIcs:!!document.getElementById('remOfferIcs'),
          hasNo:!!document.getElementById('remOfferNo'),
          note:(document.getElementById('remOfferNote')||{}).innerText||''
        })""")
        ck(st["vis"] and not st["hasOn"] and st["hasIcs"] and st["hasNo"], f"unsupported calendar-only: {st}")
        ck("doesn't support" in st["note"].lower() or "does not support" in st["note"].lower() or "calendar reminder" in st["note"].lower(),
           f"remUnsup text shown: {st['note'][:160]}")
        ctx.close()

        # ---- 7. Banner shows after 18:00 (no reminder), hides on dismiss and on save ----
        print("======= missed-today banner =======")
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        ctx.add_init_script(NOTIF_INIT)
        pg = ctx.new_page()
        pg.goto(BASE + "/app/", wait_until="domcontentloaded")
        boot(pg)
        # before 18:00, no banner
        pg.evaluate(evening(17, 0))
        pg.evaluate("show('today')")
        pg.wait_for_timeout(150)
        ck(not banner_visible(pg), "no banner before 18:00 when reminder is off")
        # after 18:00, banner
        pg.evaluate(evening(18, 5))
        pg.evaluate("show('today')")
        pg.wait_for_timeout(150)
        ck(banner_visible(pg), "banner shows after 18:00 with no reminder and no entry")
        ck(pg.locator("#missedBan p").inner_text() == "You haven't checked in today", "banner copy EN")
        ck(pg.locator("#missedBanGo").inner_text() == "Check in now", "Check in now EN")
        # Check in now scrolls toward the form
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        pg.wait_for_timeout(100)
        far = pg.evaluate("() => { const f=document.getElementById('checkInForm'); const r=f.getBoundingClientRect(); return r.bottom < 0 || r.top > window.innerHeight; }")
        ck(far, "precondition: form is off-screen before Check in now")
        pg.locator("#missedBanGo").click()
        pg.wait_for_timeout(700)
        form_in_view = pg.evaluate("""() => {
          const f = document.getElementById('checkInForm');
          if (!f) return false;
          const r = f.getBoundingClientRect();
          return r.top < window.innerHeight && r.bottom > 0;
        }""")
        ck(form_in_view, "Check in now brings the form into view")
        # dismiss for the day
        pg.locator("#missedBanX").click()
        pg.wait_for_timeout(200)
        ck(not banner_visible(pg), "banner hides after dismiss")
        ck(pg.evaluate("S.remBanDis === today()"), "dismiss stored for today")
        pg.evaluate("show('today')")
        pg.wait_for_timeout(100)
        ck(not banner_visible(pg), "dismissed banner stays hidden for the day")
        # next "day" would show again — don't fake a date change; instead clear remBanDis and confirm show, then save hides
        pg.evaluate("delete S.remBanDis; persist(); show('today')")
        pg.wait_for_timeout(150)
        ck(banner_visible(pg), "banner returns after dismiss is cleared")
        # hides once she saves
        pg.locator("#saveBtn").click()
        pg.wait_for_timeout(300)
        ck(not banner_visible(pg), "banner hides once today's check-in is saved")

        # with a reminder at 20:30, 19:00 is too early, 20:45 shows
        pg.evaluate("() => { delete S.e[today()]; delete S.remBanDis; S.remOn = true; S.remT = '20:30'; persist(); }")
        pg.evaluate(evening(19, 0))
        pg.evaluate("show('today')")
        pg.wait_for_timeout(150)
        ck(not banner_visible(pg), "no banner at 19:00 when reminder is 20:30")
        pg.evaluate(evening(20, 45))
        pg.evaluate("show('today')")
        pg.wait_for_timeout(150)
        ck(banner_visible(pg), "banner shows after the reminder time")
        ctx.close()

        # ---- 8. Hebrew RTL ----
        print("======= Hebrew RTL =======")
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        ctx.add_init_script(NOTIF_INIT)
        pg = ctx.new_page()
        pg.goto(BASE + "/app/", wait_until="domcontentloaded")
        boot(pg)
        save_today(pg)
        pg.evaluate("() => { LANG = 'he'; S.lang = 'he'; persist(); applyLang(); show('today'); }")
        pg.wait_for_timeout(300)
        he = pg.evaluate("""() => ({
          dir: document.documentElement.dir,
          lang: document.documentElement.lang,
          title: (document.getElementById('remOfferT')||{}).innerText||'',
          ics: (document.getElementById('remOfferIcs')||{}).innerText||'',
          no: (document.getElementById('remOfferNo')||{}).innerText||'',
          note: (document.getElementById('remOfferNote')||{}).innerText||'',
          on: (document.getElementById('remOfferOn')||{}).innerText||'',
          offerDir: document.getElementById('remOffer') ? getComputedStyle(document.getElementById('remOffer')).direction : null
        })""")
        ck(he["dir"] == "rtl" and he["lang"] == "he", f"html dir/lang: {he}")
        ck(he["title"] == "רוצה תזכורת עדינה בכל ערב?", f"HE title: {he['title']}")
        ck(he["ics"] == "להוסיף ליומן במקום", f"HE ICS: {he['ics']}")
        ck(he["no"] == "לא תודה", f"HE no: {he['no']}")
        ck(he["on"] == "הפעלת תזכורת", f"HE turn on (existing remOnB): {he['on']}")
        ck("מסך הבית" in he["note"] and "16.4" in he["note"], f"HE honest note: {he['note']}")
        ck(he["offerDir"] == "rtl", f"offer direction: {he['offerDir']}")
        # banner in Hebrew
        pg.evaluate("() => { delete S.e[today()]; delete S.remBanDis; S.remOn=false; persist(); }")
        pg.evaluate(evening(21, 0))
        pg.evaluate("() => { LANG='he'; applyLang(); show('today'); }")
        pg.wait_for_timeout(250)
        bh = pg.evaluate("""() => ({
          vis: !!document.getElementById('missedBan'),
          text: (document.querySelector('#missedBan p')||{}).innerText||'',
          go: (document.getElementById('missedBanGo')||{}).innerText||'',
          dir: document.getElementById('missedBan') ? getComputedStyle(document.getElementById('missedBan')).direction : null
        })""")
        ck(bh["vis"] and bh["text"] == "עוד לא עשית צ'ק-אין היום", f"HE banner: {bh}")
        ck(bh["go"] == "לצ'ק-אין עכשיו", f"HE check-in now: {bh}")
        ck(bh["dir"] == "rtl", f"banner RTL: {bh}")
        ctx.close()
        b.close()
finally:
    srv.terminate()
    srv.wait()

print("REMINDER_OFFER", "PASS" if not fails else "FAIL")
if fails:
    print("FAILURES:")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("PASS reminder offer, re-offer, permission paths, banner, and Hebrew RTL")
