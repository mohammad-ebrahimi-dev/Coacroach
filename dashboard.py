"""Local-only dashboard with a tightly scoped reviewed pilot."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlsplit, parse_qs

from market_tool.dashboard_state import DashboardState
from market_tool.local_dataset import local_records
from market_tool.ninisite_continuous import ContinuousNiniSiteCollector

PAGE = Path(__file__).parent / 'dashboard' / 'index.html'


def make_server(port=8765, *, state=None):
    state = state or DashboardState()
    pilot = ContinuousNiniSiteCollector(state)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def allowed_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def send_data(self, status, body, content_type):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.allowed_host():
                return self.send_data(403, b'Forbidden', 'text/plain')
            if self.path == '/':
                body = PAGE.read_text(encoding='utf-8').replace('__TOKEN__', token).encode('utf-8')
                return self.send_data(200, body, 'text/html; charset=utf-8')
            if urlsplit(self.path).path == '/api/records':
                if not secrets.compare_digest(self.headers.get('X-Dashboard-Token', ''), token):
                    return self.send_data(403, b'Forbidden', 'text/plain')
                params = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                if set(params) - {'offset'} or len(params.get('offset', ['0'])) != 1:
                    return self.send_data(400, b'Invalid page', 'text/plain')
                offset = params.get('offset', ['0'])[0]
                if not offset.isascii() or not offset.isdigit() or len(offset) > 7:
                    return self.send_data(400, b'Invalid page', 'text/plain')
                data = local_records(state.root, offset=int(offset)) if not state.demo else {'counts': {}, 'latest': None, 'records': [], 'has_more': False}
                return self.send_data(200, json.dumps(data, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')
            if self.path == '/api/state':
                snapshot = state.snapshot()
                snapshot['controls']['start'] = not state.demo and not state.attached and pilot.permitted()
                return self.send_data(200, json.dumps(snapshot, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')
            return self.send_data(404, b'Not found', 'text/plain')

        def do_POST(self):
            host = self.headers.get('Host', '')
            if (not self.allowed_host() or self.headers.get('Origin') != f'http://{host}'
                    or not secrets.compare_digest(self.headers.get('X-Dashboard-Token', ''), token)):
                return self.send_data(403, b'Forbidden', 'text/plain')
            if self.path not in ('/api/pause', '/api/resume', '/api/start', '/api/stop'):
                return self.send_data(404, b'Not found', 'text/plain')
            if self.path.endswith('/start'):
                success = False if state.demo else pilot.start()
            elif self.path.endswith('/stop'):
                success = state.stop()
            else:
                success = state.pause() if self.path.endswith('/pause') else state.resume()
            return self.send_data(200 if success else 409, json.dumps({'ok': success}).encode('utf-8'), 'application/json')

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def start_demo(state):
    """Synthetic, explicitly labeled UI demonstration; no HTTP calls."""
    class DemoMonitor:
        delay_seconds = 12
        stop_reason = None
        def get(self, url, *, before_request):
            before_request()
            class Response:
                status_code = 200
                content = b'x' * 256
            return Response()
    state.attach(DemoMonitor(), lambda: True)
    def work():
        while state.checkpoint():
            state.monitored_get('https://example.invalid/discussion/topic/1/example')
            state.count(pages=1, topics_identified=2, topics_examined=1, messages_identified=4, messages_saved=3)
            time.sleep(2)
        if state.attached:
            state.finish()
    threading.Thread(target=work, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description='Local-only collection dashboard')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--demo', action='store_true', help='Show clearly labeled synthetic activity')
    args = parser.parse_args()
    state = DashboardState(demo=args.demo)
    if args.demo:
        start_demo(state)
    server = make_server(args.port, state=state)
    print(f'Dashboard: http://127.0.0.1:{server.server_port}/' + (' (demo)' if args.demo else ''))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        state.detach()
        server.server_close()


if __name__ == '__main__':
    main()
