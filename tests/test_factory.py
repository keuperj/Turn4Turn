"""Factory platforms, floor-aware machinery and connected interior routes."""
import random
import unittest
from types import SimpleNamespace
from game import Game
from world import generate
from scenarios.factory.layout import validate_factory_access


class FactoryTests(unittest.TestCase):
    def test_seeded_open_hall_and_connected_levels(self):
        for n in (24,30,40):
            layouts=set()
            for seed in range(10):
                g=SimpleNamespace(rng=random.Random(seed),size=n,theme='factory');generate(g)
                again=SimpleNamespace(rng=random.Random(seed),size=n,theme='factory');generate(again)
                layouts.add(tuple((b['x'],b['y'],b['width'],b['depth']) for b in g.buildings))
                self.assertEqual(g.props,again.props);self.assertEqual(g.buildings,again.buildings)
                self.assertEqual({p[2] for p in g.surfaces},{0,1,2,3})
                self.assertEqual({w['side'] for w in g.walls.values()},{'north','west'})
                self.assertTrue(all(t=='floor' for row in g.tiles for t in row))
                self.assertEqual({p.get('z') for p in g.props},{0,1,2,3})
                self.assertTrue({'FactoryLathe','FactoryMill','FactoryCNC','FactoryCompressor','FactoryRack','FactoryForklift','FactoryRobot','FactoryConveyor'}<={p['model'] for p in g.props})
                self.assertGreaterEqual(len(g.props),n*n//14)
                central=next(b for b in g.buildings if b['name']=='CENTRAL PRODUCTION STACK')
                self.assertEqual(central['level'],3)
                self.assertTrue(central['x']>0 and central['y']>0)
                for a,d in g.stairs:
                    self.assertIn(tuple(a),g.surfaces);self.assertIn(tuple(d),g.surfaces)
                    self.assertEqual(abs(a[0]-d[0])+abs(a[1]-d[1]),3)
                    self.assertEqual(d[2]-a[2],1)
                holes={tuple(p) for b in g.buildings for p in b.get('floor_holes',[])}
                self.assertEqual(len(holes),len(g.stairs)*3)
                self.assertFalse(holes&g.surfaces)
                occupied=set()
                for p in g.props:
                    cells=set(Game.footprint(p));self.assertTrue(cells<=g.surfaces)
                    self.assertFalse(cells&occupied);occupied.update(cells)
                self.assertEqual(g.blocked,occupied)
                self.assertFalse({tuple(p) for link in g.stairs for p in link}&g.blocked)
            self.assertGreater(len(layouts),1)
            g=Game(41,'factory',size=n)
            self.assertFalse(g.surfaces-g.blocked-set(g.paths(g.units[0],999,ignore_units=True,ignore_doors=True)))

    def test_every_tile_reachable_across_300_layouts(self):
        for n in (24,30,40):
            for seed in range(100):
                # Exercise the real movement graph without unrelated spawn/fog work.
                g=Game.__new__(Game);g.rng=random.Random(seed);g.size=n;g.theme='factory';g.fires=[]
                generate(g)
                unit=dict(x=n//2-3,y=n-2,z=0,stance='standing')
                reachable=set(g.paths(unit,999,ignore_units=True,ignore_doors=True))
                self.assertEqual(g.surfaces-g.blocked,reachable,(n,seed))

    def test_access_guard_rejects_missing_or_blocked_connections(self):
        g=Game(41,'factory');top=g.stairs.pop()
        with self.assertRaisesRegex(ValueError,'no accessible'):validate_factory_access(g)
        g.stairs.append(top);g.blocked.add(top[1])
        with self.assertRaisesRegex(ValueError,'landing is obstructed'):validate_factory_access(g)

    def test_stair_flights_allow_real_moves_both_ways(self):
        g=Game(41,'factory');u=g.units[0]
        for other in g.units[1:]:other.update(x=0,y=g.size-1,z=0)
        for a,d in g.stairs:
            for start,end in ((a,d),(d,a)):
                u.update(x=start[0],y=start[1],z=start[2],ap=2,stance='standing')
                g.init_fog()
                g.action(dict(action='move',unit=u['id'],x=end[0],y=end[1],z=end[2]))
                self.assertEqual(g.position(u),end)

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
