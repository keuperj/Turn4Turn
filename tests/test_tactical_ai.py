"""Behavioral checks for team intelligence, coordinated plans and civilian safety."""
import copy
import unittest
from unittest.mock import patch
from game import Game
from scenarios.common import edge_key


class TacticalAITests(unittest.TestCase):
    """Exercise decisions on small controlled maps with actual sight and movement."""

    @classmethod
    def setUpClass(cls):
        """Generate once, then reuse an empty deterministic battlefield."""
        g = Game(42, size=24, mission='eliminate')
        g.tiles = [['grass']*24 for _ in range(24)]
        g.heights = [[0]*24 for _ in range(24)]
        g.surfaces = {(x,y,0) for x in range(24) for y in range(24)}
        g.buildings, g.props, g.portals, g.stairs, g.ladders = [], [], [], [], []
        g.walls, g.blocked = {}, set()
        g.units = []
        g.geometry_revision += 1
        g._los_cache.clear()
        g.init_fog()
        cls.empty = g

    def setUp(self):
        """Isolate random state and memories between tests."""
        self.g = copy.deepcopy(self.empty)

    def unit(self, uid, team, x, y, z=0):
        """Add a fighter or an unarmed civilian."""
        u = self.g.make_unit(uid,uid,team,x,y,'M4A1' if team!='civilian' else None,'test',z)
        self.g.units.append(u)
        return u

    def wall(self, a, b, kind='wall'):
        """Add a sight-blocking edge or a closed door."""
        wall = dict(id='door',a=a,b=b,kind=kind,open=False,building='test')
        self.g.walls[edge_key(a,b)] = wall
        if kind=='door': self.g.portals.append(wall)
        self.g.geometry_revision += 1
        return wall

    def test_team_uses_sighting_from_distant_scout(self):
        g=self.g
        scout=self.unit('e0','alien',10,8)
        remote=self.unit('e1','alien',1,1)
        target=self.unit('s0','soldier',16,12)
        self.assertTrue(g.sees(scout,target))
        self.assertFalse(g.sees(remote,target))
        g.observe_ai()
        plan=g.plan_enemy(remote,{},set())
        self.assertEqual(plan['target'],'s0')
        self.assertEqual(plan['goal'],g.position(target))
        self.assertTrue(plan['route'])
        self.assertEqual(g.chance(remote,target),0,'Radio sightings do not permit blocked shots')

    def test_memory_does_not_follow_hidden_movement_or_death(self):
        g=self.g
        enemy=self.unit('e0','alien',1,1)
        target=self.unit('s0','soldier',10,1)
        g.observe_ai()
        enemy.update(x=1,y=23)
        target.update(x=22,y=1,hp=0)
        g.observe_ai()
        self.assertEqual(g.enemy_contacts['s0']['x'],10)
        self.assertGreater(g.enemy_contacts['s0']['hp'],0)
        g.round+=4;g.observe_ai()
        self.assertFalse(g.enemy_contacts)

    def test_inspecting_empty_contact_clears_it(self):
        g=self.g
        self.unit('e0','alien',1,1)
        target=self.unit('s0','soldier',10,1)
        g.observe_ai()
        target.update(x=23,y=23)
        g.observe_ai()
        self.assertFalse(g.enemy_contacts)

    def test_rescue_search_has_no_unseen_civilian_coordinates(self):
        g=self.g;g.mission='rescue'
        enemy=self.unit('e0','alien',1,1)
        civilian=self.unit('c0','civilian',23,22)
        other=copy.deepcopy(g)
        other.units[-1].update(x=22,y=23)
        g.observe_ai();other.observe_ai()
        self.assertFalse(g.enemy_contacts)
        self.assertEqual(g.plan_enemy(enemy,{},set()),other.plan_enemy(other.units[0],{},set()))

    def test_shared_target_gets_distinct_support_and_flanking_positions(self):
        g=self.g
        enemies=[self.unit('e'+str(i),'alien',9+i*2,4) for i in range(3)]
        self.unit('s0','soldier',11,12)
        g.observe_ai();assigned,reserved={},set()
        plans=[g.plan_enemy(e,assigned,reserved) for e in enemies]
        self.assertEqual([p['role'] for p in plans],['support','flank_left','flank_right'])
        self.assertEqual(len({p['destination'] for p in plans}),3)
        self.assertTrue(any(len(p['route'])>g.speed(e) for p,e in zip(plans,enemies)))

    def test_route_takes_detour_away_from_goal(self):
        g=self.g
        enemy=self.unit('e0','alien',5,5)
        # A U-shaped enclosure, open to the north, requires initially retreating.
        for x in range(3,8):g.blocked.add((x,7,0))
        for y in range(3,7):g.blocked.update({(3,y,0),(7,y,0)})
        enemy['ap']=2
        g.advance_enemy(enemy,(5,10,0))
        self.assertNotEqual(g.position(enemy),(5,5,0))
        self.assertTrue(enemy['x']<3 or enemy['x']>7)
        self.assertGreaterEqual(enemy['ap'],0)

    def test_closed_door_is_opened_before_crossing_with_ap_cost(self):
        g=self.g
        enemy=self.unit('e0','alien',4,4)
        door=self.wall((4,4,0),(5,4,0),'door')
        enemy['ap']=1
        g.follow_enemy_route(enemy,[(5,4,0),(6,4,0)],1)
        self.assertTrue(door['open'])
        self.assertEqual(g.position(enemy),(4,4,0))
        self.assertEqual(enemy['ap'],0)
        enemy['ap']=1
        g.follow_enemy_route(enemy,[(5,4,0),(6,4,0)],1)
        self.assertEqual(g.position(enemy),(6,4,0))
        self.assertEqual(enemy['ap'],0)

    def test_stairs_used_and_prone_cannot_climb(self):
        g=self.g
        enemy=self.unit('e0','alien',4,4)
        g.surfaces.update({(4,4,1),(5,4,1)})
        g.stairs=[((4,4,0),(4,4,1))]
        self.assertIn((5,4,1),g.ai_routes(enemy)[0])
        enemy['stance']='prone'
        self.assertNotIn((5,4,1),g.ai_routes(enemy)[0])

    def test_civilian_memories_are_independent(self):
        g=self.g
        observer=self.unit('c0','civilian',2,2)
        unaware=self.unit('c1','civilian',23,23)
        self.unit('e0','alien',5,2)
        g.observe_ai()
        self.assertIn('e0',g.civilian_contacts[observer['id']])
        self.assertFalse(g.civilian_contacts[unaware['id']])
        other=copy.deepcopy(g)
        other.units[0]['hp']=0
        self.assertEqual(g.plan_civilian(unaware),other.plan_civilian(other.units[1]))

    def test_civilian_waits_in_cover_then_resumes_escape(self):
        g=self.g
        civilian=self.unit('c0','civilian',10,10)
        enemy=self.unit('e0','alien',10,14)
        g.observe_ai()
        # Now hide behind a wall, with only an exposed escape corridor to the east.
        for x in (9,10):self.wall((x,10,0),(x,11,0))
        g.blocked.update({(9,10,0),(10,9,0)})
        plan=g.plan_civilian(civilian)
        self.assertEqual(plan['strategy'],'hide')
        self.assertEqual(plan['route'],[])
        enemy['hp']=0
        g.round+=4
        plan=g.plan_civilian(civilian)
        self.assertEqual(plan['strategy'],'escape')
        self.assertTrue(plan['route'])

    def test_civilian_routes_around_obstacle_instead_of_maximizing_y(self):
        g=self.g
        civilian=self.unit('c0','civilian',10,10)
        for x in range(8,13):g.blocked.add((x,12,0))
        for y in range(8,12):g.blocked.update({(8,y,0),(12,y,0)})
        plan=g.plan_civilian(civilian)
        self.assertTrue(plan['route'])
        self.assertLess(plan['route'][-1][1],10)
        self.assertEqual(len(plan['future']),3)

    def test_civilian_cannot_open_doors_and_evacuates_only_at_ground_edge(self):
        g=self.g
        civilian=self.unit('c0','civilian',10,22)
        self.wall((10,22,0),(10,23,0),'door')
        plan=g.plan_civilian(civilian)
        self.assertNotEqual(plan['route'],[(10,23,0)])
        civilian.update(y=23,z=1)
        g.surfaces.add((10,23,1))
        g.civilian_turn()
        self.assertFalse(civilian['evacuated'])
        civilian['z']=0
        g.civilian_turn()
        self.assertTrue(civilian['evacuated'])

    def test_plans_are_private_and_seeded(self):
        g=self.g
        enemy=self.unit('e0','alien',10,10)
        self.unit('s0','soldier',10,15)
        civilian=self.unit('c0','civilian',12,15)
        g.observe_ai()
        twin=copy.deepcopy(g)
        self.assertEqual(g.plan_enemy(enemy,{},set()),twin.plan_enemy(twin.units[0],{},set()))
        g.plan_civilian(civilian)
        public=g.state()
        self.assertNotIn('enemy_contacts',public)
        self.assertNotIn('civilian_plans',public)
        for unit in public['units']:
            self.assertNotIn('route',unit)
            self.assertNotIn('goal',unit)

    def test_enemy_reacts_to_contact_seen_during_movement(self):
        g=self.g
        scout=self.unit('e0','alien',2,2)
        target=self.unit('s0','soldier',18,2)
        g.observe_ai();self.assertFalse(g.enemy_contacts)
        g.move(scout,[(3,2,0),(4,2,0)])
        self.assertIn(target['id'],g.enemy_contacts)

    def test_enemy_plan_commits_to_long_detour(self):
        g=self.g;g.enemy_time=1
        enemy=self.unit('e0','alien',10,10)
        g.mission='defend_flag';g.flag=dict(x=10,y=15,z=0)
        for x in range(8,13):g.blocked.add((x,12,0))
        for y in range(2,12):g.blocked.update({(8,y,0),(12,y,0)})
        plan=g.plan_enemy(enemy,{},set())
        self.assertTrue(plan['route'])
        self.assertLess(min(p[1] for p in plan['route']),10)
        self.assertGreater(len(plan['route']),g.speed(enemy))

    def test_fire_and_occupied_tiles_are_not_crossed(self):
        g=self.g
        enemy=self.unit('e0','alien',4,4)
        self.unit('e1','alien',5,4)
        g.fires=[dict(x=4,y=5,z=0,turns=2)]
        costs,_=g.ai_routes(enemy)
        self.assertNotIn((5,4,0),costs)
        self.assertNotIn((4,5,0),costs)
        g.follow_enemy_route(enemy,[(5,4,0)],2)
        self.assertEqual(g.position(enemy),(4,4,0))

    def test_reaction_death_stops_planned_route(self):
        g=self.g
        enemy=self.unit('e0','alien',5,5)
        soldier=self.unit('s0','soldier',5,10)
        soldier['overwatch']=True;enemy['hp']=1
        with patch.object(g.rng,'randint',return_value=1):
            g.follow_enemy_route(enemy,[(5,6,0),(5,7,0),(5,8,0)],2)
        self.assertEqual(enemy['hp'],0)
        self.assertEqual(g.position(enemy),(5,6,0))
        self.assertGreaterEqual(enemy['ap'],0)

    def test_complete_phases_are_reproducible(self):
        g=self.g;g.mission='rescue'
        self.unit('e0','alien',4,4)
        self.unit('e1','alien',12,4)
        self.unit('s0','soldier',8,20)
        self.unit('c0','civilian',16,16)
        twin=copy.deepcopy(g)
        for _ in range(3):
            if g.status!='active':break
            g.enemy_turn();twin.enemy_turn()
            self.assertEqual(g.units,twin.units)
            self.assertEqual(g.enemy_plans,twin.enemy_plans)
            self.assertEqual(g.civilian_plans,twin.civilian_plans)
            self.assertTrue(all(u['ap']>=0 for u in g.units))

    def test_rescue_enemies_can_fight_soldiers(self):
        g=self.g;g.mission='rescue'
        enemy=self.unit('e0','alien',10,10)
        soldier=self.unit('s0','soldier',10,14)
        with patch.object(g,'fire') as fire:
            g.coordinated_enemy_turn()
        fire.assert_called_once_with(enemy,soldier)


if __name__=='__main__':unittest.main()
