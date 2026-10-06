"""Discovered facades show architecture without revealing live hidden portals."""
import unittest
from game import Game


class FacadeTests(unittest.TestCase):
    def test_station_openings_present_in_real_starting_state(self):
        g=Game(41,'train_station');state=g.state()
        station=next(b for b in state['buildings'] if b.get('station'))
        self.assertFalse(any(w['building']==station['id'] and w['kind']=='door' for w in state['walls']))
        openings=station['exterior_openings']
        self.assertEqual(sum(p['kind']=='door' for p in openings),4)
        self.assertTrue(any(p['kind']=='window' for p in openings))
        for b in state['buildings']:
            self.assertTrue({'door','window'}<={p['kind'] for p in b['exterior_openings']})
        self.assertTrue(all(not {'id','open','door_group'}&p.keys() for p in openings))
        door=next(p for p in g.portals if p.get('door_group')=='b0:east')
        door['open']=True;g.geometry_revision+=1
        after=g.state()
        self.assertEqual(next(b for b in after['buildings'] if b['id']==station['id'])['exterior_openings'],openings)
        self.assertNotIn(door['id'],{p['id'] for p in after['portals']})
        self.assertFalse(any(w['building']==station['id'] and w.get('side')=='interior' for w in after['walls']))

    def test_unobserved_facade_changes_do_not_update_remembered_architecture(self):
        g=Game(41,'train_station');before=g.public_world()
        station=next(b for b in before['buildings'] if b.get('station'))
        g.walls={key:w for key,w in g.walls.items() if w['building']!=station['id']}
        after=g.public_world()
        self.assertEqual(next(b for b in after['buildings'] if b['id']==station['id'])['exterior_openings'],station['exterior_openings'])

    def test_observed_door_keeps_actual_state_and_interaction(self):
        g=Game(41,'train_station');door=next(p for p in g.portals if p.get('door_group')=='b0:east')
        for u in g.alive('soldier'):u.update(x=door['b'][0],y=door['b'][1],z=0)
        g.init_fog();state=g.state()
        self.assertIn(door['id'],{p['id'] for p in state['portals']})
        g.toggle_portal(g.units[0],door)
        state=g.state()
        self.assertTrue(next(p for p in state['portals'] if p['id']==door['id'])['open'])
