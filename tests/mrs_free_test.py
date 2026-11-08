"""Run with python3 tests/mrs_free_test.py (requires Playwright Chromium)."""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
html=(Path(__file__).resolve().parents[1]/'app/index.html').read_text()
assert not any(re.search(r'MRS|Menopause Rating Scale', text, re.I) for text in re.findall(r'upL[1-5]:"([^"]+)"', html))
assert 'PAYWALL_ENABLED=false' in html and 'LICENSE_SERVER_ENABLED=false' in html
with sync_playwright() as p:
 b=p.chromium.launch()
 pg=b.new_page()
 pg.route('https://mrs.test/**',lambda r:r.fulfill(content_type='text/html',body=html.replace('PAYWALL_ENABLED=false','PAYWALL_ENABLED=true')))
 pg.goto('https://mrs.test/app/')
 pg.evaluate("S.onb=true;S.instSeen=true;S.lang='en';S.t0='2020-01-01';S.plus=null;S.mrs=[{d:'2026-09-01',a:Array(11).fill(2)},{d:'2026-10-01',a:Array(11).fill(1)}];persist()")
 pg.reload();pg.evaluate("show('insights');gateAll()")
 assert pg.evaluate("!hasAccess() && $('v-insights').classList.contains('lockv')")
 assert pg.locator('#mrsBtn').is_visible(), 'MRS entry locked'
 assert pg.locator('#mrsBox svg').is_visible(), 'MRS trend locked'
 pg.locator('#mrsBtn').click()
 assert pg.locator('.mrsq').count()==11
 for q in pg.locator('.mrsq').all():q.locator('button[data-v="1"]').click()
 pg.locator('#mrsSave').click()
 assert pg.evaluate('S.mrs.some(m=>m.d===today() && m.a.every(v=>v===1))')
 assert pg.locator('#mrsBox svg').is_visible()
 assert not pg.locator('#corr').is_visible()
 b.close()
print('PASS: MRS entry, save and trend remain free with paywall enabled')
