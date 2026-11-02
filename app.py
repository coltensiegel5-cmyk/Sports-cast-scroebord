#!/usr/bin/env python3
"""Sportscast Studio local/hosted scoreboard relay, Python standard library only."""
import hmac
import hashlib
import time
from http.cookies import SimpleCookie
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
COOKIE_NAME = "sportscast_session"
COOKIE_DAYS = 30

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

    def trusted_device(self):
        raw = self.headers.get('Cookie', '')
        try:
            cookies = SimpleCookie()
            cookies.load(raw)
            morsel = cookies.get(COOKIE_NAME)
            if not morsel:
                return False
            exp_string, signature = morsel.value.split('.', 1)
            expiry = int(exp_string)
            if expiry < int(time.time()) or expiry > int(time.time()) + COOKIE_DAYS * 86400 + 60:
                return False
            message = 'sportscast-controller-v1|' + exp_string
            expected = hmac.new(EDIT_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(signature, expected)
        except (ValueError, TypeError):
            return False

    def session_cookie(self, clear=False):
        # Cookies are Secure on the public HTTPS site; local development stays usable on HTTP.
        host = self.headers.get('Host', '').split(':')[0].lower()
        is_local = host in ('localhost', '127.0.0.1', '[::1]')
        attrs = '; Path=/; HttpOnly; SameSite=Lax'
        if not is_local:
            attrs += '; Secure'
        if clear:
            return COOKIE_NAME + '=; Max-Age=0' + attrs
        expires = str(int(time.time()) + COOKIE_DAYS * 86400)
        payload = 'sportscast-controller-v1|' + expires
        signature = hmac.new(EDIT_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return COOKIE_NAME + '=' + expires + '.' + signature + '; Max-Age=' + str(COOKIE_DAYS * 86400) + attrs

    def redirect(self, path, cookie=None):
        self.send_response(303)
        self.send_header('Location', path)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.send_header('Content-Length', '0')
        self.end_headers()

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
        if path == '/logout':
            return self.redirect('/', cookie=self.session_cookie(clear=True))
        if path == '/control':
            params = urllib.parse.parse_qs(query)
            submitted = params.get('key', [''])[0]
            if submitted and hmac.compare_digest(submitted, EDIT_KEY):
                # Support old private links, but remove their key from the browser URL.
                return self.redirect('/control', cookie=self.session_cookie())
            if not self.trusted_device():
                return self.respond(self.landing('Enter the controller code once to remember this browser.'), 401)
            html = (HERE / 'controller.html').read_text(encoding='utf-8')
            html = html.replace('__SPORTSCAST_KEY__', json.dumps(EDIT_KEY))
            html = html.replace('</body>', '<div style="max-width:1190px;margin:8px auto 20px;padding:0 12px;text-align:right"><a href="/logout" style="color:#b8d5ff;font:12px system-ui">Sign out of controller</a></div></body>', 1)
            return self.respond(html)
        if path == '/':
            return self.respond((HERE / 'index.html').read_bytes())
        self.respond('Not found', 404, 'text/plain; charset=utf-8')

    def landing(self, warning=''):
        alert = f'<p style="color:#ffb7a2">{escape(warning)}</p>' if warning else ''
        return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sportscast Studio</title>
        <style>body{margin:0;background:#0d1729;color:#eaf2ff;font:15px system-ui,sans-serif;min-height:100vh;display:grid;place-items:center}main{padding:32px;background:#17263e;border:1px solid #3b536f;border-radius:16px;max-width:420px;width:90%;box-sizing:border-box}h1{margin:0 0 8px}p{color:#b5c8df;line-height:1.6}input,button{padding:12px;border-radius:9px;font:inherit}input{background:#09182c;border:1px solid #617495;color:white;width:100%;box-sizing:border-box}button{background:#2b60e0;color:white;border:0;margin-top:12px;cursor:pointer}a{color:#9cc6ff}</style>
        <main><h1>▤ Sportscast Studio</h1><p>Enter your controller code once. This browser will remember you for 30 days. The public OBS overlay is view-only.</p>'''+alert+'''<form action="/login" method="POST"><input name="key" type="password" required placeholder="Controller code" autocomplete="off"/><button>Remember This Device &amp; Open Controls</button></form><p>OBS overlay: <a href="/obs">Open scoreboard-only view</a></p></main></html>'''

    def do_POST(self):
        global STATE, VERSION
        if self.path.partition('?')[0] == '/login':
            try:
                n = int(self.headers.get('Content-Length', '0'))
                if n < 1 or n > 4096:
                    raise ValueError('invalid size')
                form = urllib.parse.parse_qs(self.rfile.read(n).decode('utf-8'))
                submitted = form.get('key', [''])[0]
                if not hmac.compare_digest(submitted, EDIT_KEY):
                    return self.respond(self.landing('That controller code did not match.'), 403)
                return self.redirect('/control', cookie=self.session_cookie())
            except (ValueError, UnicodeError):
                return self.respond(self.landing('Could not read the controller code.'), 400)
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
            fields = ('code', 'record', 'score', 'logoUrl', 'logoHidden', 'recordHidden', 'wingBg', 'wingBorder', 'tabHidden', 'tabBg', 'tabBorder', 'tabText', 'tabTextColor', 'timeoutCount')
            cleaned = {}
            for side in ('away', 'home'):
                d = data[side]
                cleaned[side] = {k: (bool(d[k]) if isinstance(d.get(k), bool) else str(d.get(k, ''))[:500]) for k in fields}
            for k in ('clock','quarter','playclock','scale'):
                cleaned[k] = str(data.get(k, ''))[:40]
            cleaned['design'] = 'tv' if data.get('design') == 'tv' else 'classic'
            cleaned['possession'] = data.get('possession') if data.get('possession') in ('away', 'home') else 'none'
            cleaned['flagTeam'] = data.get('flagTeam') if data.get('flagTeam') in ('away', 'home') else 'none'
            cleaned['timeoutSide'] = data.get('timeoutSide') if data.get('timeoutSide') in ('away', 'home') else 'none'
            cleaned['timeoutActive'] = bool(data.get('timeoutActive', False)) and cleaned['timeoutSide'] != 'none'
            cleaned['timeoutRemaining'] = str(data.get('timeoutRemaining', ''))[:24]
            cleaned['timeoutTeamName'] = str(data.get('timeoutTeamName', ''))[:45]
            import re
            for name in ('timeoutBg','timeoutTrim'):
                value = str(data.get(name, ''))[:32].strip()
                cleaned[name] = value if re.fullmatch(r'#[0-9A-Fa-f]{6}', value) else '#284560'
            cleaned['centerText'] = str(data.get('centerText', 'SPORTSCAST'))[:40]
            bg = str(data.get('centerBg', ''))[:250]
            cleaned['centerBg'] = bg if ('linear-gradient(' in bg and not any(x in bg for x in '<>\\')) else ''
            trim = str(data.get('centerTrim', ''))[:45]
            cleaned['centerTrim'] = trim if not any(x in trim for x in '<>\\') else ''
            for k in ('clockHidden','playclockHidden','flag'):
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
        if self.path.partition('?')[0] in ('/control', '/login', '/logout'): return
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
