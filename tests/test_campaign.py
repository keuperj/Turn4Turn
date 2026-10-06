"""Test campaign behavior."""

import json
import unittest
from pathlib import Path

from campaign_catalog import campaign_catalog, campaign_mission
from game import DIFFICULTIES, MISSIONS, Game
from world import THEMES


class CampaignTests(unittest.TestCase):
    """Group automated checks for campaign behavior."""
    def test_three_campaigns_cover_all_scenarios_and_modes(self):
        campaigns=campaign_catalog()['campaigns']
        self.assertEqual([c['difficulty'] for c in campaigns],['easy','medium','hard'])
        self.assertEqual(len({c['id'] for c in campaigns}),3)
        seeds=set()
        for campaign in campaigns:
            self.assertEqual(len(campaign['missions']),10)
            self.assertEqual({m['theme'] for m in campaign['missions']},set(THEMES))
            self.assertEqual({m['mission'] for m in campaign['missions']},set(MISSIONS))
            art=Path(__file__).parents[1]/'static'/campaign['background'].lstrip('/')
            self.assertTrue(art.read_bytes().startswith(bytes.fromhex('89504e470d0a1a0a')))
            for mission in campaign['missions']:
                self.assertEqual(mission['size'],40)
                self.assertEqual(mission['difficulty'],campaign['difficulty'])
                self.assertNotIn(mission['seed'],seeds);seeds.add(mission['seed'])
                self.assertIn(mission['lighting'],('day','night'))
                self.assertTrue(mission['title'] and mission['objective'])

    def test_all_thirty_missions_generate_with_published_settings(self):
        for campaign in campaign_catalog()['campaigns']:
            for i,mission in enumerate(campaign['missions']):
                with self.subTest(campaign=campaign['id'],mission=i):
                    game=Game(**campaign_mission(campaign['id'],i),deployed=False)
                    state=game.state()
                    self.assertEqual((state['size'],state['difficulty']),(40,campaign['difficulty']))
                    self.assertEqual(state['theme'],mission['theme'])
                    self.assertEqual(state['mission']['key'],mission['mission'])
                    self.assertEqual(state['mission']['label'],mission['title'])
                    self.assertEqual(state['status'],'loadout')

    def test_invalid_campaign_selection_is_rejected(self):
        for campaign,index in [('missing',0),('operation-turning-point',-1),
                               ('operation-turning-point',10),('operation-turning-point',True),
                               ('operation-turning-point','1')]:
            with self.assertRaises(ValueError):campaign_mission(campaign,index)

    def test_campaign_briefing_overrides_generic_mission_copy(self):
        """Verify that campaign briefing overrides generic mission copy."""
        game=Game(7,title='Custom operation',objective='Custom objective')
        state=game.state()
        self.assertEqual(state['mission']['label'],'Custom operation')
        self.assertEqual(state['mission']['objective'],'Custom objective')


if __name__=='__main__':unittest.main()
