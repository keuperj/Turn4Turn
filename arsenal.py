"""Deployment, persistent obscurants and structural damage."""
import copy
import math


class Arsenal:
    """Manage equipment, deployable utilities, and destructible structures."""
    def deploy(self, data):
        """Validate all requested loadouts and equip the squad atomically."""
        from game import WEAPONS
        if self.status != 'loadout':raise ValueError('Equipment can only be assigned before deployment.')
        selections=data.get('loadouts')
        squad=self.alive('soldier')
        if not isinstance(selections,dict) or set(selections)!={u['id'] for u in squad}:raise ValueError('Choose equipment for all four fighters.')
        checked=[]
        for u in squad:
            v=selections[u['id']]
            if not isinstance(v,dict):raise ValueError('Choose four equipment items per fighter.')
            items=[v.get('primary'),v.get('sidearm','M9'),v.get('utility1'),v.get('utility2')]
            if any(not isinstance(w,str) or w not in WEAPONS for w in items):
                raise ValueError('Every slot must contain an available weapon or item.')
            if len(set(items))!=4:raise ValueError('Choose four different equipment items per fighter.')
            checked.append((u,items))
        for u,items in checked:
            u['inventory']={w:dict(ammo=WEAPONS[w]['capacity'],reserve=0 if WEAPONS[w]['kind'] in ('grenade','smoke','charge','medical') else 1 if w=='RPG-7' else WEAPONS[w]['capacity']*3) for w in items}
            u.update(weapon=items[0],ammo=u['inventory'][items[0]]['ammo'],fire_mode='single')
        self.status='active';self.events=[]
        self.log.append('Squad equipped and deployed. Timed charges detonate after two hostile phases; smoke lasts three.')

    def init_structures(self):
        """Initialize health and identifiers for destructible world objects."""
        for p in self.props+self.buildings:
            hp=140 if 'level' in p else {'aircraft':100,'train':90,'car':35,'truck':50,'tractor':45}.get(p.get('kind'),30)
            p.update(hp=hp,max_hp=hp,destroyed=False)

    def smoke_blocks(self,a,b):
        """Return whether active smoke blocks the line between two points."""
        dx=b['x']-a['x'];dy=b['y']-a['y'];length=dx*dx+dy*dy
        if not length:return False
        for s in self.smoke+self.fires:
            t=max(0,min(1,((s['x']-a['x'])*dx+(s['y']-a['y'])*dy)/length))
            if abs(a['z']+(b['z']-a['z'])*t-s['z'])<.8 and math.hypot(a['x']+dx*t-s['x'],a['y']+dy*t-s['y'])<=s['radius']:
                return True
        return False

    def place_utility(self,u,x,y,z):
        """Place a smoke grenade or demolition charge in the world."""
        kind='smoke' if u['weapon']=='Smoke grenade' else 'charge'
        self.spend_ammo(u);u['ap']=0
        effect=dict(x=x,y=y,z=z,radius=3 if kind=='smoke' else 4,turns=3 if kind=='smoke' else 2)
        (self.smoke if kind=='smoke' else self.charges).append(effect)
        self.events.append(dict(type='smoke' if kind=='smoke' else 'charge_place',unit=u['id'],**effect))
        self.log.append(f"{u['name']} {'throws smoke (3 hostile phases)' if kind=='smoke' else 'sets demolition charge (2 hostile phases)' }.")
        self.geometry_revision+=1

    def tick_utilities(self):
        """Advance timed utilities and resolve expirations or detonations."""
        for smoke in self.smoke:smoke['turns']-=1
        self.smoke=[s for s in self.smoke if s['turns']>0]
        for fire in self.fires:fire['turns']-=1
        self.fires=[f for f in self.fires if f['turns']>0]
        for c in list(self.charges):
            c['turns']-=1
            if c['turns']>0:continue
            self.charges.remove(c)
            point=(c['x'],c['y'],c['z'])
            self.events.append(dict(type='blast',unit=None,kind='charge',**c))
            for u in self.alive():
                distance=math.sqrt((u['x']-c['x'])**2+(u['y']-c['y'])**2+((u['z']-c['z'])*3)**2)
                if distance<=c['radius']:
                    u['hp']=max(0,u['hp']-max(8,60-int(distance)*10))
                    if self.detected(u):self.events.append(dict(type='hurt',point=self.position(u),unit=u['id']))
            self.damage_area(c['x'],c['y'],c['z'],c['radius'],220)
            self.ignite(c['x'],c['y'],c['z'],2)
            self.log.append('Demolition charge detonated.')
        self.geometry_revision+=1

    @staticmethod
    def footprint(p):
        """Return every ground coordinate occupied by a structure."""
        return [(x,y,0) for x in range(p['x'],p['x']+p['width']) for y in range(p['y'],p['y']+p['depth'])]

    def structure_targets(self,u):
        """Return damageable structures intersecting a blast area."""
        from game import WEAPONS
        w=WEAPONS[u['weapon']]
        if w['kind'] in ('smoke','charge','grenade','rocket','medical') or not u['ap']:return []
        targets=[]
        for p in self.props+self.buildings:
            if p.get('destroyed'):continue
            cells=[c for c in self.footprint(p) if any((c[0]+dx,c[1]+dy,0) in self.visible for dx,dy in [(0,0),(-1,0),(1,0),(0,-1),(0,1)])]
            if not cells:continue
            x,y,z=min(cells,key=lambda c:math.hypot(c[0]-u['x'],c[1]-u['y']))
            if math.hypot(x-u['x'],y-u['y'])>w['range']:continue
            # Shoot the exposed surface from a visible adjacent approach, not through its solid interior.
            if not any(self.line_of_sight(u,dict(x=x+dx,y=y+dy,z=0,stance='standing')) for dx,dy in [(0,0),(-1,0),(1,0),(0,-1),(0,1)] if (x+dx,y+dy,0) in self.visible):continue
            targets.append(dict(id=p['id'],name=p.get('name',p.get('kind','structure')),hp=p['hp'],max_hp=p['max_hp'],point=[x,y,z]))
        return targets

    def fire_structure(self,u,uid):
        """Resolve a direct weapon attack against a structure."""
        from game import WEAPONS
        t=next((t for t in self.structure_targets(u) if t['id']==uid),None)
        w=WEAPONS[u['weapon']]
        if not t or not u['ammo']:raise ValueError('Structure is not in sight or weapon range.')
        if w['kind']=='sniper' and u['ap']<2:raise ValueError('Sniper shots require both action points.')
        p=next(p for p in self.props+self.buildings if p['id']==uid)
        rounds=min(3,u['ammo']) if u.get('fire_mode')=='auto' and w.get('automatic') else 1
        for _ in range(rounds):
            self.spend_ammo(u)
            hit=self.rng.randint(1,100)<=(65 if rounds>1 else 95)
            self.events.append(dict(type='shot',unit=u['id'],origin=self.position(u),point=t['point'],hit=hit,structure=True,burst=rounds>1,weapon=u['weapon']))
            if hit:self.damage_structure(p,max(1,w['damage']//2))
        u['ap']=max(0,u['ap']-1) if w['kind']=='handgun' else 0
        self.geometry_revision+=1

    def damage_area(self,x,y,z,radius,power):
        """Apply blast damage to units and structures around a point."""
        for p in self.props+self.buildings:
            distance=min(math.hypot(a-x,b-y) for a,b,_ in self.footprint(p))
            if not p.get('destroyed') and distance<=radius and (z==0 or 'level' in p):
                self.damage_structure(p,max(1,round(power*(1-distance/(radius+1)))))

    def ignite(self,x,y,z,radius=1):
        """Create a temporary fire hazard at an impact position."""
        candidates=[(a,b,z) for a,b,c in self.surfaces if c==z and math.hypot(a-x,b-y)<=radius]
        self.rng.shuffle(candidates)
        occupied={(f['x'],f['y'],f['z']) for f in self.fires}
        for a,b,c in candidates[:max(1,min(4,radius*2))]:
            if (a,b,c) not in occupied:self.fires.append(dict(x=a,y=b,z=c,radius=1.35,turns=self.rng.randint(1,3)))
        self.geometry_revision+=1

    def damage_structure(self,p,damage):
        """Apply damage and collapse a structure when health is exhausted."""
        if p.get('destroyed'):return
        p['hp']=max(0,p['hp']-damage)
        if p['hp']:return
        observed=any(c in self.visible for c in self.footprint(p))
        p['destroyed']=True
        cells=set(self.footprint(p))
        x,y,_=self.rng.choice(sorted(cells));self.ignite(x,y,0,1)
        for x,y,_ in cells:self.tiles[y][x]='rubble';self.heights[y][x]=0
        self.blocked.difference_update(cells)
        if 'level' in p:
            self.walls={k:w for k,w in self.walls.items() if w['building']!=p['id']}
            self.portals=[w for w in self.portals if w['building']!=p['id']]
            removed={c for c in self.surfaces if c[2]>0 and (c[0],c[1],0) in cells}
            self.surfaces.difference_update(removed)
            self.ladders=[link for link in self.ladders if not any(tuple(c) in removed for c in link)]
            self.stairs=[link for link in self.stairs if not any(tuple(c) in removed for c in link)]
            for u in self.units:
                if (u['x'],u['y'],0) in cells and u['z']>0:
                    u['hp']=0;u['z']=0
            p['level']=0
        if observed:
            self.log.append(f"{p.get('name',p.get('kind','Structure'))} destroyed.")
            (self.known_buildings if 'level' in p else self.known_props)[p['id']]=copy.deepcopy(p)
        self.geometry_revision+=1
