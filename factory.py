"""Open-sided factory hall with three playable levels and real machine footprints."""


def factory_generate(game,theme,models):
    """Create connected mezzanine platforms, outer walls and seeded machinery."""
    r,n=game.rng,game.size
    band=n//4+r.choice([-1,0,1]);mid=(n-band)//2+r.randint(-2,2)
    game.road_x=n//2;game.cross_y=n//2
    game.tiles=[['floor']*n for _ in range(n)]
    game.heights=[[0]*n for _ in range(n)]
    game.surfaces={(x,y,0) for y in range(n) for x in range(n)}
    game.buildings=[];game.walls={};game.portals=[];game.props=[];game.blocked=set();game.stairs=[];game.ladders=[]
    zones=[(0,0,n,band,2,'ASSEMBLY GALLERY'),(0,band,band,mid,1,'MACHINE SHOP'),
           (0,band+mid,band,n-band-mid,1,'STORES MEZZANINE'),(band,band,n-band,n-band,0,'PRODUCTION HALL')]
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
    # Two access points per upper level; endpoints and their aisles stay clear.
    for x,y in [(band-2,n-6),(n-5,band-2)]:game.stairs.append(((x,y,0),(x,y,1)))
    for x,y in [(2,2),(n-5,band-2)]:game.stairs.append(((x,y,1),(x,y,2)))
    protected={tuple(p) for link in game.stairs for p in link}
    protected.update((x,y,0) for y in range(n-4,n) for x in range(n))
    for x,y,z in list(protected):
        protected.update((x+dx,y+dy,z) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)])
    sizes={'factory_machine':(3,2),'factory_rack':(3,1),'factory_robot':(2,2),'factory_conveyor':(3,2),'factory_forklift':(2,3)}
    for z in range(3):
        kinds=['factory_machine']*4+['factory_rack']*2
        if z==0:kinds+=['factory_conveyor','factory_robot']*3+['factory_forklift']
        elif z==1:kinds+=['factory_robot','factory_conveyor']
        for index,kind in enumerate(kinds):
            w,d=sizes[kind]
            positions=sorted(p for p in game.surfaces if p[2]==z);r.shuffle(positions)
            for x,y,_ in positions:
                cells={(a,b,z) for b in range(y,y+d) for a in range(x,x+w)}
                if not cells<=game.surfaces or cells&(game.blocked|protected):continue
                # Machines remain inside one supporting platform, away from outer walls.
                owner=next((b for b in game.buildings if b['x']<=x and x+w<=b['x']+b['width'] and b['y']<=y and y+d<=b['y']+b['depth'] and z<=b['level']),None)
                if not owner or x<1 or y<1:continue
                halo={(a,b,z) for a in range(x-1,x+w+1) for b in range(y-1,y+d+1)}
                if halo&game.blocked:continue
                remaining={p for p in game.surfaces if p[2]==z}-game.blocked-cells
                start=min(remaining);seen={start};queue=[start]
                for a,b,c in queue:
                    for q in ((a+1,b,c),(a-1,b,c),(a,b+1,c),(a,b-1,c)):
                        if q in remaining and q not in seen:seen.add(q);queue.append(q)
                if seen!=remaining:continue
                variant=index%len(models[kind])
                game.props.append(dict(id=f'prop{len(game.props)}',kind=kind,model=models[kind][variant],variant=variant,x=x,y=y,z=z,width=w,depth=d,interior=owner['id'],color='#819c90'))
                game.blocked.update(cells);break
    game.scenery=dict(theme='factory',road_x=game.road_x,cross_y=game.cross_y,factory_band=band,factory_levels=3,**theme)
