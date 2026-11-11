'use strict';
let current=null;
const $=id=>document.getElementById(id);
async function api(action,data){const response=await fetch('/api/live/'+action,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'Service unavailable');return result;}
function link(id,url){const el=$(id);el.hidden=true;el.removeAttribute('href');if(!url)return;const u=new URL(url);if(u.origin!=='https://market.near.ai')throw Error('Unexpected marketplace link');el.href=u.href;el.hidden=false;}
function render(job){current=job;link('accept-link',null);link('checkout',job?.approval_url);$('state').textContent=job?job.state.replaceAll('_',' '):'No pilot yet.';$('job').textContent=job?JSON.stringify({provider:job.request.worker_agent_id,request_id:job.request.client_request_id,job_id:job.job_id,quoted_price:job.quote,ceiling:job.ceiling_cents/100,status:job.status,events:job.events},null,2):'';$('artifact').textContent=job?.artifact||(job?.external_result?'This provider returned an external artifact. Review it on NEAR; FORGE has not downloaded or verified it.':'Waiting for a real provider delivery.');$('verification').textContent=job?.verification?JSON.stringify(job.verification,null,2):'No artifact checked.';$('accept').disabled=!(job?.state==='review'&&job?.verification?.passed);$('task').querySelector('button').disabled=!!job;}
async function run(work){try{$('message').textContent='Working…';await work();$('message').textContent='Saved. Payment and acceptance occur on NEAR.';}catch(e){$('message').textContent=e.message;}}
$('connect').onclick=()=>run(async()=>{const r=await api('connect',{});const u=new URL(r.url);if(r.device){link('device-link',r.url);$('device-code').textContent='Confirm this code on NEAR: '+r.user_code;$('connection').hidden=false;return;}if(u.origin!=='https://market.near.ai'||u.pathname!=='/oauth/authorize')throw Error('Unexpected connection URL');location.assign(u.href);});
$('disconnect').onclick=()=>run(async()=>{await api('disconnect',{});render(null);});
$('task').onsubmit=e=>{e.preventDefault();run(async()=>render((await api('prepare',Object.fromEntries(new FormData(e.target)))).job));};
$('refresh').onclick=()=>run(async()=>render((await api('refresh',{})).job));
$('accept').onclick=()=>run(async()=>{const r=await api('accept',{sha256:current.verification.sha256,version:current.version,assignment_id:current.assignment_id});link('accept-link',r.url);});
run(async()=>{const r=await api('status');render(r.job);if(!r.connected)throw Error('Connect your NEAR buyer account to start.');});

const picked=new URLSearchParams(location.search).get('provider');
if(picked&&/^[A-Za-z0-9_-]{1,100}$/.test(picked))$('provider-handle').value=picked;
$('quote').onclick=()=>run(async()=>{const r=await api('quote',{handle:$('provider-handle').value});const p=r.provider;$('provider').textContent=JSON.stringify(p,null,2);if(p.agent_id)$('task').elements.agent_id.value=p.agent_id;if(p.price!=null)$('task').elements.quoted_price.value=p.price;if(p.payable_with?.includes('USD'))$('task').elements.token.value='USD';else if(p.payable_with?.includes('USDC'))$('task').elements.token.value='USDC';});

$('connection').onclick=()=>run(async()=>{const r=await api('connection',{});if(r.pending)throw Error(r.message||'Authorization pending');$('connection').hidden=true;link('device-link',null);$('device-code').textContent='Buyer connected.';render((await api('status')).job);});
