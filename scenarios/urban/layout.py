"""Seeded city blocks and street furniture."""
from scenarios.common import PROP_SIZE
from scenarios.assets import transport_models

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
            models=transport_models().get(kind,[]);variant=r.randrange(len(models) if models else 4)
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


