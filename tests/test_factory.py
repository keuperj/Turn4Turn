"""Factory platforms, floor-aware machinery and connected interior routes."""
import random
import unittest
from types import SimpleNamespace
from game import Game
from world import generate


class FactoryTests(unittest.TestCase):
    def test_seeded_open_hall_and_connected_levels(self):
        for n in (24,30,40):
            layouts=set()
            for seed in range(10):
                g=SimpleNamespace(rng=random.Random(seed),size=n,theme='factory');generate(g)
                again=SimpleNamespace(rng=random.Random(seed),size=n,theme='factory');generate(again)
                layouts.add(tuple((b['x'],b['y'],b['width'],b['depth']) for b in g.buildings))
                self.assertEqual(g.props,again.props);self.assertEqual(g.buildings,again.buildings)
                self.assertEqual({p[2] for p in g.surfaces},{0,1,2})
                self.assertEqual({w['side'] for w in g.walls.values()},{'north','west'})
                self.assertTrue(all(t=='floor' for row in g.tiles for t in row))
                self.assertEqual({p.get('z') for p in g.props},{0,1,2})
                self.assertTrue({'FactoryLathe','FactoryMill','FactoryCNC','FactoryCompressor','FactoryRack','FactoryForklift','FactoryRobot','FactoryConveyor'}<={p['model'] for p in g.props})
                occupied=set()
                for p in g.props:
                    cells=set(Game.footprint(p));self.assertTrue(cells<=g.surfaces)
                    self.assertFalse(cells&occupied);occupied.update(cells)
                self.assertEqual(g.blocked,occupied)
                self.assertFalse({tuple(p) for link in g.stairs for p in link}&g.blocked)
            self.assertGreater(len(layouts),1)
            g=Game(41,'factory',size=n)
            self.assertFalse(g.surfaces-g.blocked-set(g.paths(g.units[0],999,ignore_units=True,ignore_doors=True)))

    def test_elevated_machine_visibility_targeting_and_destruction(self):
        g=Game(41,'factory');p=next(p for p in g.props if p['z']==1)
        for u in g.alive('soldier'):u.update(x=p['x'],y=p['y'],z=0)
        g.init_fog();self.assertNotIn(p['id'],g.known_props)
        cells=set(g.footprint(p))
        adjacent=next((x+dx,y+dy,z) for x,y,z in cells for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)) if (x+dx,y+dy,z) in g.surfaces-g.blocked)
        u=g.units[0];u.update(x=adjacent[0],y=adjacent[1],z=adjacent[2])
        g.init_fog();self.assertIn(p['id'],g.known_props)
        target=next(t for t in g.structure_targets(u) if t['id']==p['id'])
        self.assertEqual(target['point'][2],1)
        g.preview(dict(action='attack',unit=u['id'],structure=p['id'],x=target['point'][0],y=target['point'][1],z=1))
        heights=[row[:] for row in g.heights];surfaces=g.surfaces.copy()
        g.damage_structure(p,10000)
        self.assertTrue(p['destroyed']);self.assertFalse(cells&g.blocked)
        self.assertEqual(g.heights,heights);self.assertEqual(g.surfaces,surfaces)

    def test_blast_on_upper_floor_and_platform_collapse(self):
        g=Game(41,'factory');p=next(p for p in g.props if p['z']==2)
        g.damage_area(p['x'],p['y'],2,0,10000)
        self.assertTrue(p['destroyed'])
        g=Game(41,'factory');platform=g.buildings[0]
        upper={c for c in g.surfaces if c[2]>0 and c[1]<platform['depth']}
        g.damage_structure(platform,10000)
        self.assertFalse(upper&g.surfaces);self.assertFalse(upper&g.blocked)
        self.assertTrue(all(p['destroyed'] for p in g.props if p.get('z',0)>0 and p['y']<platform['depth']))


if __name__=='__main__':unittest.main()
