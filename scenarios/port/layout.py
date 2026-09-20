"""Deterministic harbour layout and dock equipment placement."""


def port_plan(game):
    """Build three wide piers joined by a head pier and the waterfront quay."""
    n,r=game.size,game.rng
    shore=n//2+1;piers=[3,n//2,n-4]
    game.road_x=n//2;game.cross_y=shore+2
    game.tiles=[['quay' if y>=shore else 'pier' if y in (2,3) and 2<=x<=n-3 or y>=2 and any(abs(x-p)<=1 for p in piers) else 'water' for x in range(n)] for y in range(n)]
    for y in (shore+1,shore+2):game.tiles[y]=['road']*n
    width=(n-10)//4;depth=max(3,n-shore-8);by=shore+4
    lots=[dict(x=x,y=by,width=width,depth=depth,name=name) for x,name in zip([2,4+width,6+width*2,8+width*3],['WAREHOUSE','SHIP REPAIR','PORT AUTHORITY','CUSTOMS'])]
    vessels=[]
    for i,(left,right) in enumerate(zip(piers,piers[1:])):
        vessels.append(dict(model='PortCruiser' if i==0 else 'PortCruiserNavy',x=(left+right)/2,y=(shore+4)/2,scale=min(1,(right-left-3)/3.6,(shore-5)/9),angle=r.choice([0,3.141592653589793])))
    game.port=dict(shore_y=shore,piers=piers,vessels=vessels,road_width=2,
                   water=[[x,y] for y,row in enumerate(game.tiles) for x,t in enumerate(row) if t=='water'])
    return lots


def port_props(game):
    """Dock boxes and service pedestals leave two clear tiles on each pier."""
    n=game.size
    protected={tuple(p[k]) for p in game.portals if p['kind']=='door' for k in ('a','b')}
    protected.update(tuple(p) for link in game.ladders+game.stairs for p in link)
    for i,x in enumerate(game.port['piers']):
        for j,y in enumerate(range(5,game.port['shore_y']-1,4)):
            pos=(x-1,y,0)
            if pos in protected:continue
            kind,model=('port_box','PortDockBox') if (i+j)%2==0 else ('port_pedestal','PortPedestal')
            game.props.append(dict(id=f'prop{len(game.props)}',kind=kind,model=model,x=x-1,y=y,width=1,depth=1,variant=0,color='#b4c4c9'))
            game.blocked.add(pos)
