"""Water exclusion, connected docks, mission objectives, and bundled marina assets."""
import hashlib
import json
import unittest
from pathlib import Path
from game import Game, MISSIONS


class PortTests(unittest.TestCase):
    def test_navigation_spawns_and_objectives(self):
        """All mission types remain playable without ever spawning in water."""
        for n in (24,30,40):
            for mission in MISSIONS:
                for seed in (0,7,41):
                    g=Game(seed,'port',size=n,mission=mission)
                    water={(x,y,0) for y,row in enumerate(g.tiles) for x,t in enumerate(row) if t=='water'}
                    self.assertGreater(len(water),n*n//5)
                    self.assertFalse(water&g.surfaces)
                    reachable=set(g.paths(g.units[0],999,ignore_units=True,ignore_doors=True))
                    self.assertFalse(g.surfaces-g.blocked-reachable,(n,seed,mission))
                    self.assertTrue(all(g.position(u) in reachable for u in g.units))
                    if g.flag:self.assertIn((g.flag['x'],g.flag['y'],g.flag['z']),reachable)
                    self.assertEqual(len(g.buildings),4)
                    self.assertEqual(len(g.port['vessels']),2)
                    self.assertTrue(all(g.tiles[y][x]=='pier' for x,y,z in g.blocked))

    def test_water_movement_rejected_and_docks_survive_damage(self):
        """Water is not made walkable by preview, movement, or explosions."""
        g=Game(41,'port');g.explored.update(g.surfaces)
        with self.assertRaises(ValueError):g.action(dict(action='move',unit='s0',x=0,y=0,z=0))
        before=set(g.surfaces)
        g.damage_area(3,6,0,4,1000)
        self.assertEqual(before,g.surfaces)

    def test_assets_and_determinism(self):
        """Selected CC0 files are local, intact, and repeatable from a seed."""
        root=Path(__file__).resolve().parents[1]/'static/scenarios/port/models'
        manifest=json.loads((root/'manifest.json').read_text())
        self.assertGreaterEqual(len(manifest['models']),10)
        for model in manifest['models']:
            data=(root/model['file']).read_bytes()
            self.assertEqual(data[:4],b'glTF')
            self.assertEqual(hashlib.sha256(data).hexdigest(),model['sha256'])
            self.assertEqual(model['license'],'CC0-1.0')
        self.assertEqual(Game(41,'port').state(),Game(41,'port').state())
