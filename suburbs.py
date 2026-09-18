"""Seeded four-lane suburban intersection, homes, gardens and stopped traffic."""


def street_plan(game):
    """Reserve four travel lanes, two-tile sidewalks and detached housing lots."""
    r,n=game.rng,game.size
    # Even road width keeps both sides equally usable on the smallest map.
    center=(n-1)/2;low=n//2-6;high=low+12
    game.road_x=game.cross_y=center
    game.tiles=[['road' if low<=x<high or low<=y<high else
                 'sidewalk' if low-2<=x<high+2 or low-2<=y<high+2 else 'lawn'
                 for x in range(n)] for y in range(n)]
    lots=[]
    for left,right in [(0,low-2),(high+2,n)]:
        for top,bottom in [(0,low-2),(high+2,n)]:
            vertical=r.choice([True,False])
            front=('east' if left==0 else 'west') if vertical else ('south' if top==0 else 'north')
            start,end=(top,bottom) if vertical else (left,right)
            cuts=[start,(start+end)//2,end] if end-start>=11 else [start,end]
            for a,b in zip(cuts,cuts[1:]):
                lx,ly,lw,ld=(left,a,right-left,b-a) if vertical else (a,top,b-a,bottom-top)
                width=r.randint(3,min(6,lw-(1 if vertical else 0)))
                depth=r.randint(3,min(6,ld-(0 if vertical else 1)))
                x=lx if front=='east' else lx+lw-width if front=='west' else lx+r.randrange(lw-width+1)
                y=ly if front=='south' else ly+ld-depth if front=='north' else ly+r.randrange(ld-depth+1)
                lot=dict(x=x,y=y,width=width,depth=depth,front=front,
                         garden=dict(x=lx,y=ly,width=lw,depth=ld))
                lots.append(lot)
                # A planted border beside each sidewalk makes the yard boundary explicit.
                for gy in range(ly,ly+ld):
                    for gx in range(lx,lx+lw):
                        if (vertical and gx==(lx+lw-1 if front=='east' else lx)) or (not vertical and gy==(ly+ld-1 if front=='south' else ly)):
                            game.tiles[gy][gx]='garden'
    r.shuffle(lots)
    return lots


def street_props(game,sizes,models):
    """Place lane-aligned traffic and signals without disconnecting walkable ground."""
    r,n=game.rng,game.size
    low=n//2-6;high=low+12
    protected={(x,y,0) for y in range(n-3,n) for x in range(n)}
    protected.update(tuple(p) for link in game.stairs+game.ladders for p in link)
    # Four zebra crossings occupy the mouths of the intersection, never car slots.
    crossing_rows={low,low+1,high-2,high-1}
    protected.update((x,y,0) for y in range(n) for x in range(n)
                     if (low<=x<high and y in crossing_rows) or (low<=y<high and x in crossing_rows))
    for door in game.portals:
        if door['kind']!='door' or door['side']=='interior' or door['a'][2]:continue
        x,y,_=door['b'];dx,dy={'east':(1,0),'west':(-1,0),'north':(0,-1),'south':(0,1)}[door['side']]
        while 0<=x<n and 0<=y<n and game.tiles[y][x] not in ('road','sidewalk'):
            game.tiles[y][x]='garden_path';protected.add((x,y,0));x+=dx;y+=dy
        if 0<=x<n and 0<=y<n:protected.add((x,y,0))
    exterior={(x,y,0) for y in range(n) for x in range(n) if not game.heights[y][x]}

    def place(kind,candidates,allowed,turn=0):
        r.shuffle(candidates);w,d=sizes[kind]
        if turn%2:w,d=d,w
        for x,y in candidates:
            cells={(a,b,0) for b in range(y,y+d) for a in range(x,x+w)}
            if cells&(protected|game.blocked):continue
            if any(not(0<=a<n and 0<=b<n) or game.tiles[b][a] not in allowed or game.heights[b][a] for a,b,_ in cells):continue
            remaining=exterior-game.blocked-cells;seen={(n//2,n-1,0)};queue=list(seen)
            for a,b,_ in queue:
                for q in ((a+1,b,0),(a-1,b,0),(a,b+1,0),(a,b-1,0)):
                    if q in remaining and q not in seen:seen.add(q);queue.append(q)
            if seen!=remaining:continue
            variants=models.get(kind,[]);variant=r.randrange(len(variants) if variants else 4)
            prop=dict(id=f'prop{len(game.props)}',kind=kind,x=x,y=y,width=w,depth=d,variant=variant,
                      color=r.choice(['#6587a1','#a85b49','#d5caa7','#647966','#bec4bd']))
            if variants:prop['model']=variants[variant]
            if kind=='bench':prop['variant']=r.choice([0,2])
            if kind=='sign':prop['sign']='P'
            if turn:prop['quarter_turn']=turn
            game.props.append(prop);game.blocked.update(cells);return True
        return False

    # Independently populate each arm: empty lanes and variable queue lengths
    # break up the repeated four-car rows, even on short approaches.
    for horizontal in (False,True):
        for start,end in ((0,low),(high,n if horizontal else n-3)):
            for lane in r.sample(range(4),r.randint(2,3)):
                offset=lane*3
                turn=(1 if lane<2 else 3) if horizontal else (0 if lane<2 else 2)
                for _ in range(r.randint(1,max(1,(end-start)//6))):
                    positions=[(a,low+offset) if horizontal else (low+offset,a) for a in range(start,end-4)]
                    # Keep the suburb's occasional bus, alongside the dominant car traffic.
                    kind='bus' if n>=30 and horizontal and start==0 and not any(p['kind']=='bus' for p in game.props) else 'car'
                    if kind=='bus':positions=[(a,low+offset) for a in range(start,end-6)]
                    if not place(kind,positions,{'road'},turn) and kind=='bus':
                        place('car',[(a,low+offset) for a in range(start,end-4)],{'road'},turn)
    for lane in (0,9):
        place('car',[(low+lane,y) for y in range(low+2,high-6)],{'road'},0 if lane==0 else 2)
    for x,y,turn in [(low-1,low-1,0),(high,low-1,1),(high,high,2),(low-1,high,3)]:
        positions=[(x,y)]+[(x+dx,y+dy) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]]
        place('traffic_light',positions,{'sidewalk'},turn)
    sidewalk=[(x,y) for y in range(n-3) for x in range(n) if game.tiles[y][x]=='sidewalk']
    for kind in ('lamp','lamp','sign','trash','bench'):
        place(kind,sidewalk[:],{'sidewalk'})
    for b in game.buildings:
        yard=b['garden'];positions=[(x,y) for y in range(yard['y'],yard['y']+yard['depth']) for x in range(yard['x'],yard['x']+yard['width'])]
        for kind in ('bush','flowerbed'):
            place(kind,positions[:],{'garden','lawn'})
        if n>24:place(r.choice(['tree_oak','tree_birch']),positions[:],{'lawn'})
