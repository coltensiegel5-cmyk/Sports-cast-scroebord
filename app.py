#!/usr/bin/env python3
"""Sportscast Studio local/hosted scoreboard relay, Python standard library only."""
import hmac
import json
import os
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from html import escape

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get('PORT', '8765'))
HOST = os.environ.get('HOST', '127.0.0.1')
EDIT_KEY = os.environ.get('SPORTSCAST_CONTROL_KEY') or secrets.token_urlsafe(20)
STATE = None
VERSION = 0
LOCK = threading.Lock()

# Do not embed a privileged key into an overlay URL. Only the controller can POST.
class Handler(BaseHTTPRequestHandler):
    server_version = 'Sportscast/1.0'
    def respond(self, content, code=200, ctype='text/html; charset=utf-8'):
        if isinstance(content, str): content = content.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Robots-Tag', 'noindex')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        global STATE, VERSION
        path, _, query = self.path.partition('?')
        if path == '/health':
            return self.respond('ok', ctype='text/plain; charset=utf-8')
        if path == '/api/state':
            with LOCK: payload = {'version': VERSION, 'state': STATE}
            return self.respond(json.dumps(payload), ctype='application/json; charset=utf-8')
        if path in ['/obs', '/overlay']:
            return self.respond((HERE / 'overlay.html').read_bytes())
        if path == '/control':
            params = urllib.parse.parse_qs(query)
            submitted = params.get('key', [''])[0]
            if not hmac.compare_digest(submitted, EDIT_KEY):
                return self.respond(self.landing('That controller code did not match.'), 403)
            html = (HERE / 'controller.html').read_text(encoding='utf-8')
            html = html.replace('__SPORTSCAST_KEY__', json.dumps(EDIT_KEY))
            return self.respond(html)
        if path == '/':
            return self.respond(self.landing())
        self.respond('Not found', 404, 'text/plain; charset=utf-8')

    def landing(self, warning=''):
        alert = f'<p style="color:#ffb7a2">{escape(warning)}</p>' if warning else ''
        return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sportscast Studio</title>
        <style>body{margin:0;background:#0d1729;color:#eaf2ff;font:15px system-ui,sans-serif;min-height:100vh;display:grid;place-items:center}main{padding:32px;background:#17263e;border:1px solid #3b536f;border-radius:16px;max-width:420px;width:90%;box-sizing:border-box}h1{margin:0 0 8px}p{color:#b5c8df;line-height:1.6}input,button{padding:12px;border-radius:9px;font:inherit}input{background:#09182c;border:1px solid #617495;color:white;width:100%;box-sizing:border-box}button{background:#2b60e0;color:white;border:0;margin-top:12px;cursor:pointer}a{color:#9cc6ff}</style>
        <main><h1>▤ Sportscast Studio</h1><p>Enter your private controller code to open the scoreboard controls. The OBS overlay is public and view-only.</p>'''+alert+'''<form action="/control" method="GET"><input name="key" type="password" required placeholder="Controller code" autocomplete="off"/><button>Open Scoreboard Controls</button></form><p>OBS overlay: <a href="/obs">Open scoreboard-only view</a></p></main></html>'''

    def do_POST(self):
        global STATE, VERSION
        if self.path.partition('?')[0] != '/api/state':
            return self.respond('Not found', 404, 'text/plain; charset=utf-8')
        token = self.headers.get('X-Sportscast-Key', '')
        if not hmac.compare_digest(token, EDIT_KEY):
            return self.respond('Unauthorized', 401, 'text/plain; charset=utf-8')
        try:
            n = int(self.headers.get('Content-Length', '0'))
            if n < 2 or n > 64000: raise ValueError('invalid size')
            data = json.loads(self.rfile.read(n).decode('utf-8'))
            if not isinstance(data, dict) or not isinstance(data.get('away'), dict) or not isinstance(data.get('home'), dict):
                raise ValueError('invalid scoreboard state')
            # Allow only data fields needed by our overlay.
            fields = ('code', 'record', 'score', 'logoUrl', 'logoHidden', 'recordHidden', 'wingBg', 'wingBorder', 'tabHidden', 'tabBg', 'tabBorder', 'tabText')
            cleaned = {}
            for side in ('away', 'home'):
                d = data[side]
                cleaned[side] = {k: (bool(d[k]) if isinstance(d.get(k), bool) else str(d.get(k, ''))[:500]) for k in fields}
            for k in ('clock','quarter','playclock','scale'):
                cleaned[k] = str(data.get(k, ''))[:40]
            for k in ('clockHidden','playclockHidden'):
                cleaned[k] = bool(data.get(k, False))
            with LOCK:
                STATE = cleaned
                VERSION += 1
                version = VERSION
            self.respond(json.dumps({'ok': True, 'version': version}), ctype='application/json; charset=utf-8')
        except (ValueError, UnicodeError, KeyError, TypeError) as exc:
            self.respond('Bad state: '+str(exc), 400, 'text/plain; charset=utf-8')

    def log_message(self, fmt, *args):
        # Do not print the controller secret embedded in /control URLs.
        if self.path.partition('?')[0] == '/control': return
        if self.path.startswith('/api/state'): return
        super().log_message(fmt, *args)

if __name__ == '__main__':
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f'http://127.0.0.1:{PORT}/control?key={urllib.parse.quote(EDIT_KEY)}'
    print('\n' + '='*55, flush=True)
    print('SPORTSCAST STUDIO — SCOREBOARD & OBS LINK', flush=True)
    print('Controller (keep private): '+url, flush=True)
    print(f'OBS only: http://127.0.0.1:{PORT}/obs', flush=True)
    print('Keep this terminal open while using OBS.', flush=True)
    print('='*55+'\n', flush=True)
    if os.environ.get('SPORTSCAST_OPEN_BROWSER', '0') == '1':
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try: httpd.serve_forever()
    except KeyboardInterrupt: print('\nSportscast stopped.',flush=True)
    finally: httpd.server_close()
