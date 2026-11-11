import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from relay import store
from relay.core import digest
from relay.demo import run_demo, verify_bundle, accept, load, directory, worker
from relay.demo_worker import verify

class DemoTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.patch=patch.object(store,'DATA',Path(self.temp.name));self.patch.start()
    def tearDown(self):self.patch.stop();self.temp.cleanup()
    def test_actual_worker_handoffs_rejection_revision_and_acceptance(self):
        b=run_demo(True)
        self.assertEqual([v['result'] for v in b['verifications']],['FAIL','PASS'])
        self.assertEqual(len(b['handoffs']),5)
        self.assertNotIn('acceptance',b)
        verified=verify_bundle(b)
        with self.assertRaises(ValueError):accept(b['id'],'wrong-revision')
        accepted=accept(b['id'],verified['artifact_sha256'])
        self.assertEqual(accepted,accept(b['id'],verified['artifact_sha256']))
        self.assertFalse(accepted['acceptance']['payment_executed'])
        self.assertEqual(load(b['id']),accepted)
        accepted['acceptance']['artifact_sha256']='tampered'
        with self.assertRaises(ValueError):verify_bundle(accepted)
    def test_clean_run_and_mutated_artifact(self):
        b=run_demo(False);self.assertEqual(len(b['artifacts']),1);verify_bundle(b)
        a=copy.deepcopy(b['artifacts'][-1]);a['rows'][0]['price']='999'
        self.assertEqual(verify(a,b['snapshot'],b['task'])['result'],'FAIL')
        a=copy.deepcopy(b['artifacts'][-1]);a['rows'][1]=a['rows'][0]
        self.assertEqual(verify(a,b['snapshot'],b['task'])['result'],'FAIL')
        b['artifacts'][-1]['rows'][0]['source_url']='https://fake.example'
        with self.assertRaises(ValueError):verify_bundle(b)
    def test_chain_and_handoff_corruption_even_if_resealed(self):
        for target in ['event','handoff']:
            b=run_demo(False)
            if target=='event':b['events'][0]['details']['task_sha256']='bad'
            else:b['handoffs'][0]['response']['output']['rows']=[]
            b['sealed_payload_sha256']=digest({k:v for k,v in b.items() if k not in {'sealed_payload_sha256','acceptance'}})
            with self.assertRaises(ValueError):verify_bundle(b)
    def test_path_and_worker_allowlist(self):
        with self.assertRaises(ValueError):directory('../../outside')
        with self.assertRaises(ValueError):worker('arbitrary-command',{},'demo')
        with self.assertRaises(ValueError):run_demo('yes')
