"""Rebuild the bundled Quaternius characters from FBX sources using Playwright.

Usage: .venv/bin/python tools/import_characters.py /path/to/source-fbx
With --download, fetch the manifest's public CC0 source files into that directory.
Requires the existing Playwright Python package and its Chromium browser.
"""
import argparse
import base64
import hashlib
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'static/assets/models'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_dir', type=Path)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((DEST / 'characters.json').read_text())
    args.source_dir.mkdir(parents=True, exist_ok=True)
    if args.download:
        sources = [(e['id'] + '.fbx', e['source']) for e in manifest['models']]
        for name, url in sources:
            with urlopen(url, timeout=60) as response:
                data = response.read()
            if name.endswith('.fbx') and not data.startswith(b'Kaydara FBX Binary'):
                raise ValueError(f'{name}: expected binary FBX')
            (args.source_dir / name).write_bytes(data)

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                data = b'<script type="importmap">{"imports":{"three":"/vendor/three.module.js"}}</script>'
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(data)
            else:
                super().do_GET()

        def translate_path(self, path):
            if path.startswith('/source/'):
                return str(args.source_dir / Path(path).name)
            if path == '/character-convert.js':
                return str(ROOT / 'tools/character-convert.js')
            return super().translate_path(path)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT / 'static')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            for entry in manifest['models']:
                result = page.evaluate("async entry=>(await import('/character-convert.js')).convertCharacter(entry)", entry)
                data = base64.b64decode(result['data'])
                (DEST / entry['file']).write_bytes(data)
                entry['sha256'] = hashlib.sha256(data).hexdigest()
                entry['sourceSha256'] = hashlib.sha256((args.source_dir / (entry['id'] + '.fbx')).read_bytes()).hexdigest()
                print(entry['id'], len(data), flush=True)
            browser.close()
        (DEST / 'characters.json').write_text(json.dumps(manifest, indent=2) + '\n')
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
