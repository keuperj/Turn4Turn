import unittest

from game import Game
from world import THEMES


class SceneryVarianceTests(unittest.TestCase):
    def test_requested_city_building_types_are_available(self):
        names=set(THEMES['urban']['names'])|set(THEMES['streets']['names'])
        for name in {'CORNER SHOP','LIVING QUARTERS','POST OFFICE','CAFE','RESTAURANT','HARDWARE STORE'}:
            self.assertIn(name,names)

    def test_buildings_vary_in_form_and_keep_an_entrance(self):
        buildings=[b for seed in range(8) for b in Game(seed,'urban').buildings]
        self.assertGreaterEqual(len({(b['width'],b['depth']) for b in buildings}),8)
        self.assertGreaterEqual(len({b['level'] for b in buildings}),3)
        self.assertGreaterEqual(len({b['roof'] for b in buildings}),3)
        self.assertGreaterEqual(len({b['facade'] for b in buildings}),4)
        for seed in range(8):
            game=Game(seed,'urban')
            for building in game.buildings:
                self.assertTrue(any(p['building']==building['id'] and p['kind']=='door' and p['side']!='interior' for p in game.portals))

    def test_vegetation_and_street_furniture_have_multiple_types(self):
        woods={p['kind'] for seed in range(4) for p in Game(seed,'woods').props}
        city={p['kind'] for seed in range(4) for p in Game(seed,'streets').props}
        self.assertTrue({'tree_oak','tree_pine','tree_birch','bush'}<=woods)
        self.assertTrue({'bench','sign','lamp','trash'}<=city)

    def test_visual_traits_are_public_for_the_renderer(self):
        building=Game(19,'streets').state()['buildings'][0]
        self.assertTrue({'archetype','front','roof','facade','color','accent'}<=building.keys())


if __name__=='__main__':
    unittest.main()
