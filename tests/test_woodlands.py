"""Woodland density, seeded clearings and unobstructed cabin access."""
import random
import unittest
from types import SimpleNamespace
from world import generate
from game import Game


class WoodlandTests(unittest.TestCase):
    def test_layout_and_connected_paths(self):
        for n in (24,30,40):
            layouts=set()
            for seed in range(12):
                g=SimpleNamespace(rng=random.Random(seed),size=n,theme='woods');generate(g)
                again=SimpleNamespace(rng=random.Random(seed),size=n,theme='woods');generate(again)
                self.assertEqual(g.props,again.props);self.assertEqual(g.tiles,again.tiles)
                self.assertGreaterEqual(len(g.buildings),4)
                self.assertTrue(all(b['level']==1 and b['facade']=='timber' and b['roof']=='gable' and max(b['width'],b['depth'])<=4 for b in g.buildings))
                types={t for row in g.tiles for t in row}
                self.assertEqual(types,{'forest','forest_path','meadow','floor'})
                layouts.add(tuple((b['x'],b['y']) for b in g.buildings))
                trees=[p for p in g.props if p['kind'].startswith('tree_')]
                self.assertGreater(len(trees),n*n*.10,(n,seed,len(trees)))
                self.assertTrue({'tree_oak','tree_pine','tree_birch','bush'}<={p['kind'] for p in g.props})
                paths={(x,y,0) for y in range(n) for x in range(n) if g.tiles[y][x]=='forest_path'}
                seen={(n//2,n-1,0)};queue=list(seen)
                for x,y,z in queue:
                    for q in ((x+1,y,0),(x-1,y,0),(x,y+1,0),(x,y-1,0)):
                        if q in paths and q not in seen:seen.add(q);queue.append(q)
                self.assertEqual(paths,seen);self.assertFalse(paths&g.blocked)
                for p in g.portals:
                    if p['kind']=='door' and p['side']!='interior':self.assertIn(tuple(p['b']),paths)
            self.assertGreater(len(layouts),8)

    def test_walkable_ground_and_huts_remain_reachable(self):
        for n in (24,30,40):
            for seed in (0,7,41):
                g=Game(seed,'woods',size=n)
                reachable=set(g.paths(g.units[0],999,ignore_units=True,ignore_doors=True))
                self.assertFalse(g.surfaces-g.blocked-reachable,(n,seed))
