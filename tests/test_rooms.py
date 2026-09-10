import unittest
from collections import deque
from game import Game
from world import THEMES, edge_key
import test_fog


class RoomTests(unittest.TestCase):
    def test_smoke_allows_preview_and_movement_but_still_hides_enemies(self):
        g=test_fog.FogTests().field();u=g.units[0];enemy=g.alive('alien')[0]
        enemy.update(x=14,y=23,z=0,stance='standing')
        g.refresh_visibility();self.assertTrue(g.detected(enemy))
        self.assertIn((14,25,0),g.explored)
        g.smoke=[dict(x=14,y=26,z=0,radius=3,turns=3)];g.geometry_revision+=1;g.refresh_visibility()
        self.assertNotIn((14,25,0),g.visible);self.assertFalse(g.detected(enemy))
        self.assertTrue(any((p['x'],p['y'],p['z'])==(14,25,0) for p in g.state()['movement'][u['id']]))
        order=dict(action='move',unit=u['id'],x=14,y=25,z=0)
        preview=g.preview(order);self.assertEqual(preview['cost'],1)
        g.action(order);self.assertEqual(g.position(u),(14,25,0))
        self.assertFalse(g.detected(enemy))
        # Blind movement does not authorize shooting through the obscurant.
        with self.assertRaises(ValueError):g.preview(dict(action='attack',unit=u['id'],x=14,y=23,z=0))

    def test_rooms_connected_by_operable_internal_doors_all_themes(self):
        for theme in THEMES:
            g=Game(41,theme)
            for b in g.buildings:
                for z in range(b['level']):
                    cells={(x,y,z) for x in range(b['x'],b['x']+b['width']) for y in range(b['y'],b['y']+b['depth'])}
                    def region(open_doors):
                        start=min(cells);seen={start};queue=deque([start])
                        while queue:
                            x,y,z=queue.popleft()
                            for q in [(x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z)]:
                                if q in cells and q not in seen and g.passable((x,y,z),q,open_doors):seen.add(q);queue.append(q)
                        return seen
                    self.assertLess(len(region(False)),len(cells),(theme,b['id'],z))
                    self.assertEqual(region(True),cells,(theme,b['id'],z))
            self.assertGreaterEqual(sum(bool(g.building_at(*g.position(u))) for u in g.alive('alien')),2,theme)
            if theme not in ('farm','woods'):
                self.assertTrue(any(u['z']>0 and g.building_at(*g.position(u)) for u in g.alive('alien')),theme)

    def test_internal_door_blocks_sight_and_path_until_opened(self):
        g=Game(41,'urban');p=next(p for p in g.portals if p['side']=='interior' and p['a'][2]==0)
        u=g.units[0];u.update(x=p['a'][0],y=p['a'][1],z=0)
        for other in g.units[1:]:
            if g.position(other) in (tuple(p['a']),tuple(p['b'])):other['hp']=0
        target=dict(u,x=p['b'][0],y=p['b'][1],z=0)
        self.assertFalse(g.line_of_sight(u,target));self.assertNotIn(tuple(p['b']),g.paths(u,1))
        g.action(dict(action='interact',unit=u['id'],portal=p['id']))
        self.assertTrue(g.line_of_sight(u,target));self.assertIn(tuple(p['b']),g.paths(u,1))
        g.action(dict(action='move',unit=u['id'],x=target['x'],y=target['y'],z=0))
        self.assertEqual(g.position(u),tuple(p['b']))

    def test_upper_windows_observed_from_ground_without_revealing_rooms(self):
        g=Game(41,'urban');b=g.buildings[0]
        for u in g.alive('soldier'):u.update(x=b['x']-3 if b['x']>=3 else b['x']+b['width']+3,y=b['y']+1,z=0,stance='standing')
        g.init_fog();state=g.state()
        upper=[w for w in state['walls'] if w['kind']=='window' and w['a'][2]>0]
        self.assertTrue(upper)
        self.assertTrue(all(not w['open'] for w in upper))
        self.assertFalse(any(w['side']=='interior' for w in state['walls']))
        self.assertFalse(any(g.building_at(*tuple(v)) for v in state['fog']['visible']))

    def test_inside_and_outside_ladders_exist_and_connect(self):
        g=Game(41,'urban');inside=[];outside=[]
        for a,b in g.ladders:
            (inside if a[:2]==b[:2] else outside).append((a,b))
        self.assertTrue(inside);self.assertTrue(outside)
        for a,b in [inside[0],outside[0]]:
            u=g.units[0];u.update(x=a[0],y=a[1],z=a[2],ap=2)
            for other in g.units[1:]:
                if g.position(other)==tuple(b):other['hp']=0
            g.init_fog();g.action(dict(action='move',unit=u['id'],x=b[0],y=b[1],z=b[2]))
            self.assertEqual(g.position(u),tuple(b))
