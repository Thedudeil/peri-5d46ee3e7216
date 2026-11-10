/* Prime Traker visit-counting consent (Legal option A, 10 Nov 2026).
   Loads Cloudflare Web Analytics only after Allow, never if the token is empty.
   TODO: paste the site token from the Cloudflare Web Analytics JS snippet into CF_BEACON_TOKEN.
   Leave it empty until Avi provides the snippet. An empty token must never inject the beacon. */
(function(){
"use strict";

// TODO: paste the Cloudflare Web Analytics site token here (from the dashboard snippet).
var CF_BEACON_TOKEN = "";

var STORE_KEY = "ptVisitCounting";
var BEACON_SRC = "https://static.cloudflareinsights.com/beacon.min.js";
var BAR_ID = "pt-consent-bar";
var SCRIPT_ID = "pt-cf-beacon";
var PROMPT = "Can we count your visit? We use Cloudflare Web Analytics, which sets no cookies, to see how many people use Prime Traker. Your health entries are never sent.";

function hasGpc(){
  try{return navigator.globalPrivacyControl===true}catch(e){return false}
}

function stored(){
  try{
    var v=localStorage.getItem(STORE_KEY);
    return (v==="allow"||v==="deny")?v:null;
  }catch(e){return null}
}

function effective(){
  if(hasGpc())return "deny";
  return stored();
}

function save(v){
  try{
    if(v==="allow"||v==="deny")localStorage.setItem(STORE_KEY,v);
    else localStorage.removeItem(STORE_KEY);
  }catch(e){}
}

function tokenReady(){
  return typeof CF_BEACON_TOKEN==="string" && CF_BEACON_TOKEN.length>0;
}

function privacyHref(){
  var p=location.pathname||"/";
  if(p.indexOf("/nights")===0)return "/nights/privacy.html#website-analytics";
  if(p.indexOf("/strong")===0)return "/strong/privacy.html#website-analytics";
  return "/privacy.html#website-analytics";
}

function injectBeacon(){
  if(!tokenReady())return;
  if(effective()!=="allow")return;
  if(document.getElementById(SCRIPT_ID))return;
  var s=document.createElement("script");
  s.id=SCRIPT_ID;
  s.type="module";
  s.src=BEACON_SRC;
  s.setAttribute("data-cf-beacon",JSON.stringify({token:CF_BEACON_TOKEN}));
  (document.body||document.documentElement).appendChild(s);
}

function removeBeacon(){
  var s=document.getElementById(SCRIPT_ID);
  if(s&&s.parentNode)s.parentNode.removeChild(s);
}

function bottomOffset(){
  var h=0;
  var nodes=document.querySelectorAll("nav, .sticky");
  for(var i=0;i<nodes.length;i++){
    var el=nodes[i];
    if(el.id===BAR_ID)continue;
    var cs=window.getComputedStyle(el);
    if(cs.display==="none"||cs.visibility==="hidden")continue;
    if(cs.position!=="fixed"&&cs.position!=="sticky")continue;
    var r=el.getBoundingClientRect();
    if(r.height<=0)continue;
    // Ignore off-screen sticky CTAs (homepage .sticky starts translated down).
    if(r.bottom<window.innerHeight-2||r.top>window.innerHeight)continue;
    if(r.top<window.innerHeight/2)continue;
    h=Math.max(h,Math.round(window.innerHeight-r.top));
  }
  return h;
}

function watchBottoms(){
  if(!window.ResizeObserver)return;
  if(!watchBottoms.ro)watchBottoms.ro=new ResizeObserver(function(){positionBar(document.getElementById(BAR_ID))});
  var nodes=document.querySelectorAll("nav, .sticky");
  for(var i=0;i<nodes.length;i++){
    if(nodes[i].id===BAR_ID)continue;
    try{watchBottoms.ro.observe(nodes[i])}catch(e){}
  }
}

function positionBar(bar){
  if(!bar)return;
  watchBottoms();
  var off=bottomOffset();
  bar.style.bottom=off+"px";
  bar.style.paddingBottom=off>0?"8px":"calc(8px + env(safe-area-inset-bottom,0px))";
  var sp=document.getElementById("pt-consent-spacer");
  if(bar.hidden){
    if(sp)sp.style.height="0px";
    document.documentElement.style.removeProperty("--pt-consent-gap");
    return;
  }
  if(!sp){
    sp=document.createElement("div");
    sp.id="pt-consent-spacer";
    sp.setAttribute("aria-hidden","true");
    document.body.appendChild(sp);
  }
  var gap=Math.round(bar.getBoundingClientRect().height);
  sp.style.height=gap+"px";
  document.documentElement.style.setProperty("--pt-consent-gap",gap+"px");
}

function ensureStyle(){
  if(document.getElementById("pt-consent-css"))return;
  var css=document.createElement("style");
  css.id="pt-consent-css";
  css.textContent=
    "#pt-consent-bar{position:fixed;left:0;right:0;bottom:0;z-index:16;box-sizing:border-box;display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:8px 12px;background:var(--card,#fff8f2);color:var(--ink,#4a3328);border-top:2px solid var(--line,#ecd6c8);box-shadow:0 -4px 18px rgba(74,51,40,.10);font:14.5px/1.4 Nunito,system-ui,sans-serif}"+
    "#pt-consent-bar[hidden]{display:none!important}"+
    "#pt-consent-text{margin:0;flex:1 1 200px;min-width:0}"+
    "#pt-consent-actions{display:flex;flex-wrap:wrap;align-items:center;gap:8px}"+
    "#pt-consent-bar .pt-consent-btn{appearance:none;-webkit-appearance:none;margin:0;min-height:44px;min-width:44px;padding:0 14px;border:2px solid currentColor;border-radius:12px;background:transparent;color:inherit;font:inherit;font-weight:700;cursor:pointer}"+
    "#pt-consent-bar .pt-consent-btn:focus-visible,#pt-consent-bar .pt-consent-priv:focus-visible,#ptVisitLink:focus-visible,#ptVisitCard button:focus-visible{outline:3px solid currentColor;outline-offset:2px}"+
    "#pt-consent-bar .pt-consent-priv{color:inherit;font-weight:700;text-underline-offset:2px;padding:8px 2px;margin-inline-start:4px}"+
    "#pt-consent-spacer{height:0;pointer-events:none}"+
    "html[data-theme=dark] #pt-consent-bar{background:#1a1a1c;color:#ededee;border-top-color:#2a2a2e;box-shadow:0 -4px 18px rgba(0,0,0,.4)}"+
    "#ptVisitCard .thm{display:flex;gap:6px}#ptVisitCard .thm button{flex:1;min-height:44px;border-radius:12px;border:2px solid var(--line,#ecd6c8);background:var(--card,#fff8f2);color:var(--ink,#4a3328);font-weight:700;font-size:15px;cursor:pointer}#ptVisitCard .thm button[aria-pressed=true]{border-color:var(--ink,#4a3328);background:var(--roseL,#f8e0d6)}"+
    "html[data-theme=dark] #ptVisitCard .thm button{background:#141416;color:#ededee;border-color:#2a2a2e}html[data-theme=dark] #ptVisitCard .thm button[aria-pressed=true]{border-color:#ededee;background:#3a2a28}"+
    "@media print{#pt-consent-bar,#pt-consent-spacer{display:none!important}}";
  document.head.appendChild(css);
}

function hideBar(){
  var bar=document.getElementById(BAR_ID);
  if(bar){bar.hidden=true;positionBar(bar)}
}

function showBar(){
  if(hasGpc()){hideBar();return}
  ensureStyle();
  var bar=document.getElementById(BAR_ID);
  if(!bar){
    bar=document.createElement("div");
    bar.id=BAR_ID;
    bar.setAttribute("role","region");
    bar.setAttribute("aria-label","Visit counting");
    bar.setAttribute("aria-describedby","pt-consent-text");
    var p=document.createElement("p");
    p.id="pt-consent-text";
    p.textContent=PROMPT;
    var actions=document.createElement("div");
    actions.id="pt-consent-actions";
    var allow=document.createElement("button");
    allow.type="button";
    allow.className="pt-consent-btn";
    allow.textContent="Allow";
    allow.addEventListener("click",function(){setChoice("allow")});
    var deny=document.createElement("button");
    deny.type="button";
    deny.className="pt-consent-btn";
    deny.textContent="No thanks";
    deny.addEventListener("click",function(){setChoice("deny")});
    var link=document.createElement("a");
    link.className="pt-consent-priv";
    link.href=privacyHref();
    link.textContent="Privacy Policy";
    actions.appendChild(allow);
    actions.appendChild(deny);
    actions.appendChild(link);
    bar.appendChild(p);
    bar.appendChild(actions);
    document.body.appendChild(bar);
  }else{
    var a=bar.querySelector(".pt-consent-priv");
    if(a)a.href=privacyHref();
  }
  bar.hidden=false;
  positionBar(bar);
  if(window.ResizeObserver){
    if(!bar._ptRo){
      bar._ptRo=new ResizeObserver(function(){positionBar(bar)});
      bar._ptRo.observe(bar);
    }
  }
}

function setChoice(v){
  if(v!=="allow"&&v!=="deny")return;
  if(v==="allow"&&hasGpc())v="deny";
  save(v);
  hideBar();
  if(v==="allow")injectBeacon();
  else removeBeacon();
  syncUi();
}

function reset(){
  save(null);
  removeBeacon();
  if(hasGpc()||stored())hideBar();
  else showBar();
  syncUi();
}

function footerLabel(){
  var on=effective()==="allow";
  return on?"Visit counting: On":"Visit counting: Off";
}

function wireFooter(){
  var navs=document.querySelectorAll("footer nav, footer");
  var link=document.getElementById("ptVisitLink");
  if(!link){
    for(var i=0;i<navs.length;i++){
      var host=navs[i].tagName==="NAV"?navs[i]:navs[i].querySelector("nav")||navs[i];
      if(!host)continue;
      link=document.createElement("a");
      link.id="ptVisitLink";
      link.href=privacyHref();
      host.appendChild(link);
      break;
    }
  }
  if(!link)return;
  link.textContent=footerLabel();
  link.setAttribute("aria-label",footerLabel());
  if(!link._ptBound){
    link._ptBound=true;
    link.addEventListener("click",function(ev){
      ev.preventDefault();
      if(hasGpc()){
        // Choice is forced off; take them to the policy explanation.
        location.href=privacyHref();
        return;
      }
      showBar();
      var bar=document.getElementById(BAR_ID);
      if(bar){
        var btn=bar.querySelector(".pt-consent-btn");
        if(btn)btn.focus();
      }
    });
  }
}

function mountSettings(){
  var st=document.getElementById("v-settings")||document.getElementById("v-me");
  if(!st)return;
  ensureStyle();
  var card=document.getElementById("ptVisitCard");
  if(!card){
    card=document.createElement("div");
    card.className="card";
    card.id="ptVisitCard";
    var h=document.createElement("h2");
    h.className="h3";
    h.textContent="Visit counting: On/Off";
    var row=document.createElement("div");
    row.className="thm";
    row.setAttribute("role","group");
    row.setAttribute("aria-label","Visit counting");
    var on=document.createElement("button");
    on.type="button";
    on.dataset.ptVisit="allow";
    on.textContent="On";
    var off=document.createElement("button");
    off.type="button";
    off.dataset.ptVisit="deny";
    off.textContent="Off";
    row.appendChild(on);
    row.appendChild(off);
    var note=document.createElement("p");
    note.className="muted";
    note.id="ptVisitNote";
    note.style.margin="8px 0 0";
    card.appendChild(h);
    card.appendChild(row);
    card.appendChild(note);
    var anchor=document.getElementById("thmCard")||st.querySelector("h1");
    if(anchor&&anchor.parentNode===st)anchor.insertAdjacentElement("afterend",card);
    else st.insertBefore(card,st.firstChild);
    card.addEventListener("click",function(ev){
      var b=ev.target.closest("button[data-pt-visit]");
      if(!b)return;
      setChoice(b.dataset.ptVisit);
    });
  }
  var cur=effective();
  var gpc=hasGpc();
  card.querySelectorAll("button[data-pt-visit]").forEach(function(b){
    var isOn=b.dataset.ptVisit==="allow";
    b.setAttribute("aria-pressed",((cur==="allow"&&isOn)||(cur!=="allow"&&!isOn))?"true":"false");
    b.disabled=gpc&&isOn;
  });
  var noteEl=document.getElementById("ptVisitNote");
  if(noteEl){
    noteEl.textContent=gpc
      ?"Your browser sent a Global Privacy Control signal, so visits are not counted."
      :"We use Cloudflare Web Analytics, which sets no cookies, only if you choose On. Your health entries are never sent.";
  }
}

function syncUi(){
  wireFooter();
  mountSettings();
}

function apply(){
  ensureStyle();
  var choice=stored();
  if(hasGpc()||choice){
    hideBar();
    if(effective()==="allow")injectBeacon();
    else removeBeacon();
  }else{
    showBar();
    removeBeacon();
  }
  syncUi();
}

function boot(){
  apply();
  window.addEventListener("resize",function(){positionBar(document.getElementById(BAR_ID))});
  window.addEventListener("load",function(){positionBar(document.getElementById(BAR_ID))});
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(function(){positionBar(document.getElementById(BAR_ID))});
  window.addEventListener("storage",function(ev){
    if(ev.storageArea!==localStorage)return;
    if(ev.key!==STORE_KEY&&ev.key!==null)return;
    apply();
  });
  if(window.MutationObserver){
    var moT=null;
    var mo=new MutationObserver(function(recs){
      for(var i=0;i<recs.length;i++){
        var t=recs[i].target;
        if(!t)continue;
        if(t.id===BAR_ID||t.id==="pt-consent-spacer")continue;
        if(t.closest&&t.closest("#"+BAR_ID+",#pt-consent-spacer"))continue;
        if(moT)clearTimeout(moT);
        moT=setTimeout(function(){positionBar(document.getElementById(BAR_ID))},50);
        return;
      }
    });
    mo.observe(document.body,{subtree:true,attributes:true,attributeFilter:["class","style","hidden"]});
  }
}

window.PTConsent={
  key:STORE_KEY,
  stored:stored,
  effective:effective,
  set:setChoice,
  reset:reset,
  showBar:showBar,
  hideBar:hideBar,
  apply:apply
};

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);
else boot();

})();
