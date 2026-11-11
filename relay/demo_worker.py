"""Fixed local worker programs. Deterministic data processing, no model or network calls."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from relay.core import digest

FIELDS = ('id','market','title','capabilities','price','currency','price_basis','source_url','observed_at','source_sha256')
LIMITATIONS = ['Frozen listing evidence; current availability not checked.',
               'Capabilities are listing-derived labels, not verified provider performance.',
               'Per-call prices are not full-job quotes; no currency conversion is assumed.',
               'No marketplace provider was contacted; no payment or buyer acceptance occurred.']


def extract(snapshot, task):
    wanted=set(task['capabilities'])
    eligible=[r for r in snapshot['records'] if wanted.intersection(r['capabilities'])]
    # Round-robin across markets to avoid a first-source monopoly.
    buckets={m:[r for r in eligible if r['market']==m] for m in sorted({r['market'] for r in eligible})}
    chosen=[]
    while len(chosen)<task['max_rows'] and any(buckets.values()):
        for bucket in buckets.values():
            if bucket and len(chosen)<task['max_rows']:chosen.append(bucket.pop(0))
    return {'schema':'relay-extraction/v1','snapshot_sha256':digest(snapshot),'rows':[{k:r.get(k) for k in FIELDS} for r in chosen]}


def compose(extraction, revision):
    return {'schema':'relay-comparison/v1','revision':revision,'snapshot_sha256':extraction['snapshot_sha256'],
            'rows':extraction['rows'],'limitations':LIMITATIONS,'payment_executed':False,'provider_contacted':False}


def verify(artifact, snapshot, task):
    checks=[]
    def check(name,ok):checks.append({'name':name,'pass':bool(ok)})
    check('Artifact schema',artifact.get('schema')=='relay-comparison/v1')
    check('Revision identified',artifact.get('revision') in {'r1','r2'})
    check('Snapshot hash matches frozen input',artifact.get('snapshot_sha256')==digest(snapshot))
    rows=artifact.get('rows',[])
    check('Requested row count',isinstance(rows,list) and task['min_rows']<=len(rows)<=task['max_rows'])
    source={r['id']:r for r in snapshot['records']}
    valid_rows=rows if isinstance(rows,list) else []
    check('No duplicate provider identities',len({r.get('id') for r in valid_rows})==len(valid_rows))
    check('At least two marketplaces',len({r.get('market') for r in valid_rows})>=task['min_markets'])
    for index,row in enumerate(valid_rows):
        original=source.get(row.get('id'))
        check('Row %d is grounded in the snapshot'%(index+1),original is not None and set(row)==set(FIELDS) and all(row[k]==original.get(k) for k in FIELDS))
        check('Row %d meets a requested capability'%(index+1),bool(set(task['capabilities']).intersection(row.get('capabilities',[]))))
        check('Row %d has public citation and timestamp'%(index+1),str(row.get('source_url','')).startswith('https://') and bool(row.get('observed_at')) and bool(row.get('source_sha256')))
    check('Limitations explicitly disclosed',artifact.get('limitations')==LIMITATIONS)
    check('No false execution or payment claim',artifact.get('payment_executed') is False and artifact.get('provider_contacted') is False)
    return {'schema':'relay-verification/v1','result':'PASS' if all(c['pass'] for c in checks) else 'FAIL',
            'artifact_sha256':digest(artifact),'snapshot_sha256':digest(snapshot),'checks':checks,
            'scope':'Snapshot consistency and task acceptance criteria; not independent factual truth or service quality.'}


def main():
    request=json.loads(sys.stdin.read(500000))
    role=request['worker'];payload=request['payload']
    if role=='extractor':result=extract(payload['snapshot'],payload['task'])
    elif role=='writer':result=compose(payload['extraction'],payload['revision'])
    elif role=='verifier':result=verify(payload['artifact'],payload['snapshot'],payload['task'])
    else:raise ValueError('Unknown local worker')
    print(json.dumps({'protocol':'relay-handoff/v1','run_id':request['run_id'],'worker':role,
                      'request_sha256':digest(request),'output':result,'output_sha256':digest(result)}))

if __name__=='__main__':main()
