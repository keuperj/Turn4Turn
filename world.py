"""Seeded themes, enterable structures and scenery with matching collision data."""
THEMES = {
    'urban': dict(label='Urban district', names=['APARTMENTS', 'CORNER SHOP', 'OFFICES', 'CLINIC'], ground='#858578', road='#43494b', wall='#b7afa0', props=['car', 'car', 'car', 'bench']),
    'factory': dict(label='Factory complex', names=['ASSEMBLY', 'WAREHOUSE', 'CONTROL', 'WORKSHOP'], ground='#797c72', road='#4b5050', wall='#909d9d', props=['container', 'tank', 'truck', 'pipes']),
    'train_station': dict(label='Train station', names=['TICKET HALL', 'SIGNAL BOX', 'FREIGHT DEPOT', 'CAFE'], ground='#929083', road='#69665f', wall='#ae9b82', props=['train', 'container', 'bench', 'car']),
    'airport': dict(label='Regional airport', names=['TERMINAL', 'HANGAR', 'CONTROL TOWER', 'CARGO'], ground='#939994', road='#616a6c', wall='#b7c4c2', props=['aircraft', 'truck', 'car', 'tank']),
    'streets': dict(label='Street intersection', names=['DINER', 'GARAGE', 'MARKET', 'TOWNHOUSE'], ground='#8e8b7f', road='#42494b', wall='#b6a290', props=['car', 'truck', 'car', 'bench']),
    'woods': dict(label='Woodland camp', names=['RANGER CABIN', 'LODGE', 'LOOKOUT', 'TOOL SHED'], ground='#697451', road='#84765e', wall='#80644a', props=['tree', 'tree', 'tree', 'truck']),
    'farm': dict(label='Farmstead', names=['FARMHOUSE', 'BARN', 'GRAIN STORE', 'MACHINE SHED'], ground='#a69768', road='#83745c', wall='#b08269', props=['tractor', 'silo', 'hay', 'truck']),
}


def edge_key(a, b):
    return tuple(sorted((tuple(a), tuple(b))))


# Footprints use the same approximate one-metre scale as the 1.7m fighters.
PROP_SIZE={'car':(2,5),'truck':(2,6),'tractor':(2,3),'aircraft':(10,10),
           'train':(3,10),'container':(3,6),'tank':(2,2),'silo':(2,2),
           'pipes':(2,3),'bench':(2,1),'hay':(2,2),'tree':(1,1)}


def generate(game):
    r,n,theme=game.rng,game.size,THEMES[game.theme]
    road_x=n//2+r.choice([-2,0,2]);cross_y=r.randrange(9,n-9)
    road_width=11 if game.theme=='airport' else 5
    game.road_x,game.cross_y=road_x,cross_y
    game.tiles=[['road' if abs(x-road_x)<=road_width//2 else 'grass' for x in range(n)] for y in range(n)]
    if game.theme in ('urban','streets'):
        for y in range(cross_y-1,cross_y+2):game.tiles[y]=['road']*n
    game.heights=[[0]*n for _ in range(n)]
    game.surfaces={(x,y,0) for y in range(n) for x in range(n)}
    game.buildings,game.ladders,game.stairs,game.portals,game.props=[],[],[],[],[]
    game.walls,game.blocked={},set()
    reserved={(x,y,0) for y in range(n-4,n) for x in range(n)}
    count={'urban':9,'factory':7,'train_station':7,'airport':6,'streets':8,'woods':5,'farm':6}[game.theme]
    count=max(4,round(count*(n/30)**2))
    for attempt in range(1200):
        if len(game.buildings)>=count:break
        width,depth=r.randint(3,5),r.randint(3,6)
        if game.theme=='woods':width,depth=r.randint(3,4),r.randint(3,4)
        x,y=r.randint(1,n-width-2),r.randint(2,n-depth-6)
        cells={(bx,by,0) for by in range(y-1,y+depth+1) for bx in range(x-1,x+width+1)}
        if cells&reserved or any(game.tiles[by][bx]=='road' for bx,by,_ in cells):continue
        if any(not(x+width+2<=b['x'] or b['x']+b['width']+2<=x or y+depth+2<=b['y'] or b['y']+b['depth']+2<=y) for b in game.buildings):continue
        i=len(game.buildings);levels=1 if game.theme in ('woods','farm') else (2 if i==0 else r.choice([1,2,2]))
        b=dict(id=f'b{i}',x=x,y=y,width=width,depth=depth,level=levels,name=theme['names'][i%4])
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
                kind='door' if side=='south' and a[0]==x+1 and z==0 else 'window' if (side in ('west','east') and a[1]==y+1) or (side=='north' and a[0]==x+1) else 'wall'
                portal=dict(id=f'p{len(game.portals)}',a=a,b=other,kind=kind,open=False,building=b['id'],side=side)
                game.walls[edge_key(a,other)]=portal
                if kind!='wall':game.portals.append(portal)
        # Connected two-room floors, with an optional third room in larger buildings.
        for z in range(levels):
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
        if i%2:
            # Interior ladders connect floors (or a single-storey loft/roof).
            game.ladders.extend(((x+width-1,y+depth-1,z),(x+width-1,y+depth-1,z+1)) for z in range(levels))
        else:
            game.ladders.append(((x+width,y+depth-1,0),(x+width-1,y+depth-1,levels)))
        for z in range(levels):game.stairs.append(((x+width-1,y,z),(x+width-1,y,z+1)))
        reserved.update(cells)
    kinds=list(theme['props'])
    kinds+=r.choices(['car','bench'] if game.theme in ('urban','streets') else ['tree','hay'] if game.theme in ('farm','woods') else ['truck','tank'],k=max(3,round(5*(n/30)**2)))
    if game.theme=='woods':kinds+=['tree']*round(65*(n/30)**2)
    # Large signature assets get first choice of runway/rail positions.
    kinds.sort(key=lambda k:0 if k in ('aircraft','train') else 1)
    for kind in kinds:
        w,d=PROP_SIZE[kind]
        for _ in range(400):
            x=road_x-w//2 if kind in ('aircraft','train') else r.randrange(1,n-w)
            y=r.randrange(2,n-d-5)
            cells={(bx,by,0) for by in range(y,y+d) for bx in range(x,x+w)}
            buffer={(bx,by,0) for by in range(y-1,y+d+1) for bx in range(x-1,x+w+1)}
            if cells&reserved or buffer&game.blocked or any(game.heights[by][bx] for bx,by,_ in cells):continue
            game.props.append(dict(id=f'prop{len(game.props)}',kind=kind,x=x,y=y,width=w,depth=d,color=r.choice(['#8eaca9','#aa7257','#d1be8a','#5c6975'])))
            game.blocked.update(cells);break
    if game.theme=='farm':
        for x in range(n):
            for y in range(2,n-5):
                if (x,y,0) not in reserved|game.blocked and x%6<3 and game.tiles[y][x]=='grass':game.tiles[y][x]='crops'
    for y in range(2,n-4):
        for x in range(n):
            if (x,y,0) not in reserved|game.blocked and game.tiles[y][x]=='grass' and r.random()<.06:game.tiles[y][x]=r.choice(['low','high'])
    game.scenery=dict(theme=game.theme,road_x=road_x,cross_y=cross_y,**theme)
