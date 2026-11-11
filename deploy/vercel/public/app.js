'use strict';
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if(cls)n.className=cls; return n; };
const human = s => String(s || '').replaceAll('_',' ');
async function api(path, body) { const r=await fetch('/api/'+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); const d=await r.json(); if(!r.ok)throw Error(d.error); return d; }
function evidence(p) { const a=el('a','View original listing ↗'); if(/^https:\/\//.test(p.source_url))a.href=p.source_url; a.target='_blank';a.rel='noopener noreferrer';return a; }
function download(value) { const u=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'})); const a=el('a','');a.href=u;a.download='forge-relay-proposal.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000); }
function provider(p) { const card=el('article','', 'market-card'); card.append(el('span',p.market.toUpperCase(),'panel-kicker'),el('h3',p.title),el('p',p.price==null?'Price unconfirmed':`${p.price} ${p.currency || 'currency unconfirmed'} · ${human(p.price_basis)}`),el('p','Observed '+p.observed_at,'small muted'),evidence(p));if(p.market==='near'&&p.kind==='supply'&&/^near:[A-Za-z0-9_-]+$/.test(p.id)){const live=el('a','Check live hire options ↗');live.href='/live.html?provider='+encodeURIComponent(p.id.slice(5));card.append(live);}return card; }

const examples={research:{title:'Research three competitors and return a comparison with source links.',caps:['research','web_search']},extraction:{title:'Extract key facts from public sources and return a cited research summary.',caps:['research','extraction']},cleanup:{title:'Clean a dataset, remove duplicates and verify the returned records.',caps:['data_cleanup','verification']}};
document.querySelectorAll('[data-example]').forEach(b=>b.addEventListener('click',()=>{const example=examples[b.dataset.example];$('title').value=example.title;document.querySelectorAll('[name=cap]').forEach(n=>n.checked=example.caps.includes(n.value));$('title').focus();}));
async function load(){const d=await api('catalog');$('status').textContent=`Snapshot prepared ${d.generated_at}. ${d.records.filter(p=>p.kind==='supply').length} provider listings; ${d.records.filter(p=>p.kind==='demand').length} public requests. Availability and prices may have changed.`;for(const cap of d.capabilities){const label=el('label','','capability');const i=document.createElement('input');i.type='checkbox';i.name='cap';i.value=cap;i.checked=['research','extraction'].includes(cap);label.append(i,el('span',human(cap)));$('capabilities').append(label);}$('demand').replaceChildren(...d.records.filter(p=>p.kind==='demand').map(provider));$('find-button').disabled=false;}
$('compare').addEventListener('submit',async e=>{
 e.preventDefault();const b=$('find-button');const caps=[...document.querySelectorAll('[name=cap]:checked')].map(n=>n.value);
 if(!caps.length){$('form-status').textContent='Choose at least one skill so we can find relevant providers.';return;}
 b.disabled=true;b.textContent='Finding possible matches…';$('form-status').textContent='';
 try{const d=await api('match',{title:$('title').value,capabilities:caps,budget:$('budget').value,currency:$('currency').value,max_hours:Number($('hours').value),provider_type:$('type').value});
 $('routes').replaceChildren();$('empty-state').hidden=true;$('matched-content').hidden=false;
 $('results-summary').textContent=`${d.routing.routes.length} possible options for: “${d.request.title || $('title').value}”`;
 for(const [index,r] of d.routing.routes.entries()){
 const card=el('article','','result-card');card.append(el('span',`OPTION ${index+1} · ${r.cross_market?'PROPOSED TEAM ACROSS MARKETPLACES':'ONE MARKETPLACE'}`,'panel-kicker'),el('h3',r.providers.length>1?'Combine specialists for this task':r.providers[0].title));
 card.append(el('p',r.providers.length>1?'These listings collectively advertise the selected skills. Their ability to work together is unconfirmed.':'This listing advertises skills relevant to your selection. Review the source to confirm it can deliver your task.'));
 const members=el('div','','route-members');for(const p of r.providers){const item=el('div','','route-member');item.append(el('strong',p.title),el('p',human(p.market)+' · '+(p.capabilities||[]).map(human).join(', '),'small muted'),evidence(p));members.append(item);}card.append(members);
 card.append(el('p',r.advertised_total==null?'Full task price: ask providers for a quote.':'Advertised total: '+r.advertised_total+' '+r.currency+' — confirm scope and fees.'));
 const next=el('div','','next-step');next.append(el('strong','What to do next'),el('p','Open the original listing above. Confirm the deliverable, total price and deadline before deciding to hire.'));card.append(next);
 const details=el('details','','options');details.append(el('summary',`Review ${r.unknowns.length} checks before hiring`));const ul=el('ul','');r.unknowns.forEach(x=>ul.append(el('li',x)));details.append(ul);const save=el('button','Save proposal (JSON)','button secondary');save.type='button';save.addEventListener('click',()=>download({request:d.request,route:r,mode:'UNEXECUTED_SNAPSHOT_PROPOSAL'}));details.append(save);card.append(details);$('routes').append(card);
 }
 if(!d.routing.routes.length)$('routes').append(el('p','No option covers all the selected skills in this catalog. Try fewer skills or browse individual providers below.'));
 $('candidate-summary').textContent=`Browse ${d.matches.length} individual listings evaluated`;
 $('results').replaceChildren(...d.matches.map(r=>{const c=provider(r.provider);const detail=el('details','','options');detail.append(el('summary','Why this listing appeared'),el('p',r.capability_coverage+'% of selected skills appear in its listing. This is not a quality score.'),el('p',[...r.blockers,...r.unknowns].join(' '),'small muted'));c.append(detail);return c;}));
 $('match-output').focus();$('match-output').scrollIntoView({behavior:'smooth',block:'start'});
 }catch(err){$('form-status').textContent='We could not load matches. Please try again. '+err.message;}finally{b.disabled=false;b.textContent='Find possible matches →';}
});
load().catch(()=>{$('status').textContent='The catalog could not be loaded. Refresh the page to try again.';$('form-status').textContent='Catalog unavailable. Refresh to try again.';});
