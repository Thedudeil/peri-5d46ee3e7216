"""Responsive header and removal of script-font loading."""
from pathlib import Path
import subprocess,sys,time,re
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
for path in [*root.rglob('*.html'),*root.rglob('sw.js')]:
 assert not re.search(r'caveat|amatic',path.read_text(),re.I),str(path)+' still uses dropped script font'
srv=subprocess.Popen([sys.executable,'-m','http.server','8843'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.6)
try:
 with sync_playwright() as p:
  b=p.chromium.launch()
  for width in [320,360,390,412,430]:
   page=b.new_page(viewport={'width':width,'height':915},is_mobile=True,has_touch=True)
   requests=[];page.on('request',lambda r: requests.append(r.url))
   page.goto('http://localhost:8843/');page.evaluate('document.fonts.ready')
   assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"),f'overflow at {width}'
   for sel in ['header .logo','header .btn']:
    assert page.locator(sel).evaluate("e=>getComputedStyle(e).whiteSpace==='nowrap'"),f'{sel} wraps at {width}'
   assert page.evaluate("document.querySelector('header .logo').getBoundingClientRect().right+7<=document.querySelector('header .btn').getBoundingClientRect().left"),f'header collision at {width}'
   assert not any('caveat' in u.lower() for u in requests)
   page.close()
  b.close()
finally:srv.terminate();srv.wait()
print('PASS Android header 320–430px; no script font loaded')
