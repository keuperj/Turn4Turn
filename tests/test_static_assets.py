"""Static asset compression, conditional caching, and API isolation."""
import gzip
import json
import http.client
import re
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urljoin
import server

class QuietHandler(server.Handler):
    def log_message(self, *_args):
        pass

class StaticAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
        threading.Thread(target=cls.httpd.serve_forever,daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close()

    def get(self,path,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.httpd.server_port)
        connection.request('GET',path,headers=headers or {})
        response=connection.getresponse();result=(response.status,dict(response.getheaders()),response.read())
        connection.close();return result

    def test_scene_module_dependencies_are_served(self):
        status,_,catalog=self.get('/api/scenarios')
        self.assertEqual(status,200)
        pending=['/scene.js']+[s['module'] for s in json.loads(catalog)['scenarios']];visited=set()
        while pending:
            path=pending.pop()
            if path in visited:continue
            visited.add(path)
            with self.subTest(path=path):
                status,headers,body=self.get(path)
                self.assertEqual(status,200)
                self.assertIn(headers['Content-Type'].split(';')[0],
                              ('text/javascript','application/javascript'))
                self.assertEqual(body,(server.ROOT/path.lstrip('/')).read_bytes())
                # Follow the renderer's static relative imports transitively.
                imports=re.findall(r"^(?:import|export)\s+(?:[^;\n]*?\s+from\s+)?['\"]([^'\"]+)['\"]",
                                   body.decode(),re.MULTILINE)
                pending.extend(urljoin(path,name) for name in imports if name.startswith('.'))

    def test_registry_assets_and_private_paths(self):
        status,_,body=self.get('/api/models')
        self.assertEqual(status,200)
        models=json.loads(body)['models']
        self.assertTrue(any(m['url'].startswith('/scenarios/factory/') for m in models))
        for entry in models:
            status,_,body=self.get(entry['url'])
            self.assertEqual(status,200,entry['url'])
            self.assertEqual(body[:4],b'glTF')
        for path in ['/scenarios/../../server.py','/scenarios/factory/scenario.py']:
            self.assertEqual(self.get(path)[0],404)

    def test_gzip_assets_are_identical_after_decompression(self):
        for path in ['/vendor/babylon.js','/assets/models/Ninja_Male.glb','/app.js']:
            with self.subTest(path=path):
                status,headers,body=self.get(path,{'Accept-Encoding':'gzip'})
                self.assertEqual(status,200)
                self.assertEqual(headers['Content-Encoding'],'gzip')
                original=(server.ROOT/path.lstrip('/')).read_bytes()
                self.assertEqual(gzip.decompress(body),original)
                self.assertLess(len(body),len(original)*.65)
                status,cached,body=self.get(path,{'Accept-Encoding':'gzip','If-None-Match':headers['ETag']})
                self.assertEqual((status,body),(304,b''))
                self.assertEqual(cached['ETag'],headers['ETag'])

    def test_identity_and_image_caching(self):
        for path in ['/assets/items.png','/vendor/babylon.js']:
            status,headers,body=self.get(path,{'Accept-Encoding':'gzip;q=0, *;q=1'})
            self.assertEqual(status,200)
            self.assertNotIn('Content-Encoding',headers)
            self.assertEqual(body,(server.ROOT/path.lstrip('/')).read_bytes())
            self.assertIn('must-revalidate',headers['Cache-Control'])
            self.assertEqual(self.get(path,{'If-None-Match':headers['ETag']})[0],304)

    def test_dynamic_player_data_is_never_cached(self):
        status,headers,_body=self.get('/api/session',{'Accept-Encoding':'gzip'})
        self.assertEqual(status,200)
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertNotIn('ETag',headers)

    def test_asset_edits_invalidate_both_representations(self):
        # The production root stays unchanged; serve a temporary fixture through
        # the same path validation and HTTP implementation.
        original=QuietHandler.serve_file
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);asset=root/'fixture.js';asset.write_text('const first = 1;\n'*100)
            def fixture(handler,file,root_arg=None):
                return original(handler,asset,root)
            with patch.object(QuietHandler,'serve_file',fixture):
                _,headers,body=self.get('/scene.js',{'Accept-Encoding':'gzip'})
                asset.write_text('const replacement = 2;\n'*100)
                status,updated,body=self.get('/scene.js',{'Accept-Encoding':'gzip','If-None-Match':headers['ETag']})
                self.assertEqual(status,200)
                self.assertNotEqual(headers['ETag'],updated['ETag'])
                self.assertEqual(gzip.decompress(body),asset.read_bytes())

if __name__=='__main__':unittest.main()
