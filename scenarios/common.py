"""Shared geometry and metre-scale prop footprints."""
def edge_key(a, b):
    """Return a canonical key for an undirected edge between two tiles."""
    return tuple(sorted((tuple(a), tuple(b))))


# Footprints use the same approximate one-metre scale as the 1.7m fighters.
PROP_SIZE={'car':(2,5),'truck':(2,6),'bus':(3,7),'ambulance':(2,5),'tractor':(2,3),'aircraft':(10,10),
           'factory_machine':(3,2),'factory_robot':(2,2),'factory_conveyor':(3,2),'factory_rack':(3,1),'factory_forklift':(2,3),
           'airport_tug':(2,3),'airport_fuel':(2,3),'airport_cart':(2,2),'windsock':(2,2),
           'cow':(1,2),'sheep':(1,1),'pig':(1,1),'train':(3,10),'container':(3,6),'tank':(2,2),'silo':(2,2),
           'pipes':(2,3),'bench':(2,1),'hay':(2,2),'tree':(1,1),
           'tree_oak':(1,1),'tree_pine':(1,1),'tree_birch':(1,1),'bush':(1,1),
           'flowerbed':(2,1),'sign':(1,1),'lamp':(1,1),'trash':(1,1),'traffic_light':(1,1),'cafe_table':(1,1),'ticket_counter':(2,1)}


