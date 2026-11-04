const LOCAL_RELEASE=Date.parse('2026-11-04T00:00:00Z');
const RELEASE=Date.parse('2026-11-04T01:00:00Z');
const scopes=new Set(['indian-river','florida','district','local']);
const safeUrl=value=>{try{const u=new URL(value);return u.protocol==='https:'&&['floridaelectionwatch.gov','enr.electionsfl.org'].includes(u.hostname)&&!u.username&&!u.password;}catch{return false;}};
export function validateSnapshot(data){
 if(data?.electionId!=='2026-fl-general'||data.electionDate!=='2026-11-03'||!Number.isFinite(Date.parse(data.fetchedAt))||!Array.isArray(data.races)||!data.races.length)throw Error('Invalid General Election snapshot');
 const ids=new Set();
 for(const r of data.races){
  if(!r.id||ids.has(r.id)||!scopes.has(r.scope)||!safeUrl(r.sourceUrl)||!r.name||!['pending','unofficial'].includes(r.status)||!Array.isArray(r.candidates)||r.candidates.length<2)throw Error('Invalid race');
  ids.add(r.id);
  let total=0;const candidates=new Set();
  for(const c of r.candidates){if(!c.name||candidates.has(c.name+'|'+c.party)||!(c.votes===null||Number.isSafeInteger(c.votes)&&c.votes>=0))throw Error('Invalid candidate');candidates.add(c.name+'|'+c.party);total+=c.votes||0;}
  if(!(r.totalVotes===null||Number.isSafeInteger(r.totalVotes)&&r.totalVotes>=0&&r.totalVotes===total))throw Error('Invalid total');
 }
 return data;
}
export function watchState(data,health={},now=new Date()){
 validateSnapshot(data);
 if(Object.values(health).some(h=>h.status==='error')||now-Date.parse(data.fetchedAt)>900000||Date.parse(data.fetchedAt)-now>300000)return 'delayed';
 if(now.getTime()<LOCAL_RELEASE)return 'pending';
 return data.races.some(r=>r.status==='unofficial')?'unofficial':'pending';
}
export function createWatchStore(){return {scope:'local',snapshot:null,select(value){if(scopes.has(value))this.scope=value;},accept(value){validateSnapshot(value);this.snapshot=value;}};}
const fmtDate=value=>{const t=Date.parse(value);return Number.isFinite(t)?new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(t):'Unavailable';};
export async function readWatchResponses(response,healthResponse){
 if(!response.ok)throw Error('Results unavailable');
 if(!healthResponse.ok)throw Error('Feed health unavailable');
 const snapshot=validateSnapshot(await response.json()),health=await healthResponse.json();
 if(!['state','county'].every(key=>['ok','error'].includes(health?.[key]?.status)))throw Error('Invalid feed health');
 return {snapshot,health};
}
export function watchDestination(href){
 return ({'#local-races':{scope:'local'},'#florida-races':{scope:'florida'},'#united-states-senator':{scope:'florida',race:'United States Senator'},'#governor-and-lieutenant-governor':{scope:'florida',race:'Governor and Lieutenant Governor'},'#representative-in-congress':{scope:'district',race:'Representative in Congress'}})[href]||null;
}
export function mountWatch(documentRef=document,fetcher=fetch){
 const host=documentRef.getElementById('general-watch');if(!host)return;
 const store=createWatchStore();let health={},failed=false,busy=false,closed=false,lastRender='';
 const status=host.querySelector('[data-watch-status]'),stamp=host.querySelector('[data-watch-stamp]'),grid=host.querySelector('[data-watch-races]');
 function el(tag,text,className){const n=documentRef.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
 function render(){
  if(!store.snapshot){status.textContent='Checking official General Election sources…';return;}
  const data=store.snapshot,state=failed?'delayed':watchState(data,health);
  status.textContent={pending:'Awaiting results — November 3 General Election',unofficial:'Unofficial returns — counting continues',delayed:'Updates delayed — showing the last verified snapshot'}[state];
  status.dataset.state=state;
  stamp.textContent='Official feed checked: '+fmtDate(data.fetchedAt)+(data.sourceModifiedAt?' · Source file updated: '+fmtDate(data.sourceModifiedAt):'')+' · Page checks every 30 seconds';
  host.querySelectorAll('[data-watch-scope]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.watchScope===store.scope)));
  const fingerprint=JSON.stringify([store.scope,data.races,new Date().getTime()<RELEASE]);if(fingerprint===lastRender)return;lastRender=fingerprint;
  const priority=r=>{
   if(store.scope==='district'&&/Representative in Congress, District 9/i.test(r.name))return -10;
   return /County Commissioners|City of |Mosquito|School Board|Hospital/i.test(r.name)?0:1;
  };
  let races=data.races.filter(r=>r.scope===store.scope);
  if(store.scope==='district'){
   const live=races.filter(r=>r.status==='unofficial'&&Number(r.totalVotes||0)>0);
   if(live.length)races=live;
  }
  races=races.sort((a,b)=>priority(a)-priority(b));
  grid.replaceChildren();
  if(!races.length){grid.append(el('p','No live district returns are available yet.'));return;}
  for(const r of races){
   const card=el('article',undefined,'watch-race');card.id='watch-'+r.id;card.append(el('div',store.scope==='florida'?'FLORIDA TOTALS':store.scope==='district'?'FULL DISTRICT TOTALS':store.scope==='local'?'INDIAN RIVER LOCAL CONTEST':'INDIAN RIVER VOTES', 'watch-kicker'),el('h3',r.name));
   const pending=new Date().getTime()<(r.scope==='local'?LOCAL_RELEASE:RELEASE)||r.status==='pending';
   card.append(el('p',pending?'Awaiting official returns':r.totalVotes.toLocaleString()+' votes · Unofficial','watch-race-status'));
   if(r.sourceFetchedAt)card.append(el('p','Feed checked: '+fmtDate(r.sourceFetchedAt)+(r.sourceUpdatedAt?' · Source updated: '+fmtDate(r.sourceUpdatedAt):''),'watch-reporting'));
   if(r.voteFor>1)card.append(el('p','Vote for up to '+r.voteFor+' · Share of candidate votes; no seat calls','watch-reporting'));
   if(r.precincts&&r.precinctsReporting!==null&&!pending)card.append(el('p',r.precinctsReporting+' / '+r.precincts+' precincts reporting · not percentage of ballots counted','watch-reporting'));
   const table=el('table');const thead=el('thead'),header=el('tr');for(const title of ['Candidate / choice','Votes','Share'])header.append(el('th',title));thead.append(header);table.append(thead);const tbody=el('tbody');
   for(const c of [...r.candidates].sort((a,b)=>(b.votes||0)-(a.votes||0))){const tr=el('tr');tr.append(el('td',c.name+(c.party&&c.party!=='NOP'?' · '+c.party:'')),el('td',pending?'—':c.votes.toLocaleString()),el('td',pending||!r.totalVotes?'—':(c.votes/r.totalVotes*100).toFixed(1)+'%'));tbody.append(tr);}
   table.append(tbody);card.append(table);const link=el('a','Official source ↗');link.href=r.sourceUrl;link.target='_blank';link.rel='noopener noreferrer';card.append(link);grid.append(card);
  }
 }
 host.querySelectorAll('[data-watch-scope]').forEach(button=>button.addEventListener('click',()=>{store.select(button.dataset.watchScope);render();}));
 async function refresh(){if(busy||closed)return;busy=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  try{const [response,h]=await Promise.all([fetcher('data/general-watch.json?ts='+Date.now(),{cache:'no-store',signal:controller.signal}),fetcher('data/general-watch-health.json?ts='+Date.now(),{cache:'no-store',signal:controller.signal})]);const result=await readWatchResponses(response,h);store.accept(result.snapshot);health=result.health;failed=false;}
  catch{failed=true;if(!store.snapshot)status.textContent='Results temporarily unavailable. Use the official results links below.';}
  finally{clearTimeout(timeout);busy=false;if(store.snapshot)render();}
 }
 const navLinks=documentRef.querySelectorAll('.election-rail-nav a,.election-dashboard-tabs a,.election-at-a-glance a');
 for(const link of navLinks){const dest=watchDestination(link.getAttribute('href'));if(!dest)continue;link.href='#general-watch';link.addEventListener('click',()=>{store.select(dest.scope);render();if(dest.race){const race=store.snapshot?.races.find(r=>r.scope===dest.scope&&r.name.includes(dest.race));if(race)setTimeout(()=>documentRef.getElementById('watch-'+race.id)?.scrollIntoView({block:'start',behavior:'smooth'}),0);}});}
 refresh();const timer=setInterval(refresh,30000);const visible=()=>{if(!documentRef.hidden)refresh();};documentRef.addEventListener('visibilitychange',visible);
 return ()=>{closed=true;clearInterval(timer);documentRef.removeEventListener('visibilitychange',visible);};
}
if(typeof document!=='undefined'){const boot=()=>{const dispose=mountWatch();window.addEventListener('pagehide',()=>dispose?.(),{once:true});};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();}
