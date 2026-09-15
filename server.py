"""Multi-player HTTP server. Run with: python3 server.py"""
import argparse, json, mimetypes, re, threading, time, uuid
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
from game import Game
from audio_assets import discover, PATTERN

ROOT=Path(__file__).parent/'static';CAMPAIGN_FILE=Path(__file__).parent/'campaigns'/'operation_turning_point.json'
MAX_PLAYERS=10;SESSION_TIMEOUT=30*60;COOKIE_AGE=365*24*60*60
USER_COOKIE='turn4turn_user';NAME_COOKIE='turn4turn_name';USER_ID=re.compile(r'^[0-9a-f]{32}$')
game=Game(deployed=False)  # Compatibility alias for local development tools.

@dataclass
class PlayerSession:
    user_id:str;username:str;game:Game
    last_seen:float=field(default_factory=time.monotonic)
    lock:threading.RLock=field(default_factory=threading.RLock)

class SessionRegistry:
    def __init__(self):self.sessions={};self.lock=threading.RLock()
    def prune(self,now=None):
        now=time.monotonic() if now is None else now
        for uid,s in list(self.sessions.items()):
            if now-s.last_seen>SESSION_TIMEOUT:del self.sessions[uid]
    def get(self,uid):
        with self.lock:
            self.prune();s=self.sessions.get(uid)
            if s:s.last_seen=time.monotonic()
            return s
    def create(self,username,requested_id=None):
        global game
        with self.lock:
            self.prune()
            if requested_id in self.sessions:
                s=self.sessions[requested_id];s.username=username;s.last_seen=time.monotonic();return s
            if len(self.sessions)>=MAX_PLAYERS:return None
            uid=requested_id if requested_id and USER_ID.fullmatch(requested_id) else uuid.uuid4().hex
            s=PlayerSession(uid,username,game if not self.sessions else Game(deployed=False));self.sessions[uid]=s;return s

registry=SessionRegistry()

class Handler(BaseHTTPRequestHandler):
    def send(self,status,body,content_type='application/json',cookies=()):
        self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Cache-Control','no-store')
        for cookie in cookies:self.send_header('Set-Cookie',cookie)
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def cookies(self):
        parsed=SimpleCookie()
        try:parsed.load(self.headers.get('Cookie',''))
        except Exception:return {}
        return {key:value.value for key,value in parsed.items()}
    def player(self):
        uid=self.cookies().get(USER_COOKIE,'');return registry.get(uid) if USER_ID.fullmatch(uid) else None
    def require_player(self):
        s=self.player()
        if s and len(registry.sessions)==1 and s.game is not game:s.game=game
        if not s:self.send(401,json.dumps({'error':'Cookie consent and a user name are required.','needs_consent':True}).encode())
        return s
    def read_json(self):
        length=int(self.headers.get('Content-Length','0'))
        if not 0<length<=16384:raise ValueError('Invalid request size.')
        data=json.loads(self.rfile.read(length))
        if not isinstance(data,dict):raise ValueError('Expected a JSON object.')
        return data
    def serve_file(self,file,root=ROOT):
        file=file.resolve()
        if file.is_relative_to(root.resolve()) and file.is_file():self.send(200,file.read_bytes(),mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
        else:self.send(404,b'Not found','text/plain')
    def do_GET(self):
        path=self.path.split('?')[0]
        if path=='/api/session':
            s=self.player()
            with registry.lock:registry.prune();available=max(0,MAX_PLAYERS-len(registry.sessions))
            self.send(200,json.dumps({'accepted':bool(s),**({'username':s.username} if s else {'available':available})}).encode());return
        if path=='/comparison':self.send_response(302);self.send_header('Location','/comparison/');self.end_headers();return
        if path=='/comparison/':self.serve_file(ROOT/'comparison'/'index.html',ROOT/'comparison');return
        if path.startswith('/comparison/'):self.serve_file(ROOT/path.lstrip('/'),ROOT/'comparison');return
        if path=='/api/audio':self.send(200,json.dumps(discover()).encode());return
        if path=='/api/campaign':self.send(200,CAMPAIGN_FILE.read_bytes());return
        if path=='/api/state':
            s=self.require_player()
            if s:
                with s.lock:self.send(200,json.dumps(s.game.state()).encode())
            return
        if path.startswith('/sounds/'):
            name=path.removeprefix('/sounds/');file=ROOT/'sounds'/name
            if PATTERN.fullmatch(name) and file.is_file() and not file.is_symlink():self.serve_file(file)
            else:self.send(404,b'Not found','text/plain')
            return
        if path.startswith(('/assets/','/vendor/')) or path in ('/scene.js','/rendering.js','/characters.js','/environment.js','/icons.js','/minimap.js','/audio.js'):
            self.serve_file(ROOT/path.lstrip('/'));return
        files={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css'),'/campaign.css':('campaign.css','text/css'),'/app.js':('app.js','text/javascript')}
        if path not in files:self.send(404,b'Not found','text/plain');return
        filename,mime=files[path];self.send(200,(ROOT/filename).read_bytes(),mime)
    def do_POST(self):
        global game
        path=self.path.split('?')[0]
        try:
            if path=='/api/session':
                data=self.read_json();username=data.get('username','').strip() if isinstance(data.get('username'),str) else ''
                if data.get('consent') is not True:raise ValueError('Cookie consent is required to play.')
                if not 2<=len(username)<=30 or any(ord(c)<32 for c in username):raise ValueError('User name must contain 2 to 30 visible characters.')
                s=registry.create(username,self.cookies().get(USER_COOKIE,''))
                if not s:self.send(503,json.dumps({'error':'The server is full. Please try again later.','full':True}).encode());return
                secure='; Secure' if self.headers.get('X-Forwarded-Proto')=='https' else '';attrs=f'; Path=/; Max-Age={COOKIE_AGE}; SameSite=Lax{secure}'
                self.send(200,json.dumps({'accepted':True,'username':username}).encode(),cookies=[f'{USER_COOKIE}={s.user_id}{attrs}; HttpOnly',f'{NAME_COOKIE}={quote(username)}{attrs}']);return
            if path not in ('/api/action','/api/new','/api/preview'):self.send(404,b'{}');return
            s=self.require_player()
            if not s:return
            data=self.read_json()
            with s.lock:
                if path=='/api/preview':self.send(200,json.dumps(s.game.preview(data)).encode());return
                if path=='/api/new':
                    seed=data.get('seed')
                    if seed is not None and (type(seed) is not int or not 0<=seed<=999999999):raise ValueError('Seed must be an integer from 0 to 999999999.')
                    s.game=Game(seed,data.get('theme','random'),deployed=False,size=data.get('size',30),difficulty=data.get('difficulty','medium'),mission=data.get('mission','rescue'),lighting=data.get('lighting','day'),title=data.get('title'),objective=data.get('objective'))
                    if len(registry.sessions)==1:game=s.game
                else:s.game.action(data)
                self.send(200,json.dumps(s.game.state()).encode())
        except (ValueError,TypeError,json.JSONDecodeError) as exc:self.send(400,json.dumps({'error':str(exc)}).encode())

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Turn4Turn tactical combat');parser.add_argument('--host',default='127.0.0.1',metavar='ADDRESS',help='IP address or host name to bind to (default: 127.0.0.1)');parser.add_argument('--port',type=int,default=8000);parser.add_argument('--max-players',type=int,default=MAX_PLAYERS);args=parser.parse_args()
    if args.max_players<1:parser.error('--max-players must be at least 1')
    MAX_PLAYERS=args.max_players;print(f'Turn4Turn ready at http://{args.host}:{args.port} (max {MAX_PLAYERS} active players)',flush=True)
    try:ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
    except KeyboardInterrupt:print('\nServer stopped.')
