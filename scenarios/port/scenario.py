"""A working port with connected piers and an industrial quay."""
from scenarios.base import LotScenario
from .layout import port_plan, port_props


class PortScenario(LotScenario):
    """Keep open water outside the navigation graph and all piers connected."""
    id='port'
    order=7
    theme={'label':'Port','names':['WAREHOUSE','SHIP REPAIR','PORT AUTHORITY'],
           'ground':'#8b9696','road':'#525f64','wall':'#a7b6b8',
           'props':['port_box','port_pedestal','port_crane']}
    industrial=interior_ladders=True

    def plan(self,game):
        """Reserve basin, piers, quay road, and industrial building lots."""
        return port_plan(game),None

    def building_levels(self,game,lot,index,archetype):
        """A raised port office overlooks the single-storey warehouses."""
        return 2 if index==2 else 1

    def configure_building(self,game,b,lot,index):
        """Face the industrial sheds toward the waterfront."""
        b.update(port=True,name=lot['name'],front='north',archetype='industrial',
                 roof='sawtooth' if index==0 else 'gable' if index==1 else 'flat',
                 facade='metal' if index<2 else 'concrete',
                 color=['#81979b','#8a9487','#c0c3b2','#869894'][index],accent='#d2aa59')

    def open_interior(self,b):
        """Keep loading halls open for tactical movement."""
        return True

    def place_props(self,game,context):
        """Remove water surfaces before spawns and place collision-safe cover."""
        game.surfaces={p for p in game.surfaces if p[2] or game.tiles[p[1]][p[0]]!='water'}
        port_props(game)

    def scenery_details(self,game,context):
        """Publish static harbour geography without exposing any units."""
        return game.port


SCENARIO=PortScenario()
