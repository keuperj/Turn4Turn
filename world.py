"""Seeded themes, enterable structures and scenery with matching collision data."""
import json
from pathlib import Path
from suburbs import street_plan, street_props
from woodlands import woodland_plan, woodland_props
from railway import railway_plan, railway_props

# One catalog drives server-side seeded selection and the browser's asset loader.
_TRANSPORT_CATALOG = json.loads((Path(__file__).parent / 'static/assets/models/transport/manifest.json').read_text())['models']
TRANSPORT_MODELS = {}
for _model in _TRANSPORT_CATALOG:
    TRANSPORT_MODELS.setdefault(_model['kind'], []).append(_model['id'])

THEMES = {
    'urban': dict(label='Urban district', names=['APARTMENTS', 'CORNER SHOP', 'POST OFFICE', 'CAFE', 'HARDWARE STORE', 'LIVING QUARTERS', 'RESTAURANT', 'CLINIC', 'BOOK SHOP', 'OFFICES'], ground='#858578', road='#43494b', wall='#b7afa0', props=['car', 'car', 'ambulance', 'bench', 'sign', 'lamp', 'bush']),
    'factory': dict(label='Factory complex', names=['ASSEMBLY', 'WAREHOUSE', 'CONTROL', 'WORKSHOP', 'CANTEEN', 'PARTS STORE', 'ADMIN', 'LOADING HALL'], ground='#797c72', road='#4b5050', wall='#909d9d', props=['container', 'tank', 'truck', 'pipes', 'sign', 'trash']),
    'train_station': dict(label='Train station', names=['TICKET HALL', 'SIGNAL BOX', 'FREIGHT DEPOT', 'CAFE', 'POST OFFICE', 'WAITING ROOM', 'RESTAURANT', 'RAIL OFFICES'], ground='#929083', road='#69665f', wall='#ae9b82', props=['train', 'container', 'bench', 'car', 'sign', 'lamp']),
    'airport': dict(label='Regional airport', names=['TERMINAL', 'HANGAR', 'CONTROL TOWER', 'CARGO', 'CAFE', 'AIRPORT HOTEL', 'FIRE STATION', 'MAINTENANCE'], ground='#939994', road='#616a6c', wall='#b7c4c2', props=['aircraft', 'truck', 'bus', 'car', 'tank', 'sign', 'lamp']),
    'streets': dict(label='Street crossing', names=['FAMILY HOME', 'GARDEN HOUSE', 'BUNGALOW', 'COTTAGE'], ground='#8c9c71', road='#42494b', wall='#b6a290', props=['car', 'truck', 'bus', 'bench', 'sign', 'lamp', 'trash', 'bush']),
    'woods': dict(label='Woodland camp', names=['RANGER CABIN', 'LODGE', 'LOOKOUT', 'TOOL SHED', 'FIELD OFFICE', 'MESS HALL'], ground='#697451', road='#84765e', wall='#80644a', props=['tree_oak', 'tree_pine', 'tree_birch', 'bush', 'bench', 'truck']),
    'farm': dict(label='Farmstead', names=['FARMHOUSE', 'BARN', 'GRAIN STORE', 'MACHINE SHED', 'FARM SHOP', 'LIVING QUARTERS', 'PACKING HOUSE'], ground='#a69768', road='#83745c', wall='#b08269', props=['tractor', 'silo', 'hay', 'truck', 'tree_oak', 'bush', 'flowerbed']),
}

def edge_key(a, b):
    """Return a canonical key for an undirected edge between two tiles."""
    return tuple(sorted((tuple(a), tuple(b))))


# Footprints use the same approximate one-metre scale as the 1.7m fighters.
PROP_SIZE={'car':(2,5),'truck':(2,6),'bus':(3,7),'ambulance':(2,5),'tractor':(2,3),'aircraft':(10,10),
           'train':(3,10),'container':(3,6),'tank':(2,2),'silo':(2,2),
           'pipes':(2,3),'bench':(2,1),'hay':(2,2),'tree':(1,1),
           'tree_oak':(1,1),'tree_pine':(1,1),'tree_birch':(1,1),'bush':(1,1),
           'flowerbed':(2,1),'sign':(1,1),'lamp':(1,1),'trash':(1,1),'traffic_light':(1,1),'cafe_table':(1,1),'ticket_counter':(2,1)}


def urban_plan(game):
    """Lay out compact blocks, continuous sidewalks and one seeded pocket park."""
    r,n=game.rng,game.size
    rx=n//2+r.choice([-1,0,1]);cy=n//2-2+r.choice([-1,0,1])
    game.road_x,game.cross_y=rx,cy
    game.tiles=[['road' if abs(x-rx)<=2 or abs(y-cy)<=2 else
                 'sidewalk' if abs(x-rx)<=4 or abs(y-cy)<=4 else 'plaza'
                 for x in range(n)] for y in range(n)]

    def divide(start,end):
        length=end-start
        if length<3:return []
        maximum=8 if n==40 else 6
        if length<=maximum:return [(start,length)]
        first=r.randint(4 if n==40 else 3,min(maximum,length-4))
        return [(start,first)]+divide(start+first+1,end)

    lots=[]
    for left,right in [(1,rx-4),(rx+5,n-1)]:
        for top,bottom in [(1,cy-4),(cy+5,n-4)]:
            for x,w in divide(left,right):
                for y,d in divide(top,bottom):lots.append(dict(x=x,y=y,width=w,depth=d))
    # Pick among the more spacious lots so paths and furniture fit even at 24x24.
    park_lots=[lot for lot in lots if lot['width']>=4 and lot['depth']>=4] or [lot for lot in lots if lot['width']>=4]
    largest=max(lot['width']*lot['depth'] for lot in park_lots)
    park=r.choice([lot for lot in park_lots if lot['width']*lot['depth']>=largest*.8])
    lots.remove(park)
    px,py,w,d=(park[k] for k in ('x','y','width','depth'))
    for y in range(py,py+d):
        for x in range(px,px+w):game.tiles[y][x]='park_path' if x==px+w//2 or y==py+d//2 else 'park'
    r.shuffle(lots)
    lots.sort(key=lambda lot: min(abs(lot['x']+lot['width']-rx),abs(lot['x']-rx),abs(lot['y']+lot['depth']-cy),abs(lot['y']-cy)))
    return lots,park


def urban_props(game,park):
    """Place physical furniture without blocking doors, crossings or walking routes."""
    r,n=game.rng,game.size
    rx,cy=game.road_x,game.cross_y
    protected={tuple(p['b']) for p in game.portals if p['kind']=='door' and p['side']!='interior'}
    protected.update(tuple(p) for link in game.ladders+game.stairs for p in link)
    # Keep the junction, crossings, and deployment promenade clear.
    protected.update((x,y,0) for y in range(n) for x in range(n)
                     if y>=n-4 or (abs(x-rx)<=4 and abs(y-cy)<=4))

    exterior={(x,y,0) for y in range(n) for x in range(n) if not game.heights[y][x]}

    def place(kind,positions,allowed,building=None,quarter_turn=0):
        r.shuffle(positions)
        w,d=PROP_SIZE[kind]
        if quarter_turn:w,d=d,w
        for x,y in positions:
            cells={(a,b,0) for b in range(y,y+d) for a in range(x,x+w)}
            if any(not(0<=a<n and 0<=b<n) or game.tiles[b][a] not in allowed for a,b,_ in cells):continue
            if cells&(game.blocked|protected):continue
            # Leave a gap between parked vehicles for access from the curb.
            if kind in ('car','ambulance') and any((a+dx,b+dy,0) in game.blocked for a,b,_ in cells for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]):continue
            # Reject any placement that disconnects a pavement, entrance or park path.
            remaining=exterior-game.blocked-cells
            seen={(0,n-1,0)};queue=list(seen)
            for a,b,_ in queue:
                for q in ((a+1,b,0),(a-1,b,0),(a,b+1,0),(a,b-1,0)):
                    if q in remaining and q not in seen:seen.add(q);queue.append(q)
            if seen!=remaining:continue
            models=TRANSPORT_MODELS.get(kind,[]);variant=r.randrange(len(models) if models else 4)
            prop=dict(id=f'prop{len(game.props)}',kind=kind,x=x,y=y,width=w,depth=d,variant=variant,
                      color=r.choice(['#81999e','#a56850','#cab482','#495d70','#71805f']))
            if kind=='bench':prop['variant']=r.choice([0,2])
            if kind=='sign':prop['sign']='STOP' if sum(p['kind']=='sign' for p in game.props)%2==0 else 'P'
            if building:prop['building']=building
            if quarter_turn:prop['quarter_turn']=quarter_turn
            if models:prop['model']=models[variant]
            game.props.append(prop);game.blocked.update(cells)
            return True
        return False

    # Cars stay in curb lanes; the central road tile and intersection remain open.
    for lane in [rx-2,rx+1]:
        for start,end in [(1,cy-4),(cy+5,n-4)]:
            positions=[(lane,y) for y in range(start,end-4)]
            for _ in range(max(1,(end-start)//7)):
                kind=r.choice(['car','car','ambulance']) if any(p['kind']=='car' for p in game.props) else 'car'
                place(kind,positions[:],{'road'})
    for lane in [cy-2,cy+1]:
        for start,end in [(1,rx-4),(rx+5,n-1)]:
            place('car',[(x,lane) for x in range(start,end-4)],{'road'},quarter_turn=1)
    px,py,w,d=(park[k] for k in ('x','y','width','depth'))
    corners=[(px,py),(px+w-1,py+d-1),(px+w-1,py),(px,py+d-1)]
    place('bench',[(x,y) for y in range(py,py+d) for x in range(px,px+w-1)],{'park'})
    for kind in ['tree_oak','tree_birch','bush']:
        place(kind,corners[:],{'park'})
    # Tables sit against the cafe frontage, leaving the outer sidewalk lane free.
    for b in game.buildings:
        if b['name']!='CAFE':continue
        x,y,w,d=(b[k] for k in ('x','y','width','depth'))
        positions=([(a,y-1 if b['front']=='north' else y+d) for a in range(x,x+w)]
                   if b['front'] in ('north','south') else
                   [(x-1 if b['front']=='west' else x+w,a) for a in range(y,y+d)])
        # An alley only one tile wide is a through-route, not a terrace.
        positions=[(a,b) for a,b in positions if game.tiles[b][a]=='sidewalk' or
                   (0<a<n-1 and 0<b<n-1 and all(game.heights[b+dy][a+dx]==0 for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]))]
        for _ in range(2):place('cafe_table',positions[:],{'sidewalk','plaza'},b['id'])
    # Furniture is set back from the curb: continuous inner walking lanes remain.
    pavement=[(x,y) for y in range(1,n-4) for x in range(1,n-1)
              if (abs(x-rx)==3 and abs(y-cy)>4) or (abs(y-cy)==3 and abs(x-rx)>4)]
    for kind in ['traffic_light','traffic_light','sign','sign','lamp','lamp','trash','trash','bench','bench']:
        positions=pavement[:]
        if kind=='traffic_light':
            near=[(x,y) for x,y in pavement if abs(x-rx)<=5 and abs(y-cy)<=5]
            if place(kind,near,{'sidewalk'}):continue
        place(kind,positions,{'sidewalk'})


def generate(game):
    """Generate a deterministic, connected battlefield for a theme and size."""
    r,n,theme=game.rng,game.size,THEMES[game.theme]
    road_x=n//2+r.choice([-2,0,2]);cross_y=r.randrange(9,n-9)
    road_width=11 if game.theme=='airport' else 5
    game.road_x,game.cross_y=road_x,cross_y
    game.tiles=[['road' if abs(x-road_x)<=road_width//2 else 'grass' for x in range(n)] for y in range(n)]
    if game.theme in ('urban','streets'):
        for y in range(cross_y-1,cross_y+2):game.tiles[y]=['road']*n
    urban_lots,park=urban_plan(game) if game.theme=='urban' else (None,None)
    street_lots=street_plan(game) if game.theme=='streets' else None
    woodland_lots=woodland_plan(game) if game.theme=='woods' else None
    railway_lots=railway_plan(game) if game.theme=='train_station' else None
    planned_lots=urban_lots if urban_lots is not None else street_lots if street_lots is not None else woodland_lots if woodland_lots is not None else railway_lots
    if planned_lots is not None:road_x,cross_y=game.road_x,game.cross_y
    game.heights=[[0]*n for _ in range(n)]
    game.surfaces={(x,y,0) for y in range(n) for x in range(n)}
    game.buildings,game.ladders,game.stairs,game.portals,game.props=[],[],[],[],[]
    game.walls,game.blocked={},set()
    reserved={(x,y,0) for y in range(n-4,n) for x in range(n)}
    count={'urban':9,'factory':7,'train_station':7,'airport':6,'streets':8,'woods':5,'farm':6}[game.theme]
    count=len(planned_lots) if planned_lots is not None else max(4,round(count*(n/30)**2))
    commercial={'CORNER SHOP','CAFE','HARDWARE STORE','RESTAURANT','BOOK SHOP','DINER','MARKET','PHARMACY','PARTS STORE','CANTEEN'}
    residential={'APARTMENTS','LIVING QUARTERS','TOWNHOUSE','FARMHOUSE','LODGE','AIRPORT HOTEL'}
    civic={'POST OFFICE','CLINIC','TERMINAL','TICKET HALL','WAITING ROOM','FIRE STATION','OFFICES','ADMIN','RAIL OFFICES'}
    for attempt in range(2400):
        if len(game.buildings)>=count:break
        name=(['CAFE','CORNER SHOP'][len(game.buildings)] if urban_lots is not None and len(game.buildings)<2 else r.choice(theme['names']))
        archetype='commercial' if name in commercial else 'residential' if name in residential else 'civic' if name in civic else 'industrial' if game.theme in ('factory','airport','train_station') else 'rural'
        ranges={'commercial':((4,7),(3,6)),'residential':((3,6),(4,7)),'industrial':((5,8),(4,8)),'civic':((4,7),(4,7)),'rural':((3,6),(3,6))}
        wr,dr=ranges[archetype];width,depth=min(r.randint(*wr),n-5),min(r.randint(*dr),n-8)
        roadside=game.theme in ('urban','streets','train_station') and r.random()<.72
        if roadside and game.theme in ('urban','streets') and r.random()<.42:
            x=r.randint(1,n-width-2);y=r.choice([cross_y-2-depth,cross_y+2])
        elif roadside:
            x=r.choice([road_x-road_width//2-1-width,road_x+road_width//2+2]);y=r.randint(2,n-depth-6)
        else:x,y=r.randint(1,n-width-2),r.randint(2,n-depth-6)
        if planned_lots is not None:
            lot=planned_lots[len(game.buildings)];x,y,width,depth=(lot[k] for k in ('x','y','width','depth'))
            roadside=True;clearance=0
            cells={(bx,by,0) for by in range(y,y+depth) for bx in range(x,x+width)}
        else:
            if x<1 or y<2 or x+width>=n-1 or y+depth>=n-5:continue
            clearance=r.choice([1,1,1,2,3])
            if x-clearance<0 or y-clearance<0 or x+width+clearance>n or y+depth+clearance>n:continue
            cells={(bx,by,0) for by in range(y-clearance,y+depth+clearance) for bx in range(x-clearance,x+width+clearance)}
            if cells&reserved or any(game.tiles[by][bx]=='road' for bx,by,_ in cells):continue
            if any(not(x+width+clearance<=b['x'] or b['x']+b['width']+clearance<=x or y+depth+clearance<=b['y'] or b['y']+b['depth']+clearance<=y) for b in game.buildings):continue
        i=len(game.buildings)
        levels=r.choice([2,2,3,4]) if archetype=='residential' and game.theme not in ('woods','farm') else r.choice([1,1,2]) if archetype in ('commercial','industrial','rural') else r.choice([1,2,2,3])
        if game.theme in ('woods','farm'):levels=r.choice([1,1,2])
        if woodland_lots is not None:levels=1
        if urban_lots is not None:levels=r.choice([3,4,4,5,6])
        if i==0 and game.theme not in ('woods','farm'):levels=max(2,levels)
        if street_lots is not None:levels=2 if i==0 else r.choice([1,1,2])
        if railway_lots is not None:levels=1 if lot['station'] else r.choice([1,2])
        distances={'north':abs(y-cross_y),'south':abs(y+depth-cross_y),'west':abs(x-road_x),'east':abs(x+width-road_x)}
        front=('east' if x<road_x else 'west') if roadside and game.theme=='train_station' else min(distances,key=distances.get) if roadside else r.choice(['north','south','west','east'])
        roof_choices={'commercial':['flat','flat','terrace'],'residential':['gable','flat','terrace'],'industrial':['sawtooth','flat','vented'],'civic':['flat','dome','gable'],'rural':['gable','gable','vented']}
        b=dict(id=f'b{i}',x=x,y=y,width=width,depth=depth,level=levels,name=name,archetype=archetype,front=front,roof=r.choice(roof_choices[archetype]),facade=r.choice(['brick','stucco','concrete','timber','metal']),color=r.choice(['#9d8d78','#a99d88','#8e9894','#9c725f','#7f8d92','#a69b72']),accent=r.choice(['#b9aa83','#6f8990','#9b614f','#75836a']))
        if urban_lots is not None:
            b['roof']=r.choice(['flat','terrace','vented'])
            b['facade']=r.choice(['brick','stucco','concrete','metal'])
        if street_lots is not None:
            b.update(archetype='residential',front=lot['front'],roof='gable',garden=lot['garden'],
                     facade=r.choice(['brick','stucco','timber']),color=r.choice(['#c2b59d','#bac5bc','#cfb49d','#a9bac4']),accent=r.choice(['#815e4c','#64736c','#7c7b7c']))
            front=b['front'];archetype='residential'
        if woodland_lots is not None:
            b.update(archetype='rural',roof='gable',facade='timber',color=r.choice(['#806044','#96734e','#70563e']),accent='#625845')
        if railway_lots is not None:
            b.update(station=lot['station'],name='CENTRAL STATION' if lot['station'] else r.choice(['TOWNHOUSE','CORNER SHOP','APARTMENTS']),archetype='civic' if lot['station'] else 'residential',front='east' if x<road_x else 'west',roof='gable',facade='brick',color=r.choice(['#a58970','#b6aa90','#9e8575']))
            front=b['front'];archetype=b['archetype']
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
                double=b.get('station') and side in ('east','west') and z==0 and along in (entrance,entrance+1)
                kind='door' if double or (side==front and along==entrance and z==0) else 'window' if along%2==(i+z)%2 and (side==front or archetype in ('commercial','residential','civic')) else 'wall'
                portal=dict(id=f'p{len(game.portals)}',a=a,b=other,kind=kind,open=False,building=b['id'],side=side)
                if double:portal.update(door_group=f'{b["id"]}:{side}',door_leaf=along-entrance)
                game.walls[edge_key(a,other)]=portal
                if kind!='wall':game.portals.append(portal)
        # Connected two-room floors, with an optional third room in larger buildings.
        for z in range(levels):
            if b.get('station'):continue  # An uninterrupted public waiting hall.
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
        if i%2 or street_lots is not None or railway_lots is not None:
            # Interior ladders connect floors (or a single-storey loft/roof).
            game.ladders.extend(((x+width-1,y+depth-1,z),(x+width-1,y+depth-1,z+1)) for z in range(levels))
        else:
            game.ladders.append(((x+width,y+depth-1,0),(x+width-1,y+depth-1,levels)))
        for z in range(levels):game.stairs.append(((x+width-1,y,z),(x+width-1,y,z+1)))
        reserved.update(cells)
    if urban_lots is not None:
        urban_props(game,park)
        game.scenery=dict(theme=game.theme,road_x=road_x,cross_y=cross_y,road_width=5,sidewalk_width=2,park=park,**theme)
        return
    if street_lots is not None:
        street_props(game,PROP_SIZE,TRANSPORT_MODELS)
        game.scenery=dict(theme=game.theme,road_x=road_x,cross_y=cross_y,road_width=12,lanes=4,sidewalk_width=2,**theme)
        return
    if woodland_lots is not None:
        woodland_props(game)
        game.scenery=dict(theme=game.theme,road_x=road_x,cross_y=cross_y,road_width=1,meadows=game.meadows,**theme)
        return
    if railway_lots is not None:
        railway_props(game,PROP_SIZE,TRANSPORT_MODELS)
        game.scenery=dict(theme=game.theme,road_x=road_x,cross_y=cross_y,tracks=game.track_centers,road_width=2,**theme)
        return
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
            models=TRANSPORT_MODELS.get(kind,[])
            variant=r.randrange(len(models) if models else 4)
            prop=dict(id=f'prop{len(game.props)}',kind=kind,x=x,y=y,width=w,depth=d,variant=variant,color=r.choice(['#8eaca9','#aa7257','#d1be8a','#5c6975','#71805f','#a2a4a0']))
            if models:prop['model']=models[variant]
            game.props.append(prop)
            game.blocked.update(cells);break
    if game.theme=='farm':
        for x in range(n):
            for y in range(2,n-5):
                if (x,y,0) not in reserved|game.blocked and x%6<3 and game.tiles[y][x]=='grass':game.tiles[y][x]='crops'
    for y in range(2,n-4):
        for x in range(n):
            if (x,y,0) not in reserved|game.blocked and game.tiles[y][x]=='grass' and r.random()<.06:game.tiles[y][x]=r.choice(['low','high'])
    game.scenery=dict(theme=game.theme,road_x=road_x,cross_y=cross_y,**theme)
