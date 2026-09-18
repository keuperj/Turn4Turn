"""Downtown layout must remain seeded, fully zoned and traversable."""
import random
import unittest
from types import SimpleNamespace
from game import Game
from world import generate


class UrbanTests(unittest.TestCase):
    def layout(self,seed,size):
        game=SimpleNamespace(rng=random.Random(seed),size=size,theme='urban')
        generate(game)
        return game

    def test_zones_and_amenities_across_sizes_and_seeds(self):
        parks=set()
        for size in (24,30,40):
            for seed in range(16):
                g=self.layout(seed,size)
                self.assertEqual(g.props,self.layout(seed,size).props)
                self.assertTrue({t for row in g.tiles for t in row}<={'road','sidewalk','plaza','floor','park','park_path'})
                self.assertGreaterEqual(len(g.buildings),5)
                self.assertTrue(all(3<=b['level']<=6 for b in g.buildings))
                park=g.scenery['park'];parks.add((park['x'],park['y']))
                kinds={p['kind'] for p in g.props}
                self.assertTrue({'car','tree_oak','tree_birch','bush','bench','cafe_table','traffic_light','sign','lamp','trash'}<=kinds,(size,seed,kinds))
                self.assertTrue({'CAFE','CORNER SHOP'}<={b['name'] for b in g.buildings})
                self.assertTrue(any(p['kind']=='bench' and park['x']<=p['x']<park['x']+park['width'] and park['y']<=p['y']<park['y']+park['depth'] for p in g.props))
                cells=set()
                for prop in g.props:
                    footprint={(x,y,0) for x in range(prop['x'],prop['x']+prop['width']) for y in range(prop['y'],prop['y']+prop['depth'])}
                    self.assertFalse(cells&footprint);cells.update(footprint)
                    self.assertTrue(all(g.heights[y][x]==0 for x,y,_ in footprint))
                    if prop['kind']=='car':self.assertTrue(all(g.tiles[y][x]=='road' for x,y,_ in footprint))
                self.assertFalse(any(tuple(p['b']) in g.blocked for p in g.portals if p['kind']=='door' and p['side']!='interior'))
                self.assertTrue(all(g.tiles[y][g.road_x]=='road' and (g.road_x,y,0) not in g.blocked for y in range(size)))
        self.assertGreater(len(parks),8)

    def test_walkways_rooms_and_upper_floors_remain_connected(self):
        for size in (24,30,40):
            for seed in (0,7,41):
                g=Game(seed,'urban',size=size)
                reachable=set(g.paths(g.units[0],999,ignore_units=True,ignore_doors=True))
                self.assertFalse(g.surfaces-g.blocked-reachable,(size,seed,sorted(g.surfaces-g.blocked-reachable)[:10]))
