"""Rescue spawn separation, reachability and seeded variation across scenarios."""
import math
import unittest
from unittest.mock import patch
from game import Game
from scenarios import THEMES
from deployment import CIVILIAN_COUNT, RESCUE_ENEMY_DISTANCE, place_rescue_civilians


class RescueDeploymentTests(unittest.TestCase):
    def test_safe_random_starts_across_scenarios_sizes_and_difficulties(self):
        for theme in THEMES:
            for size in (24,30,40):
                layouts=set()
                for seed in range(8):
                    difficulty=('easy','medium','hard')[seed%3]
                    with self.subTest(theme=theme,size=size,seed=seed,difficulty=difficulty):
                        g=Game(seed,theme,size=size,difficulty=difficulty,lighting='night' if seed%2 else 'day')
                        civilians=g.alive('civilian');enemies=g.alive('alien')
                        self.assertEqual(len(civilians),CIVILIAN_COUNT)
                        low,high={24:(5,7),30:(7,9),40:(10,13)}[size]
                        self.assertTrue(low<=len(enemies)<=high)
                        positions=[g.position(u) for u in g.units]
                        self.assertEqual(len(positions),len(set(positions)))
                        reachable=g.paths(g.units[0],999,ignore_units=True,ignore_doors=True)
                        self.assertTrue(all(p in reachable and p not in g.blocked for p in positions))
                        links={tuple(p) for link in g.stairs+g.ladders for p in link}
                        for civilian in civilians:
                            self.assertEqual(civilian['z'],0)
                            self.assertNotIn(g.position(civilian),links)
                            self.assertTrue(4<civilian['y']<size-6)
                            for enemy in enemies:
                                self.assertGreaterEqual(math.hypot(enemy['x']-civilian['x'],enemy['y']-civilian['y']),RESCUE_ENEMY_DISTANCE)
                                self.assertFalse(g.sees(enemy,civilian))
                                self.assertEqual(g.chance(enemy,civilian),0)
                        layouts.add(tuple(g.position(u) for u in civilians+enemies))
                self.assertEqual(len(layouts),8,'Different seeds should not use fixed spawn positions')

    def test_same_seed_reproduces_replanned_enemy_and_civilian_positions(self):
        replanned=False
        for theme in THEMES:
            g=Game(41,theme,size=24)
            self.assertEqual(g.units,Game(41,theme,size=24).units)
            normal=Game(41,theme,size=24,mission='eliminate')
            self.assertEqual([u['weapon'] for u in g.alive('alien')],[u['weapon'] for u in normal.alive('alien')])
            indoor=lambda world:[u for u in world.alive('alien') if world.building_at(*world.position(u))]
            self.assertGreaterEqual(len(indoor(g)),min(2,len(indoor(normal))))
            if any(u['z']>0 for u in indoor(normal)):
                self.assertTrue(any(u['z']>0 for u in indoor(g)))
            replanned|=[g.position(u) for u in g.alive('alien')]!=[normal.position(u) for u in normal.alive('alien')]
        self.assertTrue(replanned,'Exercise the constrained-map relocation path')

    def test_other_missions_do_not_use_rescue_placement(self):
        with patch('game.place_rescue_civilians',side_effect=AssertionError('Unexpected rescue placement')):
            for mission in ('eliminate','capture_flag','defend_flag'):
                g=Game(41,mission=mission)
                self.assertFalse(g.alive('civilian'))

    def test_insufficient_space_never_silently_relaxes_safety(self):
        g=Game(41,'factory',mission='eliminate',size=24)
        before=[g.position(u) for u in g.units]
        with self.assertRaisesRegex(ValueError,'no safe rescue deployment'):
            place_rescue_civilians(g,[(12,12,0)],[(12,12,0)])
        self.assertEqual(before,[g.position(u) for u in g.units])
        self.assertFalse(g.alive('civilian'))
