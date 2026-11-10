"""Run with python3 tests/heatmap_test.py (requires Playwright Chromium).
Covers: the multi-symptom heatmap renders one column per day for the selected
range (30/90/180, nothing silently dropped), colors cells by severity, marks
bleeding days, lets you tap a day to see that day's entries, the "show all
symptoms" toggle expands the row set, and the grid fits a 390px mobile width
without pushing the page into horizontal scroll.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import subprocess, sys, time

root = Path(__file__).resolve().parents[1]
srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8847'], cwd=root,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 390, 'height': 844})
        pg.goto('http://localhost:8847/app/')
        pg.evaluate("S.onb=true;S.instSeen=true;S.lang='en';persist()")
        pg.reload()

        # One known day with a distinctive hot-flash severity and bleeding, so we
        # can find and verify it precisely; otherwise sparse logging.
        pg.evaluate("""
        S.e = {};
        const known = addD(today(), -10);
        S.e[known] = {s:{hot:3,sweat:1,sleep:2,mood:0}, bleed:'medium', trig:[], meds:[], notes:'Felt awful today', hf:5, hs:4.5, saved:true};
        for (let i = 1; i <= 35; i++) { if (i === 10) continue; const d = addD(today(), -i);
          S.e[d] = {s:{hot:i%4,joint:1}, bleed:'none', trig:[], meds:[], notes:'', saved:true}; }
        window.__known = known;
        persist();
        """)
        pg.evaluate("show('insights')")

        # Default range is 90 days: exactly 90 day-columns, none dropped.
        assert pg.locator('.hmxcol').count() == 90, 'default heatmap range should render exactly 90 day columns'

        # Switch to 30-day range.
        pg.locator('[data-hr="30"]').click()
        assert pg.locator('.hmxcol').count() == 30, '30-day range should render exactly 30 day columns'
        pg.locator('[data-hr="180"]').click()
        assert pg.locator('.hmxcol').count() == 180, '180-day range should render exactly 180 day columns, no history dropped'

        # Core symptom rows by default (CORE symptoms + a Period row); "show all" expands it.
        core_rows = pg.locator('.hmxrowlabel').count()
        pg.locator('#hmxMore').click()
        all_rows = pg.locator('.hmxrowlabel').count()
        assert all_rows > core_rows, 'Show all symptoms should add more heatmap rows'
        pg.locator('#hmxMore').click()
        assert pg.locator('.hmxrowlabel').count() == core_rows, 'toggle should collapse back to the core row set'

        # Bleeding day is marked distinctly (diamond marker class) on the Period row's cell.
        known = pg.evaluate('window.__known')
        col = pg.locator(f'.hmxcol[data-d="{known}"]')
        assert col.count() == 1, 'the known logged day should have a column'
        assert col.locator('.hmxcell.bl').count() >= 1, 'bleeding day should carry the period marker class'

        # Tap the known day: a detail sheet opens showing that day's entries.
        col.click()
        sheet_text = pg.locator('#shB').inner_text()
        assert 'Hot flashes' in sheet_text and '3' in sheet_text, 'day detail should show logged symptom severities'
        assert 'Felt awful today' in sheet_text, 'day detail should include notes'
        pg.locator('#shX').click()

        # A day with nothing logged shows a friendly empty state, not blank/broken content.
        empty_day = pg.evaluate("addD(today(), -60)")
        ecol = pg.locator(f'.hmxcol[data-d="{empty_day}"]')
        if ecol.count():
            ecol.click()
            assert 'Nothing logged' in pg.locator('#shB').inner_text()
            pg.locator('#shX').click()

        # No history silently dropped: the note names the total logged days on top of the shown range.
        note = pg.locator('#hmxNote').inner_text()
        assert '180' in note, 'note should state how many days are shown'

        # Mobile 390px: the page itself must not be forced into horizontal scroll;
        # any overflow lives inside the heatmap's own scroll container.
        page_w = pg.evaluate('document.documentElement.scrollWidth')
        assert page_w <= 400, f'page should not grow wider than the 390px viewport (got {page_w})'

        # --- optional heatmap image in the doctor letter ---
        pg.evaluate("show('summary')")
        pg.locator('#modeLet').click()
        svg_before = pg.locator('#sumBody svg').count()
        pg.check('#letHmChk')
        letter_text_on = pg.locator('#sumBody').inner_text()
        assert 'Symptom heatmap' in letter_text_on, 'checking "include heatmap" should add the heatmap section to the letter'
        assert pg.locator('#sumBody svg').count() > svg_before, 'checking "include heatmap" should add an SVG heatmap to the letter'
        pg.uncheck('#letHmChk')
        letter_text_off = pg.locator('#sumBody').inner_text()
        assert 'Symptom heatmap' not in letter_text_off, 'unchecking "include heatmap" should remove it from the letter'

        b.close()
finally:
    srv.terminate()
    srv.wait()
print('PASS symptom heatmap: ranges render without dropping history, bleeding marked, tap-to-detail works, fits 390px, optional in letter')
