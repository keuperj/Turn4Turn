"""Regression coverage for authoritative mission totals."""
import unittest
from unittest.mock import patch
from game import Game
import test_game


class StatisticsTests(unittest.TestCase):
    def test_firearms_and_overwatch(self):
        g=test_game.CombatTests().clear();soldier=g.units[0];enemy=g.units[4]
        enemy.update(x=5,y=10,hp=100)
        with patch.object(g.rng,'randint',return_value=1):
            soldier['fire_mode']='auto';g.fire(soldier,enemy)
            g.fire(soldier,enemy,reaction=True)
            g.fire(enemy,soldier)
        with patch.object(g.rng,'randint',return_value=100):g.fire(soldier,enemy,reaction=True)
        s=g.mission_statistics()
        self.assertEqual((s['shots_fired'],s['shots_hit'],s['shots_missed']),(5,4,1))

    def test_ground_shots_and_invalid_actions(self):
        g=test_game.CombatTests().clear();g.refresh_visibility()
        with patch.object(g.rng,'randint',return_value=1):
            g.action(dict(action='attack',unit='s0',x=5,y=15,z=0))
        self.assertEqual(g.mission_statistics()['shots_missed'],1)
        with self.assertRaises(ValueError):g.action(dict(action='shoot',unit='s0',target='missing'))
        self.assertEqual(g.shots_fired,1)

    def test_summary_and_fresh_attempt(self):
        g=Game(42);g.units[0]['hp']=0
        civilians=[u for u in g.units if u['team']=='civilian'];civilians[0]['evacuated']=True;civilians[1]['hp']=0
        for u in g.units:
            if u['team']=='alien':u['hp']=0
        g.round=4;g.check_end();s=g.state()['summary']
        self.assertEqual(g.status,'defeat')
        self.assertEqual((s['fighters_killed'],s['civilians_rescued'],s['civilians_killed'],s['turns']),(1,1,1,4))
        self.assertEqual(s,g.state()['summary'])
        self.assertNotEqual(g.mission_id,Game(42).mission_id)
        self.assertIsNone(Game(42,deployed=False).state()['summary'])
