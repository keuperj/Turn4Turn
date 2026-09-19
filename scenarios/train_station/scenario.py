"""Train station scenario definition."""
from scenarios.base import LotScenario
from .layout import railway_plan, railway_props


class RailwayScenario(LotScenario):
    id = 'train_station'
    order = 2
    theme = {'label': 'Train station', 'names': ['TICKET HALL', 'SIGNAL BOX', 'FREIGHT DEPOT', 'CAFE', 'POST OFFICE', 'WAITING ROOM', 'RESTAURANT', 'RAIL OFFICES'], 'ground': '#929083', 'road': '#69665f', 'wall': '#ae9b82', 'props': ['train', 'container', 'bench', 'car', 'sign', 'lamp']}

    industrial = roadside = face_road = interior_ladders = True

    def plan(self, game):
        return railway_plan(game),None

    def building_levels(self, game, lot, index, archetype):
        super().building_levels(game,lot,index,archetype)
        return 1 if lot['station'] else game.rng.choice([1,2])

    def configure_building(self, game, b, lot, index):
        b.update(station=lot['station'],name='CENTRAL STATION' if lot['station'] else game.rng.choice(['TOWNHOUSE','CORNER SHOP','APARTMENTS']),archetype='civic' if lot['station'] else 'residential',front='east' if b['x']<game.road_x else 'west',roof='gable',facade='brick',color=game.rng.choice(['#a58970','#b6aa90','#9e8575']))

    def double_door(self, b, side, level, along, entrance):
        return b.get('station') and side in ('east','west') and level==0 and along in (entrance,entrance+1)

    def open_interior(self, b):
        return b.get('station')

    def place_props(self, game, context):
        from scenarios.common import PROP_SIZE
        from scenarios.assets import transport_models
        railway_props(game,PROP_SIZE,transport_models())

    def scenery_details(self, game, context):
        return dict(tracks=game.track_centers,road_width=2)


SCENARIO = RailwayScenario()
