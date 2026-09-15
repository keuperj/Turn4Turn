import threading
import unittest
from http.server import HTTPServer
from urllib.request import urlopen

import server


class QuietHandler(server.Handler):
    def log_message(self, *_args):
        pass


class GPUTestRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.httpd.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def fetch(self, path):
        with urlopen(self.base + path) as response:
            return response.status, response.headers.get_content_type(), response.read()

    def test_gpu_test_aliases_serve_the_diagnostic_page(self):
        for path in ('/gpu-test', '/gpu-test/', '/gpu-test.html'):
            status, content_type, body = self.fetch(path)
            self.assertEqual(status, 200)
            self.assertEqual(content_type, 'text/html')
            self.assertIn(b'WebGPU capability test', body)
            self.assertIn(b'/gpu-test.js', body)

    def test_gpu_test_assets_are_served_with_expected_types(self):
        status, content_type, script = self.fetch('/gpu-test.js')
        self.assertEqual((status, content_type), (200, 'text/javascript'))
        self.assertIn(b'navigator.gpu.requestAdapter', script)
        self.assertIn(b'createComputePipelineAsync', script)
        self.assertIn(b'dom.webgpu.enabled', script)
        self.assertIn(b'about:support', script)
        status, content_type, _ = self.fetch('/gpu-test.css')
        self.assertEqual((status, content_type), (200, 'text/css'))


if __name__ == '__main__':
    unittest.main()
