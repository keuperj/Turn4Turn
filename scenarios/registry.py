"""Ordered scenario registration and convention-based addon discovery."""
import importlib
import re
from pathlib import Path
from .base import Scenario


class ScenarioRegistry:
    def __init__(self):
        self._scenarios = {}

    def register(self, scenario):
        if not isinstance(scenario, Scenario):
            raise TypeError('Scenarios must derive from Scenario')
        if not re.fullmatch(r'[a-z][a-z0-9_]*', scenario.id) or scenario.id == 'random':
            raise ValueError(f'Invalid scenario ID: {scenario.id!r}')
        if scenario.id in self._scenarios:
            raise ValueError(f'Duplicate scenario ID: {scenario.id}')
        required = {'label', 'names', 'ground', 'road', 'wall', 'props'}
        if not required <= scenario.theme.keys():
            raise ValueError(f'{scenario.id}: missing theme fields {required - scenario.theme.keys()}')
        self._scenarios[scenario.id] = scenario

    def __getitem__(self, scenario_id):
        return self._scenarios[scenario_id]

    def __iter__(self):
        return iter(sorted(self._scenarios.values(), key=lambda s: (s.order, s.id)))

    def themes(self):
        return {s.id: s.theme for s in self}

    def client_catalog(self):
        return {'scenarios': [dict(id=s.id, label=s.theme['label'],
                                  module=f'/scenarios/{s.id}/index.js') for s in self]}


def discover():
    """Discover direct subpackages exporting SCENARIO from scenario.py at startup."""
    registry = ScenarioRegistry()
    for definition in sorted(Path(__file__).parent.glob('*/scenario.py')):
        scenario = importlib.import_module(f'scenarios.{definition.parent.name}.scenario').SCENARIO
        if scenario.id != definition.parent.name:
            raise ValueError(f'Scenario ID must match folder: {definition}')
        renderer = Path(__file__).resolve().parents[1]/'static/scenarios'/scenario.id/'index.js'
        if not renderer.is_file():
            raise ValueError(f'Missing scenario renderer: {renderer}')
        registry.register(scenario)
    return registry
