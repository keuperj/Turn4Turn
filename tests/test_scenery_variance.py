"""Test scenery variance behavior."""

import unittest

from game import Game
from world import THEMES, TRANSPORT_MODELS, PROP_SIZE
import hashlib
import json
from pathlib import Path


class SceneryVarianceTests(unittest.TestCase):
    """Group automated checks for sceneryvariance behavior."""
    def test_transport_selection_is_seeded_and_all_variants_are_reachable(self):
        seen={kind:set() for kind in TRANSPORT_MODELS}
        for theme in ('urban','streets','airport','train_station','farm'):
            for seed in range(12):
                game=Game(seed,theme)
                self.assertEqual(game.props,Game(seed,theme).props)
                for prop in game.props:
                    if prop['kind'] not in seen:continue
                    models=TRANSPORT_MODELS[prop['kind']]
                    self.assertEqual(prop['model'],models[prop['variant']])
                    seen[prop['kind']].add(prop['model'])
        for kind,models in TRANSPORT_MODELS.items():
            self.assertEqual(seen[kind],set(models),kind)

    def test_transport_assets_fit_human_scale_and_collision_footprints(self):
        directory=Path(__file__).resolve().parents[1]/'static/assets/models/transport'
        catalog=json.loads((directory/'manifest.json').read_text())
        height_ranges={'car':(1.15,1.7),'truck':(1.4,2.8),'train':(2.3,3.5),'bus':(2.4,3.2),'ambulance':(1.8,2.4)}
        for entry in catalog['models']:
            data=(directory/entry['file']).read_bytes()
            self.assertEqual(data[:4],b'glTF')
            self.assertEqual(hashlib.sha256(data).hexdigest(),entry['sha256'])
            width,height,length=entry['dimensions']
            footprint=PROP_SIZE[entry['kind']]
            self.assertLessEqual(width,footprint[0]*.94+.001)
            self.assertLessEqual(length,footprint[1]*.94+.001)
            low,high=height_ranges[entry['kind']]
            self.assertTrue(low<=height<=high,entry['id'])

    def test_requested_city_building_types_are_available(self):
        """Verify that requested city building types are available."""
        names=set(THEMES['urban']['names'])|set(THEMES['streets']['names'])
        for name in {'CORNER SHOP','LIVING QUARTERS','POST OFFICE','CAFE','RESTAURANT','HARDWARE STORE'}:
            self.assertIn(name,names)

    def test_buildings_vary_in_form_and_keep_an_entrance(self):
        """Verify that buildings vary in form and keep an entrance."""
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
        """Verify that vegetation and street furniture have multiple types."""
        woods={p['kind'] for seed in range(4) for p in Game(seed,'woods').props}
        city={p['kind'] for seed in range(4) for p in Game(seed,'streets').props}
        self.assertTrue({'tree_oak','tree_pine','tree_birch','bush'}<=woods)
        self.assertTrue({'bench','sign','lamp','trash'}<=city)

    def test_visual_traits_are_public_for_the_renderer(self):
        """Verify that visual traits are public for the renderer."""
        building=Game(19,'streets').state()['buildings'][0]
        self.assertTrue({'archetype','front','roof','facade','color','accent'}<=building.keys())


if __name__=='__main__':
    unittest.main()
