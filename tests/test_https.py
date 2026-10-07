"""Integration tests for the optional self-signed HTTPS server mode."""
import json
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

import server


class QuietHandler(server.Handler):
    """Suppress request logging during integration tests."""
    timeout=0.5

    def log_message(self,format,*args):
        """Discard the standard HTTP access-log entry."""


class HttpsServerTests(unittest.TestCase):
    """Verify certificate generation and encrypted request handling."""

    def setUp(self):
        """Replace the shared registry so tests cannot leak player sessions."""
        self.old_registry,self.old_game=server.registry,server.game;server.registry=server.SessionRegistry()

    def tearDown(self):
        """Restore the process-wide registry used by other server tests."""
        server.registry,server.game=self.old_registry,self.old_game

    def test_certificate_contains_requested_ip_and_is_reused(self):
        """Generate an IP SAN once and reuse the valid certificate afterward."""
        with tempfile.TemporaryDirectory() as directory:
            certificate,key,created=server.ensure_self_signed_certificate('127.0.0.1',directory)
            self.assertTrue(created);self.assertEqual(key.stat().st_mode & 0o777,0o600)
            details=subprocess.run(['openssl','x509','-in',str(certificate),'-noout','-text'],check=True,capture_output=True,text=True).stdout
            self.assertIn('IP Address:127.0.0.1',details)
            self.assertEqual(server.ensure_self_signed_certificate('127.0.0.1',directory),(certificate,key,False))

    def test_https_server_serves_page_and_sets_secure_cookies(self):
        """Complete a TLS request and ensure session cookies are Secure."""
        with tempfile.TemporaryDirectory() as directory:
            httpd,certificate,created=server.create_server('127.0.0.1',0,True,directory,QuietHandler)
            self.assertTrue(created);self.assertTrue(Path(certificate).is_file())
            thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
            context=ssl._create_unverified_context();base=f'https://127.0.0.1:{httpd.server_port}'
            try:
                with urlopen(base+'/gpu-test',context=context) as response:
                    self.assertEqual(response.status,200);self.assertIn(b'WebGPU',response.read())
                body=json.dumps({'username':'TLS Player','consent':True}).encode()
                request=Request(base+'/api/session',data=body,headers={'Content-Type':'application/json'},method='POST')
                with urlopen(request,context=context) as response:
                    cookies=response.headers.get_all('Set-Cookie');self.assertEqual(response.status,200)
                self.assertEqual(len(cookies),2);self.assertTrue(all('; Secure' in cookie for cookie in cookies))
            finally:
                httpd.shutdown();httpd.server_close();thread.join(timeout=2)

    def test_unfinished_tls_handshake_does_not_block_other_clients(self):
        """A browser opening a TCP socket without sending TLS must not stop accept()."""
        class HandshakeHandler(QuietHandler):
            timeout=2
        with tempfile.TemporaryDirectory() as directory:
            httpd,_,_=server.create_server('127.0.0.1',0,True,directory,HandshakeHandler)
            thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
            stalled=socket.create_connection(httpd.server_address,timeout=3)
            context=ssl._create_unverified_context();base=f'https://127.0.0.1:{httpd.server_port}'
            try:
                with urlopen(base+'/api/session',context=context,timeout=1) as response:
                    self.assertEqual(response.status,200)
                # The abandoned handshake's worker must eventually release its socket.
                self.assertEqual(stalled.recv(1),b'')
            finally:
                stalled.close()
                httpd.shutdown();httpd.server_close();thread.join(timeout=2)

    def test_disconnects_and_incomplete_https_requests_preserve_player(self):
        """Reconnect after closing at different stages without losing the player's game."""
        with tempfile.TemporaryDirectory() as directory:
            httpd,_,_=server.create_server('127.0.0.1',0,True,directory,QuietHandler)
            thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
            context=ssl._create_unverified_context();base=f'https://127.0.0.1:{httpd.server_port}'
            player=server.registry.create('Returning Player',fresh=True);player.game.round=7
            cookie=f'{server.USER_COOKIE}={player.user_id}'
            try:
                # Close before TLS, after TLS, and halfway through a request body.
                with socket.create_connection(httpd.server_address,timeout=2):pass
                for body in (b'',b'POST /api/action HTTP/1.0\r\nContent-Length: 100\r\nCookie: '+cookie.encode()+b'\r\n\r\n{'):
                    with socket.create_connection(httpd.server_address,timeout=2) as raw:
                        with context.wrap_socket(raw,server_hostname='localhost') as client:
                            if body:client.sendall(body)
                # A client that stays connected but stops transmitting also expires.
                with socket.create_connection(httpd.server_address,timeout=2) as raw:
                    with context.wrap_socket(raw,server_hostname='localhost') as client:
                        client.sendall(b'GET /api/state HTTP/1.0\r\nCookie: '+cookie.encode())
                        self.assertEqual(client.recv(1),b'')
                request=Request(base+'/api/state',headers={'Cookie':cookie})
                with urlopen(request,context=context,timeout=2) as response:
                    self.assertEqual(response.status,200)
                    self.assertEqual(json.load(response)['round'],7)
                self.assertIs(server.registry.get(player.user_id),player)
            finally:
                httpd.shutdown();httpd.server_close();thread.join(timeout=2)


if __name__=='__main__':unittest.main()
