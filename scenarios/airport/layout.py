"""A regional airfield with an open runway, apron and connected passenger terminal."""


def airport_plan(game):
    """Reserve the runway and apron before placing the four airport buildings."""
    r,n=game.rng,game.size
    width=n//3;depth=max(5,n//4-1);hangar_depth=4 if n==24 else 5
    terminal_y=n-4-depth
    game.road_x=n-4;game.cross_y=terminal_y+depth//2
    game.airport=dict(runway_x=n-4.5,runway_width=6,apron_x=width+3,access_y=game.cross_y)
    game.tiles=[['runway' if n-7<=x<n-1 else 'apron' if width+3<=x<n-7 else
                 'road' if x<2 and abs(y-game.cross_y)<=1 else 'grass'
                 for x in range(n)] for y in range(n)]
    return [dict(x=2,y=terminal_y,width=width,depth=depth,name='AIRPORT TERMINAL',airport_role='terminal',level=1),
            dict(x=2,y=2,width=width-1,depth=hangar_depth,name='HANGAR 01',airport_role='hangar',level=1),
            dict(x=r.randint(2,width-2),y=2+2*(hangar_depth+1),width=3,depth=2 if n==24 else 3,name='CONTROL TOWER',airport_role='tower',level=3),
            dict(x=2,y=3+hangar_depth,width=width-1,depth=hangar_depth,name='HANGAR 02',airport_role='hangar',level=1)]


def airport_props(game,models):
    """Park equipment and furnish the hall without cutting any ground route."""
    r,n=game.rng,game.size
    ground={(x,y,0) for y in range(n) for x in range(n)}
    protected={tuple(p[k]) for p in game.portals if p['kind']=='door' for k in ('a','b')}
    protected.update(tuple(p) for link in game.ladders+game.stairs for p in link)
    protected.update((x,y,0) for y in range(n-4,n) for x in range(n))
    # Short paved approaches join every entrance to the apron or the public road.
    for door in game.portals:
        if door['kind']!='door' or door['side']=='interior':continue
        x,y,z=door['b']
        if z:continue
        if door['side']=='east':
            for a in range(x,game.airport['apron_x']+1):
                if not game.heights[y][a]:
                    game.tiles[y][a]='apron';protected.add((a,y,0))
        elif door['side']=='west':
            for a in range(x+1):game.tiles[y][a]='road';protected.add((a,y,0))

    def place(kind,w,d,positions,allowed,model=None,interior=None):
        r.shuffle(positions)
        for x,y in positions:
            cells={(a,b,0) for b in range(y,y+d) for a in range(x,x+w)}
            if not cells<=ground or cells&(protected|game.blocked):continue
            if any(game.tiles[b][a] not in allowed for a,b,_ in cells):continue
            # Check walls too: every room and every exterior tile must stay reachable.
            remaining=ground-game.blocked-cells;seen={(n//2,n-1,0)};queue=list(seen)
            for a,b,z in queue:
                for q in ((a+1,b,z),(a-1,b,z),(a,b+1,z),(a,b-1,z)):
                    wall=game.walls.get(tuple(sorted(((a,b,z),q))))
                    if q in remaining and q not in seen and (not wall or wall['kind']=='door'):seen.add(q);queue.append(q)
            if seen!=remaining:continue
            prop=dict(id=f'prop{len(game.props)}',kind=kind,x=x,y=y,width=w,depth=d,variant=0,color='#c3ccd0')
            if model:prop.update(model=model,variant=models[kind].index(model))
            if interior:prop['interior']=interior
            game.props.append(prop);game.blocked.update(cells);return True
        return False

    apron=game.airport['apron_x'];available=n-7-apron
    # Park aircraft on the apron, never on the active runway or the deployment edge.
    aircraft_width=min(10,available-1);aircraft_depth=min(9,n//3)
    for i,model in enumerate(['AirportLightPlane','AirportBusinessJet'] if n>=30 else [r.choice(['AirportLightPlane','AirportBusinessJet'])]):
        start=1+i*(aircraft_depth+1)
        place('aircraft',aircraft_width,aircraft_depth,[(apron+1,y) for y in range(start,min(start+3,n-4-aircraft_depth))],{'apron'},model)
    positions=[(x,y) for y in range(1,n-4) for x in range(apron,n-7)]
    for kind,w,d,model in [('airport_tug',2,3,'AirportTug'),('airport_fuel',2,3,'AirportFuelBowser'),('airport_cart',2,2,'AirportPowerCart')]:
        place(kind,w,d,positions[:],{'apron'},model)
    place('windsock',2,2,[(x,y) for y in range(1,n-6) for x in range(1,apron-2)],{'grass'},'AirportWindsock')
    terminal=game.buildings[0];x,y,w,d=(terminal[k] for k in ('x','y','width','depth'))
    place('ticket_counter',2,1,[(x+w-3,y+d-2)],{'floor'},interior=terminal['id'])
    for row in range(y+1,y+d-1,2):
        for col in range(x+1,x+w-2,3):place('bench',2,1,[(col,row)],{'floor'},interior=terminal['id'])
    place('trash',1,1,[(x,y+d-2)],{'floor'},interior=terminal['id'])
