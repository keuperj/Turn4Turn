"""Test sessions behavior."""

import http.client
import json
import threading
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer
from urllib.parse import quote
import time
import unittest
import server


class SessionRegistryTests(unittest.TestCase):
    """Group automated checks for sessionregistry behavior."""
    def setUp(self):
        """Prepare isolated state required by this test case."""
        self.old_registry,self.old_max,self.old_timeout=server.registry,server.MAX_PLAYERS,server.SESSION_TIMEOUT
        server.registry=server.SessionRegistry();server.MAX_PLAYERS=2;server.SESSION_TIMEOUT=1800

    def tearDown(self):
        """Release resources and restore shared state after the test."""
        server.registry,server.MAX_PLAYERS,server.SESSION_TIMEOUT=self.old_registry,self.old_max,self.old_timeout

    def test_players_have_isolated_games_and_existing_cookie_reconnects(self):
        """Verify that players have isolated games and existing cookie reconnects."""
        first=server.registry.create('Alpha');second=server.registry.create('Bravo')
        self.assertIsNot(first.game,second.game)
        first.game.round=7
        self.assertEqual(second.game.round,1)
        self.assertIs(server.registry.create('Alpha Again',first.user_id),first)
        self.assertEqual(first.username,'Alpha Again')

    def test_capacity_blocks_new_player_and_idle_session_frees_slot(self):
        """Verify that capacity blocks new player and idle session frees slot."""
        first=server.registry.create('Alpha');server.registry.create('Bravo')
        self.assertIsNone(server.registry.create('Charlie'))
        first.last_seen=time.monotonic()-10;server.SESSION_TIMEOUT=5;server.registry.prune()
        self.assertIsNotNone(server.registry.create('Charlie'))

    def test_player_ids_are_unpredictable_cookie_safe_values(self):
        """Verify that player ids are unpredictable cookie safe values."""
        player=server.registry.create('Alpha')
        self.assertRegex(player.user_id,server.USER_ID)
        self.assertEqual(len(player.user_id),32)


class QuietHandler(server.Handler):
    def log_message(self,*_args):pass


class PersistentConsentTests(unittest.TestCase):
    """Exercise real HTTP cookies independently of the in-memory player registry."""
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
        threading.Thread(target=cls.httpd.serve_forever,daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close()

    def setUp(self):
        self.original=(server.registry,server.game,server.MAX_PLAYERS)
        server.registry=server.SessionRegistry();server.MAX_PLAYERS=2

    def tearDown(self):
        server.registry,server.game,server.MAX_PLAYERS=self.original

    def request(self,method='GET',cookie='',data=None,path='/api/session'):
        connection=http.client.HTTPConnection('127.0.0.1',self.httpd.server_port)
        headers={'Cookie':cookie,'Content-Type':'application/json'}
        connection.request(method,path,body=json.dumps(data) if data is not None else None,headers=headers)
        response=connection.getresponse();result=response.status,json.loads(response.read()),response.getheaders()
        connection.close();return result

    def consent(self,name='Returning Player'):
        status,result,headers=self.request('POST',data=dict(username=name,consent=True))
        self.assertEqual(status,200);self.assertTrue(result['accepted'])
        cookies=SimpleCookie()
        for key,value in headers:
            if key.lower()=='set-cookie':cookies.load(value)
        return '; '.join(f'{key}={value.value}' for key,value in cookies.items()),cookies[server.USER_COOKIE].value

    def test_active_profile_reconnects_without_reset_or_duplicate_slot(self):
        cookie,uid=self.consent();session=server.registry.sessions[uid]
        for _ in range(2):
            status,result,_=self.request(cookie=cookie)
            self.assertEqual(status,200);self.assertTrue(result['accepted'])
            self.assertIs(server.registry.sessions[uid],session)
        self.assertEqual(len(server.registry.sessions),1)

    def test_restart_restores_identity_from_existing_cookies(self):
        cookie,uid=self.consent('Zoë Player');previous=server.registry.sessions[uid].game
        server.registry=server.SessionRegistry()
        status,result,headers=self.request(cookie=cookie)
        self.assertEqual((status,result),(200,dict(accepted=True,username='Zoë Player')))
        restored=server.registry.sessions[uid]
        self.assertIsNot(restored.game,previous);self.assertEqual(restored.game.status,'loadout')
        self.assertIs(restored.game,server.game)
        self.assertFalse(any(k.lower()=='set-cookie' for k,_ in headers))
        self.assertEqual(self.request(cookie=cookie,path='/api/state')[0],200)

    def test_idle_timeout_restores_identity_into_a_fresh_game(self):
        cookie,uid=self.consent();previous=server.registry.sessions[uid]
        previous.last_seen=time.monotonic()-server.SESSION_TIMEOUT-1
        status,result,_=self.request(cookie=cookie)
        self.assertEqual(status,200);self.assertTrue(result['accepted'])
        restored=server.registry.sessions[uid]
        self.assertIsNot(restored,previous);self.assertIsNot(restored.game,previous.game)

    def test_new_or_incomplete_profiles_still_require_consent(self):
        uid='a'*32
        for cookie in ('',f'{server.NAME_COOKIE}=Player',f'{server.USER_COOKIE}={uid}',
                       f'{server.USER_COOKIE}=invalid; {server.NAME_COOKIE}=Player',
                       f'{server.USER_COOKIE}={uid}; {server.NAME_COOKIE}=%00Bad',
                       f'{server.USER_COOKIE}={uid}; {server.NAME_COOKIE}=%FF'):
            with self.subTest(cookie=cookie):
                status,result,_=self.request(cookie=cookie)
                self.assertEqual(status,200);self.assertFalse(result['accepted'])
                self.assertFalse(server.registry.sessions)
        self.assertEqual(self.request('POST',data=dict(username='Player',consent=False))[0],400)

    def test_capacity_does_not_request_consent_again_or_replace_other_players(self):
        cookie,uid=self.consent();server.registry=server.SessionRegistry();server.MAX_PLAYERS=1
        other=server.registry.create('Other Player')
        status,result,_=self.request(cookie=cookie)
        self.assertEqual(status,503);self.assertTrue(result['full'])
        self.assertNotIn(uid,server.registry.sessions)
        self.assertIs(server.registry.sessions[other.user_id],other)
        other_cookie=f'{server.USER_COOKIE}={other.user_id}; {server.NAME_COOKIE}={quote(other.username)}'
        self.assertTrue(self.request(cookie=other_cookie)[1]['accepted'])
        server.registry.sessions.clear()
        self.assertTrue(self.request(cookie=cookie)[1]['accepted'])


if __name__=='__main__':unittest.main()
