"""Factory complex scenario definition."""
from scenarios.base import Scenario
from .layout import factory_generate


class FactoryScenario(Scenario):
    id = 'factory'
    order = 1
    theme = {'label': 'Factory complex', 'names': ['ASSEMBLY', 'WAREHOUSE', 'CONTROL', 'WORKSHOP', 'CANTEEN', 'PARTS STORE', 'ADMIN', 'LOADING HALL'], 'ground': '#797c72', 'road': '#4b5050', 'wall': '#909d9d', 'props': ['container', 'tank', 'truck', 'pipes', 'sign', 'trash']}

    def generate(self, game):
        from scenarios.assets import transport_models
        factory_generate(game,self.theme,transport_models())


SCENARIO = FactoryScenario()
