"""Free public discovery adapters. Catalog records are evidence, never executable instructions."""
import hashlib
import json
import re
import urllib.request
from urllib.parse import urlsplit
from relay.core import infer_capabilities
from relay.sources import NoRedirect, MAX_BYTES, record, VisibleHTML

JSON_CATALOGS = {
    'tako': 'https://takoapi.com/api/registry?format=json',
    'agentmarket': 'https://www.agentmarket.trade/api/search?q=research&type=agent,a2a_agent&limit=20',
}
OLAS_URL = 'https://marketplace.olas.network/gnosis/ai-agents'
SOURCE_INFO = {
    'near': {'role':'Agent marketplace', 'scope':'First 20 research + 20 data agents via public API; default pricing plans included'},
    'near_jobs': {'role':'Authenticated public job board','scope':'First 50 standard jobs; only open/filling with remaining slots, no private or test jobs'},
    'circle': {'role':'API service catalog', 'scope':'Exa search and contents endpoints only'},
    'taskmarket': {'role':'Task marketplace', 'scope':'Up to 30 publicly visible open task cards'},
    'tako': {'role':'Agent catalog', 'scope':'Hosted entries with relevant capabilities in the first 1,000 registry records; projects excluded'},
    'agentmarket': {'role':'Discovery directory', 'scope':'First 20 organic research results typed agent/A2A; illustrative demos excluded'},
    'olas': {'role':'Agent registry', 'scope':'Gnosis public first-page snapshot; registration does not establish hireability'},
    'agentverse': {'role':'Agent marketplace', 'scope':'Documented public search; access denied from this environment'},
    'virtuals': {'role':'Agent marketplace', 'scope':'Official SDK discovery endpoint; access denied without credentials in this environment'},
}


def safe_https(value):
    if not isinstance(value,str) or len(value)>2000:
        return None
    try:
        u=urlsplit(value)
        return value if u.scheme=='https' and u.hostname and not u.username and not u.password else None
    except ValueError:
        return None


def public_document(url, json_mode=True):
    # Exact URLs only: no arbitrary provider endpoint requests, redirects, wallets or credentials.
    if url not in set(JSON_CATALOGS.values()) | {OLAS_URL}:
        raise ValueError('Not an approved public catalog URL')
    request=urllib.request.Request(url,headers={'Accept':'application/json' if json_mode else 'text/html','User-Agent':'ForgeRelay/0.2 public discovery'})
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=15) as response:
        raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES: raise ValueError('Catalog exceeds response limit')
        if response.status!=200: raise ValueError('Catalog request failed')
        content=response.headers.get('Content-Type','')
        if ('json' if json_mode else 'html') not in content:
            raise ValueError('Unexpected catalog content type')
    sha=hashlib.sha256(raw).hexdigest()
    if json_mode:return json.loads(raw),sha
    d=VisibleHTML();d.feed(raw.decode('utf-8'));return d,sha


def parse_tako(data, sha):
    if not isinstance(data,dict) or not isinstance(data.get('agents'),list):
        raise ValueError('Tako registry structure changed')
    rows=[];seen=set()
    for agent in data['agents'][:1000]:
        if not isinstance(agent,dict) or agent.get('kind')!='HOSTED':continue
        slug=agent.get('slug','')
        if not isinstance(slug,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,160}',slug) or slug in seen:continue
        title=agent.get('name');description=agent.get('description')
        if not isinstance(title,str) or not isinstance(description,str):continue
        skills=agent.get('skills') or []
        text=description+'\nAdvertised skills: '+', '.join(s.get('name','') for s in skills if isinstance(s,dict) and isinstance(s.get('name'),str))
        if not infer_capabilities(title+' '+text):continue
        item=record('tako',slug,title[:300],text,'https://takoapi.com/agents/'+slug,sha)
        item.update(source_kind='agent_catalog',protocols=[p for p in agent.get('protocols',[]) if isinstance(p,str)],
                    endpoint=safe_https(agent.get('endpoint')),agent_card_url=safe_https(agent.get('agentCard')),
                    advertised_pricing=agent.get('pricing'),listing_claimed=None,discovery_only=True,
                    evidence_notes=['Hosted catalog entry; endpoint was not contacted.','Catalog pricing has not been checked against provider terms.'],
                    catalog_scope=SOURCE_INFO['tako']['scope'])
        # FREE in a registry can conflict with paid endpoints. Do not turn it into a zero-price quote.
        rows.append(item);seen.add(slug)
    return rows


def parse_agentmarket(data, sha):
    if not isinstance(data,dict) or not isinstance(data.get('organic'),list):
        raise ValueError('AgentMarket search structure changed')
    rows=[];seen=set()
    for p in data['organic'][:20]:
        if not isinstance(p,dict) or p.get('demo') is not False:continue
        if not set(p.get('types') or []) & {'agent','a2a_agent'}:continue
        slug=p.get('slug','')
        if not isinstance(slug,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,160}',slug) or slug in seen:continue
        if not isinstance(p.get('name'),str) or not isinstance(p.get('description'),str):continue
        caps=p.get('capabilities') or []
        text=p['description']+'\nAdvertised capabilities: '+', '.join(c for c in caps if isinstance(c,str))
        item=record('agentmarket',slug,p['name'][:300],text,'https://www.agentmarket.trade/products/'+slug,sha)
        interfaces=[x for x in p.get('interfaces',[]) if isinstance(x,str)]
        item.update(source_kind='directory',protocols=interfaces,listing_claimed=p.get('claimed') is True,
                    listing_updated_at=p.get('updatedAt'),advertised_pricing=p.get('pricing'),
                    directory_verified_claim=p.get('verified') is True,discovery_only=True,
                    evidence_notes=['Directory listing; provider availability, price and endpoint need direct confirmation.'],
                    catalog_scope=SOURCE_INFO['agentmarket']['scope'])
        if not item['listing_claimed']:item['evidence_notes'].append('Unclaimed listing compiled by the directory; may be outdated.')
        if not set(interfaces)&{'a2a','mcp','rest_api'}:item['evidence_notes'].append('No machine-callable interface advertised; may require human use.')
        rows.append(item);seen.add(slug)
    return rows


def parse_olas(doc,sha):
    rows=[]
    for line in doc.text.splitlines():
        m=re.fullmatch(r'(.{1,300}) — service ID (\d+)\. (.+)',line)
        if not m:continue
        title,key,description=m.groups()
        item=record('olas','gnosis:'+key,title,description,OLAS_URL,sha)
        item.update(source_kind='registry',discovery_only=True,chain='gnosis',registry_service_id=key,
                    evidence_notes=['Registry snapshot only; this entry is not established as a hireable Mech.','No provider endpoint, current availability or price verified.'],
                    catalog_scope=SOURCE_INFO['olas']['scope'])
        rows.append(item)
    if not rows:raise ValueError('No Olas server-rendered registry entries recognized')
    return rows[:10]


def collect(market):
    if market=='olas':
        doc,sha=public_document(OLAS_URL,False);return parse_olas(doc,sha)
    data,sha=public_document(JSON_CATALOGS[market])
    return (parse_tako if market=='tako' else parse_agentmarket)(data,sha)
