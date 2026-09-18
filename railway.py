"""Double-track city station with connected platforms and a public waiting hall."""


def railway_plan(game):
    r,n=game.rng,game.size
    c=n//2-(1 if n>=30 else 0)
    game.road_x=c;game.cross_y=n-3;game.track_centers=[c,c+4]
    game.tiles=[['railway' if c-1<=x<=c+5 else 'platform' if c-4<=x<=c-2 or c+6<=x<=c+8 else 'road' if x<2 or x>=n-2 else 'sidewalk' if x==2 or x==n-3 else 'plaza' for x in range(n)] for _ in range(n)]
    # Designated track crossings keep both platforms accessible past stopped trains.
    for y in (1,n-3):
        for x in range(c-4,c+9):game.tiles[y][x]='rail_crossing'
    width=min(9,c-7)
    station=dict(x=c-4-width,y=3,width=width,depth=min(18,n//2),station=True)
    lots=[station]
    y=station['y']+station['depth']+2
    if n-4-y>=3:
        lots.append(dict(x=3,y=y,width=min(5,c-7),depth=min(5,n-4-y),station=False))
    left,right=c+10,n-3
    if right-left>=3:
        for y in range(3,n-8,9):
            lots.append(dict(x=left,y=y,width=min(6,right-left),depth=r.randint(4,6),station=False))
    return lots


def railway_props(game,sizes,models):
    r,n=game.rng,game.size;c=game.track_centers[0]
    protected={tuple(p['b']) for p in game.portals if p['kind']=='door' and p['side']!='interior'}
    protected.update(tuple(p['a']) for p in game.portals if p['kind']=='door')
    protected.update(tuple(p) for link in game.ladders+game.stairs for p in link)
    protected.update((x,y,0) for y in range(n) for x in range(n) if y>=n-3 or game.tiles[y][x]=='rail_crossing')
    ground={(x,y,0) for y in range(n) for x in range(n)}
    def place(kind,positions,allowed,turn=0):
        r.shuffle(positions);w,d=sizes[kind]
        if turn%2:w,d=d,w
        for x,y in positions:
            cells={(a,b,0) for b in range(y,y+d) for a in range(x,x+w)}
            if not cells<=ground or cells&(protected|game.blocked):continue
            if any(game.tiles[b][a] not in allowed for a,b,_ in cells):continue
            # Furniture cannot isolate any ground tile or entrance.
            remaining=ground-game.blocked-cells;seen={(n//2,n-1,0)};queue=list(seen)
            for a,b,_ in queue:
                for q in ((a+1,b,0),(a-1,b,0),(a,b+1,0),(a,b-1,0)):
                    wall=game.walls.get(tuple(sorted(((a,b,0),q))))
                    if q in remaining and q not in seen and (not wall or wall['kind']=='door'):seen.add(q);queue.append(q)
            if seen!=remaining:continue
            variants=models.get(kind,[]);variant=r.randrange(len(variants) if variants else 4)
            prop=dict(id=f'prop{len(game.props)}',kind=kind,x=x,y=y,width=w,depth=d,variant=variant,color=r.choice(['#4e737d','#a55343','#c7bfa5','#648272']))
            if variants:prop['model']=variants[variant]
            if allowed=={'floor'}:prop['interior']=game.buildings[0]['id']
            if kind=='bench':prop['variant']=r.choice([0,2])
            if kind.startswith('tree_'):prop.update(woodland=True,growth=1.0)
            if turn:prop['quarter_turn']=turn
            game.props.append(prop);game.blocked.update(cells);return True
        return False
    # Independent offsets and queue lengths on the two tracks, never over crossings.
    for track in game.track_centers:
        for _ in range(r.randint(1,2) if n>=30 else 1):
            place('train',[(track-1,y) for y in range(2,n-12)],{'railway'},r.choice([0,2]))
    for edge in (c-4,c+8):
        for y in range(4,n-5,6):
            place('bench',[(edge,y)],{'platform'},1 if edge<c else 3)
            place('trash',[(edge,y+2)],{'platform'})
            place('lamp',[(edge,y+3)],{'platform'})
    station=game.buildings[0]
    for y in range(station['y']+2,station['y']+station['depth']-2,4):
        place('bench',[(station['x']+1,y)],{'floor'})
    for x in (0,n-2):place('car',[(x,y) for y in range(3,n-8)],{'road'})
    # Hall fittings have real collision footprints, clear of both entrance leaves.
    x,y,w,d=(station[k] for k in ('x','y','width','depth'))
    place('ticket_counter',[(x+w-3,y+d-2)],{'floor'})
    place('cafe_table',[(x+w-2,y+2)],{'floor'})
    place('trash',[(x,y+d-2)],{'floor'})
    # Street and forecourt planting stays off the platforms and railway corridor.
    planting=[(x,y) for y in range(2,n-4) for x in range(3,n-3) if game.tiles[y][x]=='plaza' and not any(abs(x-p[0])+abs(y-p[1])<=2 for p in protected)]
    for i in range(max(4,n//4)):
        place('tree_birch' if i%2 else 'tree_oak',planting[:],{'plaza'})
