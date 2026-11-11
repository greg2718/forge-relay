import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from relay.live import Live, LiveError, SQLiteState, cents, market_link, verify_artifact

class FakeBuyer:
    def __init__(self): self.calls=[];self.funded=False;self.version=1;self.price='0.50';self.timeout=False
    def call(self,name,args):
        self.calls.append((name,args.copy()))
        if name=='prepare_job':
            if self.timeout: self.timeout=False;raise TimeoutError()
            return {'job_id':'job-1','assignment_id':'a-1','funded':True} if self.funded else {'approval_url':'https://market.near.ai/drafts/5364a757-28c8-5fa3-bb9c-1d13c160e523','quoted_price':self.price}
        if name=='get_draft_status': return {'draft_id':args['draft_id'],'approved':self.funded,**({'job_id':'job-1','assignment_id':'a-1','funded':True} if self.funded else {})}
        if name=='get_job_status': return {'result_available':True,'job_status':'active'}
        if name=='get_job_result':return {'status':'delivered','content_chunk':'Source-based findings. '*20+'https://one.example/a https://two.example/b https://three.example/c','version':self.version,'assignment_id':'a-1'}
        if name=='accept_result':return {'action_required':True,'job_url':'https://market.near.ai/jobs/job-1'}
        if name=='whoami':return {'user':{'handle':'frbl'}}
        raise AssertionError(name)

class LiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=SQLiteState(Path(self.tmp.name)/'state.db');self.b=FakeBuyer()
        self.live=Live(self.store,'http://127.0.0.1:8767','client',buyer_factory=lambda token:self.b)
        self.store.cas('session:session',None,{'token':'private-test-token','expires':time.time()+3600,'handle':'frbl'})
        self.brief={'agent_id':'agent-1','title':'Research directories','description':'Research directory listing requirements with three official cited sources. '*3,'quoted_price':'.50','token':'USD'}
    def tearDown(self): self.tmp.cleanup()
    def test_complete_checkout_result_verification_handoff(self):
        draft=self.live.prepare('session',self.brief);self.assertEqual(draft['state'],'awaiting_checkout')
        self.b.funded=True;self.live.refresh('session');result=self.live.refresh('session')
        self.assertTrue(result['verification']['passed'])
        self.assertIn('market.near.ai',self.live.accept_link('session',result['verification']['sha256'],result['version'],result['assignment_id'])['url'])
        self.assertNotIn('create_job',[c[0] for c in self.b.calls])
    def test_duplicate_and_timeout_keep_same_request(self):
        self.b.timeout=True
        with self.assertRaises(TimeoutError):self.live.prepare('session',self.brief)
        self.live.prepare('session',self.brief);self.live.prepare('session',self.brief)
        self.assertEqual(len(set(c[1]['client_request_id'] for c in self.b.calls if c[0]=='prepare_job')),1)
    def test_budget_invalid_and_repriced_refused(self):
        for p in ['5.01','NaN','Infinity','-1','0','0.001']:
            with self.subTest(p=p),self.assertRaises(LiveError):self.live.prepare('session',{**self.brief,'quoted_price':p})
        self.b.price='1.00'
        with self.assertRaises(LiveError):self.live.prepare('session',self.brief)
        self.assertNotIn('approval_url',self.store.get('pilot:frbl'))
    def test_unauthenticated_cannot_read_or_create(self):
        with self.assertRaises(LiveError):self.live.job('other')
        with self.assertRaises(LiveError):self.live.prepare('other',self.brief)
    def test_atomic_compare_and_swap(self):
        self.assertTrue(self.store.cas('x',None,{'v':1}));self.assertFalse(self.store.cas('x',None,{'v':2}))
        self.assertFalse(self.store.cas('x',{'v':2},None));self.assertEqual(self.store.get('x'),{'v':1})
    def test_changed_artifact_cannot_be_accepted(self):
        self.live.prepare('session',self.brief);self.b.funded=True;self.live.refresh('session');self.live.refresh('session')
        with self.assertRaises(LiveError):self.live.accept_link('session','old-digest')
        self.assertNotIn('accept_result',[x[0] for x in self.b.calls])
    def test_oauth_state_browser_bound_single_use(self):
        from urllib.parse import urlsplit,parse_qs
        state=parse_qs(urlsplit(self.live.start('session')).query)['state'][0]
        with self.assertRaises(LiveError):self.live.callback('other','code',state)
        with patch('relay.live.remote',return_value=({'access_token':'new','expires_in':600},{})):
            self.live.callback('session','code',state)
            with self.assertRaises(LiveError):self.live.callback('session','code',state)
    def test_links_and_artifact_claims(self):
        for url in ['http://market.near.ai/x','https://market.near.ai.evil/x','https://evil@market.near.ai/x','javascript:alert(1)']:
            with self.assertRaises(LiveError):market_link(url)
        self.assertFalse(verify_artifact('No sources')['passed'])
        self.assertIn('buyer must review',verify_artifact('No sources')['scope'])


class LiveHTTPTests(unittest.TestCase):
    def test_private_boundary_cookie_csrf_and_no_paid_routes(self):
        import json
        import threading
        import urllib.request
        import urllib.error
        from http.server import ThreadingHTTPServer
        from relay.live_server import Handler
        with tempfile.TemporaryDirectory() as tmp:
            state=SQLiteState(Path(tmp)/'state.db')
            app=Live(state,'http://127.0.0.1:8767','client')
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            url='http://127.0.0.1:'+str(server.server_port)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def request(path,data=None,headers=None):
                req=urllib.request.Request(url+path,data=data,headers={'Host':'127.0.0.1:8767',**(headers or {})})
                try: response=urllib.request.urlopen(req)
                except urllib.error.HTTPError as e: response=e
                return response.status,response.headers,json.load(response)
            try:
                with patch('relay.live_server.configured',return_value=app):
                    status,headers,body=request('/api/live/status')
                    self.assertFalse(body['connected']);self.assertIn('HttpOnly',headers['Set-Cookie'])
                    self.assertIn('SameSite=Lax',headers['Set-Cookie'])
                    self.assertEqual(request('/api/live/prepare',b'{}',{'Content-Type':'application/json','Origin':'https://evil.example'})[0],403)
                    good={'Content-Type':'application/json','Origin':app.origin}
                    self.assertEqual(request('/api/live/pay',b'{}',good)[0],404)
                    self.assertEqual(request('/api/live/prepare',b'[]',good)[0],400)
                    self.assertEqual(request('/api/live/prepare',b'x'*16385,good)[0],413)
                    self.assertEqual(request('/api/live/prepare',b'{}',good)[0],400)
                    self.assertEqual(request('/api/live/callback?code=x&state=missing')[0],400)
                    self.assertEqual(request('/api/live/status',headers={'Host':'attacker.example'})[0],403)
                    result=request('/api/live/connect',b'{}',good)
                    self.assertEqual(result[0],200);self.assertTrue(result[2]['url'].startswith('https://market.near.ai/oauth/authorize?'))
            finally:server.shutdown();server.server_close();thread.join()

    def test_hosted_requires_durable_store(self):
        from relay.live_server import configured
        with patch.dict('os.environ',{'VERCEL':'1'},clear=True),self.assertRaises(LiveError): configured()

    def test_redis_compare_and_swap_is_one_atomic_script(self):
        from relay.live import RedisState
        state=RedisState('https://test.upstash.io','test-only')
        with patch('relay.live.remote',return_value=({'result':1},{})) as call:
            self.assertTrue(state.cas('job',None,{'a':1}))
            command=call.call_args[0][1]
            self.assertEqual(command[0],'EVAL');self.assertEqual(command[3],'forge-live:job')
            self.assertIn("redis.call('SET'",command[1])

    def test_mcp_protocol_and_tool_allowlist(self):
        from relay.live import Buyer
        replies=[({'result':{}},{}),({},{}),({'result':{'tools':[{'name':'marketplace__whoami'}]}},{}),({'result':{'content':[{'type':'text','text':'{"user":{"handle":"frbl"}}'}]}},{})]
        with patch('relay.live.remote',side_effect=replies) as call:
            self.assertEqual(Buyer('private-test').call('whoami',{})['user']['handle'],'frbl')
            self.assertEqual(call.call_args_list[1][0][1]['method'],'notifications/initialized')
        with self.assertRaises(LiveError):Buyer('private-test').call('create_job',{})

class DeviceConnectionTests(unittest.TestCase):
    def test_code_stays_server_side_and_poll_is_throttled(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=SQLiteState(Path(tmp)/'state.db')
            app=Live(store,'https://forge.example','client',buyer_factory=lambda token:FakeBuyer())
            reply={'device_code':'private-device-code','user_code':'ABCD-EFGH','verification_uri_complete':'https://market.near.ai/oauth/device?user_code=ABCD-EFGH','expires_in':900,'interval':5}
            with patch('relay.live.remote',return_value=(reply,{})):
                public=app.device_start('browser-a')
            self.assertNotIn('private-device-code',str(public))
            with patch('relay.live.remote') as remote:
                self.assertTrue(app.device_poll('browser-a')['pending']);remote.assert_not_called()
            with self.assertRaises(LiveError):app.device_poll('browser-b')
            old=store.get('device:browser-a');store.cas('device:browser-a',old,{**old,'next_poll':0})
            with patch('relay.live.remote',return_value=({'access_token':'test-only','expires_in':600},{})):
                self.assertTrue(app.device_poll('browser-a')['connected'])
            self.assertIsNone(store.get('device:browser-a'))
            self.assertEqual(store.get('session:browser-a')['handle'],'frbl')

    def test_draft_status_read_does_not_replay_changed_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=SQLiteState(Path(tmp)/'state.db');buyer=FakeBuyer();app=Live(store,'http://127.0.0.1:8767','client',buyer_factory=lambda token:buyer)
            store.cas('session:s',None,{'token':'test','expires':time.time()+3600})
            store.cas('pilot:frbl',None,{'request':{'client_request_id':'original'},'draft_id':'5364a757-28c8-5fa3-bb9c-1d13c160e523','state':'awaiting_checkout'})
            app.refresh('s')
            self.assertEqual([name for name,args in buyer.calls],['get_draft_status'])

if __name__=='__main__':unittest.main()
