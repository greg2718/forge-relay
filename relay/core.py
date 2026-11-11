"""Canonical records and conservative, explainable matching. No network or wallets."""
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation

CAPABILITIES = {
    'research': r'\bresearch\b|sourced (?:report|brief)|fact.check',
    'web_search': r'web search|search the web',
    'extraction': r'extract|scrap|page.*json|document.*json',
    'data_cleanup': r'clean(?:up|ing|s)?|dedup|normaliz',
    'verification': r'verif|validation|fact.check|audit|review',
    'coding': r'code generation|coding|software development|build.{0,40}(?:app|game)|programming',
    'media': r'video|image|poster|voice|cinematic',
    'onchain_research': r'on.chain|wallet|treasury|token|blockchain',
}

def now():
    return datetime.now(timezone.utc).isoformat()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return dt

def money(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('Amount must be a non-negative decimal')
    if not result.is_finite() or result < 0 or result > Decimal('1000000'):
        raise ValueError('Amount must be finite and between 0 and 1000000')
    return result

def infer_capabilities(text):
    return sorted(key for key, pattern in CAPABILITIES.items() if re.search(pattern, text, re.I))

def validate_request(data):
    allowed = {'title', 'capabilities', 'budget', 'currency', 'max_hours', 'provider_type', 'source_market', 'source_url', 'markets'}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError('Unknown request fields')
    if not isinstance(data.get('title'), str):
        raise ValueError('Task title must be text')
    title = data['title'].strip()
    if not 3 <= len(title) <= 500:
        raise ValueError('Use a task title between 3 and 500 characters')
    caps = data.get('capabilities', [])
    if not isinstance(caps, list) or not caps or any(not isinstance(c,str) or c not in CAPABILITIES for c in caps):
        raise ValueError('Choose at least one supported capability')
    currency = data.get('currency', 'USD')
    if currency not in {'USD', 'USDC', 'NEAR', 'OUSD'}:
        raise ValueError('Unsupported currency')
    budget = str(money(data.get('budget', '25')))
    hours = data.get('max_hours', 24)
    if type(hours) is not int or not 1 <= hours <= 168:
        raise ValueError('Delivery window must be 1–168 hours')
    kind = data.get('provider_type', 'agent')
    if kind not in {'agent', 'api', 'either'}:
        raise ValueError('Choose agent, API or either')
    if data.get('source_market', 'local') not in {'local','near','circle','taskmarket','tako','agentmarket','olas'}:
        raise ValueError('Unsupported task source')
    if not isinstance(data.get('source_url', ''), str) or len(data.get('source_url', '')) > 2000:
        raise ValueError('Source URL must be bounded text')
    markets=data.get('markets', ['near','circle','taskmarket','tako','agentmarket','olas'])
    if not isinstance(markets,list) or not markets or any(not isinstance(m,str) or m not in {'near','circle','taskmarket','tako','agentmarket','olas'} for m in markets):
        raise ValueError('Choose at least one supported marketplace')
    return {'markets': sorted(set(markets)), 'title': title, 'capabilities': sorted(set(caps)), 'budget': budget, 'currency': currency,
            'max_hours': hours, 'provider_type': kind, 'source_market': data.get('source_market', 'local'),
            'source_url': data.get('source_url', ''), 'mode': 'LOCAL_PLAN_ONLY'}

def match(request, providers, at=None):
    """Listings are claims, never quotes. No candidate is authorized for execution."""
    at = timestamp(at or now())
    results = []
    for p in providers:
        if p['kind'] != 'supply' or p['market'] not in request.get('markets', [p['market']]):
            continue
        reasons, blockers, unknowns = [], [], list(p.get('evidence_notes', []))
        discovery_only = p.get('discovery_only', False)
        missing = sorted(set(request['capabilities']) - set(p['capabilities']))
        matched = sorted(set(request['capabilities']) & set(p['capabilities']))
        if matched:
            reasons.append('Listing mentions: ' + ', '.join(matched))
        if missing:
            unknowns.append('Not established by listing: ' + ', '.join(missing))
        if request['provider_type'] != 'either' and p['provider_type'] != request['provider_type']:
            blockers.append('Provider type differs from requested ' + request['provider_type'])
        try:
            age = at - timestamp(p['observed_at'])
            if age > timedelta(hours=24) or age < timedelta(minutes=-5):
                unknowns.append('Source observation is stale or has an invalid future timestamp')
        except (ValueError, TypeError):
            unknowns.append('Observation freshness is unknown')
        if p.get('availability') == 'unavailable':
            blockers.append('Listing reports unavailable')
        elif p.get('availability') != 'available':
            unknowns.append('Current availability is unconfirmed')
        price = p.get('price')
        if price is None:
            unknowns.append('Price is unknown')
        elif p.get('currency') != request['currency']:
            unknowns.append('Currency differs; no conversion or price equivalence assumed')
        elif p.get('price_basis') != 'per_job':
            unknowns.append('Per-call/from pricing is not a complete job quote')
        elif money(price) > money(request['budget']):
            blockers.append('Advertised job price exceeds budget')
        else:
            reasons.append('Advertised job price is within budget; binding quote still needed')
        if p.get('delivery_hours') is None:
            unknowns.append('Delivery window is unconfirmed')
        elif p['delivery_hours'] > request['max_hours']:
            blockers.append('Advertised delivery window exceeds task deadline')
        if not p.get('delivered_jobs'):
            unknowns.append('No completed-job evidence established')
        unknowns.append('Provider ownership and independence need confirmation')
        if request['source_market'] != 'local' and request['source_market'] != p['market']:
            unknowns.append('Cross-market subcontracting and data-sharing permission not established')
        score = round(100 * len(matched) / len(request['capabilities']))
        status = 'EXCLUDED' if blockers else ('CANDIDATE' if not missing and not discovery_only else 'REVIEW')
        results.append({'provider': p, 'status': status, 'capability_coverage': score,
                        'reasons': reasons, 'blockers': blockers, 'unknowns': unknowns,
                        'matched_capabilities': matched, 'missing_capabilities': missing,
                        'execution_allowed': False, 'payment_allowed': False})
    order = {'CANDIDATE': 0, 'REVIEW': 1, 'EXCLUDED': 2}
    return sorted(results, key=lambda r: (order[r['status']], -r['capability_coverage'], r['provider']['id']))
