"""Loopback-only UI/API, fixed static assets, same-origin writes, no payment endpoints."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from relay.core import CAPABILITIES, match, validate_request
from relay.store import ROOT, records, runs, plans
from relay.sources import refresh, CATALOGS
from relay.workflow import plan, rehearsal, verify_artifact, route_plan
from relay.routing import route_proposals
from relay.catalogs import SOURCE_INFO
from relay.demo import run_demo, accept as accept_demo, seed_snapshot
from relay.near import session as near_session

refresh_lock = threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Do not log request contents, credentials or query strings.
        pass

    def allowed_host(self):
        return self.headers.get('Host') == '127.0.0.1:'+str(self.server.server_port)

    def send(self, code, body, kind='application/json; charset=utf-8'):
        raw = body if isinstance(body,bytes) else json.dumps(body,ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if not self.allowed_host():
            return self.send(403,{'error':'Use the displayed 127.0.0.1 address'})
        path=urlsplit(self.path).path
        assets={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
        if path in assets:
            name,kind=assets[path]
            return self.send(200,(ROOT/'web'/name).read_bytes(),kind)
        if path=='/api/catalog':
            return self.send(200,{'records':records(),'sources':runs(),'capabilities':list(CAPABILITIES),
                                  'source_info':SOURCE_INFO,'mode':'OFFLINE_DEMO' if getattr(self.server,'demo_only',False) else 'READ_ONLY_MARKET_DISCOVERY','payment_enabled':False,'dispatch_enabled':False})
        if path=='/api/near/status' and getattr(self.server,'demo_only',False):
            return self.send(200,{'connected':False,'demo_only':True})
        if path=='/api/near/status':
            return self.send(200,near_session.status())
        if path=='/api/plans':
            return self.send(200,{'plans':plans()})
        if path=='/health':
            return self.send(200,{'status':'ok','payment_enabled':False,'dispatch_enabled':False})
        return self.send(404,{'error':'Not found'})

    def do_POST(self):
        expected='http://127.0.0.1:'+str(self.server.server_port)
        if not self.allowed_host() or self.headers.get('Origin') != expected or self.headers.get('Content-Type','').split(';')[0] != 'application/json':
            return self.send(403,{'error':'Same-origin JSON request required'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 65536:
                raise ValueError('Request body must be 1–65536 bytes')
            self.connection.settimeout(5)
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):
                raise ValueError('Expected JSON object')
            path=urlsplit(self.path).path
            if getattr(self.server,'demo_only',False) and (path.startswith('/api/near/') or path=='/api/refresh'):
                return self.send(403,{'error':'Offline demo: network refresh and credentials are disabled'})
            if path=='/api/near/connect':
                if set(data)!={'token'}:raise ValueError('Only the project token is accepted')
                return self.send(200,near_session.connect(data['token']))
            if path=='/api/near/disconnect':
                return self.send(200,near_session.disconnect())
            if path=='/api/near/refresh':
                return self.send(200,near_session.refresh())
            if path=='/api/demo/run':
                if set(data)-{'inject_fault'}:raise ValueError('Unknown demo fields')
                return self.send(200,run_demo(data.get('inject_fault',True)))
            if path=='/api/demo/accept':
                if set(data)!={'run_id','artifact_sha256'}:raise ValueError('Acceptance requires run and artifact hash')
                return self.send(200,accept_demo(data['run_id'],data['artifact_sha256']))
            if path=='/api/match':
                request=validate_request(data)
                catalog=records()
                return self.send(200,{'request':request,'matches':match(request,catalog),'routing':route_proposals(request,catalog)})
            if path=='/api/route-plan':
                return self.send(200,route_plan(data['request'],data['provider_ids']))
            if path=='/api/plan':
                return self.send(200,plan(data['request'],data['provider_id']))
            if path=='/api/rehearsal':
                return self.send(200,rehearsal())
            if path=='/api/verify':
                return self.send(200,verify_artifact(data))
            if path=='/api/refresh':
                if not refresh_lock.acquire(blocking=False):
                    return self.send(409,{'error':'A public refresh is already running'})
                try:
                    result=[refresh(m) for m in CATALOGS]
                    return self.send(200,{'sources':result})
                finally:
                    refresh_lock.release()
            return self.send(404,{'error':'Operation not supported. Payments and dispatch are disabled.'})
        except (ValueError,KeyError,TypeError) as exc:
            return self.send(400,{'error':str(exc)[:300]})
        except Exception:
            return self.send(500,{'error':'Operation failed. No external work or payment was initiated.'})

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--demo',action='store_true',help='Separate offline demo database; no credentials or catalog networking')
    args=parser.parse_args()
    if args.demo:
        from relay import store
        store.DATA=ROOT/'data'/'offline_demo'
        store.DATA.mkdir(parents=True,exist_ok=True)
        seed_snapshot()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.demo_only=args.demo
    print('FORGE Relay: http://127.0.0.1:'+str(server.server_port)+' — payments and dispatch disabled',flush=True)
    server.serve_forever()

if __name__=='__main__':
    main()
