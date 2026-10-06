"""Regional airport scenario definition."""
from scenarios.base import LotScenario
from .layout import airport_plan, airport_props


class AirportScenario(LotScenario):
    id = 'airport'
    order = 3
    theme = {'label': 'Regional airport', 'names': ['TERMINAL', 'HANGAR', 'CONTROL TOWER', 'CARGO', 'CAFE', 'AIRPORT HOTEL', 'FIRE STATION', 'MAINTENANCE'], 'ground': '#809565', 'road': '#616a6c', 'wall': '#b7c4c2', 'props': ['aircraft', 'truck', 'bus', 'car', 'tank', 'sign', 'lamp']}

    road_width = 11
    industrial = interior_ladders = True

    def plan(self, game):
        return airport_plan(game),None

    def building_levels(self, game, lot, index, archetype):
        super().building_levels(game,lot,index,archetype)
        return lot['level']

    def configure_building(self, game, b, lot, index):
        role=lot['airport_role']
        b.update(name=lot['name'],airport_role=role,archetype='civic' if role!='hangar' else 'industrial',front='east',roof='gable' if role=='hangar' else 'flat',facade='metal' if role=='hangar' else 'concrete',color='#b9c5c7' if role=='terminal' else '#788c99',accent='#4e6572')

    def double_door(self, b, side, level, along, entrance):
        return (b.get('airport_role')=='terminal' and side in ('east','west') or b.get('airport_role')=='hangar' and side=='east') and level==0 and along in (entrance,entrance+1)

    def portal_kind(self, b, level, kind):
        return 'window' if b.get('airport_role')=='tower' and level==b['level']-1 else kind

    def open_interior(self, b):
        return b.get('airport_role') in ('terminal','hangar','tower')

    def place_props(self, game, context):
        from scenarios.assets import transport_models
        airport_props(game,transport_models())

    def scenery_details(self, game, context):
        return game.airport


SCENARIO = AirportScenario()
