"""Bounded public GET adapters. Fixed source URLs, no credentials, no arbitrary URL fetches."""
import hashlib
import re
import ssl
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from relay.core import infer_capabilities, now
from relay.store import save_source

CATALOGS = {
    'near': 'https://market.near.ai/discover/all',
    'circle': 'https://agents.circle.com/services/exa',
    'taskmarket': 'https://taskmarket.dev/tasks?status=open',
    'tako': 'https://takoapi.com/api/registry?format=json',
    'agentmarket': 'https://www.agentmarket.trade/api/search?q=research&type=agent,a2a_agent&limit=20',
    'olas': 'https://marketplace.olas.network/gnosis/ai-agents',
}
ALLOWED_HOSTS = {'market.near.ai', 'agents.circle.com', 'taskmarket.dev'}
MAX_BYTES = 2_000_000

class VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.headings = [], [], []
        self.hidden = 0
        self.anchor = None
        self.heading = None

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'svg'}:
            self.hidden += 1
        if self.hidden:
            return
        if tag == 'a':
            self.anchor = [dict(attrs).get('href', ''), []]
        if tag in {'h1', 'h2', 'h3'}:
            self.heading = []
        if tag in {'p','div','li','h1','h2','h3','br','dt','dd','tr'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'svg'}:
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag == 'a' and self.anchor is not None:
            self.links.append((self.anchor[0], ' '.join(' '.join(self.anchor[1]).split())))
            self.anchor = None
        if tag in {'h1','h2','h3'} and self.heading is not None:
            self.headings.append(' '.join(' '.join(self.heading).split()))
            self.heading = None
        if tag in {'p','div','li','h1','h2','h3','dt','dd','tr'}:
            self.parts.append('\n')

    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)
            if self.anchor is not None:
                self.anchor[1].append(text)
            if self.heading is not None:
                self.heading.append(text)

    @property
    def text(self):
        return '\n'.join(line for line in (' '.join(x.split()) for x in ''.join(self.parts).splitlines()) if line)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Source redirected; review the adapter before following it')

def fetch(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in {None,443}:
        raise ValueError('URL is outside public marketplace allowlist')
    if not ((parsed.hostname == 'market.near.ai' and (parsed.path == '/discover/all' or re.fullmatch(r'/a/[a-zA-Z0-9_-]+', parsed.path)))
            or (parsed.hostname == 'agents.circle.com' and parsed.path == '/services/exa')
            or (parsed.hostname == 'taskmarket.dev' and parsed.path == '/tasks' and parsed.query == 'status=open')):
        raise ValueError('Path is outside read-only catalog scope')
    request = urllib.request.Request(url, headers={'User-Agent':'ForgeRelay/0.1 (public listing research; GET only)', 'Accept':'text/html'})
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    with opener.open(request, timeout=15) as response:
        if response.status != 200 or 'text/html' not in response.headers.get('Content-Type',''):
            raise ValueError('Source did not return an HTML listing')
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Source exceeds the bounded response limit')
    doc = VisibleHTML()
    doc.feed(raw.decode('utf-8'))
    return doc, hashlib.sha256(raw).hexdigest()

def record(market, key, title, text, url, sha, kind='supply', provider_type='agent'):
    return {'id':market + ':' + key, 'market':market, 'kind':kind, 'title':title,
            'description':text[:6000], 'source_url':url, 'observed_at':now(), 'source_sha256':sha,
            'evidence_type':'PUBLIC_LISTING', 'capabilities':infer_capabilities(title+' '+text),
            'capability_basis':'KEYWORD_INFERENCE_FROM_LISTING', 'provider_type':provider_type,
            'price':None, 'currency':None, 'price_basis':'unknown', 'delivery_hours':None,
            'delivered_jobs':None, 'availability':'unknown', 'operator_group':None,
            'payment_verified':False, 'execution_verified':False, 'market_state':'unknown'}

def parse_near(doc, url, sha):
    if not doc.headings:
        raise ValueError('NEAR detail page has no title')
    text = doc.text
    if 'Price' not in text or 'Delivery window' not in text:
        raise ValueError('NEAR listing structure changed')
    item = record('near', url.rsplit('/',1)[-1], doc.headings[0], text, url, sha)
    # Review widgets and API boilerplate are not provider capability evidence.
    item['capabilities'] = infer_capabilities(doc.headings[0]+' '+text.split('\nPrice\n')[0])
    price = re.search(r'Price\s*\$([\d,.]+)(?:\s+(per call|per job|per task))?', text)
    if price:
        basis = {'per call':'per_call','per job':'per_job','per task':'per_job'}.get(price[2], 'unknown')
        item.update(price=price[1].replace(',',''), currency='USD', price_basis=basis)
        # Dollar display is not a claim that the provider accepts fiat or that USDC conversion is 1:1.
    delivery = re.search(r'Delivery window\s*(\d+(?:\.\d+)?)\s*(h|d|m)\b', text)
    if delivery:
        item['delivery_hours'] = float(delivery[1]) * {'h':1,'d':24,'m':1/60}[delivery[2]]
    jobs = re.search(r'Delivered jobs\s*(\d+)', text)
    if jobs:
        item['delivered_jobs'] = int(jobs[1])
    if re.search(r'Availability\s*Available',text,re.I):
        item['availability'] = 'available'
    elif re.search(r'Availability\s*(Unavailable|Offline)',text,re.I):
        item['availability'] = 'unavailable'
    return item

def collect_near():
    doc, _ = fetch(CATALOGS['near'])
    candidates = []
    # Curated capability categories, not arbitrary links supplied by a task or model.
    for href, title in doc.links:
        url = urljoin(CATALOGS['near'], href)
        parsed = urlsplit(url)
        if parsed.hostname == 'market.near.ai' and re.fullmatch(r'/a/[a-zA-Z0-9_-]+', parsed.path) and re.search(r'research|extract|csv|data quality|dataset|web page|integration preflight', title, re.I):
            if url not in candidates:
                candidates.append(url)
    if not candidates:
        raise ValueError('No relevant NEAR listing links found; source may require authentication or changed markup')
    rows, errors = [], []
    for url in candidates[:10]:
        try:
            detail, sha = fetch(url)
            rows.append(parse_near(detail, url, sha))
        except Exception as exc:
            errors.append(url.rsplit('/',1)[-1]+': '+str(exc))
    if errors:
        # Fail a partial refresh rather than silently deleting unseen providers.
        raise ValueError('Incomplete detail refresh: ' + '; '.join(errors)[:700])
    return rows

def parse_circle(doc, sha):
    text = doc.text
    if 'Exa' not in text or '/search' not in text or '/contents' not in text:
        raise ValueError('Circle Exa listing structure changed')
    rows = []
    for endpoint, title, cap in [('/search','Exa · web search','web_search'),('/contents','Exa · content extraction','extraction')]:
        # Anchor to the actual request URL near the price, avoiding generic "from" prices.
        pattern = r'Price\s*\$([\d.]+)\s*per use\s*Request\s*POST\s*https://api\.exa\.ai' + re.escape(endpoint)
        price = re.search(pattern, text)
        item = record('circle','exa'+endpoint,title,text,CATALOGS['circle'],sha,provider_type='api')
        item.update(capabilities=[cap], capability_basis='LISTED_ENDPOINT_FUNCTION', operator_group='exa', price_basis='per_call',
                    price=price[1] if price else None, currency='USD' if price else None)
        rows.append(item)
    return rows

def parse_taskmarket(doc, sha):
    rows, seen = [], set()
    for href, text in doc.links:
        if not re.fullmatch(r'/tasks/(?:TSK-[A-Z0-9]+|0x[a-fA-F0-9]{64})',href) or href in seen or 'Open for submissions' not in text:
            continue
        seen.add(href)
        item = record('taskmarket',href.rsplit('/',1)[-1],text[:180],text,urljoin(CATALOGS['taskmarket'],href),sha,kind='demand')
        item['market_state'] = 'OPEN_AS_OBSERVED'
        item['price_basis'] = 'reward_not_guaranteed'
        # Preserve original reward text; tokens and approximate dollar valuations are not binding budgets.
        reward = re.search(r'(\d+(?:\.\d+)?)\s+(USDC|OUSD)\b',text)
        if reward:
            item.update(price=reward[1],currency=reward[2])
        item['subcontracting_permission'] = 'UNKNOWN'
        rows.append(item)
    if not rows:
        raise ValueError('No open task cards recognized; empty/changed source is not proof of no demand')
    return rows[:30]

def refresh(market):
    if market not in CATALOGS:
        raise ValueError('Unknown marketplace')
    try:
        if market in {'tako','agentmarket','olas'}:
            from relay.catalogs import collect
            rows = collect(market)
        elif market == 'near':
            from relay.near import collect_agents
            rows = collect_agents()
        else:
            doc, sha = fetch(CATALOGS[market])
            rows = parse_circle(doc,sha) if market == 'circle' else parse_taskmarket(doc,sha)
        if not rows:
            raise ValueError('No records extracted')
        save_source(market, rows, 'OK', 'Public catalog snapshot; listing claims only. No providers contacted.')
        return {'market':market,'status':'OK','count':len(rows)}
    except Exception as exc:
        detail = str(exc)[:800]
        save_source(market, [], 'ERROR', detail)
        return {'market':market,'status':'ERROR','count':0,'detail':detail}
