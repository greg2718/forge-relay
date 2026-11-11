"""Build a new, allowlisted deployment folder. Does not deploy or read credentials."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from relay.core import now
from relay.store import records

# Exclude authenticated-board records, plans, private source baselines and all credentials.
FIELDS = {'id','market','kind','title','description','source_url','source_sha256','observed_at',
          'capabilities','capability_basis','provider_type','price','currency','price_basis',
          'delivery_hours','availability','source_kind','evidence_type','evidence_notes',
          'protocols','endpoint','operator_group','discovery_only','delivered_jobs'}
PUBLIC_MARKETS = {'near','circle','taskmarket','tako','agentmarket','olas'}


def public_rows(rows):
    return [{k:v for k,v in r.items() if k in FIELDS} for r in rows
            if r.get('market') in PUBLIC_MARKETS and r.get('kind') in {'supply','demand'}
            and not str(r.get('evidence_type','')).startswith('AUTHENTICATED')
            and not (r.get('market') == 'near' and r.get('kind') == 'demand')]


def prepare(live=False):
    parent = ROOT / 'build'
    if parent.is_symlink(): raise ValueError('Build directory cannot be a symlink')
    parent.mkdir(exist_ok=True)
    target = parent / ('vercel-' + now().replace(':','').replace('.','').replace('+',''))
    target.mkdir()
    for name in ['api/index.py','api/catalog.py','api/match.py','api/health.py','public/index.html','public/workflow.html','public/handoff.html','public/handoff.js','public/sample-evidence.json','public/app.js','vercel.json','.vercelignore']:
        dest=target/name; dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'deploy/vercel'/name,dest)
    if live:
        for name in ['live.html','live.js','live.css']:
            shutil.copyfile(ROOT/'deploy/vercel/public'/name,target/'public'/name)
        (target/'api/live').mkdir()
        for route in ['connect','connection','callback','status','quote','prepare','refresh','accept','disconnect']:
            (target/'api/live'/(route+'.py')).write_text('from relay.live_server import Handler\n\nclass handler(Handler):\n    pass\n')
        config=json.loads((target/'vercel.json').read_text())
        config['functions']={'api/**/*.py':{'maxDuration':60,'includeFiles':'{catalog.json,relay/**,api/**}'}}
        (target/'vercel.json').write_text(json.dumps(config,indent=2))
    shutil.copyfile(ROOT/'web/style.css',target/'public/style.css')
    with (target/'public/style.css').open('a') as f:f.write('\nmain.preview { margin-left: 0; max-width: 1400px; margin-right: auto; margin-left: auto; }\n')
    (target/'relay').mkdir()
    for name in (['__init__.py','core.py','routing.py']+(['live.py','live_server.py'] if live else [])):shutil.copyfile(ROOT/'relay'/name,target/'relay'/name)
    (target/'catalog.json').write_text(json.dumps({'generated_at':now(),'records':public_rows(records())},ensure_ascii=False))
    (target/'pyproject.toml').write_text('[project]\nname = "forge-relay-preview"\nversion = "0.4.0"\nrequires-python = ">=3.12"\ndependencies = []\n')
    manifest={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file()}
    (target/'MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    print(target)
    return target

if __name__ == '__main__':prepare(live='--live' in sys.argv)
