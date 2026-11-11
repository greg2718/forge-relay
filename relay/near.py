"""NEAR discovery integration: fixed-origin GET only; optional credential held in memory."""
import hashlib
import json
import re
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from relay.core import now, money
from relay.sources import NoRedirect, MAX_BYTES, record
from relay.store import save_source

ORIGIN='https://market.near.ai'
CATALOG_PATHS=('/v1/agents?category=research&limit=20&offset=0','/v1/agents?category=data&limit=20&offset=0')
BOARD_PATH='/v1/jobs/board?kind=standard&sort=recent&limit=50&offset=0'
UUID=r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'

class NearError(ValueError):pass


def get_json(path, token=None):
    allowed=path in CATALOG_PATHS or path==BOARD_PATH or re.fullmatch(r'/v1/agents/'+UUID+r'/pricing-plans',path)
    if not allowed:raise NearError('Operation is outside NEAR discovery scope')
    if token is not None and path!=BOARD_PATH:raise NearError('Credential use is limited to reading the public job board')
    headers={'Accept':'application/json','User-Agent':'ForgeRelay/0.3 discovery-only'}
    if token is not None:
        if not re.fullmatch(r'aat_[a-fA-F0-9]{32}',token):raise NearError('Use the project agent API token, not a password, wallet key or browser session')
        headers['Authorization']='Bearer '+token
    request=urllib.request.Request(ORIGIN+path,headers=headers,method='GET')
    try:
        with urllib.request.build_opener(NoRedirect()).open(request,timeout=15) as response:
            if 'application/json' not in response.headers.get('Content-Type',''):raise NearError('NEAR did not return JSON')
            raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise NearError('NEAR response exceeds the size limit')
    except urllib.error.HTTPError as exc:
        # Never return server response bodies/headers, which may contain sensitive material.
        raise NearError('NEAR returned HTTP '+str(exc.code)+('. Authentication required or credential rejected.' if exc.code in (401,403) else '.')) from None
    except (urllib.error.URLError,TimeoutError,OSError):
        raise NearError('NEAR network request failed; no external action was initiated') from None
    try:return json.loads(raw),hashlib.sha256(raw).hexdigest()
    except (ValueError,UnicodeDecodeError):raise NearError('NEAR returned invalid JSON') from None


def parse_agents(data,sha):
    if not isinstance(data,dict) or not isinstance(data.get('agents'),list):raise NearError('Unexpected NEAR agent catalog shape')
    rows=[]
    for a in data['agents'][:20]:
        if a.get('listing_status')!='live':continue
        handle=a.get('handle','');agent_id=a.get('agent_id','')
        if not re.fullmatch(r'[a-z0-9-]{3,100}',handle) or not re.fullmatch(UUID,agent_id):raise NearError('Invalid NEAR agent identity')
        if not isinstance(a.get('name'),str):raise NearError('Missing NEAR agent name')
        text='\n'.join(s for s in [a.get('description'),a.get('bio_markdown')] if isinstance(s,str))
        p=record('near',handle,a['name'],text,ORIGIN+'/a/'+handle,sha)
        owner=a.get('owner_account_id')
        sla=a.get('sla_seconds');delivered=a.get('delivered_jobs')
        available=a.get('available_now')
        availability='available' if available is True else 'unavailable' if available is False else 'unknown'
        if a.get('availability') in {'paused','suspended','unavailable_funding'}:availability='unavailable'
        p.update(evidence_type='PUBLIC_API',source_kind='agent_marketplace',agent_id=agent_id,
                 operator_group=owner if isinstance(owner,str) and re.fullmatch(UUID,owner) else None,
                 availability=availability,delivery_hours=sla/3600 if type(sla) is int and sla>0 else None,
                 delivered_jobs=delivered if type(delivered) is int and delivered>=0 else None,
                 marketplace_reported_success_rate=a.get('success_rate'),builder_verification=(a.get('builder') or {}).get('verification'),
                 listing_updated_at=a.get('updated_at'),payable_with=a.get('payable_with') or [],
                 protocols=['NEAR marketplace'],input_schema=a.get('input_schema'),output_schema=a.get('output_schema'),
                 evidence_notes=['Delivery counts, success rates and builder badges are reported by NEAR; not independently audited.'],
                 catalog_scope='First 20 research and 20 data agents; public API')
        rows.append(p)
    return rows


def add_pricing(p,plans,sha):
    if not isinstance(plans,list):raise NearError('Unexpected NEAR pricing-plan shape')
    live=[x for x in plans if x.get('listing_status')=='live' and x.get('agent_id')==p['agent_id']]
    default=[x for x in live if x.get('is_default') is True]
    p['pricing_source_sha256']=sha
    p['advertised_pricing']=[{k:x.get(k) for k in ('pricing_plan_id','model','price_amount','is_default','sla_seconds')} for x in live]
    if len(default)!=1:
        p['evidence_notes'].append('No unique live default pricing plan established.');return p
    x=default[0];amount=str(money(x['price_amount']))
    # Price has no currency field. Keep the advertised unit and payment options without inventing FX parity.
    currencies=[c for c in p['payable_with'] if c in {'USD','USDC'}]
    p.update(price=amount,currency=currencies[0] if len(currencies)==1 else None,
             price_basis={'per_call':'per_call','per_task':'per_job'}.get(x.get('model'),'unknown'))
    if len(currencies)!=1:p['evidence_notes'].append('Multiple or missing payment denominations; request a currency-specific quote.')
    sla=x.get('sla_seconds')
    if type(sla) is int and sla>0:p['delivery_hours']=sla/3600
    return p


def collect_agents():
    rows=[];seen=set()
    for path in CATALOG_PATHS:
        data,sha=get_json(path)
        for p in parse_agents(data,sha):
            if p['id'] not in seen:rows.append(p);seen.add(p['id'])
    def price(p):
        try:
            plans,sha=get_json('/v1/agents/'+p['agent_id']+'/pricing-plans');return add_pricing(p,plans,sha)
        except NearError:
            p['evidence_notes'].append('Pricing lookup failed; no price assumed.');return p
    with ThreadPoolExecutor(max_workers=4) as pool:return list(pool.map(price,rows))


def parse_board(data,sha):
    if not isinstance(data,dict) or not isinstance(data.get('jobs'),list):raise NearError('Unexpected NEAR job-board shape')
    rows=[]
    for j in data['jobs'][:50]:
        # Only open, public standard jobs with actual remaining slots enter the demand catalog.
        if j.get('isPrivate') is not False or j.get('isTestRun') is not False:continue
        if j.get('status') not in {'open','filling'} or j.get('jobKind')!='standard':continue
        if type(j.get('currentMaxSlots')) is not int or j['currentMaxSlots']<=0:continue
        key=j.get('jobId','')
        if not re.fullmatch(UUID,key) or not isinstance(j.get('title'),str) or not isinstance(j.get('description'),str):raise NearError('Invalid NEAR board job')
        p=record('near','job:'+key,j['title'][:500],j['description'],ORIGIN+'/jobs/'+key,sha,kind='demand')
        p.update(evidence_type='AUTHENTICATED_PUBLIC_BOARD_API',market_state='OPEN_AS_OBSERVED',
                 source_kind='task_marketplace',price_basis='posted_budget_not_awarded',
                 remaining_slots=j['currentMaxSlots'],min_builder_verification=j.get('minBuilderVerification','unknown'),
                 subcontracting_permission='UNKNOWN',job_id=key,listing_updated_at=j.get('updatedAt'),
                 evidence_notes=['Public board discovery only; no bid or award.','Budget is a posted amount, not a guaranteed payout.'])
        if j.get('budgetAmount') is not None:p['price']=str(money(j['budgetAmount']));p['currency']=j.get('budgetToken')
        rows.append(p)
    return rows


class NearSession:
    """A process-local credential, used only for one fixed read endpoint. Never persisted or returned."""
    def __init__(self):
        self._token=None;self._lock=threading.Lock();self._connected_at=None
    def status(self):
        with self._lock:return {'connected':self._token is not None,'connected_at':self._connected_at,
            'mode':'READ_ONLY','token_storage':'PROCESS_MEMORY_ONLY','expected_account_handle':'frbl',
            'expected_agent_handle':'forge-relay','identity_binding':'USER_SUPPLIED_TOKEN_NOT_INDEPENDENTLY_VERIFIED',
            'payment_enabled':False,'dispatch_enabled':False,'credential_creation_enabled':False}
    def connect(self,token):
        if not isinstance(token,str) or not re.fullmatch(r'aat_[a-fA-F0-9]{32}',token):raise NearError('Expected the new FORGE Relay agent API token')
        data,sha=get_json(BOARD_PATH,token)
        rows=parse_board(data,sha)
        with self._lock:self._token=token;self._connected_at=now()
        save_source('near_jobs',rows,'OK','Authenticated public board; no bids, job starts, messages or payments.')
        return self.status()
    def disconnect(self):
        with self._lock:self._token=None;self._connected_at=None
        return self.status()
    def refresh(self):
        with self._lock:token=self._token
        if token is None:raise NearError('Connect the project agent token locally to read the NEAR job board')
        data,sha=get_json(BOARD_PATH,token);rows=parse_board(data,sha)
        save_source('near_jobs',rows,'OK','Authenticated public board; discovery only.')
        return {'market':'near_jobs','status':'OK','count':len(rows)}

session=NearSession()
