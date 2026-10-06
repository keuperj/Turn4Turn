"""Station hall, track-aligned trains, platforms and safe passenger routes."""
import random
import unittest
from types import SimpleNamespace
from game import Game
from world import generate


class RailwayTests(unittest.TestCase):
    def test_seeded_station_layout(self):
        for n in (24,30,40):
            placements=set()
            for seed in range(12):
                g=SimpleNamespace(rng=random.Random(seed),size=n,theme='train_station');generate(g)
                again=SimpleNamespace(rng=random.Random(seed),size=n,theme='train_station');generate(again)
                self.assertEqual(g.props,again.props);self.assertEqual(g.buildings,again.buildings)
                station=[b for b in g.buildings if b.get('station')]
                self.assertEqual(len(station),1);b=station[0]
                self.assertEqual(b['level'],1);self.assertGreaterEqual(b['width']*b['depth'],60)
                self.assertFalse(any(w['building']==b['id'] and w['side']=='interior' for w in g.walls.values()))
                self.assertEqual({p['side'] for p in g.portals if p['building']==b['id'] and p['kind']=='door'},{'east','west'})
                for side in ('east','west'):
                    doors=[p for p in g.portals if p['building']==b['id'] and p['kind']=='door' and p['side']==side]
                    self.assertEqual(len(doors),2)
                    self.assertEqual({p['door_leaf'] for p in doors},{0,1})
                    self.assertEqual(doors[0]['door_group'],doors[1]['door_group'])
                for building in g.buildings:
                    self.assertTrue({'door','window'}<={p['kind'] for p in g.portals if p['building']==building['id'] and p['side']!='interior'})
                self.assertTrue({'bench','ticket_counter','cafe_table','trash'}<={p['kind'] for p in g.props if p.get('interior')})
                self.assertGreaterEqual(sum(p['kind'].startswith('tree_') for p in g.props),3)
                tracks=g.scenery['tracks'];self.assertEqual(len(tracks),2)
                self.assertEqual(b['x']+b['width'],tracks[0]-4)
                trains=[p for p in g.props if p['kind']=='train']
                self.assertGreaterEqual(len(trains),2)
                placements.add(tuple((p['x'],p['y'],p['variant']) for p in trains))
                self.assertEqual({p['x']+1 for p in trains},set(tracks))
                occupied=set()
                for p in g.props:
                    cells={(x,y,0) for y in range(p['y'],p['y']+p['depth']) for x in range(p['x'],p['x']+p['width'])}
                    self.assertFalse(cells&occupied);occupied.update(cells)
                    self.assertTrue(all(g.tiles[y][x]!='rail_crossing' for x,y,_ in cells))
                    if p['kind']=='train':self.assertTrue(all(g.tiles[y][x]=='railway' for x,y,_ in cells))
                for edge in (tracks[0]-4,tracks[0]+8):
                    kinds={p['kind'] for p in g.props if p['x']==edge}
                    self.assertTrue({'bench','trash','lamp'}<=kinds)
            self.assertGreater(len(placements),8)

    def test_station_and_platforms_remain_reachable(self):
        for n in (24,30,40):
            for seed in (0,7,41):
                g=Game(seed,'train_station',size=n)
                reachable=set(g.paths(g.units[0],999,ignore_units=True,ignore_doors=True))
                self.assertFalse(g.surfaces-g.blocked-reachable,(n,seed))

    def test_double_door_opens_both_leaves_for_one_action(self):
        g=Game(41,'train_station');unit=g.units[0]
        doors=[p for p in g.portals if p.get('door_group')=='b0:east']
        unit.update(x=doors[0]['b'][0],y=doors[0]['b'][1],z=0,ap=3)
        self.assertTrue(all(not g.passable(tuple(p['a']),tuple(p['b'])) for p in doors))
        revision=g.geometry_revision
        g.toggle_portal(unit,doors[0])
        self.assertEqual(unit['ap'],2);self.assertEqual(g.geometry_revision,revision+1)
        self.assertTrue(all(p['open'] and g.passable(tuple(p['a']),tuple(p['b'])) for p in doors))
        g.toggle_portal(unit,doors[1])
        self.assertEqual(unit['ap'],1);self.assertTrue(all(not p['open'] for p in doors))
