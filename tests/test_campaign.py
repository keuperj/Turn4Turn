import json
import unittest
from pathlib import Path

from game import DIFFICULTIES, MISSIONS, Game
from world import THEMES


class CampaignTests(unittest.TestCase):
    def test_campaign_defines_ten_valid_ordered_missions(self):
        path=Path(__file__).parents[1]/'campaigns'/'operation_turning_point.json'
        campaign=json.loads(path.read_text())
        self.assertEqual(len(campaign['missions']),10)
        self.assertEqual(len({m['seed'] for m in campaign['missions']}),10)
        for mission in campaign['missions']:
            self.assertIn(mission['mission'],MISSIONS)
            self.assertIn(mission['theme'],THEMES)
            self.assertIn(mission['difficulty'],DIFFICULTIES)
            self.assertIn(mission['size'],(24,30,40))
            self.assertIn(mission['lighting'],('day','night'))
            self.assertTrue(mission['title'] and mission['objective'])

    def test_campaign_briefing_overrides_generic_mission_copy(self):
        game=Game(7,title='Custom operation',objective='Custom objective')
        state=game.state()
        self.assertEqual(state['mission']['label'],'Custom operation')
        self.assertEqual(state['mission']['objective'],'Custom objective')


if __name__=='__main__':unittest.main()
