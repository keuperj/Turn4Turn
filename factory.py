"""Open-sided factory hall with four playable levels and real machine footprints."""


def factory_generate(game,theme,models):
    """Create connected mezzanine platforms, outer walls and seeded machinery."""
    r,n=game.rng,game.size
    band=n//4+r.choice([-1,0,1]);mid=(n-band)//2+r.randint(-2,2)
    game.road_x=n//2;game.cross_y=n//2
    game.tiles=[['floor']*n for _ in range(n)]
    game.heights=[[0]*n for _ in range(n)]
    game.surfaces={(x,y,0) for y in range(n) for x in range(n)}
    game.buildings=[];game.walls={};game.portals=[];game.props=[];game.blocked=set();game.stairs=[];game.ladders=[]
    cx,cy=band+2,band+3;cw,cd=max(6,n//3),max(6,n//3-1)
    zones=[(0,0,n,band,2,'ASSEMBLY GALLERY'),(0,band,band,mid,1,'MACHINE SHOP'),
           (0,band+mid,band,n-band-mid,1,'STORES MEZZANINE'),
           (band,band,n-band,cy-band,0,'NORTH PRODUCTION AISLE'),
           (band,cy,cx-band,cd,0,'WEST PRODUCTION AISLE'),
           (cx,cy,cw,cd,3,'CENTRAL PRODUCTION STACK'),
           (cx+cw,cy,n-cx-cw,cd,0,'EAST PRODUCTION HALL'),
           (band,cy+cd,n-band,n-cy-cd,0,'DISPATCH HALL')]
    for i,(x,y,w,d,top,name) in enumerate(zones):
        b=dict(id=f'b{i}',x=x,y=y,width=w,depth=d,level=top,name=name,factory=True,archetype='industrial',front='south',roof='open',facade='metal',color='#83949a',accent='#d0ad4c')
        game.buildings.append(b)
        for by in range(y,y+d):
            for bx in range(x,x+w):
                game.heights[by][bx]=top
                game.surfaces.update((bx,by,z) for z in range(1,top+1))
        # Only the back and left outer walls exist; front and right are open.
        for z in range(top+1):
            edges=[]
            if y==0:edges.extend(((a,0,z),(a,-1,z),'north') for a in range(x,x+w))
            if x==0:edges.extend(((0,a,z),(-1,a,z),'west') for a in range(y,y+d))
            for a,c,side in edges:
                wall=dict(id=f'factory-wall-{len(game.walls)}',a=a,b=c,kind='wall',open=False,building=b['id'],side=side)
                game.walls[tuple(sorted((a,c)))]=wall
    # Long flights have distinct lower/upper landings and real openings above them.
    game.stairs=[((band-2,n-6,0),(band-2,n-9,1)),
                 ((n-5,band-2,0),(n-8,band-2,1)),
                 ((2,2,1),(5,2,2)),
                 ((n-8,band-3,1),(n-5,band-3,2)),
                 ((cx+1,cy+1,0),(cx+4,cy+1,1)),
                 ((cx+4,cy+2,1),(cx+1,cy+2,2)),
                 ((cx+1,cy+3,2),(cx+4,cy+3,3))]
    protected=set()
    for a,d in game.stairs:
        dx=(d[0]-a[0])//3;dy=(d[1]-a[1])//3
        for i in range(4):
            x,y=a[0]+dx*i,a[1]+dy*i
            for z in (a[2],d[2]):
                protected.add((x,y,z))
            if i<3:
                hole=(x,y,d[2]);game.surfaces.discard(hole)
                owner=next(b for b in game.buildings if b['x']<=x<b['x']+b['width'] and b['y']<=y<b['y']+b['depth'])
                owner.setdefault('floor_holes',[]).append(hole)
    protected.update((x,y,0) for y in range(n-4,n) for x in range(n))
    sizes={'factory_machine':(3,2),'factory_rack':(3,1),'factory_robot':(2,2),'factory_conveyor':(3,2),'factory_forklift':(2,3)}
    # Each disconnected platform has its own stairs. Keep every platform connected
    # internally while filling rows; the protected landings join the full 3D graph.
    components={};unseen=set(game.surfaces)
    while unseen:
        root=min(unseen);region={root};queue=[root];unseen.remove(root)
        for x,y,z in queue:
            for q in ((x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z)):
                if q in unseen:unseen.remove(q);region.add(q);queue.append(q)
        for cell in region:components[cell]=region
    variants={kind:0 for kind in sizes}
    pattern=['factory_machine','factory_conveyor','factory_robot','factory_machine','factory_rack','factory_machine','factory_forklift','factory_machine']
    def place(kind,x,y,z,owner,turn):
        w,d=sizes[kind]
        if turn%2:w,d=d,w
        cells={(a,b,z) for b in range(y,y+d) for a in range(x,x+w)}
        if not cells<=game.surfaces or cells&(game.blocked|protected):return False
        if x+w>owner['x']+owner['width'] or y+d>owner['y']+owner['depth']:return False
        remaining=components[(x,y,z)]-game.blocked-cells
        root=min(remaining);seen={root};queue=[root]
        for a,b,c in queue:
            for q in ((a+1,b,c),(a-1,b,c),(a,b+1,c),(a,b-1,c)):
                if q in remaining and q not in seen:seen.add(q);queue.append(q)
        if seen!=remaining:return False
        variant=variants[kind]%len(models[kind]);variants[kind]+=1
        prop=dict(id=f'prop{len(game.props)}',kind=kind,model=models[kind][variant],variant=variant,x=x,y=y,z=z,width=w,depth=d,interior=owner['id'],color='#819c90',quarter_turn=turn)
        game.props.append(prop);game.blocked.update(cells);return True
    # Reserve one forklift bay before filling the machine banks.
    forklift=False
    for owner in reversed(game.buildings):
        for y in range(owner['y']+1,owner['y']+owner['depth']-2):
            for x in range(owner['x']+1,owner['x']+owner['width']-1):
                if place('factory_forklift',x,y,0,owner,0):forklift=True;break
            if forklift:break
        if forklift:break
    # Staggered machine banks have varying row gaps and mixed orientations, with
    # one-tile circulation aisles rather than an empty buffer around every item.
    for z in range(4):
        for owner in game.buildings:
            if z>owner['level']:continue
            y=owner['y']+1;row=0
            while y<owner['y']+owner['depth']-1:
                x=owner['x']+1+(row%2);depth=2;slot=0
                while x<owner['x']+owner['width']-1:
                    kind=pattern[(row+slot+z)%len(pattern)]
                    if z and kind=='factory_forklift':kind='factory_rack'
                    turn=r.choice([0,0,2,2,1]);w,d=sizes[kind]
                    if turn%2:w,d=d,w
                    if place(kind,x,y,z,owner,turn):depth=max(depth,d);advance=w+1
                    # A compact robot or rack can fill slots too small for a machine.
                    elif place('factory_robot',x,y,z,owner,0):advance=3
                    else:advance=1
                    x+=advance;slot+=1
                y+=depth+r.choice([1,1,2]);row+=1
    validate_factory_access(game)
    game.scenery=dict(theme='factory',road_x=game.road_x,cross_y=game.cross_y,factory_band=band,factory_levels=4,**theme)


def validate_factory_access(game):
    """Reject a layout unless every walkable tile connects to the squad entrance."""
    walkable=game.surfaces-game.blocked
    links={}
    for a,b in game.stairs+game.ladders:
        a,b=tuple(a),tuple(b)
        if a not in walkable or b not in walkable:
            raise ValueError('Factory stair or ladder landing is obstructed.')
        links.setdefault(a,[]).append(b);links.setdefault(b,[]).append(a)
    start=(game.size//2-3,game.size-2,0)
    if start not in walkable:raise ValueError('Factory deployment entrance is obstructed.')
    seen={start};queue=[start]
    for x,y,z in queue:
        for q in [(x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z),*links.get((x,y,z),[])]:
            if q not in walkable or q in seen:continue
            wall=game.walls.get(tuple(sorted(((x,y,z),q))))
            if wall and wall['kind']!='door':continue
            seen.add(q);queue.append(q)
    if seen!=walkable:raise ValueError('A factory platform has no accessible stair or ladder route.')
