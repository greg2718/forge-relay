import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from relay import store
from relay.catalogs import parse_tako, parse_agentmarket, parse_olas, safe_https, public_document
from relay.sources import VisibleHTML
from relay.core import validate_request, match
from relay.routing import route_proposals
from relay.workflow import route_plan
from test_relay import provider, request

class CatalogTests(unittest.TestCase):
    def test_tako_excludes_code_projects_and_preserves_unknown_price(self):
        a={'name':'Researcher','slug':'researcher','description':'Research facts','kind':'HOSTED','protocols':['A2A'],'endpoint':'https://example.org/a2a','pricing':{'model':'FREE'},'skills':[]}
        rows=parse_tako({'agents':[a,dict(a,kind='PROJECT',slug='project'),a]},'hash')
        self.assertEqual(len(rows),1);self.assertIsNone(rows[0]['price'])
        self.assertTrue(rows[0]['discovery_only']);self.assertEqual(rows[0]['protocols'],['A2A'])
    def test_directory_excludes_demo_and_untyped_records(self):
        a={'name':'Researcher','slug':'researcher','description':'Research facts','types':['agent'],'demo':False,'claimed':False,'interfaces':['web'],'pricing':{'display':'Free'}}
        rows=parse_agentmarket({'organic':[a,dict(a,demo=True,slug='demo'),dict(a,types=['web_app'],slug='web')]},'hash')
        self.assertEqual(len(rows),1);self.assertFalse(rows[0]['listing_claimed']);self.assertIsNone(rows[0]['price'])
        self.assertTrue(any('human use' in x for x in rows[0]['evidence_notes']))
    def test_registry_not_hireability(self):
        d=VisibleHTML();d.feed('<p>Research Service — service ID 49. Research reports.</p>')
        p=parse_olas(d,'hash')[0]
        self.assertEqual(p['source_kind'],'registry');self.assertTrue(p['discovery_only'])
        r=match(validate_request(request(capabilities=['research'])),[p])[0]
        self.assertEqual(r['status'],'REVIEW')
    def test_catalog_url_allowlist_and_untrusted_endpoints(self):
        for u in ['https://example.org/private','https://takoapi.com/api/invoke','https://www.agentmarket.trade/api/search?q=secret']:
            with self.assertRaises(ValueError):public_document(u)
        for u in ['javascript:alert(1)','https://user:pass@example.org',None]:self.assertIsNone(safe_https(u))

class RouteTests(unittest.TestCase):
    def setUp(self):
        self.a=provider(id='near:a',capabilities=['research'])
        self.b=provider(id='tako:b',market='tako',capabilities=['extraction'])
        self.req=validate_request(request(capabilities=['research','extraction']))
    def routes(self,ps,req=None):return route_proposals(req or self.req,ps)['routes']
    def test_cross_market_assignments_and_total(self):
        r=self.routes([self.a,self.b])[0]
        self.assertTrue(r['cross_market']);self.assertEqual(r['advertised_total'],'24')
        self.assertFalse(any(x.startswith('Not established by listing:') for x in r['unknowns']));self.assertEqual(len(r['assignments']),2);self.assertFalse(r['execution_allowed']);self.assertFalse(r['payment_allowed'])
    def test_combined_budget_and_sequential_deadline(self):
        self.assertEqual(self.routes([dict(self.a,price='20'),self.b]),[])
        self.assertEqual(self.routes([dict(self.a,delivery_hours=20),dict(self.b,delivery_hours=20)]),[])
    def test_no_false_complete_route(self):
        self.assertEqual(self.routes([self.a]),[])
    def test_no_redundant_provider(self):
        r=self.routes([dict(self.a,capabilities=['research','extraction']),self.b])
        self.assertTrue(all(len(x['providers'])==1 for x in r))
    def test_same_endpoint_not_two_independent_providers(self):
        self.assertEqual(self.routes([dict(self.a,endpoint='https://same.org/a2a'),dict(self.b,endpoint='https://same.org/a2a/')]),[])
    def test_per_call_and_currency_not_totalled(self):
        for b in [dict(self.b,price_basis='per_call'),dict(self.b,currency='USDC')]:
            r=self.routes([self.a,b])[0];self.assertIsNone(r['advertised_total'])
    def test_market_filter_applies_to_routes(self):
        req=validate_request(request(capabilities=['research','extraction'],markets=['near']))
        self.assertEqual(self.routes([self.a,self.b],req),[])
    def test_fair_market_shortlist(self):
        many=[dict(self.a,id='near:'+str(i)) for i in range(30)]
        self.assertTrue(self.routes(many+[self.b]))
    def test_saved_bundle_revalidated_and_idempotent(self):
        with tempfile.TemporaryDirectory() as td,patch.object(store,'DATA',Path(td)):
            store.save_source('near',[self.a],'OK','test');store.save_source('tako',[self.b],'OK','test')
            req=request(capabilities=['research','extraction'])
            a=route_plan(req,['near:a','tako:b']);b=route_plan(req,['tako:b','near:a'])
            self.assertEqual(a,b);self.assertEqual(a['state'],'QUOTE_REQUEST_READY');self.assertFalse(a['provider_contacted'])
            with self.assertRaises(ValueError):route_plan(req,['near:a','missing'])
