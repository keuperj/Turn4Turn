import unittest

from game import DIFFICULTIES, Game


class DifficultyTests(unittest.TestCase):
    def test_each_difficulty_sets_team_time_units(self):
        for level, rules in DIFFICULTIES.items():
            with self.subTest(level=level):
                game = Game(73, difficulty=level)
                self.assertTrue(all(u['ap'] == rules['player_time'] for u in game.alive('soldier')))
                self.assertTrue(all(u['ap'] == rules['enemy_time'] for u in game.alive('alien')))
                state = game.state()
                self.assertEqual(level, state['difficulty'])
                self.assertEqual(rules['player_time'], state['player_time'])
                self.assertEqual(rules['enemy_time'], state['enemy_time'])

    def test_unknown_difficulty_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Difficulty'):
            Game(73, difficulty='impossible')

    def test_easy_and_hard_change_available_movement(self):
        easy = Game(73, difficulty='easy').state()
        hard = Game(73, difficulty='hard').state()
        easy_moves = len(easy['movement']['s0'])
        hard_moves = len(hard['movement']['s0'])
        self.assertGreater(easy_moves, hard_moves)


if __name__ == '__main__':
    unittest.main()
