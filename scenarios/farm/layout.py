"""A working farmyard with connected entrances and continuous surrounding fields."""
from collections import deque


def farm_plan(game):
    r,n=game.rng,game.size
    rx=n//2+r.choice([-1,0,1]);game.road_x=rx;game.cross_y=n//2
    edge=max(3,n//6);game.field_edge=edge
    game.tiles=[['road' if abs(x-rx)<=1 else 'crops' if x<edge or x>=n-edge else 'grass' for x in range(n)] for _ in range(n)]
    lots=[]
    for row in range(2):
        for side in range(2):
            w=r.randint(3,4) if n==24 else r.randint(4,5)
            d=r.randint(3,4) if n==24 else r.randint(4,5)
            x=rx-3-w if side==0 else rx+3
            y=3+row*(n//2-3)+r.randrange(2)
            lots.append(dict(x=x,y=y,width=w,depth=d,front='east' if side==0 else 'west',name=['FARMHOUSE','BARN','GRAIN STORE','MACHINE SHED'][row*2+side]))
    return lots


def farm_props(game):
    r,n=game.rng,game.size
    exterior={(x,y,0) for y in range(n) for x in range(n) if not game.heights[y][x]}
    network={p for p in exterior if game.tiles[p[1]][p[0]]=='road'}
    for door in game.portals:
        if door['kind']!='door' or door['side']=='interior':continue
        target=tuple(door['b']);queue=deque([target]);previous={target:None}
        while queue:
            p=queue.popleft()
            if p in network:break
            x,y,z=p
            for q in ((x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z)):
                if q in exterior and q not in previous:previous[q]=p;queue.append(q)
        while p is not None:
            network.add(p)
            if game.tiles[p[1]][p[0]]!='road':game.tiles[p[1]][p[0]]='farm_path'
            p=previous[p]
    protected=network|{tuple(p) for link in game.ladders+game.stairs for p in link}
    protected.update((x,y,0) for y in range(n-4,n) for x in range(n))
    # Keep all walkable ground connected as machinery and livestock are placed.
    specs=[('tractor',2,3,'FarmTractor'),('tractor',2,3,'FarmLoader'),('silo',2,2,None),('hay',2,2,None),('cow',1,2,'FarmCow'),('sheep',1,1,'FarmSheep'),('pig',1,1,'FarmPig'),('sheep',1,1,'FarmSheep')]
    # Scale the mixed orchard and undergrowth with the map, after essential props.
    specs += [('tree_oak' if i%2==0 else 'tree_birch',1,1,None) for i in range(n//3)]
    specs += [('bush',1,1,None) for _ in range(n//2)]
    for kind,w,d,model in specs:
        positions=sorted(exterior-protected);r.shuffle(positions)
        # Machinery stays near the yard; animals graze beside the barns.
        positions.sort(key=lambda p: game.tiles[p[1]][p[0]]!='grass')
        for x,y,z in positions:
            cells={(a,b,0) for b in range(y,y+d) for a in range(x,x+w)}
            if not cells<=exterior or cells&(protected|game.blocked):continue
            if any(game.tiles[b][a]=='crops' for a,b,_ in cells):continue
            remaining=exterior-game.blocked-cells;root=(game.road_x,n-1,0);seen={root};queue=[root]
            for a,b,_ in queue:
                for q in ((a+1,b,0),(a-1,b,0),(a,b+1,0),(a,b-1,0)):
                    if q in remaining and q not in seen:seen.add(q);queue.append(q)
            if seen!=remaining:continue
            prop=dict(id=f'prop{len(game.props)}',kind=kind,x=x,y=y,width=w,depth=d,variant=r.randrange(4),color='#bdab72')
            if model:
                prop['model']=model;prop['variant']=1 if model=='FarmLoader' else 0
            if kind.startswith('tree_') or kind=='bush':prop['woodland']=True
            game.props.append(prop);game.blocked.update(cells);break
