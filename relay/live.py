"""Isolated buyer pilot. Draft checkout only: never calls paid create_job."""
import base64
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

MARKET = 'https://market.near.ai'
MAX_BYTES = 1024 * 1024

class LiveError(ValueError):
    pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise LiveError('Unexpected service redirect')

def remote(url, payload, headers=None, form=False, oauth_pending=False):
    raw = urlencode(payload).encode() if form else json.dumps(payload).encode()
    req = Request(url, data=raw, headers={'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json', **(headers or {})})
    try: response=build_opener(NoRedirect()).open(req, timeout=20)
    except HTTPError as e:
        if oauth_pending and e.code==400:
            error=json.loads(e.read(4096)).get('error')
            if error in {'authorization_pending','slow_down','access_denied','expired_token'}: return {'error':error},{}
        raise LiveError('NEAR/storage service returned HTTP '+str(e.code)) from None
    with response:
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES: raise LiveError('Service response too large')
        if not body and 'id' not in payload: return {}, response.headers
        if 'text/event-stream' in response.headers.get('Content-Type', ''):
            messages = [json.loads(line[5:].strip()) for line in body.decode().splitlines() if line.startswith('data:')]
            body = next((m for m in messages if m.get('id') == payload.get('id')), None)
            if body is None: raise LiveError('No matching service response')
        else: body = json.loads(body)
        return body, response.headers

class SQLiteState:
    """Separate private database. Atomic compare-and-swap also works across processes."""
    def __init__(self, path):
        self.path = str(path)
        if Path(path).is_symlink() or Path(path).parent.is_symlink(): raise LiveError('Private state must not use symlinks')
        Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connect() as db: db.execute('CREATE TABLE IF NOT EXISTS live_state (key TEXT PRIMARY KEY, value TEXT NOT NULL, expires REAL NOT NULL)')
        os.chmod(path, 0o600)
    def connect(self): return sqlite3.connect(self.path, timeout=10)
    def get(self, key):
        with self.connect() as db:
            row = db.execute('SELECT value FROM live_state WHERE key=? AND expires>?', (key, time.time())).fetchone()
        return json.loads(row[0]) if row else None
    def cas(self, key, old, new, ttl=86400*30):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT value FROM live_state WHERE key=? AND expires>?', (key, time.time())).fetchone()
            actual = json.loads(row[0]) if row else None
            if actual != old: return False
            if new is None: db.execute('DELETE FROM live_state WHERE key=?', (key,))
            else: db.execute('INSERT OR REPLACE INTO live_state VALUES (?,?,?)', (key, json.dumps(new, sort_keys=True), time.time()+ttl))
            return True

class RedisState:
    """Dedicated free Redis REST store; no ephemeral hosted fallback."""
    def __init__(self, url, token):
        if urlsplit(url).scheme != 'https' or not urlsplit(url).hostname.endswith('.upstash.io'): raise LiveError('Dedicated Upstash endpoint required')
        self.url, self.token = url, token
    def command(self, command):
        result, _ = remote(self.url, command, {'Authorization': 'Bearer '+self.token})
        if 'error' in result: raise LiveError('State storage unavailable')
        return result.get('result')
    def get(self, key):
        value = self.command(['GET', 'forge-live:'+key])
        return json.loads(value) if value else None
    def cas(self, key, old, new, ttl=86400*30):
        script = "local v=redis.call('GET',KEYS[1]); if (v or '')~=ARGV[1] then return 0 end; if ARGV[2]=='' then redis.call('DEL',KEYS[1]) else redis.call('SET',KEYS[1],ARGV[2],'EX',ARGV[3]) end; return 1"
        encode = lambda v: '' if v is None else json.dumps(v, sort_keys=True)
        return self.command(['EVAL', script, 1, 'forge-live:'+key, encode(old), encode(new), ttl]) == 1

class Buyer:
    def __init__(self, token):
        self.token, self.session, self.tools = token, None, None
    def rpc(self, method, params):
        headers = {'Authorization': 'Bearer '+self.token, 'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2024-11-05'}
        if self.session: headers['Mcp-Session-Id'] = self.session
        result, returned = remote(MARKET+'/mcp', {'jsonrpc':'2.0', 'id':str(uuid.uuid4()), 'method':method, 'params':params}, headers)
        self.session = returned.get('Mcp-Session-Id', self.session)
        if result.get('error'): raise LiveError('NEAR declined the request; check your buyer connection')
        return result.get('result', {})
    def call(self, name, args):
        allowed = {'whoami','get_agent','prepare_job','get_draft_status','get_job_status','get_job_result','accept_result'}
        if name not in allowed: raise LiveError('Unsupported buyer action')
        if self.tools is None:
            self.rpc('initialize', {'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'forge-relay','version':'0.5.0'}})
            headers={'Authorization':'Bearer '+self.token,'Accept':'application/json, text/event-stream','MCP-Protocol-Version':'2024-11-05'}
            if self.session: headers['Mcp-Session-Id']=self.session
            remote(MARKET+'/mcp',{'jsonrpc':'2.0','method':'notifications/initialized'},headers)
            self.tools = self.rpc('tools/list', {}).get('tools', [])
        candidates = [t['name'] for t in self.tools if t['name'] == name or t['name'].endswith('__'+name)]
        if len(candidates) != 1: raise LiveError('Required NEAR buyer tool unavailable')
        result = self.rpc('tools/call', {'name':candidates[0], 'arguments':args})
        if result.get('isError'): raise LiveError('NEAR refused this action. Check the task on NEAR before retrying.')
        data = result.get('structuredContent')
        if data is None:
            texts = [c['text'] for c in result.get('content',[]) if c.get('type') == 'text']
            try: data = json.loads('\n'.join(texts))
            except (ValueError, TypeError): raise LiveError('Unexpected NEAR response format')
        if not isinstance(data, dict) or data.get('refused'): raise LiveError('NEAR action unavailable')
        return data

def cents(value):
    try: amount = Decimal(str(value))
    except InvalidOperation: raise LiveError('Invalid price')
    if not amount.is_finite() or amount < 0 or amount*100 != (amount*100).to_integral_value(): raise LiveError('Invalid price')
    return int(amount*100)

def market_link(value):
    p = urlsplit(value or '')
    if p.scheme != 'https' or p.netloc != 'market.near.ai' or p.username or p.fragment: raise LiveError('Unexpected marketplace link')
    return value

def verify_artifact(text):
    citations = sorted(set(re.findall(r'https://[^\s<>\]\)"\']+', text)))
    checks = {'substantive_text':len(text.strip()) >= 200, 'three_source_links':len(citations)>=3}
    return {'sha256':hashlib.sha256(text.encode()).hexdigest(), 'checks':checks, 'passed':all(checks.values()), 'sources':citations,
            'scope':'Checks completeness and citation presence only; buyer must review facts and source relevance.'}

class Live:
    def __init__(self, store, origin, client_id, owner='frbl', buyer_factory=Buyer):
        p=urlsplit(origin)
        if not p.hostname or p.username or p.path or p.query or p.fragment or (p.scheme!='https' and origin!='http://127.0.0.1:8767'): raise LiveError('Invalid configured origin')
        self.store,self.origin,self.client_id,self.owner,self.buyer_factory=store,origin,client_id,owner,buyer_factory
    def device_start(self,sid):
        result,_=remote(MARKET+'/oauth/device/code',{'client_id':self.client_id,'scope':'mcp profile hiring'},form=True)
        url=market_link(result.get('verification_uri_complete') or result.get('verification_uri'))
        if not result.get('device_code') or not result.get('user_code'): raise LiveError('Device connection unavailable')
        ttl=min(int(result.get('expires_in',900)),900)
        record={'code':result['device_code'],'interval':max(5,int(result.get('interval',5))),'next_poll':time.time()+5,'expires':time.time()+ttl}
        key='device:'+sid
        if not self.store.cas(key,self.store.get(key),record,ttl): raise LiveError('Connection changed; try again')
        return {'url':url,'user_code':result['user_code'],'device':True,'expires_in':ttl}
    def device_poll(self,sid):
        key='device:'+sid;pending=self.store.get(key)
        if not pending or pending['expires']<=time.time(): raise LiveError('Connection request expired; connect again')
        if pending['next_poll']>time.time(): return {'pending':True,'message':'Wait a few seconds, then check connection.'}
        locked={**pending,'next_poll':time.time()+max(30,pending['interval'])}
        if not self.store.cas(key,pending,locked,900): return {'pending':True}
        result,_=remote(MARKET+'/oauth/token',{'grant_type':'urn:ietf:params:oauth:grant-type:device_code','client_id':self.client_id,'device_code':pending['code']},form=True,oauth_pending=True)
        if result.get('error') in {'authorization_pending','slow_down'}: return {'pending':True,'message':'Approve the request on NEAR, then check again.'}
        if result.get('error'): self.store.cas(key,locked,None);raise LiveError('Connection denied or expired')
        access=result.get('access_token')
        if not access: raise LiveError('No buyer token returned')
        self.bind_token(sid,access,result.get('expires_in',3600))
        self.store.cas(key,locked,None)
        return {'connected':True}
    def bind_token(self,sid,access,expires):
        identity=self.buyer_factory(access).call('whoami',{})
        user=identity.get('user') or {}
        if user.get('handle','').lower()!=self.owner.lower(): raise LiveError('Only the configured FORGE pilot buyer may connect')
        ttl=min(int(expires),3600)
        record={'token':access,'handle':user['handle'],'expires':time.time()+ttl}
        key='session:'+sid
        if not self.store.cas(key,self.store.get(key),record,ttl): raise LiveError('Connection changed; reconnect')
    def start(self, session_id):
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        self.store.cas('oauth:'+state,None,{'verifier':verifier,'session':session_id},600)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        return MARKET+'/oauth/authorize?'+urlencode({'client_id':self.client_id,'redirect_uri':self.origin+'/api/live/callback','response_type':'code','scope':'mcp profile hiring','state':state,'code_challenge':challenge,'code_challenge_method':'S256'})
    def callback(self, session_id, code, state):
        pending=self.store.get('oauth:'+state)
        if not pending or pending['session']!=session_id or not self.store.cas('oauth:'+state,pending,None): raise LiveError('Connection expired or belongs to another browser')
        token,_=remote(MARKET+'/oauth/token',{'grant_type':'authorization_code','code':code,'client_id':self.client_id,'redirect_uri':self.origin+'/api/live/callback','code_verifier':pending['verifier']},form=True)
        access=token.get('access_token')
        if not access: raise LiveError('Buyer connection failed')
        self.bind_token(session_id,access,token.get('expires_in',3600))
    def buyer(self,sid):
        session=self.store.get('session:'+sid)
        if not session or session['expires']<=time.time(): raise LiveError('Connect your NEAR buyer account first')
        return self.buyer_factory(session['token'])
    def job(self,sid):
        self.buyer(sid)
        return self.store.get('pilot:'+self.owner)
    def quote(self,sid,handle):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',str(handle)): raise LiveError('Invalid provider handle')
        result=self.buyer(sid).call('get_agent',{'handle':handle})
        agent=result.get('agent',result)
        if not isinstance(agent,dict): raise LiveError('Unexpected provider details')
        return {k:agent.get(k) for k in ['agent_id','handle','name','price','price_token','payable_with','accepting_work','not_accepting_because','required_roles','bio_markdown','reviews','page_url']}
    def prepare(self,sid,data):
        buyer=self.buyer(sid)
        key='pilot:'+self.owner
        old=self.store.get(key)
        if old: return self.refresh(sid)  # One pilot only; stable ID survives timeouts and double-clicks.
        agent=str(data.get('agent_id','')).strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',agent): raise LiveError('Choose a NEAR provider ID')
        title=str(data.get('title','')).strip();description=str(data.get('description','')).strip()
        if not 5<=len(title)<=160 or not 80<=len(description)<=6000: raise LiveError('Provide a short title and a complete task brief')
        token=data.get('token','USD')
        if token not in {'USD','USDC'}: raise LiveError('Unsupported currency')
        price=cents(data.get('quoted_price'))
        if not 0<price<=500: raise LiveError('The provider-price ceiling is $5; funding fees require separate checkout approval')
        # Explicit operator quote, not an assumed catalog price. Checkout is authoritative.
        job={'request':{'worker_agent_id':agent,'title':title,'description':description,'token':token,'client_request_id':str(uuid.uuid4())},
             'ceiling_cents':price,'state':'preparing','created_at':time.time()}
        if not self.store.cas(key,None,job): return self.refresh(sid)
        return self.refresh(sid)
    def refresh(self,sid):
        buyer=self.buyer(sid);key='pilot:'+self.owner;job=self.store.get(key)
        if not job: return None
        updated=json.loads(json.dumps(job))
        if not job.get('job_id'):
            draft_id=job.get('draft_id')
            if not draft_id and job.get('approval_url'):
                candidate=urlsplit(market_link(job['approval_url'])).path.rsplit('/',1)[-1]
                try: draft_id=str(uuid.UUID(candidate))
                except ValueError: raise LiveError('Saved draft reference is invalid')
            response=buyer.call('get_draft_status',{'draft_id':draft_id}) if draft_id else buyer.call('prepare_job',job['request'])
            if response.get('draft_id'): updated['draft_id']=response['draft_id']
            if response.get('job_id'):
                updated.pop('approval_url',None)
                updated.update(job_id=response['job_id'],assignment_id=response.get('assignment_id'),state='funded' if response.get('funded') else 'pending_funding')
            elif response.get('approval_url'):
                quote=cents(response.get('quoted_price'))
                if quote>job['ceiling_cents'] or quote>500: raise LiveError('NEAR quote exceeds the approved pilot ceiling; do not pay')
                updated.update(approval_url=market_link(response['approval_url']),quote=response.get('quoted_price'),state='awaiting_checkout')
            elif draft_id and response.get('approved') is False:
                updated.update(draft_id=draft_id,state='awaiting_checkout')
            else: raise LiveError('No checkout or funded job returned; retain this pilot ID and inspect NEAR')
        else:
            status=buyer.call('get_job_status',{'job_id':job['job_id']})
            updated.update(status=status,state='tracking')
            if status.get('result_available'):
                result=buyer.call('get_job_result',{'job_id':job['job_id']})
                if result.get('status')=='delivered':
                    text=result.get('content_chunk','');offset=result.get('next_offset');seen=set()
                    while offset is not None:
                        if offset in seen or len(text.encode())>MAX_BYTES: raise LiveError('Result exceeds pilot limits')
                        seen.add(offset)
                        chunk=buyer.call('get_job_result',{'job_id':job['job_id'],'offset':offset,**({'assignment_id':result['assignment_id']} if result.get('assignment_id') else {})})
                        if chunk.get('version') != result.get('version') or chunk.get('assignment_id') != result.get('assignment_id'): raise LiveError('Result changed during download; refresh')
                        text+=chunk.get('content_chunk','');offset=chunk.get('next_offset')
                    if len(text.encode())>MAX_BYTES: raise LiveError('Result exceeds pilot limits')
                    updated.update(artifact=text,verification=verify_artifact(text),version=result.get('version'),assignment_id=result.get('assignment_id'),state='review')
                elif result.get('status')=='external':
                    updated.update(state='external_review',external_result=True)
                else: updated.update(state='tracking')
            if status.get('status')=='completed' or status.get('job_status')=='completed': updated['state']='completed'
        if updated.get('state')!=job.get('state') or updated.get('verification')!=job.get('verification'):
            updated['events']=(job.get('events',[])+[{'at':time.time(),'state':updated['state'],'artifact_sha256':updated.get('verification',{}).get('sha256'),'version':updated.get('version')}])[-50:]
        if not self.store.cas(key,job,updated): return self.store.get(key)
        return updated
    def accept_link(self,sid,digest,version=None,assignment_id=None):
        job=self.refresh(sid)
        if not job or job.get('state')!='review' or not job.get('verification',{}).get('passed') or job['verification']['sha256']!=digest or job.get('version')!=version or job.get('assignment_id')!=assignment_id: raise LiveError('Refresh and review the current artifact before accepting')
        args={'job_id':job['job_id']}
        if job.get('assignment_id'): args['assignment_id']=job['assignment_id']
        response=self.buyer(sid).call('accept_result',args)
        return {'url':market_link(response.get('job_url')), 'notice':'Accept on NEAR after reviewing the exact artifact. Acceptance releases escrow to the provider.'}
