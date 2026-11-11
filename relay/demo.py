"""Executable no-cost local handoffs with persisted artifacts and tamper checks."""
import json
import re
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from relay.core import canonical, digest, now
from relay import store

ROOT=Path(__file__).resolve().parents[1]
LOCK=threading.Lock()
TASK={'title':'Compare research and extraction providers across marketplaces using cited listing evidence.',
      'capabilities':['research','extraction'],'min_rows':4,'max_rows':6,'min_markets':2,
      'acceptance':['4–6 distinct provider rows','At least two marketplaces','Every value agrees with frozen evidence',
                    'Each row cites its public listing and observation timestamp','Price units and uncertainty preserved'],
      'budget':'0','mode':'LOCAL_WORKERS_ONLY'}


def directory(run_id):
    if not isinstance(run_id,str) or not re.fullmatch(r'demo-[0-9a-f]{32}',run_id):raise ValueError('Invalid demo ID')
    parent=store.DATA/'demo_runs'
    if store.DATA.is_symlink() or parent.is_symlink():raise ValueError('Demo directory cannot be a symlink')
    path=parent/run_id
    if path.is_symlink():raise ValueError('Demo run cannot be a symlink')
    return path


def worker(role,payload,run_id):
    if role not in {'extractor','writer','verifier'}:raise ValueError('Unsupported local worker')
    request={'protocol':'relay-handoff/v1','run_id':run_id,'worker':role,'payload':payload}
    done=subprocess.run([sys.executable,'-I',str(ROOT/'relay/demo_worker.py')],input=canonical(request),
        capture_output=True,text=True,timeout=15,cwd=str(ROOT),env={'PYTHONIOENCODING':'utf-8'})
    if done.returncode:raise ValueError('Local '+role+' failed; no external action occurred')
    response=json.loads(done.stdout)
    if response.get('protocol')!='relay-handoff/v1' or response.get('worker')!=role or response.get('run_id')!=run_id or response.get('request_sha256')!=digest(request) or response.get('output_sha256')!=digest(response.get('output')):
        raise ValueError('Worker handoff integrity check failed')
    return {'request':request,'response':response}


def append_event(bundle,kind,details):
    events=bundle['events']
    event={'sequence':len(events)+1,'at':now(),'kind':kind,'details':details,
           'previous_hash':events[-1]['event_hash'] if events else '0'*64}
    events.append({**event,'event_hash':digest(event)})


def save(bundle):
    path=directory(bundle['id']);path.mkdir(parents=True,exist_ok=True)
    target=path/'bundle.json'
    if target.is_symlink():raise ValueError('Run file cannot be a symlink')
    temp=path/'bundle.tmp'
    if temp.is_symlink():raise ValueError('Temporary run file cannot be a symlink')
    temp.write_text(canonical(bundle));temp.replace(target)


def render_report(artifact):
    lines=['# Marketplace comparison — '+artifact['revision'],'','Local deterministic workers; no external agents hired.','']
    for r in artifact['rows']:
        lines.extend(['## '+r['title'], '- Marketplace: '+r['market'], '- Advertised capabilities: '+', '.join(r['capabilities']),
            '- Advertised price: '+('Unconfirmed' if r['price'] is None else str(r['price'])+' '+str(r['currency'] or 'currency unconfirmed'))+' / '+str(r['price_basis']),
            '- Source: '+str(r['source_url']),'- Observed: '+str(r['observed_at']),''])
    lines+=['## Limitations',*['- '+x for x in artifact['limitations']]]
    return '\n'.join(lines)+'\n'


def run_demo(inject_fault=True):
    if type(inject_fault) is not bool:raise ValueError('Fault injection must be boolean')
    if not LOCK.acquire(blocking=False):raise ValueError('A local demo is already running')
    try:
        snapshot=json.loads((ROOT/'fixtures/market-snapshot.json').read_text())
        bundle={'id':'demo-'+uuid.uuid4().hex,'created_at':now(),'mode':'EXECUTED_LOCAL_DEMO',
            'task':TASK,'snapshot':snapshot,'snapshot_sha256':digest(snapshot),'handoffs':[],
            'artifacts':[],'verifications':[],'events':[],'fault_injected':inject_fault,
            'state':'WORK_IN_PROGRESS','payment_executed':False,'marketplace_provider_contacted':False,
            'worker_type':'Deterministic Python processes; not LLM agents or independent marketplace operators.'}
        append_event(bundle,'TASK_CREATED',{'task_sha256':digest(TASK),'snapshot_sha256':digest(snapshot)})
        def call(role,payload):
            handoff=worker(role,payload,bundle['id']);bundle['handoffs'].append(handoff)
            append_event(bundle,'WORKER_RETURNED',{'worker':role,'handoff_sha256':digest(handoff)})
            return handoff['response']['output']
        extraction=call('extractor',{'snapshot':snapshot,'task':TASK})
        artifact=call('writer',{'extraction':extraction,'revision':'r1'})
        if inject_fault:
            # Explicit fault injection tests the verifier, never masquerades as a marketplace failure.
            artifact=json.loads(canonical(artifact));artifact['rows'][0]['source_url']=''
            append_event(bundle,'TEST_FAULT_INJECTED',{'kind':'missing citation','artifact_sha256':digest(artifact)})
        for attempt in range(2):
            bundle['artifacts'].append(artifact)
            append_event(bundle,'ARTIFACT_RETURNED',{'revision':artifact['revision'],'artifact_sha256':digest(artifact)})
            result=call('verifier',{'artifact':artifact,'snapshot':snapshot,'task':TASK})
            bundle['verifications'].append(result)
            append_event(bundle,'VERIFICATION_'+result['result'],{'verification_sha256':digest(result)})
            if result['result']=='PASS':break
            if attempt==0:
                append_event(bundle,'REVISION_REQUESTED',{'failed_checks':[c['name'] for c in result['checks'] if not c['pass']]})
                artifact=call('writer',{'extraction':extraction,'revision':'r2'})
        bundle['state']='VERIFIED_PENDING_OPERATOR_ACCEPTANCE' if result['result']=='PASS' else 'VERIFICATION_FAILED'
        bundle['report_markdown']=render_report(artifact)
        append_event(bundle,bundle['state'],{'artifact_sha256':digest(artifact)})
        bundle['sealed_payload_sha256']=digest({k:v for k,v in bundle.items() if k not in {'sealed_payload_sha256','acceptance'}})
        save(bundle)
        return bundle
    finally:LOCK.release()


def load(run_id):
    path=directory(run_id)/'bundle.json'
    if path.is_symlink():raise ValueError('Run file cannot be a symlink')
    if not path.is_file():raise ValueError('Demo run not found')
    return json.loads(path.read_text())


def verify_bundle(bundle):
    sealed={k:v for k,v in bundle.items() if k not in {'sealed_payload_sha256','acceptance'}}
    if digest(sealed)!=bundle.get('sealed_payload_sha256'):raise ValueError('Demo bundle changed after verification')
    previous='0'*64
    for i,e in enumerate(bundle['events'],1):
        if e['sequence']!=i or e['previous_hash']!=previous or digest({k:v for k,v in e.items() if k!='event_hash'})!=e['event_hash']:raise ValueError('Broken demo event chain')
        previous=e['event_hash']
    if digest(bundle['snapshot'])!=bundle['snapshot_sha256']:raise ValueError('Snapshot changed')
    for h in bundle['handoffs']:
        q,r=h['request'],h['response']
        if q['run_id']!=bundle['id'] or r['run_id']!=bundle['id'] or r['request_sha256']!=digest(q) or r['output_sha256']!=digest(r['output']):raise ValueError('Changed handoff')
    from relay.demo_worker import verify
    check=verify(bundle['artifacts'][-1],bundle['snapshot'],bundle['task'])
    if check!=bundle['verifications'][-1] or check['result']!='PASS':raise ValueError('Final artifact failed verification')
    if bundle['state']!='VERIFIED_PENDING_OPERATOR_ACCEPTANCE':raise ValueError('Demo is not ready for acceptance')
    if 'acceptance' in bundle:
        receipt=bundle['acceptance']
        if receipt.get('artifact_sha256')!=check['artifact_sha256'] or receipt.get('bundle_sha256')!=bundle['sealed_payload_sha256'] or receipt.get('receipt_sha256')!=digest({k:v for k,v in receipt.items() if k!='receipt_sha256'}):raise ValueError('Acceptance receipt changed')
    return check


def accept(run_id,artifact_sha256):
    with LOCK:
        bundle=load(run_id);check=verify_bundle(bundle)
        if artifact_sha256!=check['artifact_sha256']:raise ValueError('Acceptance must name the verified artifact hash')
        if 'acceptance' not in bundle:
            receipt={'mode':'LOCAL_OPERATOR_ACCEPTANCE','accepted_at':now(),'artifact_sha256':artifact_sha256,
                'bundle_sha256':bundle['sealed_payload_sha256'],'payment_executed':False,
                'note':'Local demo review only; not acceptance by a marketplace buyer or a settlement.'}
            bundle['acceptance']={**receipt,'receipt_sha256':digest(receipt)};save(bundle)
        return bundle


def seed_snapshot():
    """Seed only a separate demo database; caller chooses the isolated data directory."""
    snapshot=json.loads((ROOT/'fixtures/market-snapshot.json').read_text())
    rows=[]
    for original in snapshot['records']:
        rows.append({**original,'kind':'supply','provider_type':'agent','availability':'unknown',
            'delivery_hours':None,'delivered_jobs':None,'evidence_type':'FROZEN_PUBLIC_SNAPSHOT',
            'source_kind':'demo_snapshot','capability_basis':'KEYWORD_INFERENCE_FROM_LISTING',
            'execution_verified':False,'payment_verified':False,
            'evidence_notes':['Frozen public evidence from 2026-11-10; no current availability or trust claim.']})
    store.save_source('demo_snapshot',rows,'OK','Bundled public facts for offline matching; no network refresh.')
