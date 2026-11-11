import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from relay import store
from relay.core import validate_request, match, now
from relay.sources import VisibleHTML, parse_near, parse_circle, parse_taskmarket, record, fetch, NoRedirect
from relay.workflow import plan, rehearsal, verify_artifact, replay


def request(**kw):
    d = dict(title='Extract cited facts', capabilities=['extraction'], budget='25', currency='USD', max_hours=24, provider_type='agent')
    d.update(kw)
    return d


def provider(**kw):
    p = record('near','example','Extraction','Extract public facts','https://market.near.ai/a/example','a'*64)
    p.update(price='12',currency='USD',price_basis='per_job',delivery_hours=2,availability='available')
    p.update(kw)
    return p


def doc(html):
    d=VisibleHTML();d.feed(html);return d

class MatchingTests(unittest.TestCase):
    def result(self, p, **kw):
        return match(validate_request(request(**kw)),[p])[0]
    def test_price_and_deadline_conflicts(self):
        self.assertEqual(self.result(provider(price='26'))['status'],'EXCLUDED')
        self.assertEqual(self.result(provider(delivery_hours=25))['status'],'EXCLUDED')
    def test_currency_never_assumes_parity(self):
        r=self.result(provider(price='100',currency='USDC'))
        self.assertNotEqual(r['status'],'EXCLUDED')
        self.assertTrue(any('Currency differs' in x for x in r['unknowns']))
    def test_per_call_is_not_job_quote(self):
        r=self.result(provider(price='100',price_basis='per_call'))
        self.assertTrue(any('Per-call' in x for x in r['unknowns']))
        self.assertFalse(r['execution_allowed'])
    def test_cross_market_permission_and_stale(self):
        r=self.result(provider(observed_at='2020-01-01T00:00:00Z'),source_market='taskmarket')
        self.assertTrue(any('stale' in x for x in r['unknowns']))
        self.assertTrue(any('subcontracting' in x for x in r['unknowns']))
    def test_missing_capabilities_and_type(self):
        self.assertEqual(self.result(provider(capabilities=['coding']))['status'],'REVIEW')
        self.assertEqual(self.result(provider(provider_type='api'))['status'],'EXCLUDED')
    def test_malformed_requests(self):
        for bad in [dict(title=None),dict(capabilities=[{}]),dict(budget='NaN'),dict(budget='-1'),dict(max_hours=True),dict(source_market='unknown'),dict(extra='x')]:
            with self.subTest(bad=bad),self.assertRaises((ValueError,TypeError)):
                validate_request(request(**bad))

class AdapterTests(unittest.TestCase):
    def test_near_price_window_and_evidence(self):
        d=doc('<h1>Fact Extractor</h1><div>Price</div><div>$12.00</div><div>Delivery window</div><div>2 h</div><div>Delivered jobs</div><div>0</div><div>Availability</div><div>Available</div>')
        p=parse_near(d,'https://market.near.ai/a/example','abc')
        self.assertEqual((p['price'],p['currency'],p['delivery_hours']),('12.00','USD',2))
        self.assertFalse(p['payment_verified'])
    def test_near_per_call_and_unknown_basis(self):
        for suffix,basis in [(' per call','per_call'),('','unknown'),(' per job','per_job')]:
            d=doc('<h1>Extractor</h1><div>Price</div><div>$1.00'+suffix+'</div><div>Delivery window</div><div>2h</div>')
            self.assertEqual(parse_near(d,'https://market.near.ai/a/x','abc')['price_basis'],basis)
    def test_circle_endpoint_prices(self):
        d=doc('<h1>Exa</h1><div>Price $0.007 per use Request POST https://api.exa.ai/search</div><div>Price $0.001 per use Request POST https://api.exa.ai/contents</div>')
        p=parse_circle(d,'abc')
        self.assertEqual([x['price'] for x in p],['0.007','0.001'])
        self.assertTrue(all(x['provider_type']=='api' for x in p))
    def test_demand_open_only_and_unknown_tokens(self):
        a='/tasks/0x'+'a'*64;b='/tasks/0x'+'b'*64
        d=doc(f'<a href="{a}">Open for submissions research bounty 100 TOKEN $500</a><a href="{b}">Closed research</a>')
        p=parse_taskmarket(d,'abc')
        self.assertEqual(len(p),1);self.assertIsNone(p[0]['price'])
        self.assertEqual(p[0]['subcontracting_permission'],'UNKNOWN')
    def test_fetch_scope(self):
        for url in ['http://market.near.ai/a/x','https://example.com/','https://market.near.ai/api/pay','https://user:pass@market.near.ai/a/x','https://taskmarket.dev/tasks/draft']:
            with self.subTest(url=url),self.assertRaises(ValueError): fetch(url)
    def test_redirect_refused(self):
        with self.assertRaises(ValueError): NoRedirect().redirect_request(None,None,302,'',{},'https://example.com')
    def test_script_is_not_listing_evidence(self):
        self.assertNotIn('research',doc('<script>research</script><p>hello</p>').text)

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.patch=patch.object(store,'DATA',Path(self.temp.name));self.patch.start()
    def tearDown(self):
        self.patch.stop();self.temp.cleanup()
    def test_failure_preserves_prior_catalog(self):
        store.save_source('near',[provider()],'OK','test');store.save_source('near',[],'ERROR','failed')
        self.assertEqual(len(store.records()),1)
    def test_plan_idempotence_and_no_dispatch(self):
        store.save_source('near',[provider()],'OK','test')
        a=plan(request(),'near:example');b=plan(request(),'near:example')
        self.assertEqual(a,b);self.assertEqual(len(store.plans()),1)
        self.assertEqual(a['state'],'QUOTE_REQUEST_READY');self.assertFalse(a['payment_executed']);self.assertFalse(a['provider_contacted'])
    def test_blocked_provider_cannot_plan(self):
        store.save_source('near',[provider(price='100')],'OK','test')
        with self.assertRaises(ValueError):plan(request(),'near:example')
    def test_rehearsal_replay_and_tampering(self):
        r=rehearsal();self.assertTrue(r['replay_verified']);self.assertFalse(r['payment_executed'])
        self.assertIn('VERIFICATION_FAILED',[e['next_state'] for e in r['events']])
        bad=copy.deepcopy(r['events']);bad[0]['data']['request_valid']=False
        with self.assertRaises(ValueError):replay(bad)
    def test_artifact_is_structure_only(self):
        r=verify_artifact({'revision':'r1','claims':[{'claim':'Anything','source_url':'https://example.org'}]})
        self.assertEqual(r['result'],'STRUCTURE_PASS');self.assertEqual(r['factual_accuracy'],'NOT_CHECKED');self.assertFalse(r['buyer_acceptance'])
        r=verify_artifact({'revision':'r2','claims':[{'claim':'Anything','source_url':'javascript:alert(1)'}]})
        self.assertEqual(r['result'],'STRUCTURE_FAIL')
    def test_vendor_hashes(self):
        v=Path(__file__).resolve().parents[1]/'vendor';m=json.loads((v/'PROVENANCE.json').read_text())
        for file,sha in m['files'].items():self.assertEqual(hashlib.sha256((v/file).read_bytes()).hexdigest(),sha)

if __name__=='__main__': unittest.main()
