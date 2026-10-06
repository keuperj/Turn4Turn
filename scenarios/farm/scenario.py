"""Farmstead scenario definition."""
from scenarios.base import LotScenario
from .layout import farm_plan, farm_props


class FarmScenario(LotScenario):
    id = 'farm'
    order = 6
    theme = {'label': 'Farmstead', 'names': ['FARMHOUSE', 'BARN', 'GRAIN STORE', 'MACHINE SHED', 'FARM SHOP', 'LIVING QUARTERS', 'PACKING HOUSE'], 'ground': '#a69768', 'road': '#83745c', 'wall': '#b08269', 'props': ['tractor', 'silo', 'hay', 'truck', 'tree_oak', 'bush', 'flowerbed']}

    rural_levels = True

    def plan(self, game):
        return farm_plan(game),None

    def building_levels(self, game, lot, index, archetype):
        super().building_levels(game,lot,index,archetype)
        return 2 if lot['name']=='FARMHOUSE' else 1

    def configure_building(self, game, b, lot, index):
        b.update(name=lot['name'],archetype='residential' if index==0 else 'rural',front=lot['front'],roof='gable',facade='stucco' if index==0 else 'timber',color='#d5c6a5' if index==0 else '#a15342',accent='#e2d5b7')

    def place_props(self, game, context):
        farm_props(game)

    def scenery_details(self, game, context):
        return dict(road_width=3,field_edge=game.field_edge)


SCENARIO = FarmScenario()
