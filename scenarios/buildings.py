"""Shared enterable-building construction; policies live in each scenario."""
from .common import edge_key


def generate_lots(game, scenario):
    """Generate a deterministic, connected battlefield for a theme and size."""
    r,n,theme=game.rng,game.size,scenario.theme
    road_x=n//2+r.choice([-2,0,2]);cross_y=r.randrange(9,n-9)
    road_width=scenario.road_width
    game.road_x,game.cross_y=road_x,cross_y
    game.tiles=[['road' if abs(x-road_x)<=road_width//2 else 'grass' for x in range(n)] for y in range(n)]
    if scenario.cross_road:
        for y in range(cross_y-1,cross_y+2):game.tiles[y]=['road']*n
    planned_lots,context=scenario.plan(game)
    road_x,cross_y=game.road_x,game.cross_y
    game.heights=[[0]*n for _ in range(n)]
    game.surfaces={(x,y,0) for y in range(n) for x in range(n)}
    game.buildings,game.ladders,game.stairs,game.portals,game.props=[],[],[],[],[]
    game.walls,game.blocked={},set()
    count=len(planned_lots)
    commercial={'CORNER SHOP','CAFE','HARDWARE STORE','RESTAURANT','BOOK SHOP','DINER','MARKET','PHARMACY','PARTS STORE','CANTEEN'}
    residential={'APARTMENTS','LIVING QUARTERS','TOWNHOUSE','FARMHOUSE','LODGE','AIRPORT HOTEL'}
    civic={'POST OFFICE','CLINIC','TERMINAL','TICKET HALL','WAITING ROOM','FIRE STATION','OFFICES','ADMIN','RAIL OFFICES'}
    for _ in range(count):
        name=scenario.building_name(game,len(game.buildings))
        archetype='commercial' if name in commercial else 'residential' if name in residential else 'civic' if name in civic else 'industrial' if scenario.industrial else 'rural'
        ranges={'commercial':((4,7),(3,6)),'residential':((3,6),(4,7)),'industrial':((5,8),(4,8)),'civic':((4,7),(4,7)),'rural':((3,6),(3,6))}
        # Keep legacy random draws before applying planned lots so existing seeds stay stable.
        wr,dr=ranges[archetype];width,depth=min(r.randint(*wr),n-5),min(r.randint(*dr),n-8)
        roadside=scenario.roadside and r.random()<.72
        if roadside and scenario.cross_road and r.random()<.42:
            x=r.randint(1,n-width-2);y=r.choice([cross_y-2-depth,cross_y+2])
        elif roadside:
            x=r.choice([road_x-road_width//2-1-width,road_x+road_width//2+2]);y=r.randint(2,n-depth-6)
        else:x,y=r.randint(1,n-width-2),r.randint(2,n-depth-6)
        lot=planned_lots[len(game.buildings)];x,y,width,depth=(lot[k] for k in ('x','y','width','depth'))
        roadside=True
        i=len(game.buildings)
        levels=scenario.building_levels(game,lot,i,archetype)
        distances={'north':abs(y-cross_y),'south':abs(y+depth-cross_y),'west':abs(x-road_x),'east':abs(x+width-road_x)}
        front=('east' if x<road_x else 'west') if roadside and scenario.face_road else min(distances,key=distances.get) if roadside else r.choice(['north','south','west','east'])
        roof_choices={'commercial':['flat','flat','terrace'],'residential':['gable','flat','terrace'],'industrial':['sawtooth','flat','vented'],'civic':['flat','dome','gable'],'rural':['gable','gable','vented']}
        b=dict(id=f'b{i}',x=x,y=y,width=width,depth=depth,level=levels,name=name,archetype=archetype,front=front,roof=r.choice(roof_choices[archetype]),facade=r.choice(['brick','stucco','concrete','timber','metal']),color=r.choice(['#9d8d78','#a99d88','#8e9894','#9c725f','#7f8d92','#a69b72']),accent=r.choice(['#b9aa83','#6f8990','#9b614f','#75836a']))
        scenario.configure_building(game,b,lot,i)
        front,archetype=b['front'],scenario.wall_archetype(b,archetype)
        game.buildings.append(b)
        for by in range(y,y+depth):
            for bx in range(x,x+width):
                game.heights[by][bx]=levels;game.tiles[by][bx]='floor'
                for z in range(1,levels+1):game.surfaces.add((bx,by,z))
        for z in range(levels):
            edges=[]
            for bx in range(x,x+width):edges += [((bx,y,z),(bx,y-1,z),'north'),((bx,y+depth-1,z),(bx,y+depth,z),'south')]
            for by in range(y,y+depth):edges += [((x,by,z),(x-1,by,z),'west'),((x+width-1,by,z),(x+width,by,z),'east')]
            for a,other,side in edges:
                along=a[0]-x if side in ('north','south') else a[1]-y
                span=width if side in ('north','south') else depth
                entrance=min(span-1,max(0,span//2+(i%3)-1))
                double=scenario.double_door(b,side,z,along,entrance)
                kind='door' if double or (side==front and along==entrance and z==0) else 'window' if along%2==(i+z)%2 and (side==front or archetype in ('commercial','residential','civic')) else 'wall'
                kind=scenario.portal_kind(b,z,kind)
                portal=dict(id=f'p{len(game.portals)}',a=a,b=other,kind=kind,open=False,building=b['id'],side=side)
                if double:portal.update(door_group=f'{b["id"]}:{side}',door_leaf=along-entrance)
                game.walls[edge_key(a,other)]=portal
                if kind!='wall':game.portals.append(portal)
        # Connected two-room floors, with an optional third room in larger buildings.
        for z in range(levels):
            if scenario.open_interior(b):continue  # An uninterrupted public waiting hall.
            split_y=y+r.randint(1,depth-1)
            doorway=x+r.randrange(width)
            for bx in range(x,x+width):
                a,other=(bx,split_y-1,z),(bx,split_y,z)
                kind='door' if bx==doorway else 'wall'
                wall=dict(id=f"{b['id']}_inner_{z}_h{bx}",a=a,b=other,kind=kind,open=False,building=b['id'],side='interior')
                game.walls[edge_key(a,other)]=wall
                if kind=='door':game.portals.append(wall)
            if width>=4 and depth>=5:
                split_x=x+width//2;door_y=r.randrange(y,split_y)
                for by in range(y,split_y):
                    a,other=(split_x-1,by,z),(split_x,by,z)
                    kind='door' if by==door_y else 'wall'
                    wall=dict(id=f"{b['id']}_inner_{z}_v{by}",a=a,b=other,kind=kind,open=False,building=b['id'],side='interior')
                    game.walls[edge_key(a,other)]=wall
                    if kind=='door':game.portals.append(wall)
        if scenario.interior_ladders or i%2:
            # Interior ladders connect floors (or a single-storey loft/roof).
            game.ladders.extend(((x+width-1,y+depth-1,z),(x+width-1,y+depth-1,z+1)) for z in range(levels))
        else:
            game.ladders.append(((x+width,y+depth-1,0),(x+width-1,y+depth-1,levels)))
        for z in range(levels):game.stairs.append(((x+width-1,y,z),(x+width-1,y,z+1)))
    scenario.place_props(game,context)
    game.scenery=dict(theme=game.theme,road_x=road_x,cross_y=cross_y,**scenario.scenery_details(game,context),**theme)
