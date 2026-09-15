"""Test fieldcraft behavior."""

import copy
import math
import unittest
import test_fog
from game import Game, WEAPONS
from world import edge_key


class FieldcraftTests(unittest.TestCase):
    """Group automated checks for fieldcraft behavior."""
    field=test_fog.FogTests.field

    def give(self,u,name):
        """Equip a test unit with the requested item and ammunition."""
        u['inventory'][name]=dict(ammo=WEAPONS[name]['capacity'],reserve=0)
        u.update(weapon=name,ammo=WEAPONS[name]['capacity'],ap=2)

    def corner(self):
        """Build a deterministic corner-cover fixture for fieldcraft tests."""
        g=self.field();u=g.units[0];u.update(x=9,y=10,z=0)
        for s in g.alive('soldier')[1:]:s.update(x=2,y=28,z=0)
        b=dict(id='b',x=10,y=10,width=3,depth=4,level=1,name='TEST')
        g.buildings=[b];g.init_structures()
        for y in range(10,14):
            a,c=(9,y,0),(10,y,0)
            g.walls[edge_key(a,c)]=dict(a=a,b=c,building='b',kind='wall',open=False)
        e=g.alive('alien')[0];e.update(x=12,y=9,z=0,stance='standing')
        g.geometry_revision+=1;g.init_fog()
        return g,u,e

    def test_medikit_heals_teammate_with_cost_and_cap(self):
        """Verify that medikit heals teammate with cost and cap."""
        g=self.field();u=g.units[0];t=g.units[1];t['hp']=2;self.give(u,'Medikit')
        data=dict(action='heal',unit=u['id'],target=t['id'])
        preview=g.preview(data);self.assertEqual(preview['heal'],6);self.assertEqual(t['hp'],2)
        g.action(data);self.assertEqual(t['hp'],8);self.assertEqual(u['ap'],1);self.assertEqual(u['ammo'],1)
        g.action(data);self.assertEqual(t['hp'],10);self.assertEqual(u['ammo'],0)

    def test_medikit_rejects_full_dead_distant_self_and_blocked(self):
        """Verify that medikit rejects full dead distant self and blocked."""
        g=self.field();u=g.units[0];t=g.units[1];self.give(u,'Medikit')
        for hp,x,uid in [(10,t['x'],t['id']),(0,t['x'],t['id']),(2,20,t['id']),(2,t['x'],u['id'])]:
            t.update(hp=hp,x=x)
            with self.assertRaises(ValueError):g.action(dict(action='heal',unit=u['id'],target=uid))
        t.update(hp=2,x=u['x']+1)
        g.walls[edge_key(g.position(u),g.position(t))]=dict(a=g.position(u),b=g.position(t),kind='window',open=True,building='unused')
        with self.assertRaises(ValueError):g.heal_solution(u,dict(target=t['id']))
        self.assertEqual(u['ap'],2);self.assertEqual(u['ammo'],2)
        with self.assertRaises(ValueError):g.attack_solution(u,dict(x=u['x'],y=u['y']-1,z=0))

    def test_shotgun_power_and_short_range(self):
        """Verify that shotgun power and short range."""
        g=self.field();u=g.units[0];e=g.alive('alien')[0];self.give(u,'Shotgun');e.update(x=u['x'],y=u['y']-3,hp=20)
        g.rng.randint=lambda a,b:1
        g.action(dict(action='attack',unit=u['id'],x=e['x'],y=e['y'],z=0));self.assertEqual(e['hp'],20-WEAPONS['Shotgun']['damage'])
        u['ap']=2;e['y']=u['y']-6
        self.assertEqual(g.chance(u,e),0)
        with self.assertRaises(ValueError):g.preview(dict(action='attack',unit=u['id'],x=e['x'],y=e['y'],z=0))

    def test_facing_is_free_without_ap_and_persists(self):
        """Verify that facing is free without ap and persists."""
        g=self.field();u=g.units[0];u['ap']=0;before=copy.deepcopy(u['inventory'])
        g.action(dict(action='face',unit=u['id'],x=u['x']+1,y=u['y']))
        self.assertAlmostEqual(u['facing'],-math.pi/2);self.assertEqual(u['ap'],0);self.assertEqual(u['inventory'],before)
        self.assertEqual(g.state()['units'][0]['facing'],u['facing'])
        with self.assertRaises(ValueError):g.action(dict(action='face',unit=u['id'],x=True,y=0))

    def test_peek_temporarily_exposes_then_retreats_and_records_contacts(self):
        """Verify that peek temporarily exposes then retreats and records contacts."""
        g,u,e=self.corner()
        # Point hidden by the west wall, but visible from just beyond its north edge.
        e.update(x=11,y=10);g.init_fog()
        self.assertFalse(g.detected(e));self.assertIn(dict(x=9,y=9,z=0),g.corner_options(u))
        ammo=e['ammo'];g.rng.randint=lambda a,b:11
        g.action(dict(action='peek',unit=u['id'],x=9,y=9,z=0))
        self.assertEqual(g.position(u),(9,10,0));self.assertEqual(u['ap'],1);self.assertEqual(u['hp'],10)
        self.assertLess(e['ammo'],ammo)
        self.assertTrue(any(ev['type']=='peek_out' and any(c['id']==e['id'] for c in ev['contacts']) for ev in g.events))
        self.assertFalse(g.detected(e));self.assertTrue(any(m['id']==e['id'] for m in g.state()['last_seen']))

    def test_peek_hit_can_kill_but_always_restores_cover_position(self):
        """Verify that peek hit can kill but always restores cover position."""
        g,u,e=self.corner();e.update(x=11,y=10);u['hp']=1;g.rng.randint=lambda a,b:1
        g.action(dict(action='peek',unit=u['id'],x=9,y=9,z=0))
        self.assertEqual(u['hp'],0);self.assertEqual(g.position(u),(9,10,0))
        self.assertEqual(g.events[-1]['type'],'peek_return')

    def test_grenade_arc_does_not_require_corner_path(self):
        """Verify that grenade arc does not require corner path."""
        g,u,e=self.corner();point=dict(x=11,y=10,z=0,stance='standing');self.give(u,'Frag grenade')
        g.explored.add((11,10,0))
        self.assertFalse(g.line_of_sight(u,point));self.assertIsNotNone(g.corner_throw(u,point))
        result=g.preview(dict(action='attack',unit=u['id'],x=11,y=10,z=0));self.assertIsNone(result['via'])
        g.action(dict(action='attack',unit=u['id'],x=11,y=10,z=0));self.assertEqual(u['ammo'],1)
        u.update(y=11,ap=2)
        self.assertIsNone(g.corner_throw(u,point))
        u.update(y=10,stance='prone');self.assertEqual(g.corner_options(u),[])

    def test_memory_does_not_track_hidden_movement_health_or_death(self):
        """Verify that memory does not track hidden movement health or death."""
        g=self.field();e=g.alive('alien')[0];e.update(x=14,y=22);g.state()
        for s in g.alive('soldier'):s.update(x=2,y=28,stance='prone')
        e.update(x=25,y=5,hp=0)
        memory=g.state()['last_seen'];self.assertEqual(len(memory),1);self.assertEqual((memory[0]['x'],memory[0]['y']),(14,22))
        self.assertNotIn('hp',memory[0]);self.assertNotIn('inventory',memory[0])
        g.units[0].update(x=14,y=23,stance='standing');self.assertEqual(g.state()['last_seen'],[])

    def test_reacquiring_contact_removes_gray_marker(self):
        """Verify that reacquiring contact removes gray marker."""
        g=self.field();e=g.alive('alien')[0];e.update(x=14,y=22);g.state()
        e.update(x=2,y=2);self.assertTrue(g.state()['last_seen'])
        e.update(x=14,y=21);self.assertFalse(any(m['id']==e['id'] for m in g.state()['last_seen']))

if __name__=='__main__':unittest.main()
