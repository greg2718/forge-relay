"""Stateless discovery preview. No credentials, storage writes, or outbound requests."""
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
from relay.core import CAPABILITIES, validate_request, match
from relay.routing import route_proposals

ROOT = Path(__file__).resolve().parents[1]


def catalog():
    data = json.loads((ROOT / 'catalog.json').read_text())
    return {**data, 'capabilities': list(CAPABILITIES), 'mode': 'HOSTED_SNAPSHOT',
            'payment_enabled': False, 'dispatch_enabled': False}


def dispatch(method, path, data=None):
    if method == 'GET' and path == '/api/health':
        return 200, {'status': 'ok', 'mode': 'HOSTED_SNAPSHOT', 'payment_enabled': False, 'dispatch_enabled': False}
    if method == 'GET' and path == '/api/catalog':
        return 200, catalog()
    if method == 'POST' and path == '/api/match':
        request = validate_request(data)
        rows = catalog()['records']
        return 200, {'request': request, 'matches': match(request, rows), 'routing': route_proposals(request, rows)}
    return 404, {'error': 'This preview supports catalog discovery and matching only.'}


class handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send_json(self, status, body):
        raw = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.respond('GET')

    def do_POST(self):
        self.respond('POST')

    def respond(self, method):
        try:
            data = None
            if method == 'POST':
                origin = urlsplit(self.headers.get('Origin', ''))
                if origin.scheme not in {'https', 'http'} or origin.netloc != self.headers.get('Host'):
                    return self.send_json(403, {'error': 'Same-origin request required'})
                if origin.scheme == 'http' and origin.hostname != '127.0.0.1':
                    return self.send_json(403, {'error': 'HTTPS required'})
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return self.send_json(415, {'error': 'JSON required'})
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384:
                    return self.send_json(413, {'error': 'Request must be between 1 and 16384 bytes'})
                self.connection.settimeout(5)
                data = json.loads(self.rfile.read(length))
            code, body = dispatch(method, urlsplit(self.path).path, data)
            self.send_json(code, body)
        except (ValueError, TypeError):
            self.send_json(400, {'error': 'Invalid comparison request'})
        except Exception:
            self.send_json(500, {'error': 'Preview unavailable'})
