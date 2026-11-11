"""Recheck a saved evidence bundle offline. Never accepts work or makes a network call."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relay.demo import verify_bundle

parser=argparse.ArgumentParser()
parser.add_argument('bundle',type=Path)
args=parser.parse_args()
result=verify_bundle(json.loads(args.bundle.read_text()))
print(json.dumps({'result':result['result'],'artifact_sha256':result['artifact_sha256'],'scope':result['scope']},indent=2))
