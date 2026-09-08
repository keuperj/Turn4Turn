import unittest
from game import Game
from world import THEMES


class InteriorTests(unittest.TestCase):
    def at_portal(self, kind='door'):
        g=Game(41,'urban')
        p=next(p for p in g.portals if p['building']=='b0' and p['kind']==kind)
        u=g.units[0]
        u.update(x=p['b'][0],y=p['b'][1],z=p['b'][2])
        for other in g.units[1:]:
            if g.position(other) in (tuple(p['a']),tuple(p['b'])):
                other.update(x=17,y=17,z=0)
        return g,u,p

    def test_door_entry_close_exit(self):
        g,u,p=self.at_portal()
        inside=tuple(p['a'])
        self.assertNotIn(inside,g.paths(u,1))
        g.action(dict(action='interact',unit=u['id'],portal=p['id']))
        self.assertTrue(p['open'])
        self.assertEqual(u['ap'],1)
        g.action(dict(action='move',unit=u['id'],x=inside[0],y=inside[1],z=inside[2]))
        self.assertEqual(g.position(u),inside)
        u['ap']=2
        g.action(dict(action='interact',unit=u['id'],portal=p['id']))
        self.assertFalse(p['open'])
        self.assertNotIn(tuple(p['b']),g.paths(u,1))
        g.action(dict(action='interact',unit=u['id'],portal=p['id']))
        u['ap']=2
        g.action(dict(action='move',unit=u['id'],x=p['b'][0],y=p['b'][1],z=0))
        self.assertEqual(g.position(u),tuple(p['b']))

    def test_remote_and_exhausted_interaction_rejected(self):
        g,u,p=self.at_portal()
        u.update(x=8,y=16,z=0)
        with self.assertRaises(ValueError):
            g.action(dict(action='interact',unit=u['id'],portal=p['id']))
        self.assertFalse(p['open'])
        u.update(x=p['b'][0],y=p['b'][1],ap=0)
        with self.assertRaises(ValueError):
            g.action(dict(action='interact',unit=u['id'],portal=p['id']))

    def test_window_sightline_shutter_sill_and_no_walkthrough(self):
        g,u,p=self.at_portal('window')
        target=dict(u,x=p['a'][0],y=p['a'][1],z=0)
        self.assertFalse(g.line_of_sight(u,target))
        g.action(dict(action='interact',unit=u['id'],portal=p['id']))
        self.assertTrue(g.line_of_sight(u,target))
        self.assertNotIn(tuple(p['a']),g.paths(u,1))
        u['stance']=target['stance']='prone'
        self.assertFalse(g.line_of_sight(u,target))
        u['stance']=target['stance']='standing'
        g.action(dict(action='interact',unit=u['id'],portal=p['id']))
        self.assertFalse(g.line_of_sight(u,target))

    def test_floor_overlap_stairs_and_slab(self):
        g=Game(2,'urban')
        a,b=g.stairs[0]
        u=g.units[0]
        u.update(x=a[0],y=a[1],z=a[2])
        # Same XY on a different floor is an independent movement destination.
        self.assertIn(tuple(b),g.paths(u,1))
        other=dict(u,z=b[2])
        self.assertFalse(g.line_of_sight(u,other))
        g.action(dict(action='move',unit=u['id'],x=b[0],y=b[1],z=b[2]))
        self.assertEqual(g.position(u),tuple(b))
        u['stance']='prone'
        self.assertNotIn(tuple(a),g.paths(u,10))

    def test_closed_door_blocks_grenade_and_blast_damage(self):
        g,u,p=self.at_portal()
        g.action(dict(action='equip',unit=u['id'],weapon='Frag grenade'))
        x,y,z=p['a']
        self.assertFalse(g.blast_valid(u,x,y,z))
        target=g.units[4]
        target.update(x=x,y=y,z=z)
        self.assertNotIn(target,g.blast_victims(u,u['x'],u['y'],0))
        p['open']=True;g.geometry_revision+=1
        self.assertTrue(g.blast_valid(u,x,y,z))
        self.assertIn(target,g.blast_victims(u,u['x'],u['y'],0))

    def test_theme_determinism_and_all_spawns_connected(self):
        for theme in THEMES:
            for seed in range(8):
                g=Game(seed,theme)
                same=Game(seed,theme)
                self.assertEqual(g.tiles,same.tiles)
                self.assertEqual(g.props,same.props)
                paths=g.paths(g.units[0],999,ignore_units=True,ignore_doors=True)
                for u in g.alive():
                    self.assertIn(g.position(u),paths,(theme,seed,u['id']))
                    self.assertNotIn(g.position(u),g.blocked)
                for a,b in g.stairs+g.ladders:
                    self.assertIn(tuple(a),paths)
                    self.assertIn(tuple(b),paths)
                for p in g.blocked:
                    self.assertNotIn(p,paths)
        self.assertIn('train',[p['kind'] for p in Game(1,'train_station').props])
        self.assertIn('aircraft',[p['kind'] for p in Game(1,'airport').props])
        with self.assertRaises(ValueError): Game(2,'not-a-theme')

    def test_civilian_evacuates_without_overwatch_fire(self):
        g=Game(5,'farm')
        c=g.alive('civilian')[0]
        c.update(x=1,y=g.size-2,z=0)
        u=g.units[0]
        u.update(x=2,y=g.size-2,z=0,overwatch=True)
        ammo=u['ammo']
        g.civilian_turn()
        self.assertTrue(c['evacuated'])
        self.assertEqual(u['ammo'],ammo)
        self.assertNotIn(c,g.alive())
        self.assertEqual(g.state()['civilians']['evacuated'],1)

    def test_civilian_is_vulnerable_to_explosives(self):
        g=Game(9,'farm')
        u=g.units[0]
        c=g.alive('civilian')[0]
        u.update(x=5,y=g.size-2,z=0)
        c.update(x=5,y=g.size-4,z=0)
        g.action(dict(action='equip',unit=u['id'],weapon='Frag grenade'))
        g.action(dict(action='blast',unit=u['id'],x=5,y=g.size-4,z=0))
        self.assertEqual(c['hp'],0)
        self.assertEqual(g.state()['civilians']['alive'],4)

    def test_enemy_cannot_spot_squad_through_closed_door(self):
        g,u,p=self.at_portal()
        enemy=g.alive('alien')[0]
        enemy.update(x=p['a'][0],y=p['a'][1],z=0,stance='standing')
        self.assertFalse(g.sees(enemy,u))
        g.action(dict(action='interact',unit=u['id'],portal=p['id']))
        self.assertTrue(g.sees(enemy,u))


if __name__=='__main__': unittest.main()
