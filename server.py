"""Run with: python3 server.py"""
import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from game import Game
from audio_assets import discover, PATTERN

ROOT = Path(__file__).parent / 'static'
game = Game(deployed=False)


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/comparison':
            self.send_response(302)
            self.send_header('Location','/comparison/')
            self.end_headers()
            return
        if path == '/comparison/':
            self.send(200,(ROOT/'comparison'/'index.html').read_bytes(),'text/html; charset=utf-8')
            return
        if path.startswith('/comparison/'):
            file=(ROOT/path.lstrip('/')).resolve()
            if file.is_relative_to((ROOT/'comparison').resolve()) and file.is_file():
                self.send(200,file.read_bytes(),mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
            else:self.send(404,b'Not found','text/plain')
            return
        if path == '/api/audio':
            self.send(200,json.dumps(discover()).encode())
            return
        if path.startswith('/sounds/'):
            name=path.removeprefix('/sounds/')
            file=ROOT/'sounds'/name
            if PATTERN.fullmatch(name) and file.is_file() and not file.is_symlink():
                self.send(200,file.read_bytes(),mimetypes.guess_type(name)[0] or 'application/octet-stream')
            else:self.send(404,b'Not found','text/plain')
            return
        if path == '/api/state':
            self.send(200, json.dumps(game.state()).encode())
            return
        if path.startswith(('/assets/', '/vendor/')) or path in ('/scene.js','/rendering.js','/characters.js','/environment.js','/icons.js','/minimap.js','/audio.js'):
            file = (ROOT / path.lstrip('/')).resolve()
            if file.is_relative_to(ROOT.resolve()) and file.is_file():
                self.send(200, file.read_bytes(), mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
            else:
                self.send(404, b'Not found', 'text/plain')
            return
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css'), '/app.js': ('app.js', 'text/javascript')}
        if path not in files:
            self.send(404, b'Not found', 'text/plain')
            return
        filename, mime = files[path]
        self.send(200, (ROOT / filename).read_bytes(), mime)

    def do_POST(self):
        global game
        if self.path not in ('/api/action', '/api/new', '/api/preview'):
            self.send(404, b'{}')
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise ValueError('Invalid request size.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object.')
            if self.path == '/api/preview':
                self.send(200, json.dumps(game.preview(data)).encode())
                return
            if self.path == '/api/new':
                seed = data.get('seed')
                if seed is not None and (type(seed) is not int or not 0 <= seed <= 999999999):
                    raise ValueError('Seed must be an integer from 0 to 999999999.')
                game = Game(seed, data.get('theme', 'random'), deployed=False,size=data.get('size',30),difficulty=data.get('difficulty','medium'),mission=data.get('mission','rescue'),lighting=data.get('lighting','day'))
            else:
                game.action(data)
            self.send(200, json.dumps(game.state()).encode())
        except (ValueError, TypeError) as exc:
            self.send(400, json.dumps({'error': str(exc)}).encode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Local tactical combat prototype')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    print(f'Battlefield ready at http://localhost:{args.port}', flush=True)
    try:
        HTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
