"""Buyer pilot HTTP boundary, shared by localhost and Vercel."""
import json
import os
import re
import secrets
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from relay.live import Live, LiveError, SQLiteState, RedisState

ROOT=Path(__file__).resolve().parents[1]

def configured():
    origin=os.environ.get('FORGE_ORIGIN','http://127.0.0.1:8767')
    if os.environ.get('VERCEL'):
        required=['FORGE_ORIGIN','FORGE_OAUTH_CLIENT_ID','FORGE_OWNER']
        redis_url=os.environ.get('UPSTASH_REDIS_REST_URL') or os.environ.get('KV_REST_API_URL')
        redis_token=os.environ.get('UPSTASH_REDIS_REST_TOKEN') or os.environ.get('KV_REST_API_TOKEN')
        if not redis_url or not redis_token: raise LiveError('Dedicated live storage is not configured')
        if not all(os.environ.get(k) for k in required): raise LiveError('Live pilot configuration is incomplete')
        store=RedisState(redis_url,redis_token)
        client=os.environ['FORGE_OAUTH_CLIENT_ID']
    else:
        store=SQLiteState(ROOT/'data/live/state.sqlite3')
        client=json.loads((ROOT/'data/live/oauth-client.json').read_text())['client_id']
    return Live(store,origin,client,os.environ.get('FORGE_OWNER','frbl'))

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass # OAuth codes and task briefs must never enter request logs.
    def output(self,code,data,content_type='application/json',location=None):
        raw=json.dumps(data).encode() if content_type=='application/json' else data
        self.send_response(code)
        self.send_header('Content-Type',content_type)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if getattr(self,'new_sid',False): self.send_header('Set-Cookie','forge_session='+self.sid+'; HttpOnly; SameSite=Lax; Path=/; Max-Age=3600'+('; Secure' if self.live.origin.startswith('https:') else ''))
        if location: self.send_header('Location',location)
        self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self): self.respond('GET')
    def do_POST(self): self.respond('POST')
    def respond(self,method):
        try:
            self.live=configured()
            if self.headers.get('Host')!=urlsplit(self.live.origin).netloc: return self.output(403,{'error':'Unexpected host'})
            cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
            sid=cookie.get('forge_session');sid=sid.value if sid else ''
            self.new_sid=not bool(re.fullmatch(r'[A-Za-z0-9_-]{43}',sid));self.sid=secrets.token_urlsafe(32) if self.new_sid else sid
            path=urlsplit(self.path).path
            if method=='GET' and path in {'/','/live.html','/live.js','/live.css','/index.html','/app.js','/style.css'}:
                name='live.html' if path=='/' else path[1:]
                directory=ROOT/'deploy/vercel/public' if (ROOT/'deploy').exists() else ROOT/'public'
                kind={'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[name.rsplit('.',1)[1]]
                if name=='style.css' and (ROOT/'web').exists(): directory=ROOT/'web'
                return self.output(200,(directory/name).read_bytes(),kind)
            if method=='GET' and path=='/api/catalog' and (ROOT/'deploy').exists():
                from scripts.prepare_vercel import public_rows
                from relay.store import records
                from relay.core import CAPABILITIES, now
                return self.output(200,{'records':public_rows(records()),'capabilities':list(CAPABILITIES),'generated_at':now()})
            if method=='GET' and path=='/api/live/callback':
                query=parse_qs(urlsplit(self.path).query)
                self.live.callback(self.sid,query.get('code',[''])[0],query.get('state',[''])[0])
                return self.output(303,{},location='/live.html')
            if method=='GET' and path=='/api/live/status':
                try: job=self.live.job(self.sid)
                except LiveError: return self.output(200,{'connected':False})
                return self.output(200,{'connected':True,'job':job,'mode':'LIVE_BUYER_CHECKOUT','automatic_payment':False})
            if method!='POST': return self.output(404,{'error':'Not found'})
            if self.headers.get('Origin')!=self.live.origin: return self.output(403,{'error':'Same-origin request required'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.output(415,{'error':'JSON required'})
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=16384: return self.output(413,{'error':'Request too large or empty'})
            self.connection.settimeout(5);data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise LiveError('Invalid request')
            if path=='/api/match' and (ROOT/'deploy').exists():
                from relay.core import validate_request,match
                from relay.routing import route_proposals
                from relay.store import records
                from scripts.prepare_vercel import public_rows
                req=validate_request(data);rows=public_rows(records())
                return self.output(200,{'request':req,'matches':match(req,rows),'routing':route_proposals(req,rows)})
            if path=='/api/live/connect':
                result=self.live.device_start(self.sid) if os.environ.get('VERCEL') else {'url':self.live.start(self.sid)}
                return self.output(200,result)
            if path=='/api/live/connection': return self.output(200,self.live.device_poll(self.sid))
            if path=='/api/live/quote': return self.output(200,{'provider':self.live.quote(self.sid,data.get('handle'))})
            if path=='/api/live/prepare': result=self.live.prepare(self.sid,data)
            elif path=='/api/live/refresh': result=self.live.refresh(self.sid)
            elif path=='/api/live/accept': return self.output(200,self.live.accept_link(self.sid,data.get('sha256'),data.get('version'),data.get('assignment_id')))
            elif path=='/api/live/disconnect':
                key='session:'+self.sid;self.live.store.cas(key,self.live.store.get(key),None)
                return self.output(200,{'connected':False})
            else: return self.output(404,{'error':'Not found'})
            return self.output(200,{'job':result})
        except LiveError as e: self.output(400,{'error':str(e)})
        except (ValueError,TypeError): self.output(400,{'error':'Invalid request'})
        except Exception: self.output(503,{'error':'Live service unavailable. No automatic payment was attempted. Refresh using the saved pilot; do not create a duplicate.'})

if __name__=='__main__':
    configured()
    print('FORGE live pilot: http://127.0.0.1:8767',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8767),Handler).serve_forever()
