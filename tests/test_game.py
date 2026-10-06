"""Test game behavior."""

import math
import unittest
from game import Game, WEAPONS


class CombatTests(unittest.TestCase):
    """Group automated checks for combat behavior."""
    def clear(self):
        """Replace generated terrain with a controlled open test map."""
        g=Game(42)
        g.size=18
        g.tiles=[['grass']*18 for _ in range(18)]
        g.heights=[[0]*18 for _ in range(18)]
        g.buildings,g.ladders,g.stairs,g.portals,g.props=[],[],[],[],[]
        g.walls,g.blocked={},set()
        g.surfaces={(x,y,0) for x in range(18) for y in range(18)}
        for i,u in enumerate(g.alive('soldier')):u.update(x=5+i*2,y=16,z=0)
        for i,u in enumerate(g.alive('alien')):u.update(x=3+i,y=2,z=0,stance='standing')
        for i,u in enumerate(g.alive('civilian')):u.update(x=17,y=i*2+1,z=0)
        g.geometry_revision+=1;g._los_cache.clear();g.init_fog()
        return g

    def test_seed_reproducible(self):
        """Verify that seed reproducible."""
        self.assertEqual(Game(72).state(), Game(72).state())

    def test_move_and_action_budget(self):
        """Verify that move and action budget."""
        g = self.clear()
        g.action(dict(action='move', unit='s0', x=5, y=11))
        self.assertEqual(g.units[0]['ap'], 1)
        with self.assertRaises(ValueError):
            g.action(dict(action='move', unit='s0', x=5, y=0))
        self.assertEqual(g.units[0]['y'], 11)

    def test_cover_and_obstruction(self):
        """Verify that cover and obstruction."""
        g = self.clear()
        a, b = g.units[0], g.units[4]
        a.update(x=3, y=8)
        b.update(x=3, y=2)
        baseline = g.chance(a, b)
        g.tiles[3][3] = 'low';g._los_cache.clear()
        self.assertEqual(g.chance(a, b), baseline-20)
        g.tiles[5][3] = 'high';g._los_cache.clear()
        self.assertEqual(g.chance(a, b), 0)

    def test_shoot_reload_and_turn(self):
        """Verify that shoot reload and turn."""
        g = self.clear()
        g.units[4].update(x=5, y=10)
        g.action(dict(action='shoot', unit='s0', target='e0'))
        self.assertEqual(g.units[0]['ap'], 0)
        self.assertEqual(g.units[0]['ammo'], 5)
        with self.assertRaises(ValueError):
            g.action(dict(action='reload', unit='s0'))
        g.units[0]['hp']=100;g.mission='eliminate'
        g.action(dict(action='end_turn'))
        self.assertEqual(g.round, 2)
        g.action(dict(action='reload', unit='s0'))
        self.assertEqual(g.units[0]['ammo'], 6)
        self.assertEqual(g.units[0]['ap'], 1)

    def test_overwatch_triggers_once(self):
        """Verify that overwatch triggers once."""
        g = self.clear()
        g.units[4].update(x=5, y=10)
        g.action(dict(action='overwatch', unit='s0'))
        g.move(g.units[4], [(5,9,0),(5,8,0)])
        self.assertFalse(g.units[0]['overwatch'])
        self.assertEqual(g.units[0]['ammo'], 5)

    def test_victory_and_reject_post_game_action(self):
        """Verify that victory and reject post game action."""
        g = self.clear()
        for u in g.alive('alien'):
            u['hp'] = 0
        g.check_end()
        self.assertEqual(g.status, 'victory')
        with self.assertRaises(ValueError):
            g.action(dict(action='end_turn'))

    def test_mission_rosters_and_elimination_victory(self):
        """Verify that mission rosters and elimination victory."""
        for mission in ('eliminate','capture_flag','defend_flag'):
            g=Game(42,mission=mission)
            self.assertFalse(any(u['team']=='civilian' for u in g.units))
        g=Game(42,mission='eliminate')
        for u in g.alive('alien'):u['hp']=0
        g.check_end()
        self.assertEqual(g.status,'victory')

    def test_rescue_victory_and_civilian_loss(self):
        """Verify that rescue victory and civilian loss."""
        g=Game(42,mission='rescue')
        for u in g.alive('civilian'):u['evacuated']=True
        g.check_end()
        self.assertEqual(g.status,'victory')
        g=Game(42,mission='rescue')
        g.alive('civilian')[0]['hp']=0
        g.check_end()
        self.assertEqual(g.status,'defeat')

    def test_capture_and_defend_flag_conditions(self):
        """Verify that capture and defend flag conditions."""
        capture=Game(42,mission='capture_flag')
        capture.units[0].update(x=capture.flag['x'],y=capture.flag['y'],z=capture.flag['z'])
        capture.check_end()
        self.assertEqual(capture.status,'victory')
        capture=Game(42,mission='capture_flag');capture.round=30;capture.check_round_limit()
        self.assertEqual(capture.status,'defeat')
        defend=Game(42,mission='defend_flag')
        defend.alive('alien')[0].update(x=defend.flag['x'],y=defend.flag['y'],z=defend.flag['z'])
        defend.check_end()
        self.assertEqual(defend.status,'defeat')
        defend=Game(42,mission='defend_flag');defend.round=30;defend.check_round_limit()
        self.assertEqual(defend.status,'victory')

    def test_generated_maps_connected(self):
        """Verify that generated maps connected."""
        for seed in range(50):
            g = Game(seed)
            paths = g.paths(g.units[0],999,ignore_units=True,ignore_doors=True)
            for u in g.units:
                self.assertIn(g.position(u), paths)

    def test_enemy_turns_complete(self):
        """Verify that enemy turns complete."""
        for seed in range(10):
            g = Game(seed)
            for _ in range(40):
                if g.status != 'active':
                    break
                g.action(dict(action='end_turn'))
            self.assertIn(g.status,('active','defeat','victory'))

    def test_inventory_preserves_ammunition(self):
        """Verify that inventory preserves ammunition."""
        g = self.clear()
        g.units[4].update(x=5, y=10)
        g.action(dict(action='equip', unit='s0', weapon='M9'))
        g.action(dict(action='shoot', unit='s0', target='e0'))
        self.assertEqual(g.units[0]['ap'], 1)
        self.assertEqual(g.units[0]['ammo'], 7)
        g.action(dict(action='equip', unit='s0', weapon='M4A1'))
        self.assertEqual(g.units[0]['ammo'], 6)
        g.action(dict(action='equip', unit='s0', weapon='M9'))
        self.assertEqual(g.units[0]['ammo'], 7)
        with self.assertRaises(ValueError):
            g.action(dict(action='equip', unit='s0', weapon='M110'))

    def test_stance_cost_speed_and_accuracy(self):
        """Verify that stance cost speed and accuracy."""
        g = self.clear()
        a, b = g.units[0], g.units[4]
        b.update(x=5, y=9)
        baseline = g.chance(a, b)
        g.action(dict(action='stance', unit='s0', stance='kneeling'))
        self.assertEqual(a['ap'], 1)
        self.assertEqual(g.chance(a, b), baseline+5)
        with self.assertRaises(ValueError):
            g.action(dict(action='move', unit='s0', x=5, y=12))
        g.action(dict(action='move', unit='s0', x=5, y=13))
        self.assertEqual(a['ap'], 0)
        a.update(stance='standing', x=5, y=16)
        b['stance'] = 'prone'
        self.assertEqual(g.chance(a, b), baseline-20)

    def test_roof_requires_ladder_and_prone_cannot_climb(self):
        """Verify that roof requires ladder and prone cannot climb."""
        g = self.clear()
        u = g.units[0]
        g.heights[15][5] = 1;g._los_cache.clear()
        g.surfaces.add((5,15,1))
        self.assertNotIn((5,15,1), g.paths(u, 10))
        g.ladders = [((5,16,0),(5,15,1))]
        u['stance'] = 'prone'
        self.assertNotIn((5,15,1), g.paths(u, 10))
        u['stance'] = 'standing'
        g.action(dict(action='move', unit='s0', x=5, y=15, z=1))
        self.assertEqual(u['z'], 1)
        g.action(dict(action='move', unit='s0', x=5, y=16, z=0))
        self.assertEqual(u['z'], 0)

    def test_building_blocks_shot_and_height_advantage(self):
        """Verify that building blocks shot and height advantage."""
        g = self.clear()
        a, b = g.units[0], g.units[4]
        a.update(x=5, y=12)
        b.update(x=5, y=5)
        baseline = g.chance(a, b)
        a['z'] = 1
        self.assertEqual(g.chance(a, b), baseline+10)
        a['z'] = 0
        g.tiles[8][5] = 'high';g._los_cache.clear()
        self.assertEqual(g.chance(a, b), 0)

    def test_grenade_friendly_fire_cover_destruction_and_consumption(self):
        """Verify that grenade friendly fire cover destruction and consumption."""
        g = self.clear()
        g.units[4].update(x=5, y=12)
        g.units[1].update(x=6, y=12)
        g.tiles[12][4] = 'high'
        g.action(dict(action='equip', unit='s0', weapon='Frag grenade'))
        enemy_hp,ally_hp=g.units[4]['hp'],g.units[1]['hp']
        g.action(dict(action='blast', unit='s0', x=5, y=12))
        self.assertEqual(g.units[4]['hp'], max(0,enemy_hp-WEAPONS['Frag grenade']['damage']))
        self.assertEqual(g.units[1]['hp'], max(0,ally_hp-WEAPONS['Frag grenade']['damage']+2))
        self.assertEqual(g.tiles[12][4], 'rubble')
        self.assertEqual(g.units[0]['ammo'], 1)
        self.assertEqual(g.units[0]['ap'], 0)
        g.units[0]['ap'] = 2
        with self.assertRaises(ValueError):
            g.action(dict(action='reload', unit='s0'))

    def test_rocket_restrictions_and_finite_reserve(self):
        """Verify that rocket restrictions and finite reserve."""
        g = self.clear()
        u = g.units[0]
        g.action(dict(action='equip', unit='s0', weapon='RPG-7'))
        u['stance'] = 'prone'
        with self.assertRaises(ValueError):
            g.action(dict(action='blast', unit='s0', x=5, y=12))
        u['stance'] = 'standing'
        with self.assertRaises(ValueError):
            g.action(dict(action='overwatch', unit='s0'))
        g.action(dict(action='blast', unit='s0', x=5, y=12))
        u['ap'] = 2
        g.fires=[];g.geometry_revision+=1;g._los_cache.clear()
        g.action(dict(action='reload', unit='s0'))
        self.assertEqual(u['ammo'], 1)
        self.assertEqual(u['inventory']['RPG-7']['reserve'], 0)
        g.action(dict(action='blast', unit='s0', x=5, y=12))
        u['ap'] = 2
        with self.assertRaises(ValueError):
            g.action(dict(action='reload', unit='s0'))

    def test_enemy_fighters_use_human_arsenal(self):
        """Verify that enemy fighters use human arsenal."""
        g=Game(42)
        enemies=g.alive('alien')
        self.assertTrue(all(u['role']=='Enemy fighter' and u['name'].startswith('HOSTILE ') for u in enemies))
        self.assertTrue(all(u['weapon']!='Alien carbine' for u in enemies))
        self.assertGreater(len({u['weapon'] for u in enemies}),1)

    def test_fire_blocks_movement_and_expires(self):
        """Verify that fire blocks movement and expires."""
        g=self.clear();u=g.units[0]
        g.fires=[dict(x=5,y=15,z=0,radius=1.35,turns=2)];g.geometry_revision+=1
        self.assertNotIn((5,15,0),g.paths(u,10))
        g.tick_utilities();self.assertTrue(g.fires)
        g.tick_utilities();self.assertFalse(g.fires)

    def test_night_reduces_visibility(self):
        """Verify that night reduces visibility."""
        day=self.clear();night=self.clear();night.lighting='night';night.geometry_revision+=1;night._los_cache.clear();night.init_fog()
        target=day.alive('alien')[0];target.update(x=5,y=5);night_target=night.alive('alien')[0];night_target.update(x=5,y=5)
        self.assertTrue(day.sees(day.units[0],target))
        self.assertFalse(night.sees(night.units[0],night_target))

    def test_fighter_turns_toward_shot(self):
        """Verify that fighter turns toward shot."""
        g=self.clear();shooter,target=g.units[0],g.alive('alien')[0];target.update(x=10,y=16)
        g.fire_round(shooter,target)
        self.assertAlmostEqual(shooter['facing'],-math.pi/2)

    def test_mission_enemies_advance_on_objectives(self):
        """Verify that mission enemies advance on objectives."""
        defend=self.clear();defend.mission='defend_flag';defend.flag=dict(x=5,y=16,z=0)
        enemy=defend.alive('alien')[0];enemy.update(x=5,y=2,ap=2)
        before=abs(enemy['y']-defend.flag['y']);defend.advance_enemy(enemy,(5,16,0))
        self.assertLess(abs(enemy['y']-defend.flag['y']),before)
        rescue=self.clear();rescue.mission='rescue';enemy=rescue.alive('alien')[0];civilian=rescue.alive('civilian')[0]
        enemy.update(x=5,y=2,ap=2);civilian.update(x=5,y=12)
        before=abs(enemy['y']-civilian['y']);rescue.patrol(enemy)
        self.assertLess(abs(enemy['y']-civilian['y']),before)

    def test_blast_does_not_cross_levels(self):
        """Verify that blast does not cross levels."""
        g = self.clear()
        g.units[4].update(x=5, y=12, z=1)
        g.action(dict(action='equip', unit='s0', weapon='Frag grenade'))
        g.action(dict(action='blast', unit='s0', x=5, y=13))
        self.assertEqual(g.units[4]['hp'], 7)

    def test_invalid_coordinates_do_not_consume_ammo(self):
        """Verify that invalid coordinates do not consume ammo."""
        g = self.clear()
        g.action(dict(action='equip', unit='s0', weapon='Frag grenade'))
        for x, y in [(-1, 2), (100, 0), (True, 3), ('2', 4)]:
            with self.assertRaises(ValueError):
                g.action(dict(action='blast', unit='s0', x=x, y=y))
        self.assertEqual(g.units[0]['ammo'], 2)


if __name__ == '__main__':
    unittest.main()
