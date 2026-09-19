"""Test fog behavior."""

import json
import unittest
from game import Game
from visibility import SIGHT
from world import THEMES, PROP_SIZE


class FogTests(unittest.TestCase):
    """Group automated checks for fog behavior."""
    def field(self):
        """Build a deterministic battlefield fixture for this scenario."""
        g=Game(41,'urban')
        g.tiles=[['grass']*g.size for _ in range(g.size)]
        g.heights=[[0]*g.size for _ in range(g.size)]
        g.surfaces={(x,y,0) for x in range(g.size) for y in range(g.size)}
        g.walls={};g.buildings=[];g.props=[];g.blocked=set();g.portals=[];g.stairs=[];g.ladders=[]
        for i,u in enumerate(g.alive('soldier')):u.update(x=14+i,y=28,z=0)
        for i,u in enumerate(g.alive('alien')):u.update(x=2+i,y=2,z=0,stance='standing')
        g.geometry_revision+=1;g._los_cache.clear();g.init_fog()
        return g

    def test_hidden_units_absent_from_payload_shots_and_events(self):
        """Verify that hidden units absent from payload shots and events."""
        g=self.field();enemy=g.alive('alien')[0];s=g.state()
        self.assertNotIn(enemy['id'],[u['id'] for u in s['units']])
        self.assertNotIn(enemy['id'],s['shots']['s0'])
        g.move(enemy,[(3,2,0)])
        self.assertFalse(any(e.get('unit')==enemy['id'] for e in g.events))
        ammo=g.units[0]['ammo']
        with self.assertRaises(ValueError):g.action(dict(action='shoot',unit='s0',target=enemy['id']))
        self.assertEqual(g.units[0]['ammo'],ammo)

    def test_stances_reduce_both_seeing_and_being_seen(self):
        """Verify that stances reduce both seeing and being seen."""
        g=self.field();a=g.units[0];b=g.alive('alien')[0]
        b.update(x=a['x'],y=a['y']-12)
        self.assertTrue(g.sees(a,b))
        a['stance']='kneeling';self.assertFalse(g.sees(a,b))
        a['stance']='standing';b['stance']='kneeling';self.assertFalse(g.sees(a,b))
        b.update(y=a['y']-8,stance='prone');self.assertFalse(g.sees(a,b))
        b['y']=a['y']-6;self.assertTrue(g.sees(a,b))
        a['stance']='prone';self.assertFalse(g.sees(a,b))
        self.assertEqual(SIGHT['prone'],7)

    def test_exploration_remembered_but_live_enemy_not_remembered(self):
        """Verify that exploration remembered but live enemy not remembered."""
        g=self.field();a=g.units[0];b=g.alive('alien')[0]
        b.update(x=14,y=22)
        first=g.state();self.assertIn(b['id'],[u['id'] for u in first['units']])
        for u in g.alive('soldier'):u.update(x=u['x']-10,y=28,stance='prone')
        second=g.state()
        self.assertNotIn(b['id'],[u['id'] for u in second['units']])
        self.assertIn((14,22,0),g.explored)
        self.assertNotIn((14,22,0),g.visible)
        self.assertEqual(second['tiles'][0][0],'unknown')

    def test_unseen_impact_does_not_include_shooter_origin(self):
        """Verify that unseen impact does not include shooter origin."""
        g=self.field();enemy=g.alive('alien')[0];target=g.units[0]
        # Direct fire() isolates public event redaction from normal shot validation.
        g.fire(enemy,target)
        event=g.events[-1]
        self.assertEqual(event['type'],'impact')
        self.assertIsNone(event['origin'])
        self.assertIsNone(event['unit'])
        self.assertNotIn(enemy['name'],g.log[-1])

    def test_blast_preview_hides_concealed_enemy(self):
        """Verify that blast preview hides concealed enemy."""
        g=self.field();u=g.units[0];e=g.alive('alien')[0]
        e.update(x=14,y=19,stance='prone')
        g.action(dict(action='equip',unit=u['id'],weapon='RPG-7'))
        state=g.state()
        self.assertFalse(g.detected(e))
        self.assertNotIn(e['id'],json.dumps(state['blast_targets']))

    def test_ladder_reveals_previously_unseen_roof(self):
        """Verify that ladder reveals previously unseen roof."""
        g=Game(51,'urban');a,b=g.ladders[0];u=g.units[0]
        u.update(x=a[0],y=a[1],z=a[2]);g.init_fog()
        self.assertTrue(g.state()['transitions'][u['id']])
        g.action(dict(action='move',unit=u['id'],x=b[0],y=b[1],z=b[2]))
        self.assertIn(tuple(b),g.visible)

    def test_map_size_scale_variation_and_connectivity(self):
        """Verify that map size scale variation and connectivity."""
        signatures=set()
        for theme in THEMES:
            for seed in range(3):
                g=Game(seed,theme)
                self.assertEqual(g.size,30)
                self.assertGreaterEqual(len(g.buildings),4)
                # The factory uses a constrained hall/mezzanine plan, tested over more seeds separately.
                if theme!='factory':signatures.add(tuple((b['x'],b['y'],b['width'],b['depth']) for b in g.buildings))
                walk=g.paths(g.units[0],999,True,True)
                for u in g.alive():self.assertIn(g.position(u),walk)
                for p in g.props:
                    footprint=PROP_SIZE[p['kind']]
                    if p.get('quarter_turn',0)%2:footprint=footprint[::-1]
                    if theme=='airport' and p['kind']=='aircraft':
                        self.assertTrue(0<p['width']<=footprint[0] and 0<p['depth']<=footprint[1])
                    else:self.assertEqual((p['width'],p['depth']),footprint)
                    if p.get('interior'):
                        building=next(b for b in g.buildings if b['id']==p['interior'])
                        self.assertTrue(building.get('station') or building.get('airport_role')=='terminal' or building.get('factory'))
                        self.assertIn(p['kind'],('bench','ticket_counter','cafe_table','trash','factory_machine','factory_robot','factory_conveyor','factory_rack','factory_forklift'))
                        self.assertTrue(all(g.building_at(x,y,p.get('z',0))==building for y in range(p['y'],p['y']+p['depth']) for x in range(p['x'],p['x']+p['width'])))
                    else:
                        self.assertFalse(any(g.heights[y][x] for y in range(p['y'],p['y']+p['depth']) for x in range(p['x'],p['x']+p['width'])))
        self.assertEqual(len(signatures),3*(len(THEMES)-1))
        self.assertGreaterEqual(PROP_SIZE['aircraft'][0],10)
        self.assertGreaterEqual(PROP_SIZE['car'][1],5)


if __name__=='__main__':unittest.main()
