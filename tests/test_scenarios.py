"""Scenario addon contracts and discovery integration."""
import unittest
import hashlib
import json
import random
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from game import Game
from scenarios import THEMES, registry, generate
from scenarios.base import Scenario, LotScenario
from scenarios.registry import ScenarioRegistry, discover


class CourtyardScenario(LotScenario):
    id = 'courtyard'
    theme = dict(label='Courtyard', names=['WORKSHOP'], ground='#8c9c71',
                 road='#42494b', wall='#b6a290', props=[])

    def plan(self, game):
        n=game.size
        game.tiles=[['grass']*n for _ in range(n)]
        return [dict(x=x,y=y,width=4,depth=4)
                for x in (2,n-7) for y in (3,n//2)],None


class ScenarioTests(unittest.TestCase):
    def test_pre_refactor_seeded_layouts_are_unchanged(self):
        # Independent snapshots include geometry, portals, props and traversal.
        def canonical(value):
            if isinstance(value,dict):return [[canonical(k),canonical(v)] for k,v in sorted(value.items(),key=lambda kv:repr(kv[0]))]
            if isinstance(value,set):return [canonical(v) for v in sorted(value,key=repr)]
            if isinstance(value,(list,tuple)):return [canonical(v) for v in value]
            return value
        records=json.loads((Path(__file__).parent/'fixtures/scenario_layouts.json').read_text())
        for record in records:
            with self.subTest(**record):
                g=SimpleNamespace(theme=record['theme'],size=record['size'],rng=random.Random(record['seed']))
                generate(g)
                data={k:v for k,v in vars(g).items() if k!='rng'}
                digest=hashlib.sha256(json.dumps(canonical(data),separators=(',',':')).encode()).hexdigest()
                self.assertEqual(digest,record['sha256'])

    def test_addon_runs_through_game_without_a_dispatch_branch(self):
        addon=CourtyardScenario()
        with patch.dict(registry._scenarios,{addon.id:addon}),patch.dict(THEMES,{addon.id:addon.theme}):
            for size in (24,30,40):
                game=Game(41,addon.id,size=size)
                self.assertEqual(game.buildings,Game(41,addon.id,size=size).buildings)
                self.assertEqual(len(game.buildings),4)
                self.assertEqual(game.state()['scenery']['label'],'Courtyard')
                self.assertTrue(all(tuple(p) in game.surfaces for link in game.stairs+game.ladders for p in link))
                self.assertIn(addon.id,[s['id'] for s in registry.client_catalog()['scenarios']])

    def test_discovery_preserves_seeded_theme_order(self):
        found=discover()
        self.assertEqual([s.id for s in found],['urban','factory','train_station','airport','streets','woods','farm'])
        self.assertTrue(all(isinstance(s,Scenario) for s in found))
        self.assertEqual(found.themes(),THEMES)

    def test_registry_rejects_duplicate_and_invalid_definitions(self):
        found=ScenarioRegistry();found.register(CourtyardScenario())
        with self.assertRaisesRegex(ValueError,'Duplicate'):found.register(CourtyardScenario())
        with self.assertRaises(TypeError):found.register(object())
        for invalid in ('random','../escape','Upper Case',''):
            addon=CourtyardScenario();addon.id=invalid
            with self.assertRaisesRegex(ValueError,'Invalid'):found.register(addon)
        addon=CourtyardScenario();addon.id='incomplete';addon.theme={}
        with self.assertRaisesRegex(ValueError,'missing theme'):found.register(addon)
        with self.assertRaises(TypeError):Scenario()
