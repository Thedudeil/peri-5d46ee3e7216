"""PT-042: retain and refresh paid views on positive entitlement events, without flicker."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
HTML=(Path(__file__).resolve().parents[1]/'app/index.html').read_text()
with sync_playwright() as p:
 b=p.chromium.launch()
 for case in ['storage-save','focus','visibility','refresh','grant','storage-new-valid','storage-new-invalid']:
  ctx=b.new_context();pg=ctx.new_page()
  html=HTML.replace('PAYWALL_ENABLED=false','PAYWALL_ENABLED=true').replace('LICENSE_SERVER_ENABLED=false','LICENSE_SERVER_ENABLED=true')
  ctx.route('https://retain.test/**',lambda r:r.fulfill(content_type='text/html',body='<html></html>' if r.request.url.endswith('/blank') else html))
  ctx.route('https://license.primetraker.com/**',lambda r:r.fulfill(status=503,content_type='application/json',body='{}'))
  pg.goto('https://retain.test/app/')
  pg.evaluate("""S.onb=true;S.instSeen=true;S.lang='en';S.t0='2020-01-01';S.seen=today();S.dev='dev-'+ 'a'.repeat(24);
  S.e={};for(let i=0;i<70;i++)S.e[addD(today(),-i)]={s:{sleep:1,mood:2},hf:27.375,ex:{t:i%2?'walk':'none',m:i%2?30:0},bleed:'none',trig:[],meds:[],notes:'',saved:true};
  S.hrt=[{id:'test',d:addD(today(),-29),x:'Test treatment'}];S.mrs=[{d:addD(today(),-35),a:Array(11).fill(1)},{d:today(),a:Array(11).fill(2)}];
  window.token=(n)=>btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600+n,dev:S.dev})).replace(/=/g,'')+'.AA';window.originalToken=token(0);window.nextToken=token(1);
  S.plus={tok:originalToken,exp:Math.floor(Date.now()/1000)+3600,chk:Date.now()};licVerified={tok:originalToken,ok:true};persist();boot();sumMode='let';show('summary');show('insights');
  window.wipes=0;const oldWipe=wipeLocked;wipeLocked=(...args)=>{wipes++;return oldWipe(...args)};
  window.insRenders=0;const oldIns=renderInsights;renderInsights=(...args)=>{insRenders++;return oldIns(...args)};
  window.sumRenders=0;const oldSum=renderSummary;renderSummary=(...args)=>{sumRenders++;return oldSum(...args)};
  """)
  assert '27.4' in pg.locator('#hwBox').text_content()
  if case=='grant':
   pg.evaluate("S.plus=null;persist();wipes=0;insRenders=0;sumRenders=0;tokValid=async()=>true")
   tok=pg.evaluate('nextToken')
   ctx.route('https://license.primetraker.com/activate',lambda r:r.fulfill(content_type='application/json',body=json.dumps({'ok':True,'token':tok,'exp':9999999999})))
   pg.evaluate("licActivate('TEST-ONLY')")
  elif case=='refresh':
   pg.evaluate('tokValid=async()=>true');tok=pg.evaluate('nextToken')
   ctx.route('https://license.primetraker.com/refresh',lambda r:r.fulfill(content_type='application/json',body=json.dumps({'ok':True,'token':tok,'exp':9999999999})))
   pg.evaluate('licRefresh(true)')
  elif case=='focus':pg.evaluate("window.dispatchEvent(new Event('focus'))")
  elif case=='visibility':pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
  else:
   pg.evaluate("()=>{"+('tokValid=async()=>true' if case=='storage-save' else 'window.verifying=false;tokValid=()=>{verifying=true;return new Promise(resolve=>window.finishVerify=resolve)}')+"}")
   other=ctx.new_page();other.goto('https://retain.test/blank')
   newtok=pg.evaluate('nextToken')
   other.evaluate("""({newtok,replace})=>{const s=JSON.parse(localStorage.getItem('periTracker.v1'));s.e[Object.keys(s.e)[0]].notes='Sibling edit';if(replace)s.plus.tok=newtok;localStorage.setItem('periTracker.v1',JSON.stringify(s))}""",{'newtok':newtok,'replace':case!='storage-save'})
   if case!='storage-save':
    pg.wait_for_function('verifying')
    assert pg.evaluate('hasAccess()') and '27.4' in pg.locator('#hwBox').text_content(),case+': cleared during pending revalidation'
    assert pg.evaluate('wipes')==0,case+': flicker while verification pending'
    pg.evaluate('finishVerify('+('false' if case=='storage-new-invalid' else 'true')+')')
   pg.wait_for_function("Object.values(S.e).some(e=>e.notes==='Sibling edit')")
   other.close()
  if case=='storage-new-invalid':
   assert not pg.evaluate('hasAccess()') and '27.4' not in pg.locator('body').text_content()
  else:
   pg.wait_for_function('hasAccess()')
   assert '27.4' in pg.locator('#hwBox').text_content(),case+': before/after not restored'
   assert '27.4' in pg.locator('#mvBox').text_content(),case+': movement not restored'
   assert pg.locator('#chart svg').count()>0 and pg.locator('#topSym').text_content().strip(),case+': patterns blank'
   assert pg.locator('#sumBody .letter').count()==1,case+': hidden letter not restored'
   assert pg.evaluate('wipes')==0,case+': transient false lock'
   if case in ['storage-save','storage-new-valid','grant','refresh','focus','visibility']:
    assert pg.evaluate('insRenders>0 && sumRenders>0'),case+': paid data not refreshed'
  assert pg.locator('#mrsBtn').is_visible(),case+': MRS unavailable'
  print('PASS',case,flush=True);ctx.close()
 b.close()
print('PASS PT-042 retention, refresh, grant and pending-validation controls')
