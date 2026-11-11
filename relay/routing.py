"""Bounded, explainable multi-provider proposals. No dispatch or payment authority."""
from itertools import combinations
from urllib.parse import urlsplit
from relay.core import match, money, digest


def identity(p):
    # Only exact advertised endpoint/operator matches; different domains do not prove independence.
    endpoint=p.get('endpoint')
    if endpoint:
        u=urlsplit(endpoint)
        return ('endpoint',u.hostname,(u.path or '/').rstrip('/'))
    if p.get('operator_group'):
        return ('operator',p['market'],p['operator_group'])
    return ('listing',p['id'])


def route_proposals(request, providers, limit=5):
    required=set(request['capabilities'])
    candidates=[r for r in match(request,providers) if r['status']!='EXCLUDED' and r['matched_capabilities']]
    # Bound combinatorial work; deterministic catalog ranking determines the shortlist.
    buckets={}
    for candidate in candidates:
        buckets.setdefault(candidate['provider']['market'], []).append(candidate)
    candidates=[]
    while len(candidates)<24 and any(buckets.values()):
        for market in sorted(buckets):
            if buckets[market] and len(candidates)<24:
                candidates.append(buckets[market].pop(0))
    proposals=[]
    for size in range(1,min(3,len(required),len(candidates))+1):
        for group in combinations(candidates,size):
            ps=[r['provider'] for r in group]
            if len({identity(p) for p in ps}) != size:continue
            covered=set().union(*(set(r['matched_capabilities']) for r in group))
            if covered != required:continue
            # Every provider must contribute a capability no other member supplies.
            if size>1 and any(set().union(*(set(other['matched_capabilities']) for other in group if other is not r))==required for r in group):continue
            complete_price=all(p.get('price') is not None and p.get('currency')==request['currency'] and p.get('price_basis')=='per_job' for p in ps)
            total=sum((money(p['price']) for p in ps),money('0')) if complete_price else None
            if total is not None and total>money(request['budget']):continue
            # Conservative sequential bound. Parallel delivery cannot be assumed from capability labels.
            complete_time=all(p.get('delivery_hours') is not None for p in ps)
            hours=sum(p['delivery_hours'] for p in ps) if complete_time else None
            if hours is not None and hours>request['max_hours']:continue
            markets=sorted({p['market'] for p in ps})
            unknowns=sorted(set(x for r in group for x in r['unknowns'] if not x.startswith('Not established by listing:')))
            unknowns.append('Capability labels do not establish input/output compatibility or execution order.')
            if len(markets)>1:unknowns.append('Cross-market data sharing, subcontracting and settlement terms need confirmation.')
            if total is None:unknowns.append('Total job cost cannot be established from these listings.')
            if hours is None:unknowns.append('End-to-end delivery time is not established.')
            key={'request':request,'providers':ps}
            proposals.append({'id':'route-'+digest(key)[:20],'mode':'LOCAL_PROPOSAL_ONLY',
                'providers':ps,'markets':markets,'cross_market':len(markets)>1,
                'assignments':[{'provider_id':r['provider']['id'],'capabilities':r['matched_capabilities']} for r in group],
                'advertised_total':str(total) if total is not None else None,'currency':request['currency'],
                'sequential_hours':hours,'unknowns':unknowns,'execution_allowed':False,'payment_allowed':False,
                'interface_gaps':sum((2 if p.get('source_kind')=='registry' else 1) for p in ps if p.get('source_kind') in {'registry','directory'} and not set(str(x).lower() for x in p.get('protocols',[])) & {'a2a','mcp','rest_api'}),
                'listing_review_count':sum(r['status']=='REVIEW' for r in group)})
    proposals.sort(key=lambda r:(len(r['providers']),r['interface_gaps'],r['listing_review_count'],len(r['unknowns']),r['id']))
    # Surface both simple and cross-market alternatives, without disguising unsupported routes as ready.
    simple=[p for p in proposals if not p['cross_market']]
    cross=[p for p in proposals if p['cross_market']]
    selected=(simple[:2]+cross[:3]) if cross else simple[:limit]
    return {'routes':selected[:limit], 'eligible_listings_considered':len(candidates),
            'search_limit':24,'maximum_providers':3,'complete_routes_found':len(proposals),
            'note':'Proposals cover capability labels only. No provider selected, contacted, or authorized.'}
