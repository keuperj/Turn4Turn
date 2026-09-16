"""Multi-player HTTP/HTTPS server. Run with: python3 server.py"""
import argparse, ipaddress, json, mimetypes, re, socket, ssl, subprocess, tempfile, threading, time, uuid
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
from game import Game
from audio_assets import discover, PATTERN

ROOT=Path(__file__).parent/'static';CAMPAIGN_FILE=Path(__file__).parent/'campaigns'/'operation_turning_point.json';CERTIFICATE_DIR=Path(__file__).parent/'.certs'
MAX_PLAYERS=10;SESSION_TIMEOUT=30*60;COOKIE_AGE=365*24*60*60
USER_COOKIE='turn4turn_user';NAME_COOKIE='turn4turn_name';USER_ID=re.compile(r'^[0-9a-f]{32}$')
game=Game(deployed=False)  # Compatibility alias for local development tools.

@dataclass
class PlayerSession:
    """Store one player identity, game instance, activity time, and lock."""
    user_id:str;username:str;game:Game
    last_seen:float=field(default_factory=time.monotonic)
    lock:threading.RLock=field(default_factory=threading.RLock)

class SessionRegistry:
    """Create, retrieve, and expire isolated player sessions safely."""
    def __init__(self):
        """Initialize an empty thread-safe session registry."""
        self.sessions={};self.lock=threading.RLock()
    def prune(self,now=None):
        """Remove sessions that have exceeded the inactivity timeout."""
        now=time.monotonic() if now is None else now
        for uid,s in list(self.sessions.items()):
            if now-s.last_seen>SESSION_TIMEOUT:del self.sessions[uid]
    def get(self,uid):
        """Return an active session and refresh its last-seen timestamp."""
        with self.lock:
            self.prune();s=self.sessions.get(uid)
            if s:s.last_seen=time.monotonic()
            return s
    def create(self,username,requested_id=None):
        """Create or reconnect a player unless server capacity is exhausted."""
        with self.lock:
            self.prune()
            if requested_id in self.sessions:
                s=self.sessions[requested_id];s.username=username;s.last_seen=time.monotonic();return s
            if len(self.sessions)>=MAX_PLAYERS:return None
            uid=requested_id if requested_id and USER_ID.fullmatch(requested_id) else uuid.uuid4().hex
            s=PlayerSession(uid,username,game if not self.sessions else Game(deployed=False));self.sessions[uid]=s;return s

registry=SessionRegistry()

class Handler(BaseHTTPRequestHandler):
    """Serve static assets and the authoritative JSON game API."""
    def send(self,status,body,content_type='application/json',cookies=()):
        """Write an HTTP response with cache, content, and cookie headers."""
        self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Cache-Control','no-store')
        for cookie in cookies:self.send_header('Set-Cookie',cookie)
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def cookies(self):
        """Parse request cookies into a plain string dictionary."""
        parsed=SimpleCookie()
        try:parsed.load(self.headers.get('Cookie',''))
        except Exception:return {}
        return {key:value.value for key,value in parsed.items()}
    def player(self):
        """Return the player session identified by the request cookie."""
        uid=self.cookies().get(USER_COOKIE,'');return registry.get(uid) if USER_ID.fullmatch(uid) else None
    def require_player(self):
        """Return the current session or send an authorization error."""
        s=self.player()
        if s and len(registry.sessions)==1 and s.game is not game:s.game=game
        if not s:self.send(401,json.dumps({'error':'Cookie consent and a user name are required.','needs_consent':True}).encode())
        return s
    def read_json(self):
        """Read and validate a size-limited JSON object request body."""
        length=int(self.headers.get('Content-Length','0'))
        if not 0<length<=16384:raise ValueError('Invalid request size.')
        data=json.loads(self.rfile.read(length))
        if not isinstance(data,dict):raise ValueError('Expected a JSON object.')
        return data
    def serve_file(self,file,root=ROOT):
        """Serve a regular file only when it remains under the allowed root."""
        file=file.resolve()
        if file.is_relative_to(root.resolve()) and file.is_file():self.send(200,file.read_bytes(),mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
        else:self.send(404,b'Not found','text/plain')
    def do_GET(self):
        """Route read-only API, diagnostic, and static-asset requests."""
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
        if path.startswith(('/assets/','/vendor/')) or path in ('/scene.js','/rendering.js','/characters.js','/environment.js','/icons.js','/minimap.js','/audio.js','/webgpu-check.js','/webgpu-quality.js','/webgpu-nature.js','/webgpu-vehicles.js','/webgpu-scenery.js'):
            self.serve_file(ROOT/path.lstrip('/'));return
        if path in ('/gpu-test','/gpu-test/'):path='/gpu-test.html'
        files={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css'),'/campaign.css':('campaign.css','text/css'),'/app.js':('app.js','text/javascript'),
               '/gpu-test.html':('gpu-test.html','text/html; charset=utf-8'),'/gpu-test.css':('gpu-test.css','text/css'),'/gpu-test.js':('gpu-test.js','text/javascript')}
        if path not in files:self.send(404,b'Not found','text/plain');return
        filename,mime=files[path];self.send(200,(ROOT/filename).read_bytes(),mime)
    def do_POST(self):
        """Route consent and state-changing game API requests."""
        global game
        path=self.path.split('?')[0]
        try:
            if path=='/api/session':
                data=self.read_json();username=data.get('username','').strip() if isinstance(data.get('username'),str) else ''
                if data.get('consent') is not True:raise ValueError('Cookie consent is required to play.')
                if not 2<=len(username)<=30 or any(ord(c)<32 for c in username):raise ValueError('User name must contain 2 to 30 visible characters.')
                s=registry.create(username,self.cookies().get(USER_COOKIE,''))
                if not s:self.send(503,json.dumps({'error':'The server is full. Please try again later.','full':True}).encode());return
                native_tls=isinstance(self.connection,ssl.SSLSocket)
                secure='; Secure' if native_tls or self.headers.get('X-Forwarded-Proto')=='https' else '';attrs=f'; Path=/; Max-Age={COOKIE_AGE}; SameSite=Lax{secure}'
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

def _certificate_names(host):
    """Return a common name and SAN entries suitable for the bind address."""
    host=host.strip().removeprefix('[').removesuffix(']')
    dns_names={'localhost'};ip_addresses={'127.0.0.1','::1'}
    try:
        address=ipaddress.ip_address(host)
        if not address.is_unspecified:ip_addresses.add(str(address))
    except ValueError:
        if not re.fullmatch(r'[A-Za-z0-9.-]+',host):raise ValueError(f'Invalid HTTPS host name: {host!r}')
        dns_names.add(host)
    local_name=socket.gethostname()
    if re.fullmatch(r'[A-Za-z0-9.-]+',local_name):dns_names.add(local_name)
    if host in ('0.0.0.0','::'):
        try:
            for info in socket.getaddrinfo(local_name,None):
                candidate=info[4][0].split('%')[0]
                try:ip_addresses.add(str(ipaddress.ip_address(candidate)))
                except ValueError:pass
        except socket.gaierror:pass
    common_name=host if host not in ('0.0.0.0','::') else local_name
    sans=[*(f'DNS:{name}' for name in sorted(dns_names)),*(f'IP:{address}' for address in sorted(ip_addresses))]
    return common_name,','.join(sans)

def ensure_self_signed_certificate(host,directory=CERTIFICATE_DIR):
    """Create or reuse a one-year self-signed TLS certificate for ``host``."""
    directory=Path(directory);directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    safe_host=re.sub(r'[^A-Za-z0-9_.-]+','_',host.strip('[]')) or 'localhost'
    certificate=directory/f'turn4turn-{safe_host}.crt';private_key=directory/f'turn4turn-{safe_host}.key'
    if certificate.is_file() and private_key.is_file():
        try:valid=subprocess.run(['openssl','x509','-checkend','86400','-noout','-in',str(certificate)],capture_output=True).returncode==0
        except FileNotFoundError:valid=True
        if valid:return certificate,private_key,False
    common_name,sans=_certificate_names(host)
    try:
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            temporary=Path(temporary);new_certificate=temporary/'certificate.crt';new_key=temporary/'private.key'
            result=subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-sha256','-days','365','-nodes','-keyout',str(new_key),'-out',str(new_certificate),'-subj',f'/CN={common_name}','-addext',f'subjectAltName={sans}','-addext','keyUsage=digitalSignature,keyEncipherment','-addext','extendedKeyUsage=serverAuth'],capture_output=True,text=True)
            if result.returncode:raise RuntimeError(f'OpenSSL could not create the certificate: {result.stderr.strip()}')
            new_key.chmod(0o600);new_certificate.chmod(0o644)
            new_key.replace(private_key);new_certificate.replace(certificate)
    except FileNotFoundError as exc:raise RuntimeError('The openssl command is required to generate an HTTPS certificate.') from exc
    return certificate,private_key,True

def create_server(host,port,use_https=False,certificate_directory=CERTIFICATE_DIR,handler_class=Handler):
    """Build the threaded server and optionally wrap its socket with TLS."""
    certificate=private_key=None;created=False
    if use_https:certificate,private_key,created=ensure_self_signed_certificate(host,certificate_directory)
    httpd=ThreadingHTTPServer((host,port),handler_class)
    if use_https:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(certificate,private_key)
        httpd.socket=context.wrap_socket(httpd.socket,server_side=True)
    return httpd,certificate,created

def main(argv=None):
    """Parse command-line options and serve requests until interrupted."""
    global MAX_PLAYERS
    parser=argparse.ArgumentParser(description='Turn4Turn tactical combat');parser.add_argument('--host',default='127.0.0.1',metavar='ADDRESS',help='IP address or host name to bind to (default: 127.0.0.1)');parser.add_argument('--port',type=int,default=8000);parser.add_argument('--max-players',type=int,default=MAX_PLAYERS);parser.add_argument('--https',action='store_true',help='generate/reuse a self-signed certificate and serve HTTPS');args=parser.parse_args(argv)
    if args.max_players<1:parser.error('--max-players must be at least 1')
    MAX_PLAYERS=args.max_players
    try:httpd,certificate,created=create_server(args.host,args.port,args.https)
    except (OSError,RuntimeError,ValueError) as exc:parser.error(str(exc))
    scheme='https' if args.https else 'http';url_host=f'[{args.host}]' if ':' in args.host and not args.host.startswith('[') else args.host
    print(f'Turn4Turn ready at {scheme}://{url_host}:{args.port} (max {MAX_PLAYERS} active players)',flush=True)
    if certificate:print(f"Self-signed certificate {'created' if created else 'reused'}: {certificate}",flush=True)
    try:httpd.serve_forever()
    except KeyboardInterrupt:print('\nServer stopped.')
    finally:httpd.server_close()

if __name__=='__main__':main()
