"""FORGE-backed local planning and explicit synthetic rehearsal. Never dispatches work."""
import sys
from pathlib import Path
from relay.core import digest, now, validate_request, match
from relay.store import records, save_plan

VENDOR = Path(__file__).resolve().parents[1] / 'vendor'
sys.path.insert(0, str(VENDOR))
from forge.transactions import Transaction, replay, settlement_receipt

def event(tx, state, data=None, actor='FORGE'):
    return tx.transition(state, actor=actor, timestamp=now(), reason_code='relay_local_'+state.lower(),
                         evidence=[{'ref':'local://forge-relay','mode':'SIMULATION_ONLY'}], data=data or {},
                         idempotency_key=tx.transaction_id+':'+str(len(tx.events)+1))

def plan(data, provider_id):
    request = validate_request(data)
    choices = match(request, records())
    chosen = next((x for x in choices if x['provider']['id']==provider_id),None)
    if not chosen:
        raise ValueError('Provider is not in the current catalog')
    if chosen['status']=='EXCLUDED':
        raise ValueError('This provider has hard conflicts; revise the request or select another')
    plan_id = 'plan-'+digest({'request':request,'provider':chosen['provider']})[:20]
    tx = Transaction(plan_id)
    event(tx,'REQUEST_READY',{'request_valid':True})
    event(tx,'MATCHING')
    event(tx,'CANDIDATES_READY',{'provider_candidate':provider_id})
    event(tx,'QUOTE_REQUEST_READY')
    payload = {'id':plan_id,'request':request,'provider':chosen['provider'],'state':tx.state,
               'mode':'LOCAL_PLAN_ONLY','events':tx.events,'unknowns':chosen['unknowns'],
               'payment_executed':False,'provider_contacted':False,
               'next_step':'Review scope, provider identity, permission to subcontract and a binding quote before external action.',
               'rfq':{'task':request['title'],'required_capabilities':request['capabilities'],
                      'maximum_budget':request['budget'],'currency':request['currency'],
                      'delivery_hours':request['max_hours'],'required_outputs':['deliverable','source evidence','limitations'],
                      'acceptance':'Explicit review of the exact artifact revision; mechanical checks do not certify factual truth.'}}
    return save_plan(payload)

def rehearsal():
    """Show the copied FORGE engine operating, with fixtures only, including a revision."""
    tx = Transaction('rehearsal-'+digest(now())[:12])
    for state,data,actor in [
        ('REQUEST_READY',{'request_valid':True},'FORGE'),('MATCHING',{},'ROUTER'),
        ('CANDIDATES_READY',{},'ROUTER'),('QUOTE_REQUEST_READY',{},'FORGE'),('QUOTING',{},'FORGE'),
        ('QUOTES_RECEIVED',{},'FORGE'),
        ('PROVIDER_SELECTED',{'quote_valid':True,'quote_status':'VALID','selection_authority':'OPERATOR','budget_status':'WITHIN','mode_compatible':True},'OPERATOR'),
        ('AUTHORIZATION_PENDING',{},'FORGE'),
        ('AUTHORIZED',{'quote_valid':True,'authorization_mode':'SIMULATED','policy_decision':'ALLOW','unresolved_conditions':[]},'FORGE'),
        ('WORK_IN_PROGRESS',{},'PROVIDER'),('DELIVERABLE_SUBMITTED',{'deliverable_submitted':True,'revision':'r1'},'PROVIDER'),
        ('VERIFICATION_PENDING',{},'BENCH'),('VERIFICATION_FAILED',{'verification_result':'FAIL'},'BENCH'),
        ('REVISION_REQUESTED',{'revision':'r2'},'BUYER'),('WORK_IN_PROGRESS',{},'PROVIDER'),
        ('DELIVERABLE_SUBMITTED',{'deliverable_submitted':True,'revision':'r2'},'PROVIDER'),('VERIFICATION_PENDING',{},'BENCH'),
        ('POLICY_PENDING',{'verification_result':'PASS','verification_ref':'fixture://verification-r2'},'BENCH'),
        ('ACCEPTANCE_PENDING',{'policy_decision':'ALLOW','policy_ref':'fixture://policy-r2'},'SENTINEL'),
        ('ACCEPTED',{'acceptance_status':'ACCEPTED','authority':'BUYER','verification_ref':'fixture://verification-r2','policy_ref':'fixture://policy-r2'},'BUYER'),
        ('TRANSACTION_READY',{'request_valid':True,'quote_valid':True,'simulated_authorization':True,'deliverable_submitted':True,'verification_pass':True,'policy_satisfied':True,'buyer_accepted':True,'unresolved_conditions':[]},'FORGE'),
        ('SIMULATED_SETTLED',settlement_receipt(),'COMMERCE')]:
        event(tx,state,data,actor)
    return {'mode':'SYNTHETIC_REHEARSAL','state':tx.state,'events':tx.events,'replay_verified':replay(tx.events)==tx.snapshot,
            'payment_executed':False,'provider_contacted':False,'note':'Fixture roles only. No live Scout, Router, Bench, Sentinel or Commerce agent was invoked.'}

def verify_artifact(data):
    """Bounded research-package structural check. No external fetching or content execution."""
    if not isinstance(data,dict) or set(data)-{'revision','claims'}:
        raise ValueError('Artifact must contain revision and claims only')
    claims = data.get('claims')
    if not isinstance(claims,list) or len(claims)>100:
        raise ValueError('Claims must be a list with at most 100 entries')
    from urllib.parse import urlsplit
    checks = [{'name':'Revision identified','pass':isinstance(data.get('revision'),str) and bool(data['revision'].strip())},
              {'name':'At least one claim','pass':bool(claims)}]
    for index,c in enumerate(claims):
        good = isinstance(c,dict) and set(c)=={'claim','source_url'} and isinstance(c['claim'],str) and bool(c['claim'].strip()) and isinstance(c['source_url'],str)
        if good:
            try:
                u=urlsplit(c['source_url']);good=u.scheme=='https' and bool(u.hostname) and not u.username and not u.password
            except ValueError:
                good=False
        checks.append({'name':'Claim '+str(index+1)+' has text and an HTTPS citation','pass':bool(good)})
    return {'result':'STRUCTURE_PASS' if all(c['pass'] for c in checks) else 'STRUCTURE_FAIL',
            'checks':checks,'artifact_sha256':digest(data),'revision':data.get('revision'),
            'factual_accuracy':'NOT_CHECKED','source_reachability':'NOT_CHECKED','buyer_acceptance':False,
            'payment_executed':False,'verifier':'relay-structural-check/v1 (not live FLOP Bench)'}


def route_plan(data, provider_ids):
    """Revalidate selected catalog evidence locally; do not trust a client-supplied route."""
    from relay.routing import route_proposals
    request=validate_request(data)
    if not isinstance(provider_ids,list) or not 1 <= len(provider_ids) <= 3 or any(not isinstance(x,str) for x in provider_ids) or len(set(provider_ids))!=len(provider_ids):
        raise ValueError('Choose one to three distinct provider listings')
    catalog=[p for p in records() if p['id'] in provider_ids]
    if len(catalog)!=len(provider_ids):raise ValueError('A provider is no longer in the catalog')
    proposals=route_proposals(request,catalog)['routes']
    chosen=next((p for p in proposals if {r['id'] for r in p['providers']}==set(provider_ids)),None)
    if chosen is None:raise ValueError('These providers do not form a supported route for this task')
    tx=Transaction('plan-'+chosen['id'])
    event(tx,'REQUEST_READY',{'request_valid':True})
    event(tx,'MATCHING')
    event(tx,'CANDIDATES_READY',{'provider_candidates':provider_ids})
    event(tx,'QUOTE_REQUEST_READY')
    return save_plan({'id':tx.transaction_id,'request':request,'providers':chosen['providers'],
        'route':chosen,'state':tx.state,'mode':'LOCAL_PLAN_ONLY','events':tx.events,
        'unknowns':chosen['unknowns'],'payment_executed':False,'provider_contacted':False,
        'next_step':'Confirm each scope, handoff format, total quote, execution order and buyer permission before external action.'})
