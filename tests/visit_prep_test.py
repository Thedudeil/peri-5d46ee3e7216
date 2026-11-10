"""Run with python3 tests/visit_prep_test.py (requires Playwright Chromium).
Covers: visit-prep observations are derived from the user's own before/after logs,
phrased neutrally; adding one pushes it into the doctor-letter questions list;
custom questions can be edited, reordered and deleted; blank/too-long/duplicate
questions are rejected.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import subprocess, sys, time

root = Path(__file__).resolve().parents[1]
srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8846'], cwd=root,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 390, 'height': 844})
        pg.goto('http://localhost:8846/app/')
        pg.evaluate("S.onb=true;S.instSeen=true;S.lang='en';persist()")
        pg.reload()

        # Visit date = 20 days ago. The app compares a symmetric before/after window
        # around it (21 days each side here, since today-vd+1 == 21). Seed the
        # "before" window (today-41..today-21) with no symptoms, and the "after"
        # window (today-20..today) with frequent hot flashes/night sweats plus a
        # supplement first taken right at the visit date, so both a frequency
        # observation and a new-supplement observation should be generated.
        pg.evaluate("""
        (function(){
          const vd = addD(today(), -20);
          for (let i = 41; i >= 21; i--) {
            const d = addD(today(), -i);
            S.e[d] = {s:{hot:0,sweat:0,sleep:0,mood:0}, bleed:'none', trig:[], meds:[], notes:'', saved:true};
          }
          for (let i = 20; i >= 0; i--) {
            const d = addD(today(), -i);
            S.e[d] = {s:{hot:2,sweat:2,sleep:1,mood:1}, bleed:'none', trig:[], meds:['Magnesium'], notes:'', saved:true};
          }
          S.meds = ['Magnesium'];
          window.__vd = vd;
          persist();
        })()
        """)
        pg.evaluate("show('summary')")

        # Set the visit date in the picker and read the generated observations.
        vd = pg.evaluate('window.__vd')
        pg.fill('#vpDate', vd)
        pg.locator('#vpDate').dispatch_event('change')

        obs_text = pg.locator('#vpOut').inner_text()
        assert 'day' in obs_text.lower() or 'week' in obs_text.lower(), 'no frequency observation rendered: ' + obs_text
        assert '?' in obs_text, 'observations should be phrased as neutral questions'
        assert 'diagnos' not in obs_text.lower() and 'you have' not in obs_text.lower(), 'must not use diagnostic language'

        n_before = len(pg.evaluate("S.qc||[]"))
        pg.locator('.vpAddBtn').first.click()
        n_after = len(pg.evaluate("S.qc||[]"))
        assert n_after == n_before + 1, 'adding a suggestion should push exactly one custom question'
        added_text = pg.evaluate("S.qc[S.qc.length-1]")
        assert added_text, 'added question text should be non-empty'

        # The added question must appear in the printed "Questions for my doctor" letter section.
        pg.locator('#modeLet').click()
        letter_text = pg.locator('#sumBody').inner_text()
        assert added_text in letter_text, 'added visit-prep question missing from the letter'

        # --- custom question validation: blank / too long / duplicate rejected ---
        qc_len = len(pg.evaluate("S.qc||[]"))
        pg.fill('.qIn', '   ')
        pg.locator('.qAdd').click()
        assert len(pg.evaluate("S.qc||[]")) == qc_len, 'blank question must be rejected'

        # The .qIn field also has maxlength=200 in the HTML itself, so a 201-char
        # string can't actually be typed into it via the UI; verify the JS
        # validator independently rejects over-length text (defense in depth).
        too_long_err = pg.evaluate("qcValidate('x'.repeat(201), null)")
        assert too_long_err, 'qcValidate should reject text over 200 characters'

        pg.fill('.qIn', added_text)
        pg.locator('.qAdd').click()
        assert len(pg.evaluate("S.qc||[]")) == qc_len, 'duplicate question must be rejected'

        pg.fill('.qIn', 'A brand new question for my doctor')
        pg.locator('.qAdd').click()
        assert len(pg.evaluate("S.qc||[]")) == qc_len + 1, 'valid new question should be accepted'

        # --- edit, reorder, delete on the custom list ---
        before_order = pg.evaluate("S.qc.slice()")
        pg.locator('[data-qup]').last.click()  # move the last item up
        after_order = pg.evaluate("S.qc.slice()")
        assert after_order != before_order, 'reorder (move up) should change S.qc order'
        assert sorted(after_order) == sorted(before_order), 'reorder must not add/remove items'

        pg.locator('[data-qe]').first.click()
        pg.fill('.qEditIn', 'An edited question text')
        pg.locator('[data-qse]').first.click()
        assert 'An edited question text' in pg.evaluate("S.qc||[]"), 'edit should update the question text in place'

        del_len = len(pg.evaluate("S.qc||[]"))
        pg.once('dialog', lambda d: d.accept())
        pg.locator('[data-cx]').first.click()
        assert len(pg.evaluate("S.qc||[]")) == del_len - 1, 'delete should remove exactly one question'

        b.close()
finally:
    srv.terminate()
    srv.wait()
print('PASS visit prep: data-driven observations, add-to-letter, and edit/reorder/delete/validate on custom questions')
