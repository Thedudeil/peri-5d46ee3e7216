"""PT-039: movement is never computed/rendered for free or expired users."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'app/index.html').read_text()
with sync_playwright() as p:
 b=p.chromium.launch()
 for mode in ['free','expired','trial','plus','flags-off']:
  context=b.new_context();pg=context.new_page()
  source=html if mode=='flags-off' else html.replace('PAYWALL_ENABLED=false','PAYWALL_ENABLED=true')
  if mode=='expired':source=source.replace('LICENSE_SERVER_ENABLED=false','LICENSE_SERVER_ENABLED=true')
  pg.route('https://paid.test/**',lambda r:r.fulfill(content_type='text/html',body=source))
  pg.goto('https://paid.test/app/')
  pg.evaluate("""S.onb=true;S.instSeen=true;S.lang='en';S.t0='2020-01-01';S.plus=null;
  S.e={};for(let i=0;i<70;i++)S.e[addD(today(),-i)]={s:{sleep:1,mood:2},hf:27.375,ex:{t:i%2?'walk':'none',m:i%2?30:0},bleed:'none',trig:[],meds:[],notes:'',saved:true};
  S.hrt=[{id:'test',d:addD(today(),-29),x:'Test treatment'}];S.mrs=[{d:addD(today(),-35),a:Array(11).fill(1)},{d:today(),a:Array(11).fill(2)}];persist()""")
  if mode=='trial':pg.evaluate('S.t0=today();persist()')
  if mode=='plus':pg.evaluate("S.plus={tok:'test'};persist()")
  if mode=='expired':pg.evaluate("S.plus={tok:'expired',exp:1};persist()")
  pg.reload()
  pg.evaluate("window.mvCalls=0;const oldMv=mvStats;mvStats=(...args)=>{mvCalls++;return oldMv(...args)};show('insights');gateAll()")
  locked=mode in ['free','expired']
  assert pg.evaluate('hasAccess()') != locked,mode
  if locked:
   assert pg.evaluate('mvCalls')==0,mode+': paid movement computed'
   assert '27.4' not in pg.locator('body').text_content(),mode+': paid average in hidden/visible DOM'
   assert pg.locator('#mvBox td').all_text_contents().count('••')==6,mode+': missing movement placeholders'
   assert all(x=='••' for x in pg.locator('#hwBox td:not(:first-child)').all_text_contents()),mode+': treatment value leaked'
   assert pg.locator('#mrsBtn').is_visible() and pg.locator('#mrsBox svg').is_visible(),mode+': MRS locked'
  else:
   assert pg.evaluate('mvCalls')>0,mode+': movement unavailable'
   assert '27.4' in pg.locator('#mvBox').text_content(),mode+': paid averages missing'
   if mode in ['trial','plus']:
    pg.evaluate("S.plus=null;S.t0='2020-01-01';gateAll()")
    assert '27.4' not in pg.locator('#mvBox').text_content(),mode+': stale movement after access loss'
    assert pg.locator('#mvBox td').all_text_contents().count('••')==6
  context.close()
 b.close()
print('PASS paid DOM: free, expired, trial, Plus and flags-off; MRS stays free')
