"""Four-lane roads, residential zoning, safe crossings and connected garden paths."""
import random
import unittest
from types import SimpleNamespace
from game import Game
from world import generate


class StreetsTests(unittest.TestCase):
    def test_suburban_layout_and_traffic(self):
        for n in (24,30,40):
            layouts=set();traffic_counts=set()
            for seed in range(12):
                g=SimpleNamespace(rng=random.Random(seed),size=n,theme='streets');generate(g)
                again=SimpleNamespace(rng=random.Random(seed),size=n,theme='streets');generate(again)
                self.assertEqual(g.props,again.props);self.assertEqual(g.buildings,again.buildings)
                self.assertTrue({t for row in g.tiles for t in row}<={'road','sidewalk','lawn','garden','garden_path','floor'})
                self.assertEqual(g.scenery['lanes'],4);self.assertEqual(g.scenery['road_width'],12)
                low=n//2-6;high=low+12
                self.assertTrue(all(g.tiles[y][x]=='road' for y in range(n) for x in range(n) if low<=x<high or low<=y<high))
                self.assertGreaterEqual(len(g.buildings),4)
                layouts.add(tuple((b['x'],b['y'],b['width'],b['depth'],b['front']) for b in g.buildings))
                for b in g.buildings:
                    self.assertIn(b['level'],(1,2));self.assertEqual(b['roof'],'gable');self.assertEqual(b['archetype'],'residential')
                    yard=b['garden']
                    self.assertTrue(any(g.tiles[y][x] in ('lawn','garden') for y in range(yard['y'],yard['y']+yard['depth']) for x in range(yard['x'],yard['x']+yard['width'])))
                    door=next(p for p in g.portals if p['building']==b['id'] and p['kind']=='door' and p['side']!='interior')
                    x,y,_=door['b'];self.assertEqual(g.tiles[y][x],'garden_path');self.assertNotIn((x,y,0),g.blocked)
                cars=[p for p in g.props if p['kind']=='car']
                self.assertGreaterEqual(len(cars),6,(n,seed,len(cars)))
                traffic_counts.add(len(cars))
                # Short approaches must leave some lanes empty instead of a full row.
                north_lanes={p['x'] for p in cars if p['y']+p['depth']<=low}
                self.assertLess(len(north_lanes),4)
                self.assertEqual(sum(p['kind']=='traffic_light' for p in g.props),4,(n,seed))
                occupied=set()
                for p in g.props:
                    cells={(x,y,0) for x in range(p['x'],p['x']+p['width']) for y in range(p['y'],p['y']+p['depth'])}
                    self.assertFalse(cells&occupied);occupied.update(cells)
                    self.assertTrue(all(not g.heights[y][x] for x,y,_ in cells))
                    if p['kind'] in ('car','bus'):
                        self.assertTrue(all(g.tiles[y][x]=='road' for x,y,_ in cells))
                        self.assertFalse(any((low<=x<high and y in (low,low+1,high-2,high-1)) or (low<=y<high and x in (low,low+1,high-2,high-1)) for x,y,_ in cells))
            self.assertGreater(len(layouts),8)
            self.assertGreater(len(traffic_counts),1)

    def test_all_homes_and_routes_remain_reachable(self):
        for n in (24,30,40):
            for seed in (0,7,41):
                g=Game(seed,'streets',size=n)
                reachable=set(g.paths(g.units[0],999,ignore_units=True,ignore_doors=True))
                self.assertFalse(g.surfaces-g.blocked-reachable,(n,seed))
