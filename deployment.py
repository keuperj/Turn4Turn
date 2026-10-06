"""Seeded rescue deployment with time and space for the squad to intervene."""

RESCUE_ENEMY_DISTANCE = 10
CIVILIAN_COUNT = 5


def place_rescue_civilians(game, reachable, enemy_candidates):
    """Keep civilians separated horizontally and outside initial enemy sight.

    Try the existing hostile deployment first. If it leaves too few safe tiles,
    try shuffled civilian pockets and relocate hostiles within their original
    deployment pool. Never weaken the separation rule to fill the map.
    """
    enemies=game.alive('alien')
    indoor={p for p in enemy_candidates if game.building_at(*p)}
    upper={p for p in indoor if p[2]>0}
    required_indoor=min(2,sum(game.position(e) in indoor for e in enemies))
    require_upper=any(game.position(e) in upper for e in enemies)
    soldiers={game.position(u) for u in game.alive('soldier')}
    transitions={tuple(p) for link in game.ladders+game.stairs for p in link}
    candidates=sorted(p for p in reachable if p[2]==0 and 4<p[1]<game.size-6
                      and p not in soldiers and p not in transitions)

    def civilian_at(position):
        x,y,z=position
        return dict(x=x,y=y,z=z,stance='standing')

    def safe(enemy, civilian):
        # Do not count height as separation: a guard directly upstairs is close.
        distance_squared=(enemy['x']-civilian['x'])**2+(enemy['y']-civilian['y'])**2
        return distance_squared>=RESCUE_ENEMY_DISTANCE**2 and not game.sees(enemy,civilian)

    safe_tiles=[p for p in candidates if all(safe(e,civilian_at(p)) for e in enemies)]
    if len(safe_tiles)>=CIVILIAN_COUNT:
        positions=game.rng.sample(safe_tiles,CIVILIAN_COUNT)
    else:
        # A compact randomized pocket leaves room for the complete enemy force,
        # including on small maps. Start nearer the squad, then try other areas.
        anchors=candidates[:];game.rng.shuffle(anchors)
        anchors.sort(key=lambda p:p[1]<game.size//2)
        positions=None
        for anchor in anchors:
            nearby=[p for p in candidates if p!=anchor and
                    (p[0]-anchor[0])**2+(p[1]-anchor[1])**2<=16]
            if len(nearby)<CIVILIAN_COUNT-1:continue
            pocket=[anchor]+game.rng.sample(nearby,CIVILIAN_COUNT-1)
            civilians=[civilian_at(p) for p in pocket]
            occupied=soldiers|set(pocket);placements=[]
            indoor_count=0;has_upper=False
            for enemy in enemies:
                # Retain indoor and upstairs defenders, using the original
                # shuffled order to break ties between equally suitable tiles.
                pool=sorted(enemy_candidates,key=lambda p:
                            0 if require_upper and not has_upper and p in upper else
                            1 if indoor_count<required_indoor and p in indoor else 2)
                for p in pool:
                    if p in occupied:continue
                    hypothetical=dict(enemy,x=p[0],y=p[1],z=p[2])
                    if all(safe(hypothetical,c) for c in civilians):
                        placements.append(p);occupied.add(p)
                        indoor_count+=p in indoor;has_upper|=p in upper
                        break
                else:break
            if len(placements)!=len(enemies) or indoor_count<required_indoor or require_upper and not has_upper:continue
            for enemy,p in zip(enemies,placements):enemy.update(x=p[0],y=p[1],z=p[2])
            positions=pocket;break
        if positions is None:
            raise ValueError('Scenario has no safe rescue deployment for all civilians and enemies.')

    for i,(x,y,z) in enumerate(positions):
        game.units.append(game.make_unit(f'c{i}',f'CIVILIAN {i+1}','civilian',x,y,None,'Noncombatant',z))
