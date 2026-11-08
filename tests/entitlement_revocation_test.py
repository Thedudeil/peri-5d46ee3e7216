"""PT-041: all paid DOM/actions revoked in-session; all license responses mocked."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
HTML=(Path(__file__).resolve().parents[1]/'app/index.html').read_text()
CASES=['trial-tick','token-tick','persist-clear','manual-gate','license-401','license-403','invalid-refresh','invalid-verify','release','focus-expiry','visibility-expiry','storage-license','storage-remove','storage-clear']
with sync_playwright() as p:
 b=p.chromium.launch()
 for case in CASES:
  ctx=b.new_context();pg=ctx.new_page();pg.clock.install()
  html=HTML.replace('PAYWALL_ENABLED=false','PAYWALL_ENABLED=true').replace('LICENSE_SERVER_ENABLED=false','LICENSE_SERVER_ENABLED=true')
  ctx.route('https://revoke.test/**',lambda r:r.fulfill(content_type='text/html',body='<html></html>' if r.request.url.endswith('/blank') else html))
  def license_response(route):
   if case=='release':result={'ok':True};status=200
   elif case=='invalid-refresh':result={'ok':True,'token':'invalid','exp':1};status=200
   else:result={};status=401 if case=='license-401' else 403 if case=='license-403' else 503
   route.fulfill(status=status,content_type='application/json',body=json.dumps(result))
  ctx.route('https://license.primetraker.com/**',license_response)
  pg.on('dialog',lambda d:d.accept())
  pg.goto('https://revoke.test/app/')
  pg.evaluate("""S.onb=true;S.instSeen=true;S.lang='en';S.t0='2020-01-01';S.seen=today();S.dev='dev-'+ 'a'.repeat(24);
  S.e={};for(let i=0;i<70;i++)S.e[addD(today(),-i)]={s:{sleep:1,mood:2},hf:27.375,ex:{t:i%2?'walk':'none',m:i%2?30:0},bleed:'none',trig:[],meds:[],notes:'PT041-PRIVATE-NOTE',saved:true};
  S.hrt=[{id:'test',d:addD(today(),-29),x:'Test treatment'}];S.mrs=[{d:addD(today(),-35),a:Array(11).fill(1)},{d:today(),a:Array(11).fill(2)}];
  window.fixtureTok=btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600,dev:S.dev})).replace(/=/g,'')+'.AA';
  S.plus={tok:fixtureTok,exp:Math.floor(Date.now()/1000)+3600,chk:Date.now()};licVerified={tok:fixtureTok,ok:true};persist();
  """)
  if case=='trial-tick':pg.evaluate('S.plus=null;S.t0=today();persist()')
  pg.evaluate("boot();sumMode='let';show('summary');show('insights')")
  assert pg.evaluate('hasAccess()'),case+': fixture not entitled'
  assert '27.4' in pg.locator('#hwBox').text_content(),case+': before/after fixture missing'
  assert '27.4' in pg.locator('#mvBox').text_content(),case+': movement fixture missing'
  assert pg.locator('#sumBody').text_content().strip(),case+': letter fixture missing'
  if case=='trial-tick':
   pg.evaluate("S.t0=addD(today(),-14)");pg.clock.run_for(1001)
  elif case=='token-tick':
   pg.clock.run_for(2000);assert pg.evaluate('hasAccess()'), '503 must retain an unexpired entitlement'
   pg.clock.run_for(3600000)
  elif case in ['focus-expiry','visibility-expiry']:
   pg.evaluate("S.plus=null;S.t0='2020-01-01'")
   pg.evaluate("window.dispatchEvent(new Event('focus'))" if case=='focus-expiry' else "document.dispatchEvent(new Event('visibilitychange'))")
  elif case=='persist-clear':pg.evaluate('S.plus=null;persist()')
  elif case=='manual-gate':pg.evaluate('S.plus=null;gateAll()')
  elif case in ['license-401','license-403','invalid-refresh']:
   if case=='invalid-refresh':pg.evaluate('tokValid=async()=>false')
   pg.evaluate('licRefresh(true)')
  elif case=='invalid-verify':pg.evaluate("licVerified={tok:null,ok:false};tokValid=async()=>false;licVerify()")
  elif case=='release':pg.evaluate('licRelease()')
  else:
   other=ctx.new_page();other.goto('https://revoke.test/blank')
   if case=='storage-clear':other.evaluate('localStorage.clear()')
   elif case=='storage-remove':other.evaluate("localStorage.removeItem('periTracker.v1')")
   else:other.evaluate("const s=JSON.parse(localStorage.getItem('periTracker.v1'));s.plus=null;localStorage.setItem('periTracker.v1',JSON.stringify(s))")
   pg.wait_for_function('!hasAccess()');other.close()
  assert not pg.evaluate('hasAccess()'),case+': entitlement not revoked'
  assert '27.4' not in pg.locator('body').text_content(),case+': paid average remains anywhere in DOM'
  for sel in ['#sumBody','#chart','#topSym','#corr','#cntBox']:
   assert not pg.locator(sel).text_content().strip(),case+': stale paid surface '+sel
  assert pg.locator('#mvBox td').all_text_contents().count('••')==6,case+': movement teaser missing'
  assert all(x=='••' for x in pg.locator('#hwBox td:not(:first-child)').all_text_contents()),case+': stale before/after cells'
  assert pg.locator('#hwBox .hwUnlock').count()==1,case+': before/after teaser missing'
  # A direct delayed letter callback or CSV/print click cannot restore/export results.
  pg.evaluate("window.exports=0;window.prints=0;URL.createObjectURL=()=>{exports++;return 'blob:blocked'};window.print=()=>prints++;renderLetter();$('expCsv').click();$('printBtn').click()")
  assert pg.evaluate('exports===0 && prints===0'),case+': paid action still allowed'
  assert not pg.locator('#sumBody').text_content().strip(),case+': direct letter callback bypass'
  pg.evaluate("$('chartSym').onchange();sumMode='sum';$('sumMonth').onchange();renderHeatmap()")
  for sel in ['#sumBody','#chart','#cal']:
   assert not pg.locator(sel).inner_html().strip(),case+': delayed paid callback bypass '+sel
  pg.evaluate("$('sheet').classList.add('hide')")
  assert pg.locator('#mrsBtn').is_visible(),case+': MRS locked'
  if case not in ['storage-clear','storage-remove']:assert pg.locator('#mrsBox svg').is_visible(),case+': MRS trend lost'
  print('PASS',case,flush=True);ctx.close()
 b.close()
print('PASS all PT-041 revocation paths')
