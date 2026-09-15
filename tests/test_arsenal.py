"""Test arsenal behavior."""

import unittest
from game import Game, WEAPONS
import test_fog


class ArsenalTests(unittest.TestCase):
    """Group automated checks for arsenal behavior."""
    field=test_fog.FogTests.field

    def give(self,u,name):
        """Equip a test unit with the requested item and ammunition."""
        u['inventory'][name]=dict(ammo=WEAPONS[name]['capacity'],reserve=0)
        u.update(weapon=name,ammo=WEAPONS[name]['capacity'],ap=2)

    def test_deployment_validates_all_loadouts_atomically(self):
        """Verify that deployment validates all loadouts atomically."""
        g=Game(41,deployed=False)
        choices={u['id']:dict(primary='M24 sniper',utility1='Smoke grenade',utility2='Demolition charge') for u in g.alive('soldier')}
        with self.assertRaises(ValueError):g.action(dict(action='move',unit='s0',x=1,y=1))
        choices['s3']['utility2']='Smoke grenade'
        with self.assertRaises(ValueError):g.action(dict(action='deploy',loadouts=choices))
        self.assertEqual(g.units[0]['weapon'],'M4A1')
        choices['s3']['utility2']='Demolition charge'
        g.action(dict(action='deploy',loadouts=choices))
        self.assertEqual(g.status,'active')
        self.assertEqual(set(g.units[0]['inventory']),{'M24 sniper','M9','Smoke grenade','Demolition charge'})
        with self.assertRaises(ValueError):g.action(dict(action='deploy',loadouts=choices))

    def test_every_item_is_allowed_in_every_slot(self):
        """Verify that every item is allowed in every slot."""
        slots=['primary','sidearm','utility1','utility2']
        for item in WEAPONS:
            for slot in slots:
                g=Game(41,deployed=False)
                others=[w for w in WEAPONS if w!=item][:3]
                values=dict(zip([s for s in slots if s!=slot],others));values[slot]=item
                choices={u['id']:dict(values) for u in g.alive('soldier')}
                g.deploy(dict(loadouts=choices))
                self.assertEqual(set(g.units[0]['inventory']),set(values.values()))
                self.assertEqual(g.units[0]['weapon'],values['primary'])

    def test_sniper_range_accuracy_and_slow_action(self):
        """Verify that sniper range accuracy and slow action."""
        g=self.field();u=g.units[0];e=g.alive('alien')[0];e.update(x=u['x'],y=u['y']-18,hp=20)
        self.give(u,'M24 sniper');g.refresh_visibility()
        self.assertTrue(g.detected(e));self.assertGreater(g.chance(u,e),75)
        u['ap']=1
        with self.assertRaises(ValueError):g.action(dict(action='shoot',unit=u['id'],target=e['id']))
        u['ap']=2;g.action(dict(action='shoot',unit=u['id'],target=e['id']))
        self.assertEqual(u['ap'],0);self.assertEqual(u['ammo'],4)

    def test_auto_consumes_rounds_and_penalizes_accuracy(self):
        """Verify that auto consumes rounds and penalizes accuracy."""
        g=self.field();u=g.units[0];e=g.alive('alien')[0];e.update(x=u['x'],y=u['y']-4,hp=100)
        chance=g.chance(u,e)
        g.action(dict(action='fire_mode',unit=u['id'],mode='auto'))
        self.assertEqual(g.chance(u,e),chance-20)
        g.action(dict(action='shoot',unit=u['id'],target=e['id']))
        self.assertEqual(u['ammo'],3);self.assertEqual(u['ap'],0)
        self.assertEqual(sum(e['type']=='shot' for e in g.events),3)

    def test_smoke_blocks_both_directions_and_expires(self):
        """Verify that smoke blocks both directions and expires."""
        g=self.field();u=g.units[0];e=g.alive('alien')[0];e.update(x=u['x'],y=u['y']-8)
        self.give(u,'Smoke grenade');self.assertTrue(g.sees(u,e))
        g.action(dict(action='blast',unit=u['id'],x=u['x'],y=u['y']-4,z=0))
        self.assertFalse(g.sees(u,e));self.assertFalse(g.sees(e,u))
        self.assertNotIn(e['id'],[v['id'] for v in g.state()['units']])
        for _ in range(2):g.tick_utilities()
        self.assertTrue(g.smoke)
        g.tick_utilities();self.assertFalse(g.smoke);self.assertTrue(g.sees(u,e))

    def test_demolition_timer_and_collapse_clear_paths(self):
        """Verify that demolition timer and collapse clear paths."""
        g=Game(51,'urban');b=g.buildings[0];x,y=b['x'],b['y'];u=g.units[0]
        u.update(x=x,y=y,z=1);g.init_fog()
        g.charges=[dict(x=x,y=y,z=0,radius=4,turns=2)]
        g.tick_utilities();self.assertFalse(b['destroyed'])
        g.tick_utilities();self.assertTrue(b['destroyed']);self.assertEqual(u['z'],0);self.assertEqual(u['hp'],0)
        self.assertFalse(any(w['building']==b['id'] for w in g.walls.values()))
        self.assertFalse(any(c[2]>0 and (c[0],c[1],0) in g.footprint(b) for c in g.surfaces))
        g.state()

    def test_firepower_and_destroyed_vehicle_path(self):
        """Verify that firepower and destroyed vehicle path."""
        g=self.field();u=g.units[0]
        p=dict(id='testcar',kind='car',x=14,y=25,width=2,depth=2,color='#888888')
        g.props=[p];g.init_structures();g.blocked=set(g.footprint(p));g.geometry_revision+=1;g.init_fog()
        self.assertNotIn((14,25,0),g.paths(u,10))
        g.rng.randint=lambda a,b:1
        g.action(dict(action='structure',unit=u['id'],target=p['id']))
        self.assertEqual(p['hp'],33)
        g.damage_area(14,26,0,2,40)
        self.assertTrue(p['destroyed']);self.assertIn((14,25,0),g.paths(u,10))
        self.assertTrue(g.state()['props'][0]['destroyed'])

    def test_corpses_do_not_block_path_or_movement(self):
        """Verify that corpses do not block path or movement."""
        g=self.field();u=g.units[0];e=g.alive('alien')[0];e.update(x=u['x'],y=u['y']-1,hp=0)
        destination=g.position(e)
        self.assertIn(destination,g.paths(u,2))
        g.action(dict(action='move',unit=u['id'],x=e['x'],y=e['y'],z=0))
        self.assertEqual(g.position(u),destination)

if __name__=='__main__':unittest.main()
