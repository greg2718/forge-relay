import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from relay.server import Handler
from relay import store

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.p=patch.object(store,'DATA',Path(self.temp.name));self.p.start()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.port=self.server.server_port
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.p.stop();self.temp.cleanup()
    def call(self,path,body=None,origin=True,host=None):
        c=http.client.HTTPConnection('127.0.0.1',self.port)
        h={'Host':host or '127.0.0.1:'+str(self.port)}
        if body is not None:
            h['Content-Type']='application/json'
            if origin:h['Origin']='http://127.0.0.1:'+str(self.port)
        c.request('GET' if body is None else 'POST',path,None if body is None else json.dumps(body),h)
        r=c.getresponse();data=r.read();status=r.status;c.close();return status,data
    def test_host_origin_and_asset_boundaries(self):
        self.assertEqual(self.call('/health')[0],200)
        self.assertEqual(self.call('/health',host='evil.example')[0],403)
        self.assertEqual(self.call('/api/rehearsal',{},origin=False)[0],403)
        self.assertEqual(self.call('/../relay/server.py')[0],404)
        self.assertEqual(self.call('/api/pay',{})[0],404)
    def test_rehearsal_over_http(self):
        code,data=self.call('/api/rehearsal',{})
        self.assertEqual(code,200);r=json.loads(data)
        self.assertTrue(r['replay_verified']);self.assertFalse(r['payment_executed'])
    def test_invalid_input_returns_client_error(self):
        code,data=self.call('/api/match',{'title':None})
        self.assertEqual(code,400)

    def test_offline_demo_rejects_network_and_credentials(self):
        self.server.demo_only=True
        for path in ['/api/refresh','/api/near/connect','/api/near/refresh']:
            self.assertEqual(self.call(path,{})[0],403)
        self.assertTrue(json.loads(self.call('/api/near/status')[1])['demo_only'])
    def test_demo_run_and_exact_revision_acceptance(self):
        code,raw=self.call('/api/demo/run',{'inject_fault':True})
        self.assertEqual(code,200);run=json.loads(raw)
        self.assertEqual([v['result'] for v in run['verifications']],['FAIL','PASS'])
        self.assertEqual(self.call('/api/demo/accept',{'run_id':run['id'],'artifact_sha256':'wrong'})[0],400)
        code,raw=self.call('/api/demo/accept',{'run_id':run['id'],'artifact_sha256':run['verifications'][-1]['artifact_sha256']})
        self.assertEqual(code,200);self.assertFalse(json.loads(raw)['acceptance']['payment_executed'])
