import importlib.util
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from scripts.prepare_vercel import public_rows

spec=importlib.util.spec_from_file_location('hosted',Path(__file__).resolve().parents[1]/'deploy/vercel/api/index.py')
hosted=importlib.util.module_from_spec(spec);spec.loader.exec_module(hosted)

class HostedTests(unittest.TestCase):
    def test_export_excludes_authenticated_and_unknown_fields(self):
        rows=[{'id':'a','market':'near','kind':'supply','token':'secret'},
              {'market':'near','kind':'demand','evidence_type':'PUBLIC_API'},
              {'market':'taskmarket','kind':'demand','evidence_type':'AUTHENTICATED_PUBLIC_BOARD_API'},
              {'market':'other','kind':'supply'}]
        self.assertEqual(public_rows(rows),[{'id':'a','market':'near','kind':'supply'}])

    def test_no_credential_payment_or_write_routes(self):
        for path in ['near/connect','near/refresh','plan','route-plan','refresh','pay','dispatch']:
            self.assertEqual(hosted.dispatch('POST','/api/'+path,{} )[0],404)

    def test_snapshot_and_match_are_stateless(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(hosted,'ROOT',Path(tmp)):
            p=Path(tmp)/'catalog.json';p.write_text(json.dumps({'records':[],'generated_at':'test'}));before=p.read_bytes()
            status,result=hosted.dispatch('POST','/api/match',{'title':'Research task','capabilities':['research']})
            self.assertEqual(status,200);self.assertEqual(result['matches'],[])
            self.assertEqual(p.read_bytes(),before);self.assertEqual(len(list(Path(tmp).iterdir())),1)

    def test_http_boundary(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),hosted.handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url='http://127.0.0.1:'+str(server.server_port)
        def post(origin,body=b'{}',kind='application/json',path='/api/match'):
            req=urllib.request.Request(url+path,data=body,headers={'Origin':origin,'Content-Type':kind})
            try:
                with urllib.request.urlopen(req) as r:return r.status,json.load(r)
            except urllib.error.HTTPError as e:return e.code,json.load(e)
        try:
            self.assertEqual(post('https://evil.example')[0],403)
            self.assertEqual(post(url,kind='text/plain')[0],415)
            self.assertEqual(post(url,body=b'x'*16385)[0],413)
            self.assertEqual(post(url,body=b'{')[0],400)
            self.assertEqual(post(url,path='/api/near/connect')[0],404)
            with urllib.request.urlopen(url+'/api/health') as r:self.assertFalse(json.load(r)['payment_enabled'])
        finally:server.shutdown();server.server_close();thread.join()
