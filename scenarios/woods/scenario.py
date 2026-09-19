"""Woodland camp scenario definition."""
from scenarios.base import LotScenario
from .layout import woodland_plan, woodland_props


class WoodlandScenario(LotScenario):
    id = 'woods'
    order = 5
    theme = {'label': 'Woodland camp', 'names': ['RANGER CABIN', 'LODGE', 'LOOKOUT', 'TOOL SHED', 'FIELD OFFICE', 'MESS HALL'], 'ground': '#697451', 'road': '#84765e', 'wall': '#80644a', 'props': ['tree_oak', 'tree_pine', 'tree_birch', 'bush', 'bench', 'truck']}

    rural_levels = True

    def plan(self, game):
        return woodland_plan(game),None

    def building_levels(self, game, lot, index, archetype):
        super().building_levels(game,lot,index,archetype)
        return 1

    def configure_building(self, game, b, lot, index):
        b.update(archetype='rural',roof='gable',facade='timber',color=game.rng.choice(['#806044','#96734e','#70563e']),accent='#625845')

    def wall_archetype(self, building, original):
        # Cabins retain their original window layout under the timber exterior.
        return original

    def place_props(self, game, context):
        woodland_props(game)

    def scenery_details(self, game, context):
        return dict(road_width=1,meadows=game.meadows)


SCENARIO = WoodlandScenario()
