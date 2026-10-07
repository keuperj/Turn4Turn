import http.client
import socket
import threading
import unittest
from unittest.mock import Mock, patch

import server


class QuietHandler(server.Handler):
    timeout = 0.2

    def log_message(self, *args):
        pass


class ConnectionTests(unittest.TestCase):
    def test_idle_and_incomplete_clients_expire_without_blocking_requests(self):
        with server.GameHTTPServer(('127.0.0.1', 0), QuietHandler) as httpd:
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            address = httpd.server_address
            try:
                for request in (b'', b'POST /api/session HTTP/1.0\r\nContent-Length: 100\r\n\r\n{'):
                    with socket.create_connection(address, timeout=2) as stalled:
                        if request:
                            stalled.sendall(request)
                        connection = http.client.HTTPConnection(*address, timeout=2)
                        try:
                            connection.request('GET', '/api/session')
                            response = connection.getresponse()
                            self.assertEqual(response.status, 200)
                            response.read()
                        finally:
                            connection.close()
                        self.assertEqual(stalled.recv(1), b'')
            finally:
                httpd.shutdown()
                thread.join(timeout=2)

    def test_idle_sessions_are_pruned_without_incoming_requests(self):
        registry=server.SessionRegistry()
        idle=registry.create('Idle Player');active=registry.create('Active Player')
        idle.last_seen-=server.SESSION_TIMEOUT+1
        cleaned=threading.Event()
        prune=registry.prune

        def observe_prune():
            prune()
            if idle.user_id not in registry.sessions:cleaned.set()

        with patch.object(server,'registry',registry), patch.object(registry,'prune',side_effect=observe_prune):
            with server.GameHTTPServer(('127.0.0.1',0),QuietHandler) as httpd:
                thread=threading.Thread(target=httpd.serve_forever,kwargs={'poll_interval':0.01},daemon=True)
                thread.start()
                try:
                    self.assertTrue(cleaned.wait(timeout=2))
                    with registry.lock:
                        self.assertNotIn(idle.user_id,registry.sessions)
                        self.assertIs(registry.sessions[active.user_id],active)
                finally:
                    httpd.shutdown();thread.join(timeout=2)

    def test_responses_do_not_hold_player_lock(self):
        session = server.PlayerSession('a' * 32, 'Alpha', Mock())
        session.game.state.return_value = {'round': 1}
        session.game.preview.return_value = {'valid': True}
        for path in ('/api/state', '/api/preview', '/api/action', '/api/new'):
            with self.subTest(path=path):
                handler = object.__new__(server.Handler)
                handler.path = path
                handler.require_player = lambda: session
                handler.read_json = lambda: {}
                acquired = []

                def send(*args):
                    def probe():
                        locked = session.lock.acquire(timeout=0.2)
                        acquired.append(locked)
                        if locked:
                            session.lock.release()
                    worker = threading.Thread(target=probe)
                    worker.start()
                    worker.join(timeout=1)

                handler.send = send
                with patch.object(server, 'Game', return_value=session.game), patch.object(server, 'game', session.game):
                    if path == '/api/state':
                        handler.do_GET()
                    else:
                        handler.do_POST()
                self.assertEqual(acquired, [True])


if __name__ == '__main__':
    unittest.main()
