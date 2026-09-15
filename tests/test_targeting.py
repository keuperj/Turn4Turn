"""Test targeting behavior."""

import json
import unittest
import test_fog
from game import Game, WEAPONS
from world import THEMES, edge_key


class TargetingTests(unittest.TestCase):
    """Group automated checks for targeting behavior."""
    field=test_fog.FogTests.field

    def give(self,u,name):
        """Equip a test unit with the requested item and ammunition."""
        u['inventory'][name]=dict(ammo=WEAPONS[name]['capacity'],reserve=0)
        u.update(weapon=name,ammo=WEAPONS[name]['capacity'],ap=2)

    def test_empty_ground_preview_does_not_spend_then_attack_spends(self):
        """Verify that empty ground preview does not spend then attack spends."""
        g=self.field();u=g.units[0];data=dict(action='attack',unit=u['id'],x=u['x']-2,y=u['y']-2,z=0)
        before=(u['ammo'],u['ap'],list(g.events))
        preview=g.preview(data)
        self.assertEqual(preview['name'],'Ground point')
        self.assertEqual(before,(u['ammo'],u['ap'],g.events))
        g.action(data);self.assertEqual(u['ammo'],before[0]-1);self.assertEqual(u['ap'],0)

    def test_every_weapon_accepts_visible_ground(self):
        """Verify that every weapon accepts visible ground."""
        for name in WEAPONS:
            if WEAPONS[name]['kind']=='medical':continue
            g=self.field();u=g.units[0];self.give(u,name)
            data=dict(action='attack',unit=u['id'],x=u['x']-1,y=u['y'],z=0)
            g.preview(data);g.action(data)
            self.assertEqual(u['ammo'],WEAPONS[name]['capacity']-1,name)

    def test_wall_smoke_range_and_invalid_points_rejected_without_cost(self):
        """Verify that wall smoke range and invalid points rejected without cost."""
        g=self.field();u=g.units[0];data=dict(action='attack',unit=u['id'],x=u['x'],y=u['y']-5,z=0)
        g.smoke=[dict(x=u['x'],y=u['y']-2,z=0,radius=1,turns=3)];g.geometry_revision+=1
        with self.assertRaises(ValueError):g.action(data)
        self.assertEqual(u['ammo'],6)
        g.smoke=[];g.geometry_revision+=1
        for updates in [dict(x=-1),dict(x=True),dict(y=0),dict(z=9)]:
            with self.assertRaises(ValueError):g.preview(dict(data,**updates))
        self.assertEqual(u['ap'],2)

    def test_grenade_can_arc_over_blocking_wall_to_explored_ground(self):
        """Verify that grenade can arc over blocking wall to explored ground."""
        g=self.field();u=g.units[0];self.give(u,'Frag grenade')
        target=(u['x'],u['y']-2,0)
        edge=edge_key((u['x'],u['y']-1,0),target)
        g.buildings.append(dict(id='barrier',x=0,y=0,width=1,depth=1,level=0))
        g.walls[edge]=dict(a=(u['x'],u['y']-1,0),b=target,building='barrier',kind='wall',open=False)
        g.geometry_revision+=1;g._los_cache.clear();g.explored.add(target)
        self.assertFalse(g.line_of_sight(u,dict(x=target[0],y=target[1],z=0,stance='standing')))
        self.assertTrue(g.blast_valid(u,*target))
        preview=g.preview(dict(action='attack',unit=u['id'],x=target[0],y=target[1],z=0))
        self.assertEqual(preview['name'],'Ground point')
        self.assertIsNone(preview['via'])

    def test_structure_surface_target_and_blocking_wall(self):
        """Verify that structure surface target and blocking wall."""
        g=self.field();u=g.units[0]
        b=dict(id='front',name='BUILDING',x=12,y=23,width=4,depth=3,level=1)
        g.buildings=[b];g.init_structures()
        for x in range(12,16):
            wall=dict(a=(x,25,0),b=(x,26,0),building='front',kind='wall',open=False,id='wall')
            g.walls[edge_key(wall['a'],wall['b'])]=wall
        g.geometry_revision+=1;g.init_fog()
        data=dict(action='attack',unit=u['id'],x=14,y=25,z=0,structure='front')
        self.assertEqual(g.preview(data)['hp'],140)
        g.rng.randint=lambda a,b:1;g.action(data);self.assertEqual(b['hp'],138)
        u['ap']=2
        with self.assertRaises(ValueError):g.preview(dict(data,y=23))
        # An intervening wall belonging to a different structure cannot be bypassed.
        g.walls[edge_key((14,27,0),(14,28,0))]=dict(a=(14,27,0),b=(14,28,0),building='other',kind='wall',open=False)
        with self.assertRaises(ValueError):g.attack_solution(u,data)

    def test_friendly_target_warns_and_can_take_damage(self):
        """Verify that friendly target warns and can take damage."""
        g=self.field();u=g.units[0];friend=g.units[1]
        data=dict(action='attack',unit=u['id'],x=friend['x'],y=friend['y'],z=0)
        self.assertTrue(g.preview(data)['friendly']);g.rng.randint=lambda a,b:1
        g.action(data);self.assertLess(friend['hp'],friend['max_hp'])

    def test_hidden_unit_does_not_leak_through_preview(self):
        """Verify that hidden unit does not leak through preview."""
        g=self.field();u=g.units[0];enemy=g.alive('alien')[0];enemy.update(x=u['x'],y=u['y']-9,stance='prone')
        self.give(u,'M110')
        # Squad sees the standing-height tile, but cannot detect the prone unit.
        for s in g.alive('soldier')[1:]:s.update(x=u['x'],y=u['y'],stance='prone')
        g.init_fog();data=dict(action='attack',unit=u['id'],x=enemy['x'],y=enemy['y'],z=0)
        preview=g.preview(data)
        self.assertEqual(preview['name'],'Ground point');self.assertIsNone(preview['hp'])
        self.assertNotIn(enemy['id'],json.dumps(preview))

    def test_move_preview_has_path_and_does_not_move(self):
        """Verify that move preview has path and does not move."""
        g=self.field();u=g.units[0];old=g.position(u)
        preview=g.preview(dict(action='move',unit=u['id'],x=u['x'],y=u['y']-2,z=0))
        self.assertEqual(len(preview['path']),2);self.assertEqual(g.position(u),old)

    def test_sizes_generate_all_themes_and_keep_spawns_reachable(self):
        """Verify that sizes generate all themes and keep spawns reachable."""
        for size in (24,40):
            for theme in THEMES:
                g=Game(83,theme,size=size)
                self.assertEqual(len(g.tiles),size);self.assertGreaterEqual(len(g.buildings),2)
                reachable=g.paths(g.units[0],999,True,True)
                for u in g.alive():self.assertIn(g.position(u),reachable,(size,theme,u['id']))
                if theme=='airport':self.assertTrue(any(p['kind']=='aircraft' for p in g.props))
        for invalid in [True,0,25,100,'40']:
            with self.assertRaises(ValueError):Game(size=invalid)

if __name__=='__main__':unittest.main()
