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

# ESPN currently exposes Division I college-football team catalogs and game records.
# Cache to prevent slow repeated requests and gracefully retain the list if ESPN is unavailable.
COLLEGE_CACHE = {'teams': [], 'time': 0}
COLLEGE_LOCK = threading.RLock()
# FBS fallback names (records intentionally unavailable rather than invented).
CFB_FALLBACK_NAMES = """Air Force|Akron|Alabama|Appalachian State|Arizona|Arizona State|Arkansas|Arkansas State|Army|Auburn|Ball State|Baylor|Boise State|Boston College|Bowling Green|Buffalo|BYU|California|Central Michigan|Charlotte|Cincinnati|Clemson|Coastal Carolina|Colorado|Colorado State|Connecticut|Duke|East Carolina|Eastern Michigan|FIU|Florida|Florida Atlantic|Florida State|Fresno State|Georgia|Georgia Southern|Georgia State|Georgia Tech|Hawaii|Houston|Illinois|Indiana|Iowa|Iowa State|Jacksonville State|James Madison|Kansas|Kansas State|Kennesaw State|Kent State|Kentucky|Liberty|Louisiana|Louisiana Tech|Louisville|LSU|Marshall|Maryland|Memphis|Miami (FL)|Miami (OH)|Michigan|Michigan State|Middle Tennessee|Minnesota|Mississippi State|Missouri|Missouri State|Navy|NC State|Nebraska|Nevada|New Mexico|New Mexico State|North Carolina|North Texas|Northern Illinois|Northwestern|Notre Dame|Ohio|Ohio State|Oklahoma|Oklahoma State|Old Dominion|Ole Miss|Oregon|Oregon State|Penn State|Pittsburgh|Purdue|Rice|Rutgers|Sam Houston|San Diego State|San Jose State|SMU|South Alabama|South Carolina|South Florida|Southern Miss|Stanford|Syracuse|TCU|Temple|Tennessee|Texas|Texas A&M|Texas State|Texas Tech|Toledo|Troy|Tulane|Tulsa|UAB|UCF|UCLA|UMass|UNLV|USC|Utah|Utah State|UTEP|UTSA|Vanderbilt|Virginia|Virginia Tech|Wake Forest|Washington|Washington State|West Virginia|Western Kentucky|Western Michigan|Wisconsin|Wyoming|Delaware""".split('|')
CFB_SEED_IDS = {'Boise State':('BSU','68','0033A0','D64309'),'Oregon':('ORE','2483','007030','FEE123'),'Indiana':('IND','84','990000','EEEDDD'),'Tennessee':('TENN','2633','FF8200','FFFFFF'),'Alabama':('BAMA','333','9E1B32','FFFFFF'),'Georgia':('UGA','61','BA0C2F','000000'),'Ohio State':('OSU','194','BB0000','666666'),'Michigan':('MICH','130','00274C','FFCB05'),'Penn State':('PSU','213','041E42','FFFFFF'),'Texas':('TEX','251','BF5700','FFFFFF'),'Notre Dame':('ND','87','0C2340','C99700'),'Clemson':('CLEM','228','F56600','522D80'),'Oklahoma':('OU','201','841617','FFFFFF'),'LSU':('LSU','99','461D7C','FDD023'),'Miami (FL)':('MIAMI','2390','F47321','005030'),'USC':('USC','30','990000','FFC72C'),'UCLA':('UCLA','26','2D68C4','F2A900'),'Washington':('WASH','264','4B2E83','B7A57A'),'BYU':('BYU','252','002E5D','FFFFFF'),'Florida':('FLA','57','0021A5','FA4616'),'Florida State':('FSU','52','782F40','CEB888'),'Auburn':('AUB','2','0C2340','E87722'),'Nebraska':('NEB','158','E41C38','FFFFFF'),'Iowa':('IOWA','2294','000000','FFCD00'),'Wisconsin':('WIS','275','C5050C','FFFFFF'),'Northwestern':('NW','77','4E2A84','FFFFFF')}

def _college_fallback():
    import re
    used = set(); out = []
    for name in CFB_FALLBACK_NAMES:
        code, tid, color, trim = CFB_SEED_IDS.get(name, ('', '', '21496F', 'E5EBF5'))
        if not code:
            code = ''.join(p[0] for p in re.findall(r'[A-Za-z]+', name)).upper()[:6]
            if len(code) < 2: code = re.sub('[^A-Z0-9]', '', name.upper())[:6]
        orig = code
        n = 2
        while code in used: code = orig + str(n); n += 1
        used.add(code)
        out.append({'code':code,'abbr':code,'name':name,'id':tid,'bg':'#'+color,'trim':'#'+trim,'record':'','logo':f'https://a.espncdn.com/i/teamlogos/ncaa/500/{tid}.png' if tid else ''})
    return out

def _espn_get(path):
    import urllib.request
    url = 'https://site.api.espn.com' + path
    req = urllib.request.Request(url, headers={'User-Agent':'SportscastStudio/2.0 (college football scoreboard)', 'Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)

def _college_catalog(force=False):
    with COLLEGE_LOCK:
        if COLLEGE_CACHE['teams'] and time.time()-COLLEGE_CACHE['time'] < (90 if force else 1200):
            return {'teams':COLLEGE_CACHE['teams'], 'source':COLLEGE_CACHE.get('source','fallback'), 'cached':True}
        import concurrent.futures
        import re
        # Fetch Division I FBS/FCS catalogs, current-week records and conference standings in parallel.
        year = time.gmtime().tm_year if time.gmtime().tm_mon >= 2 else time.gmtime().tm_year-1
        paths = {
            f'teams{g}': f'/apis/site/v2/sports/football/college-football/teams?groups={g}&limit=500'
            for g in (80,81)
        }
        paths.update({f'games{g}':f'/apis/site/v2/sports/football/college-football/scoreboard?groups={g}&limit=500' for g in (80,81)})
        paths.update({f'standings{g}':f'/apis/v2/sports/football/college-football/standings?season={year}&group={g}' for g in (80,81)})
        payloads = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            future_map={ex.submit(_espn_get,path):name for name,path in paths.items()}
            for future in concurrent.futures.as_completed(future_map):
                try:payloads[future_map[future]]=future.result()
                except Exception:pass
        entries={}
        for group in (80,81):
            payload=payloads.get(f'teams{group}') or {}
            sports=payload.get('sports') or []
            leagues=[lg for sp in sports for lg in sp.get('leagues',[])]
            lists=[lg.get('teams') or [] for lg in leagues]
            if not lists and isinstance(payload.get('teams'),list): lists=[payload['teams']]
            for arr in lists:
                for wrapper in arr:
                    t=wrapper.get('team',wrapper) if isinstance(wrapper,dict) else {}
                    if not isinstance(t,dict):continue
                    tid=str(t.get('id') or '')
                    if not tid.isdigit():continue
                    name=str(t.get('location') or t.get('shortDisplayName') or t.get('displayName') or '').strip()
                    if not name:continue
                    color=str(t.get('color') or '21496F').lstrip('#')
                    trim=str(t.get('alternateColor') or 'E5EBF5').lstrip('#')
                    if not re.fullmatch('[0-9A-Fa-f]{6}',color):color='21496F'
                    if not re.fullmatch('[0-9A-Fa-f]{6}',trim):trim='E5EBF5'
                    abbr=re.sub('[^A-Z0-9]','',str(t.get('abbreviation') or name[:4]).upper())[:8] or str(tid)
                    logo=next((x.get('href') for x in (t.get('logos') or []) if isinstance(x,dict) and str(x.get('href','')).startswith('https://') and 'espn' in str(x.get('href'))),None)
                    if not logo:logo=f'https://a.espncdn.com/i/teamlogos/ncaa/500/{tid}.png'
                    entries[tid]={'code':abbr,'abbr':abbr,'name':name,'id':tid,'bg':'#'+color,'trim':'#'+trim,'record':'','logo':logo}
        records={}
        for group in (80,81):
            payload=payloads.get(f'games{group}') or {}
            for event in payload.get('events') or []:
                for competition in event.get('competitions') or []:
                    for competitor in competition.get('competitors') or []:
                        tid=str((competitor.get('team') or {}).get('id',''))
                        arr=competitor.get('records') or []
                        overall=next((str(r.get('summary','')) for r in arr if r.get('type')=='total' or r.get('name')=='overall'), '')
                        if not overall and arr:overall=str(arr[0].get('summary',''))
                        if tid and re.fullmatch(r'\d+-\d+(?:-\d+)?',overall):records[tid]=overall
        # On bye weeks, overall standings can provide W-L even if a team has no game.
        def from_standings(payload):
            found={};seen=set()
            def visit(node,depth=0):
                if depth>15 or not isinstance(node,(dict,list)) or id(node) in seen:return
                seen.add(id(node))
                if isinstance(node,list):
                    for x in node:visit(x,depth+1)
                    return
                team=node.get('team') or {}
                tid=str(team.get('id','')) if isinstance(team,dict) else ''
                stats=node.get('stats') or []
                if tid and isinstance(stats,list):
                    by_name={str(x.get('name','')).lower():x for x in stats if isinstance(x,dict)}
                    overall=str(by_name.get('overall',{}).get('displayValue',''))
                    if not re.fullmatch(r'\d+-\d+(?:-\d+)?',overall):
                        try:
                            wins=int(float(by_name['wins'].get('value',by_name['wins'].get('displayValue',0))))
                            losses=int(float(by_name['losses'].get('value',by_name['losses'].get('displayValue',0))))
                            overall=f'{wins}-{losses}'
                        except (ValueError,TypeError,KeyError):overall=''
                    if re.fullmatch(r'\d+-\d+(?:-\d+)?',overall):found[tid]=overall
                for k,v in node.items():
                    if k in ('children','standings','entries','groups','teams','conferences','items'):
                        visit(v,depth+1)
            visit(payload)
            return found
        for group in (80,81):
            records.update({k:v for k,v in from_standings(payloads.get(f'standings{group}') or {}).items() if k not in records})
        fallback=_college_fallback()
        if entries:
            # The ESPN catalogs may omit a team due to API outages or pagination.
            known={x['name'].casefold() for x in entries.values()}
            rows=list(entries.values())+[x for x in fallback if x['name'].casefold() not in known]
        else:rows=fallback
        used=set()
        for row in rows:
            code=row['code'];index=2
            while code in used:code=row['code']+'_'+str(index);index+=1
            row['code']=code;used.add(code)
            row['record']=records.get(row['id'],'')
        rows.sort(key=lambda t:t['name'].casefold())
        if entries or not COLLEGE_CACHE['teams']:
            COLLEGE_CACHE['teams']=rows
            COLLEGE_CACHE['time']=time.time()
            COLLEGE_CACHE['source']='ESPN+fallback' if entries else 'fallback'
        return {'teams':COLLEGE_CACHE['teams'],'source':COLLEGE_CACHE.get('source','fallback'),'cached':False}

PORT = int(os.environ.get('PORT', '8765'))
HOST = os.environ.get('HOST', '127.0.0.1')
EDIT_KEY = os.environ.get('SPORTSCAST_CONTROL_KEY') or secrets.token_urlsafe(20)
PENALTY_TYPES = {'False Start': ('5 YARDS', 'False Start'), 'Offside': ('5 YARDS', 'Offside'), 'Encroachment': ('5 YARDS', 'Encroachment'), 'Neutral Zone Infraction': ('5 YARDS', 'Neutral Zone Infraction'), 'Delay of Game': ('5 YARDS', 'Delay of Game'), 'Illegal Formation': ('5 YARDS', 'Illegal Formation'), 'Illegal Shift / Motion': ('5 YARDS', 'Illegal Shift / Motion'), 'Illegal Substitution / Too Many Men on the Field': ('5 YARDS', 'Too Many Men on Field'), 'Ineligible Receiver Downfield': ('5 YARDS', 'Ineligible Downfield'), 'Running into the Kicker': ('5 YARDS', 'Running into the Kicker'), 'Defensive Holding': ('5 YARDS', 'Defensive Holding'), 'Illegal Use of Hands': ('5 YARDS', 'Illegal Use of Hands'), 'Offensive Holding': ('10 YARDS', 'Offensive Holding'), 'Offensive Pass Interference (OPI)': ('10 YARDS', 'Offensive Pass Interference'), 'Illegal Block in the Back': ('10 YARDS', 'Illegal Block in the Back'), 'Intentional Grounding': ('10 YARDS', 'Intentional Grounding'), 'Illegal Forward Pass': ('10 YARDS', 'Illegal Forward Pass'), 'Roughing the Passer': ('15 YARDS', 'Roughing the Passer'), 'Roughing the Kicker': ('15 YARDS', 'Roughing the Kicker'), 'Face Mask': ('15 YARDS', 'Face Mask'), 'Horse Collar Tackle': ('15 YARDS', 'Horse Collar Tackle'), 'Unnecessary Roughness': ('15 YARDS', 'Unnecessary Roughness'), 'Unsportsmanlike Conduct': ('15 YARDS', 'Unsportsmanlike Conduct'), 'Chop Block / Clipping': ('15 YARDS', 'Chop Block / Clipping'), 'Tripping': ('15 YARDS', 'Tripping'), 'Defensive Pass Interference (DPI)': ('SPOT FOUL', 'Defensive Pass Interference')}

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
        if path == '/api/college-teams':
            result = _college_catalog(force='refresh=1' in query)
            return self.respond(json.dumps(result), ctype='application/json; charset=utf-8')
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
            fields = ('code', 'name', 'rank', 'bgColor', 'trimColor', 'record', 'score', 'logoUrl', 'logoHidden', 'recordHidden', 'wingBg', 'wingBorder', 'tabHidden', 'tabBg', 'tabBorder', 'tabText', 'tabTextColor', 'timeoutCount')
            cleaned = {}
            for side in ('away', 'home'):
                d = data[side]
                cleaned[side] = {k: (bool(d[k]) if isinstance(d.get(k), bool) else str(d.get(k, ''))[:500]) for k in fields}
                rank = str(d.get('rank', ''))
                cleaned[side]['rank'] = rank if rank.isdecimal() and 1 <= int(rank) <= 25 else ''
                import re
                for colorfield in ('bgColor','trimColor'):
                    raw = str(d.get(colorfield, ''))[:20]
                    cleaned[side][colorfield] = raw if re.fullmatch(r'#[0-9a-fA-F]{6}', raw) else '#254a73'
            for k in ('clock','quarter','playclock','scale'):
                cleaned[k] = str(data.get(k, ''))[:40]
            cleaned['design'] = data.get('design') if data.get('design') in ('classic','tv','fox') else 'classic'
            cleaned['sport'] = 'cfb' if data.get('sport') == 'cfb' else 'nfl'
            cleaned['reviewActive'] = bool(data.get('reviewActive', False))
            cleaned['cfbDown'] = str(data.get('cfbDown', '1ST & 10'))[:44]
            cleaned['cfbDownHidden'] = bool(data.get('cfbDownHidden', False))
            cleaned['possession'] = data.get('possession') if data.get('possession') in ('away', 'home') else 'none'
            cleaned['flagTeam'] = data.get('flagTeam') if data.get('flagTeam') in ('away', 'home') else 'none'
            cleaned['foxDown'] = str(data.get('foxDown', '1ST & 10'))[:50]
            cleaned['foxDownHidden'] = bool(data.get('foxDownHidden', False))
            import re
            for color_name in ('foxAccent','foxTrim'):
                c = str(data.get(color_name, ''))[:20]
                cleaned[color_name] = c if re.fullmatch(r'#[0-9a-fA-F]{6}',c) else '#4f2683'
            selected_penalty = str(data.get('penaltyType', ''))[:90]
            cleaned['penaltyType'] = selected_penalty if selected_penalty in PENALTY_TYPES else ''
            penalty_meta = PENALTY_TYPES.get(cleaned['penaltyType'], ('', ''))
            cleaned['penaltyYards'], cleaned['penaltyDisplay'] = penalty_meta
            cleaned['timeoutSide'] = data.get('timeoutSide') if data.get('timeoutSide') in ('away', 'home') else 'none'
            cleaned['timeoutActive'] = bool(data.get('timeoutActive', False)) and cleaned['timeoutSide'] != 'none'
            cleaned['timeoutRemaining'] = str(data.get('timeoutRemaining', ''))[:24]
            cleaned['timeoutTeamName'] = str(data.get('timeoutTeamName', ''))[:45]
            cleaned['fgSide'] = data.get('fgSide') if data.get('fgSide') in ('away', 'home') else 'away'
            cleaned['fgActive'] = bool(data.get('fgActive', False))
            fg_number = str(data.get('fgYards', '')).strip()
            cleaned['fgYards'] = fg_number if fg_number.isascii() and fg_number.isdecimal() and 1 <= int(fg_number) <= 120 else '' 
            import re
            for name in ('timeoutBg','timeoutTrim','fgBg','fgTrim'):
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
