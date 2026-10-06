"""Airport layout, collision-safe parking, waiting hall and clear runway."""
import random
import unittest
from types import SimpleNamespace
from game import Game
from world import generate


class AirportTests(unittest.TestCase):
    def test_layout_and_equipment(self):
        for n in (24,30,40):
            for seed in range(20):
                g=SimpleNamespace(rng=random.Random(seed),size=n,theme='airport');generate(g)
                again=SimpleNamespace(rng=random.Random(seed),size=n,theme='airport');generate(again)
                self.assertEqual(g.props,again.props)
                terminal=g.buildings[0]
                self.assertEqual(terminal['airport_role'],'terminal')
                self.assertEqual(sum(b['airport_role']=='hangar' for b in g.buildings),2)
                self.assertEqual(next(b['level'] for b in g.buildings if b['airport_role']=='tower'),3)
                self.assertGreater(terminal['width']*terminal['depth'],max(b['width']*b['depth'] for b in g.buildings[1:]))
                runway={(x,y,0) for y in range(n) for x in range(n) if g.tiles[y][x]=='runway'}
                self.assertEqual(len(runway),n*6)
                self.assertFalse(runway&g.blocked)
                self.assertTrue(all(not g.heights[y][x] for x,y,_ in runway))
                models={p.get('model') for p in g.props}
                self.assertTrue({'AirportTug','AirportFuelBowser','AirportPowerCart','AirportWindsock'}<=models,(n,seed,models))
                self.assertTrue({'AirportLightPlane','AirportBusinessJet'}&models)
                self.assertEqual(sum(p['kind']=='aircraft' for p in g.props),1 if n==24 else 2)
                furnishings=[p for p in g.props if p.get('interior')==terminal['id']]
                self.assertTrue({'bench','ticket_counter'}<={p['kind'] for p in furnishings})
                self.assertFalse(any(w['side']=='interior' and w['building']==terminal['id'] for w in g.walls.values()))
                self.assertTrue(any(p['side']=='west' and p['kind']=='door' and p['building']==terminal['id'] for p in g.portals))
                for p in g.props:
                    if p['kind']=='aircraft':
                        self.assertTrue(all(g.tiles[y][x]=='apron' for y in range(p['y'],p['y']+p['depth']) for x in range(p['x'],p['x']+p['width'])))

    def test_all_surfaces_remain_reachable(self):
        for n in (24,30,40):
            for seed in (0,7,41):
                g=Game(seed,'airport',size=n)
                reachable=set(g.paths(g.units[0],999,ignore_units=True,ignore_doors=True))
                self.assertFalse(g.surfaces-g.blocked-reachable,(n,seed))


if __name__=='__main__':unittest.main()
