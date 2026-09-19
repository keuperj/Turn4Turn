"""Farm access, field continuity and collision-safe equipment and livestock."""
import random
import unittest
from types import SimpleNamespace
from game import Game
from world import generate


class FarmTests(unittest.TestCase):
    def test_seeded_farm_and_clear_connected_paths(self):
        for n in (24,30,40):
            layouts=set()
            for seed in range(20):
                g=SimpleNamespace(rng=random.Random(seed),size=n,theme='farm');generate(g)
                again=SimpleNamespace(rng=random.Random(seed),size=n,theme='farm');generate(again)
                self.assertEqual(g.props,again.props);self.assertEqual(g.tiles,again.tiles)
                self.assertEqual({b['name'] for b in g.buildings},{'FARMHOUSE','BARN','GRAIN STORE','MACHINE SHED'})
                self.assertTrue(all(b['roof']=='gable' for b in g.buildings))
                layouts.add(tuple((b['x'],b['y'],b['width']) for b in g.buildings))
                paths={(x,y,0) for y in range(n) for x in range(n) if g.tiles[y][x] in ('road','farm_path')}
                root=(g.road_x,n-1,0);seen={root};queue=[root]
                for x,y,z in queue:
                    for q in ((x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z)):
                        if q in paths and q not in seen:seen.add(q);queue.append(q)
                self.assertEqual(paths,seen);self.assertFalse(paths&g.blocked)
                for p in g.portals:
                    if p['kind']=='door' and p['side']!='interior':self.assertIn(tuple(p['b']),paths)
                self.assertTrue({'FarmTractor','FarmLoader','FarmCow','FarmSheep','FarmPig'}<={p.get('model') for p in g.props},(n,seed))
                for row in g.tiles:
                    self.assertEqual(row[0],'crops');self.assertEqual(row[-1],'crops')
                self.assertLessEqual(sum(p['kind'].startswith('tree_') for p in g.props),3)
            self.assertGreater(len(layouts),10)

    def test_farm_remains_fully_reachable(self):
        for n in (24,30,40):
            for seed in (0,7,41):
                g=Game(seed,'farm',size=n)
                reachable=set(g.paths(g.units[0],999,ignore_units=True,ignore_doors=True))
                self.assertFalse(g.surfaces-g.blocked-reachable,(n,seed))
