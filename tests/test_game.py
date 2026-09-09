import unittest
from game import Game, WEAPONS


class CombatTests(unittest.TestCase):
    def clear(self):
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
        self.assertEqual(Game(72).state(), Game(72).state())

    def test_move_and_action_budget(self):
        g = self.clear()
        g.action(dict(action='move', unit='s0', x=5, y=11))
        self.assertEqual(g.units[0]['ap'], 1)
        with self.assertRaises(ValueError):
            g.action(dict(action='move', unit='s0', x=5, y=0))
        self.assertEqual(g.units[0]['y'], 11)

    def test_cover_and_obstruction(self):
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
        g = self.clear()
        g.units[4].update(x=5, y=10)
        g.action(dict(action='shoot', unit='s0', target='e0'))
        self.assertEqual(g.units[0]['ap'], 0)
        self.assertEqual(g.units[0]['ammo'], 5)
        with self.assertRaises(ValueError):
            g.action(dict(action='reload', unit='s0'))
        g.action(dict(action='end_turn'))
        self.assertEqual(g.round, 2)
        g.action(dict(action='reload', unit='s0'))
        self.assertEqual(g.units[0]['ammo'], 6)
        self.assertEqual(g.units[0]['ap'], 1)

    def test_overwatch_triggers_once(self):
        g = self.clear()
        g.units[4].update(x=5, y=10)
        g.action(dict(action='overwatch', unit='s0'))
        g.move(g.units[4], [(5,9,0),(5,8,0)])
        self.assertFalse(g.units[0]['overwatch'])
        self.assertEqual(g.units[0]['ammo'], 5)

    def test_victory_and_reject_post_game_action(self):
        g = self.clear()
        for u in g.alive('alien'):
            u['hp'] = 0
        g.check_end()
        self.assertEqual(g.status, 'victory')
        with self.assertRaises(ValueError):
            g.action(dict(action='end_turn'))

    def test_generated_maps_connected(self):
        for seed in range(50):
            g = Game(seed)
            paths = g.paths(g.units[0],999,ignore_units=True,ignore_doors=True)
            for u in g.units:
                self.assertIn(g.position(u), paths)

    def test_enemy_turns_complete(self):
        for seed in range(10):
            g = Game(seed)
            for _ in range(40):
                if g.status != 'active':
                    break
                g.action(dict(action='end_turn'))
            self.assertIn(g.status,('active','defeat','victory'))

    def test_inventory_preserves_ammunition(self):
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
        g.action(dict(action='reload', unit='s0'))
        self.assertEqual(u['ammo'], 1)
        self.assertEqual(u['inventory']['RPG-7']['reserve'], 0)
        g.action(dict(action='blast', unit='s0', x=5, y=12))
        u['ap'] = 2
        with self.assertRaises(ValueError):
            g.action(dict(action='reload', unit='s0'))

    def test_blast_does_not_cross_levels(self):
        g = self.clear()
        g.units[4].update(x=5, y=12, z=1)
        g.action(dict(action='equip', unit='s0', weapon='Frag grenade'))
        g.action(dict(action='blast', unit='s0', x=5, y=13))
        self.assertEqual(g.units[4]['hp'], 7)

    def test_invalid_coordinates_do_not_consume_ammo(self):
        g = self.clear()
        g.action(dict(action='equip', unit='s0', weapon='Frag grenade'))
        for x, y in [(-1, 2), (100, 0), (True, 3), ('2', 4)]:
            with self.assertRaises(ValueError):
                g.action(dict(action='blast', unit='s0', x=x, y=y))
        self.assertEqual(g.units[0]['ammo'], 2)


if __name__ == '__main__':
    unittest.main()
