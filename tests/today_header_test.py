from pathlib import Path
from playwright.sync_api import sync_playwright
import subprocess,sys,time
root=Path(__file__).resolve().parents[1]
srv=subprocess.Popen([sys.executable,'-m','http.server','8845'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.6)
try:
 with sync_playwright() as p:
  b=p.chromium.launch()
  for w in [320,360,390,412,430]:
   pg=b.new_page(viewport={'width':w,'height':915})
   pg.goto('http://localhost:8845/app/');pg.evaluate("S.onb=true;S.instSeen=true;S.lang='en';persist()");pg.reload();pg.evaluate("show('today');$('streakTop').textContent='15 days in a row'")
   assert pg.locator('#v-today .top h1').evaluate('e=>e.getBoundingClientRect().height<=parseFloat(getComputedStyle(e).lineHeight)+1'),f'title wraps at {w}'
   assert pg.locator('#streakTop').evaluate('e=>e.getBoundingClientRect().height<=parseFloat(getComputedStyle(e).lineHeight)+1'),f'streak wraps at {w}'
   assert pg.evaluate("$('streakTop').getBoundingClientRect().top >= document.querySelector('#v-today .top h1').getBoundingClientRect().bottom"),f'not stacked at {w}'
   pg.close()
  b.close()
finally:srv.terminate();srv.wait()
print('PASS Today header stacked without wrapping at 320–430px')
