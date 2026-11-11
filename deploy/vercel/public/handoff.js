'use strict';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n;};
let bundle,stage=0;
const titles=['Requirements travel with the request.','Separate workers exchange structured results.','Missing evidence stops the first revision.','The writer returns a corrected revision.','The corrected artifact passes. Acceptance is separate.'];
const descriptions=['The task asks for a cited comparison of research and extraction providers across marketplaces. These are its recorded acceptance criteria.','The recorded run used separate local Python processes. Each returned result records the worker and the request/output hashes.','A missing citation was deliberately injected to exercise the rejection path. The verifier failed the artifact and the recorded workflow requested revision.','Compare the actual citation field in the two recorded artifacts. The revised writer output restores the source link.','The final revision passed the recorded snapshot checks. This run ends pending operator acceptance; it did not hire or pay a marketplace provider.'];
function list(items){const u=el('ul','');items.forEach(x=>u.append(el('li',x)));return u;}
function render(){
 $('stage-kicker').textContent=`RECORDED STEP ${stage+1} OF 5`;$('stage-title').textContent=titles[stage];$('stage-description').textContent=descriptions[stage];const box=$('stage-content');box.replaceChildren();
 if(stage===0){box.append(list(bundle.task.acceptance));}
 if(stage===1){const names=bundle.handoffs.map(h=>h.request.worker);box.append(el('p',names.join(' → '),'artifact-field'),el('p','These are extractor/writer/verifier workers, not the planned Scout/Bench/Router/Sentinel/Commerce Router agents.'));}
 if(stage===2){box.append(el('p','Revision r1: FAIL','artifact-field missing'));const failed=bundle.verifications[0].checks.filter(c=>!c.pass).map(c=>c.name);box.append(list(failed),el('p','Decision recorded: request a revision. Do not treat this artifact as verified.'));}
 if(stage===3){for(const a of bundle.artifacts){const field=el('div','',a.revision==='r1'?'artifact-field missing':'artifact-field');field.append(el('strong',a.revision+' · '+a.rows[0].title),el('p',a.rows[0].source_url||'Source URL: missing'));box.append(field);}}
 if(stage===4){const v=bundle.verifications[bundle.verifications.length-1];box.append(el('p',`${v.result} · ${v.checks.filter(c=>c.pass).length}/${v.checks.length} recorded checks passed`,'artifact-field'));const details=el('details','');details.append(el('summary','Inspect all recorded checks'),list(v.checks.map(c=>(c.pass?'PASS: ':'FAIL: ')+c.name)));box.append(details,el('p','Artifact SHA-256: '+v.artifact_sha256,'recorded-hash'),el('p','State: '+bundle.state.replaceAll('_',' ')));}
 document.querySelectorAll('[data-stage]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.stage)===stage)));
 $('next-stage').textContent=stage===4?'Back to the request ↺':['Inspect the handoff →','See why it failed →','Inspect the revision →','See the verification →'][stage];
}
function canonical(v){if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';if(v!==null&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
async function start(){
 const response=await fetch('/sample-evidence.json');if(!response.ok)throw Error('Evidence unavailable');bundle=await response.json();
 if(bundle.mode!=='EXECUTED_LOCAL_DEMO'||bundle.artifacts.length!==2||bundle.verifications.length!==2||bundle.payment_executed||bundle.marketplace_provider_contacted)throw Error('Unexpected evidence format');
 const a=bundle.artifacts[bundle.artifacts.length-1];
 for(const [label,value] of [['Returned provider rows',a.rows.length],['Marketplaces in the artifact',new Set(a.rows.map(r=>r.market)).size],['Recorded revisions',bundle.artifacts.length],['External providers contacted','0'],['Funds moved','$0']]){const line=el('div','','metric-row');line.append(el('span',label),el('strong',String(value)));$('evidence-facts').append(line);}
 $('replay-status').textContent='Recorded run: '+bundle.id+' · '+new Date(bundle.created_at).toLocaleDateString();$('replay-controls').hidden=false;$('next-stage').disabled=false;render();
 document.querySelectorAll('[data-stage]').forEach(b=>b.addEventListener('click',()=>{stage=Number(b.dataset.stage);render();}));$('next-stage').addEventListener('click',()=>{stage=(stage+1)%5;render();});
 try{const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(a)));const hex=[...new Uint8Array(hash)].map(n=>n.toString(16).padStart(2,'0')).join('');$('hash-status').textContent=hex===bundle.verifications[1].artifact_sha256?'Browser hash check: final artifact matches its recorded SHA-256. This does not verify the full bundle or factual truth.':'Hash mismatch: do not rely on this artifact.';}catch{$('hash-status').textContent='Browser hash check unavailable. Download and run the offline verifier.';}
}
start().catch(()=>{$('replay-status').textContent='The recorded evidence could not be loaded. Please reload or use the repository’s offline verifier.';});
