import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from relay import store
from relay.near import get_json,parse_agents,parse_board,add_pricing,NearSession,NearError,BOARD_PATH

A='11111111-1111-1111-1111-111111111111'
O='22222222-2222-2222-2222-222222222222'
TOKEN='aat_'+'a'*32

def agent(**kwargs):
    d={'agent_id':A,'owner_account_id':O,'handle':'example','name':'Research agent','description':'Research and extract facts','listing_status':'live','available_now':True,'availability':'available','sla_seconds':3600,'delivered_jobs':4,'payable_with':['USDC']}
    d.update(kwargs);return d

def job(**kwargs):
    d={'jobId':A,'title':'Research facts','description':'Use cited public sources','isPrivate':False,'isTestRun':False,'status':'open','jobKind':'standard','currentMaxSlots':1,'budgetAmount':'10','budgetToken':'USDC','minBuilderVerification':'none'}
    d.update(kwargs);return d

class NearParsingTests(unittest.TestCase):
    def test_structured_availability_and_owner(self):
        p=parse_agents({'agents':[agent()]},'hash')[0]
        self.assertEqual(p['operator_group'],O);self.assertEqual(p['delivered_jobs'],4);self.assertEqual(p['delivery_hours'],1)
        self.assertFalse(p['execution_verified'])
        p=parse_agents({'agents':[agent(available_now=None)]},'hash')[0]
        self.assertEqual(p['availability'],'unknown')
        p=parse_agents({'agents':[agent(availability='suspended')]},'hash')[0]
        self.assertEqual(p['availability'],'unavailable')
    def test_only_live_agents(self):
        self.assertEqual(parse_agents({'agents':[agent(listing_status='draft')]},'hash'),[])
    def test_pricing_requires_matching_live_default(self):
        p=parse_agents({'agents':[agent()]},'hash')[0]
        plan={'agent_id':A,'is_default':True,'listing_status':'live','model':'per_call','price_amount':'0.50'}
        p=add_pricing(p,[plan],'pricehash')
        self.assertEqual((p['price'],p['currency'],p['price_basis']),('0.50','USDC','per_call'))
        p=parse_agents({'agents':[agent(payable_with=['USD','USDC'])]},'hash')[0]
        self.assertIsNone(add_pricing(p,[plan],'pricehash')['currency'])
    def test_private_test_closed_full_and_competition_jobs_excluded(self):
        rows=[job(),job(isPrivate=True),job(isTestRun=True),job(currentMaxSlots=0),job(status='completed'),job(jobKind='competition')]
        p=parse_board({'jobs':rows},'hash')
        self.assertEqual(len(p),1);self.assertEqual(p[0]['price_basis'],'posted_budget_not_awarded')
        self.assertEqual(p[0]['subcontracting_permission'],'UNKNOWN')
    def test_empty_authenticated_board_is_valid(self):
        self.assertEqual(parse_board({'jobs':[]},'hash'),[])
    def test_schema_drift_fails_closed(self):
        for payload in [{}, {'jobs':None}, {'jobs':'not a list'}]:
            with self.assertRaises(NearError):parse_board(payload,'hash')

class NearBoundaryTests(unittest.TestCase):
    def test_no_write_path_or_arbitrary_host(self):
        with patch('urllib.request.build_opener') as opener:
            for path in ['/v1/jobs','/v1/auth/signin','/v1/assignments/'+A+'/start','/mcp/pro','https://evil.example','/v1/jobs/board?kind=competition']:
                with self.assertRaises(NearError):get_json(path,TOKEN)
            opener.assert_not_called()
    def test_credential_never_sent_to_catalog(self):
        with patch('urllib.request.build_opener') as opener:
            with self.assertRaises(NearError):get_json('/v1/agents?category=research&limit=20&offset=0',TOKEN)
            opener.assert_not_called()
    def test_transport_is_get_and_fixed_origin(self):
        response=Mock();response.headers={'Content-Type':'application/json'};response.read.return_value=b'{"jobs":[]}'
        context=Mock();context.__enter__=Mock(return_value=response);context.__exit__=Mock(return_value=False)
        opener=Mock();opener.open.return_value=context
        with patch('urllib.request.build_opener',return_value=opener):get_json(BOARD_PATH,TOKEN)
        req=opener.open.call_args.args[0]
        self.assertEqual(req.get_method(),'GET');self.assertEqual(req.full_url,'https://market.near.ai'+BOARD_PATH)
    def test_session_memory_only_and_disconnect(self):
        with tempfile.TemporaryDirectory() as td,patch.object(store,'DATA',Path(td)),patch('relay.near.get_json',return_value=({'jobs':[job()]},'hash')):
            s=NearSession();status=s.connect(TOKEN)
            self.assertTrue(status['connected']);self.assertNotIn(TOKEN,json.dumps(status))
            self.assertNotIn(TOKEN,(Path(td)/'relay.sqlite3').read_bytes().decode('latin1'))
            self.assertFalse(s.disconnect()['connected'])
            with self.assertRaises(NearError):s.refresh()
    def test_rejected_token_is_not_retained(self):
        s=NearSession()
        with patch('relay.near.get_json',side_effect=NearError('NEAR returned HTTP 401.')):
            with self.assertRaises(NearError):s.connect(TOKEN)
        self.assertFalse(s.status()['connected'])
    def test_passwords_and_wallet_keys_are_rejected_before_network(self):
        with patch('relay.near.get_json') as request:
            for token in ['password','0x'+'a'*64,None,'aat_bad']:
                with self.assertRaises(NearError):NearSession().connect(token)
            request.assert_not_called()
