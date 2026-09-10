"""Seeded themes, enterable structures and scenery with matching collision data."""
THEMES = {
    'urban': dict(label='Urban district', names=['APARTMENTS', 'CORNER SHOP', 'POST OFFICE', 'CAFE', 'HARDWARE STORE', 'LIVING QUARTERS', 'RESTAURANT', 'CLINIC', 'BOOK SHOP', 'OFFICES'], ground='#858578', road='#43494b', wall='#b7afa0', props=['car', 'car', 'bench', 'sign', 'lamp', 'bush']),
    'factory': dict(label='Factory complex', names=['ASSEMBLY', 'WAREHOUSE', 'CONTROL', 'WORKSHOP', 'CANTEEN', 'PARTS STORE', 'ADMIN', 'LOADING HALL'], ground='#797c72', road='#4b5050', wall='#909d9d', props=['container', 'tank', 'truck', 'pipes', 'sign', 'trash']),
    'train_station': dict(label='Train station', names=['TICKET HALL', 'SIGNAL BOX', 'FREIGHT DEPOT', 'CAFE', 'POST OFFICE', 'WAITING ROOM', 'RESTAURANT', 'RAIL OFFICES'], ground='#929083', road='#69665f', wall='#ae9b82', props=['train', 'container', 'bench', 'car', 'sign', 'lamp']),
    'airport': dict(label='Regional airport', names=['TERMINAL', 'HANGAR', 'CONTROL TOWER', 'CARGO', 'CAFE', 'AIRPORT HOTEL', 'FIRE STATION', 'MAINTENANCE'], ground='#939994', road='#616a6c', wall='#b7c4c2', props=['aircraft', 'truck', 'car', 'tank', 'sign', 'lamp']),
    'streets': dict(label='Street intersection', names=['DINER', 'GARAGE', 'MARKET', 'TOWNHOUSE', 'HARDWARE STORE', 'POST OFFICE', 'CAFE', 'RESTAURANT', 'LIVING QUARTERS', 'PHARMACY'], ground='#8e8b7f', road='#42494b', wall='#b6a290', props=['car', 'truck', 'bench', 'sign', 'lamp', 'trash', 'bush']),
    'woods': dict(label='Woodland camp', names=['RANGER CABIN', 'LODGE', 'LOOKOUT', 'TOOL SHED', 'FIELD OFFICE', 'MESS HALL'], ground='#697451', road='#84765e', wall='#80644a', props=['tree_oak', 'tree_pine', 'tree_birch', 'bush', 'bench', 'truck']),
    'farm': dict(label='Farmstead', names=['FARMHOUSE', 'BARN', 'GRAIN STORE', 'MACHINE SHED', 'FARM SHOP', 'LIVING QUARTERS', 'PACKING HOUSE'], ground='#a69768', road='#83745c', wall='#b08269', props=['tractor', 'silo', 'hay', 'truck', 'tree_oak', 'bush', 'flowerbed']),
}

def edge_key(a, b):
    return tuple(sorted((tuple(a), tuple(b))))


# Footprints use the same approximate one-metre scale as the 1.7m fighters.
PROP_SIZE={'car':(2,5),'truck':(2,6),'tractor':(2,3),'aircraft':(10,10),
           'train':(3,10),'container':(3,6),'tank':(2,2),'silo':(2,2),
           'pipes':(2,3),'bench':(2,1),'hay':(2,2),'tree':(1,1),
           'tree_oak':(1,1),'tree_pine':(1,1),'tree_birch':(1,1),'bush':(1,1),
           'flowerbed':(2,1),'sign':(1,1),'lamp':(1,1),'trash':(1,1)}


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
    commercial={'CORNER SHOP','CAFE','HARDWARE STORE','RESTAURANT','BOOK SHOP','DINER','MARKET','PHARMACY','PARTS STORE','CANTEEN'}
    residential={'APARTMENTS','LIVING QUARTERS','TOWNHOUSE','FARMHOUSE','LODGE','AIRPORT HOTEL'}
    civic={'POST OFFICE','CLINIC','TERMINAL','TICKET HALL','WAITING ROOM','FIRE STATION','OFFICES','ADMIN','RAIL OFFICES'}
    for attempt in range(2400):
        if len(game.buildings)>=count:break
        name=r.choice(theme['names'])
        archetype='commercial' if name in commercial else 'residential' if name in residential else 'civic' if name in civic else 'industrial' if game.theme in ('factory','airport','train_station') else 'rural'
        ranges={'commercial':((4,7),(3,6)),'residential':((3,6),(4,7)),'industrial':((5,8),(4,8)),'civic':((4,7),(4,7)),'rural':((3,6),(3,6))}
        wr,dr=ranges[archetype];width,depth=min(r.randint(*wr),n-5),min(r.randint(*dr),n-8)
        roadside=game.theme in ('urban','streets','train_station') and r.random()<.72
        if roadside and game.theme in ('urban','streets') and r.random()<.42:
            x=r.randint(1,n-width-2);y=r.choice([cross_y-2-depth,cross_y+2])
        elif roadside:
            x=r.choice([road_x-road_width//2-1-width,road_x+road_width//2+2]);y=r.randint(2,n-depth-6)
        else:x,y=r.randint(1,n-width-2),r.randint(2,n-depth-6)
        if x<1 or y<2 or x+width>=n-1 or y+depth>=n-5:continue
        clearance=r.choice([1,1,1,2,3])
        if x-clearance<0 or y-clearance<0 or x+width+clearance>n or y+depth+clearance>n:continue
        cells={(bx,by,0) for by in range(y-clearance,y+depth+clearance) for bx in range(x-clearance,x+width+clearance)}
        if cells&reserved or any(game.tiles[by][bx]=='road' for bx,by,_ in cells):continue
        if any(not(x+width+clearance<=b['x'] or b['x']+b['width']+clearance<=x or y+depth+clearance<=b['y'] or b['y']+b['depth']+clearance<=y) for b in game.buildings):continue
        i=len(game.buildings)
        levels=r.choice([2,2,3,4]) if archetype=='residential' and game.theme not in ('woods','farm') else r.choice([1,1,2]) if archetype in ('commercial','industrial','rural') else r.choice([1,2,2,3])
        if game.theme in ('woods','farm'):levels=r.choice([1,1,2])
        if i==0 and game.theme not in ('woods','farm'):levels=max(2,levels)
        distances={'north':abs(y-cross_y),'south':abs(y+depth-cross_y),'west':abs(x-road_x),'east':abs(x+width-road_x)}
        front=('east' if x<road_x else 'west') if roadside and game.theme=='train_station' else min(distances,key=distances.get) if roadside else r.choice(['north','south','west','east'])
        roof_choices={'commercial':['flat','flat','terrace'],'residential':['gable','flat','terrace'],'industrial':['sawtooth','flat','vented'],'civic':['flat','dome','gable'],'rural':['gable','gable','vented']}
        b=dict(id=f'b{i}',x=x,y=y,width=width,depth=depth,level=levels,name=name,archetype=archetype,front=front,roof=r.choice(roof_choices[archetype]),facade=r.choice(['brick','stucco','concrete','timber','metal']),color=r.choice(['#9d8d78','#a99d88','#8e9894','#9c725f','#7f8d92','#a69b72']),accent=r.choice(['#b9aa83','#6f8990','#9b614f','#75836a']))
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
                kind='door' if side==front and along==entrance and z==0 else 'window' if along%2==(i+z)%2 and (side==front or archetype in ('commercial','residential','civic')) else 'wall'
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
    streetscape=['bench','sign','lamp','trash','bush','flowerbed']
    natural=['tree_oak','tree_pine','tree_birch','bush','flowerbed']
    extras=natural if game.theme in ('farm','woods') else streetscape
    kinds+=r.choices(extras,k=max(8,round(14*(n/30)**2)))
    kinds+=r.choices(['car','bench'] if game.theme in ('urban','streets') else ['tree_oak','hay'] if game.theme in ('farm','woods') else ['truck','tank'],k=max(3,round(5*(n/30)**2)))
    if game.theme=='woods':kinds+=r.choices(['tree_oak','tree_pine','tree_birch','bush'],weights=[4,5,2,4],k=round(58*(n/30)**2))
    # Large signature assets get first choice of runway/rail positions.
    kinds.sort(key=lambda k:0 if k in ('aircraft','train') else 1)
    for kind in kinds:
        w,d=PROP_SIZE[kind]
        for _ in range(400):
            if kind in ('aircraft','train'):x=road_x-w//2
            elif kind in ('bench','sign','lamp','trash') and r.random()<.7:x=r.choice([max(1,road_x-road_width//2-2),min(n-w-1,road_x+road_width//2+1)])
            else:x=r.randrange(1,n-w)
            y=r.randrange(2,n-d-5)
            cells={(bx,by,0) for by in range(y,y+d) for bx in range(x,x+w)}
            buffer={(bx,by,0) for by in range(y-1,y+d+1) for bx in range(x-1,x+w+1)}
            if cells&reserved or buffer&game.blocked or any(game.heights[by][bx] for bx,by,_ in cells):continue
            game.props.append(dict(id=f'prop{len(game.props)}',kind=kind,x=x,y=y,width=w,depth=d,variant=r.randrange(4),color=r.choice(['#8eaca9','#aa7257','#d1be8a','#5c6975','#71805f','#a2a4a0'])))
            game.blocked.update(cells);break
    if game.theme=='farm':
        for x in range(n):
            for y in range(2,n-5):
                if (x,y,0) not in reserved|game.blocked and x%6<3 and game.tiles[y][x]=='grass':game.tiles[y][x]='crops'
    for y in range(2,n-4):
        for x in range(n):
            if (x,y,0) not in reserved|game.blocked and game.tiles[y][x]=='grass' and r.random()<.06:game.tiles[y][x]=r.choice(['low','high'])
    game.scenery=dict(theme=game.theme,road_x=road_x,cross_y=cross_y,**theme)
