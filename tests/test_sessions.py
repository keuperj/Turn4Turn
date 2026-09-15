"""Test sessions behavior."""

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


if __name__=='__main__':unittest.main()
