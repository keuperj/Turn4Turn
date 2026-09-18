"""Seeded woodland clearings, scattered cabins and connected forest footpaths."""
from collections import deque


def woodland_plan(game):
    r,n=game.rng,game.size
    game.tiles=[['forest']*n for _ in range(n)]
    game.meadows=[]
    for _ in range(r.randint(1,3)):
        cx,cy=r.randint(4,n-5),r.randint(4,n-7)
        rx,ry=r.uniform(2.5,4.5),r.uniform(2,4)
        game.meadows.append(dict(x=cx,y=cy,rx=rx,ry=ry))
        for y in range(n):
            for x in range(n):
                if ((x-cx)/rx)**2+((y-cy)/ry)**2<r.uniform(.85,1.15):game.tiles[y][x]='meadow'
    # One hut in each broad sector leaves woodland between the buildings.
    lots=[];rows=3 if n==40 else 2
    for row in range(rows):
        for col in range(2):
            width,depth=r.randint(3,4),r.randint(3,4)
            left,right=col*(n//2)+2,(col+1)*(n//2)-2
            top,bottom=2+row*((n-6)//rows),2+(row+1)*((n-6)//rows)-2
            lots.append(dict(x=r.randint(left,right-width),y=r.randint(top,max(top,bottom-depth)),width=width,depth=depth))
    r.shuffle(lots)
    return lots


def woodland_props(game):
    r,n=game.rng,game.size
    exterior={(x,y,0) for y in range(n) for x in range(n) if not game.heights[y][x]}
    root=(n//2,n-1,0);network={root}
    entrances=[tuple(p['b']) for p in game.portals if p['kind']=='door' and p['side']!='interior']
    # Grow one path network from deployment to every hut, then out the far edge.
    for target in entrances+[(n//2,0,0)]:
        queue=deque([target]);previous={target:None}
        while queue:
            p=queue.popleft()
            if p in network:break
            x,y,_=p;neighbors=[(x+1,y,0),(x-1,y,0),(x,y+1,0),(x,y-1,0)];r.shuffle(neighbors)
            for q in neighbors:
                if q in exterior and q not in previous:previous[q]=p;queue.append(q)
        while p is not None:
            network.add(p);game.tiles[p[1]][p[0]]='forest_path';p=previous[p]
    protected=set(network)
    protected.update(tuple(p) for link in game.ladders+game.stairs for p in link)
    protected.update((x,y,0) for y in range(n-3,n) for x in range(n))
    # Keep a clear apron around entrances and walls; crowns can overhang forest.
    protected.update((x,y,0) for b in game.buildings for y in range(b['y']-1,b['y']+b['depth']+1) for x in range(b['x']-1,b['x']+b['width']+1))
    candidates=sorted(exterior-protected);r.shuffle(candidates)
    for x,y,z in candidates:
        meadow=game.tiles[y][x]=='meadow'
        if r.random()>(.035 if meadow else .35):continue
        kind=r.choice(['bush','flowerbed']) if meadow else r.choices(['tree_oak','tree_pine','tree_birch','bush'],[4,5,3,3])[0]
        w=2 if kind=='flowerbed' else 1
        cells={(x+i,y,0) for i in range(w)}
        if not cells<=exterior or cells&(protected|game.blocked):continue
        remaining=exterior-game.blocked-cells;seen={root};queue=[root]
        for a,b,_ in queue:
            for q in ((a+1,b,0),(a-1,b,0),(a,b+1,0),(a,b-1,0)):
                if q in remaining and q not in seen:seen.add(q);queue.append(q)
        if seen!=remaining:continue
        prop=dict(id=f'prop{len(game.props)}',kind=kind,x=x,y=y,width=w,depth=1,woodland=True,variant=r.randrange(4),color=r.choice(['#45613b','#65824b','#75864d']))
        if kind.startswith('tree_'):prop['growth']=round(r.uniform(1.3,1.9),2)
        game.props.append(prop);game.blocked.update(cells)
