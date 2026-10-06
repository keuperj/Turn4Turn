"""Street crossing scenario definition."""
from scenarios.base import LotScenario
from .layout import street_plan, street_props


class StreetScenario(LotScenario):
    id = 'streets'
    order = 4
    theme = {'label': 'Street crossing', 'names': ['FAMILY HOME', 'GARDEN HOUSE', 'BUNGALOW', 'COTTAGE'], 'ground': '#8c9c71', 'road': '#42494b', 'wall': '#b6a290', 'props': ['car', 'truck', 'bus', 'bench', 'sign', 'lamp', 'trash', 'bush']}

    cross_road = roadside = interior_ladders = True

    def plan(self, game):
        return street_plan(game),None

    def building_levels(self, game, lot, index, archetype):
        super().building_levels(game,lot,index,archetype)
        return 2 if index==0 else game.rng.choice([1,1,2])

    def configure_building(self, game, b, lot, index):
        r=game.rng
        b.update(archetype='residential',front=lot['front'],roof='gable',garden=lot['garden'],facade=r.choice(['brick','stucco','timber']),color=r.choice(['#c2b59d','#bac5bc','#cfb49d','#a9bac4']),accent=r.choice(['#815e4c','#64736c','#7c7b7c']))

    def place_props(self, game, context):
        from scenarios.common import PROP_SIZE
        from scenarios.assets import transport_models
        street_props(game,PROP_SIZE,transport_models())

    def scenery_details(self, game, context):
        return dict(road_width=12,lanes=4,sidewalk_width=2)


SCENARIO = StreetScenario()
