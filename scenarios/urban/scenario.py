"""Urban district scenario definition."""
from scenarios.base import LotScenario
from .layout import urban_plan, urban_props


class UrbanScenario(LotScenario):
    id = 'urban'
    order = 0
    theme = {'label': 'Urban district', 'names': ['APARTMENTS', 'CORNER SHOP', 'POST OFFICE', 'CAFE', 'HARDWARE STORE', 'LIVING QUARTERS', 'RESTAURANT', 'CLINIC', 'BOOK SHOP', 'OFFICES'], 'ground': '#858578', 'road': '#43494b', 'wall': '#b7afa0', 'props': ['car', 'car', 'ambulance', 'bench', 'sign', 'lamp', 'bush']}

    cross_road = roadside = True

    def plan(self, game):
        return urban_plan(game)

    def building_name(self, game, index):
        return ['CAFE','CORNER SHOP'][index] if index<2 else super().building_name(game,index)

    def building_levels(self, game, lot, index, archetype):
        super().building_levels(game,lot,index,archetype)
        return game.rng.choice([3,4,4,5,6])

    def configure_building(self, game, b, lot, index):
        b['roof']=game.rng.choice(['flat','terrace','vented'])
        b['facade']=game.rng.choice(['brick','stucco','concrete','metal'])

    def place_props(self, game, context):
        urban_props(game,context)

    def scenery_details(self, game, context):
        return dict(road_width=5,sidewalk_width=2,park=context)


SCENARIO = UrbanScenario()
