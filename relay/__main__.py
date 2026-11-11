import argparse
import json
from relay.sources import refresh, CATALOGS
from relay.store import records, runs
from relay.workflow import rehearsal

parser=argparse.ArgumentParser(description='Isolated FORGE Relay research tools; no payments or dispatch')
parser.add_argument('command',choices=['refresh','catalog','rehearsal','demo'])
parser.add_argument('--market',choices=list(CATALOGS))
args=parser.parse_args()
if args.command=='refresh':
    for name in ([args.market] if args.market else CATALOGS):
        result=refresh(name)
        print(json.dumps(result),flush=True)
elif args.command=='catalog':
    print(json.dumps({'records':records(),'sources':runs()},indent=2))
elif args.command=='demo':
    from relay.demo import run_demo
    result=run_demo()
    print(json.dumps({'id':result['id'],'state':result['state'],'artifact_sha256':result['verifications'][-1]['artifact_sha256'],'bundle':'data/demo_runs/'+result['id']+'/bundle.json','verification_results':[v['result'] for v in result['verifications']]},indent=2))
else:
    print(json.dumps(rehearsal(),indent=2))
