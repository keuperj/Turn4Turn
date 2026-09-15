"""Test gpu test behavior."""

import threading
import unittest
from http.server import HTTPServer
from urllib.request import urlopen

import server


class QuietHandler(server.Handler):
    """Suppress request logging for route-level tests."""
    def log_message(self, *_args):
        """Suppress HTTP access logging during tests."""
        pass


class GPUTestRouteTests(unittest.TestCase):
    """Verify GPU diagnostic and landing-status resources are reachable."""
    @classmethod
    def setUpClass(cls):
        """Prepare isolated state required by this test case."""
        cls.httpd = HTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.httpd.server_port}'

    @classmethod
    def tearDownClass(cls):
        """Release resources and restore shared state after the test."""
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def fetch(self, path):
        """Fetch a server path and return status, MIME type, and bytes."""
        with urlopen(self.base + path) as response:
            return response.status, response.headers.get_content_type(), response.read()

    def test_gpu_test_aliases_serve_the_diagnostic_page(self):
        """Verify that gpu test aliases serve the diagnostic page."""
        for path in ('/gpu-test', '/gpu-test/', '/gpu-test.html'):
            status, content_type, body = self.fetch(path)
            self.assertEqual(status, 200)
            self.assertEqual(content_type, 'text/html')
            self.assertIn(b'WebGPU capability test', body)
            self.assertIn(b'/gpu-test.js', body)

    def test_gpu_test_assets_are_served_with_expected_types(self):
        """Verify that gpu test assets are served with expected types."""
        status, content_type, script = self.fetch('/gpu-test.js')
        self.assertEqual((status, content_type), (200, 'text/javascript'))
        self.assertIn(b"from './webgpu-check.js'", script)
        self.assertIn(b'dom.webgpu.enabled', script)
        self.assertIn(b'about:support', script)
        self.assertIn(b'Accept the Risk and Continue', script)
        self.assertIn(b'HTTPS-Only Mode exception', script)
        status, content_type, probe = self.fetch('/webgpu-check.js')
        self.assertEqual((status, content_type), (200, 'text/javascript'))
        self.assertIn(b'navigator.gpu.requestAdapter', probe)
        self.assertIn(b'createComputePipelineAsync', probe)
        self.assertIn(b'Promise.race', probe)
        self.assertIn(b'export async function testWebGPU', probe)
        status, content_type, _ = self.fetch('/gpu-test.css')
        self.assertEqual((status, content_type), (200, 'text/css'))

    def test_landing_page_shows_renderer_status_and_test_link(self):
        """Verify that landing page shows renderer status and test link."""
        status, content_type, body = self.fetch('/')
        self.assertEqual((status, content_type), (200, 'text/html'))
        self.assertIn(b'id="gpu-status"', body)
        self.assertIn(b'href="/gpu-test"', body)


if __name__ == '__main__':
    unittest.main()
