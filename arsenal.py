"""Deployment, persistent obscurants and structural damage."""
import math


class Arsenal:
    def deploy(self, data):
        from game import WEAPONS
        if self.status != 'loadout':raise ValueError('Equipment can only be assigned before deployment.')
        selections=data.get('loadouts')
        squad=self.alive('soldier')
        if not isinstance(selections,dict) or set(selections)!={u['id'] for u in squad}:raise ValueError('Choose equipment for all four fighters.')
        primary=['M4A1','HK416','M110','M249','M24 sniper','Shotgun','M9','RPG-7']
        utility=['Medikit','Frag grenade','Smoke grenade','Demolition charge','RPG-7']
        checked=[]
        for u in squad:
            v=selections[u['id']]
            if not isinstance(v,dict) or v.get('primary') not in primary or v.get('utility1') not in utility or v.get('utility2') not in utility or v['utility1']==v['utility2']:
                raise ValueError('Choose a weapon and two different support items per fighter.')
            checked.append((u,list(dict.fromkeys([v['primary'],'M9',v['utility1'],v['utility2']]))))
        for u,items in checked:
            u['inventory']={w:dict(ammo=WEAPONS[w]['capacity'],reserve=0 if WEAPONS[w]['kind'] in ('grenade','smoke','charge','medical') else 1 if w=='RPG-7' else WEAPONS[w]['capacity']*3) for w in items}
            u.update(weapon=items[0],ammo=u['inventory'][items[0]]['ammo'],fire_mode='single')
        self.status='active';self.events=[]
        self.log.append('Squad equipped and deployed. Timed charges detonate after two hostile phases; smoke lasts three.')

    def init_structures(self):
        for p in self.props+self.buildings:
            hp=140 if 'level' in p else {'aircraft':100,'train':90,'car':35,'truck':50,'tractor':45}.get(p.get('kind'),30)
            p.update(hp=hp,max_hp=hp,destroyed=False)

    def smoke_blocks(self,a,b):
        dx=b['x']-a['x'];dy=b['y']-a['y'];length=dx*dx+dy*dy
        if not length:return False
        for s in self.smoke:
            t=max(0,min(1,((s['x']-a['x'])*dx+(s['y']-a['y'])*dy)/length))
            if abs(a['z']+(b['z']-a['z'])*t-s['z'])<.8 and math.hypot(a['x']+dx*t-s['x'],a['y']+dy*t-s['y'])<=s['radius']:
                return True
        return False

    def place_utility(self,u,x,y,z):
        kind='smoke' if u['weapon']=='Smoke grenade' else 'charge'
        self.spend_ammo(u);u['ap']=0
        effect=dict(x=x,y=y,z=z,radius=3 if kind=='smoke' else 4,turns=3 if kind=='smoke' else 2)
        (self.smoke if kind=='smoke' else self.charges).append(effect)
        self.events.append(dict(type='smoke' if kind=='smoke' else 'reload',unit=u['id'],**effect))
        self.log.append(f"{u['name']} {'throws smoke (3 hostile phases)' if kind=='smoke' else 'sets demolition charge (2 hostile phases)' }.")
        self.geometry_revision+=1

    def tick_utilities(self):
        for smoke in self.smoke:smoke['turns']-=1
        self.smoke=[s for s in self.smoke if s['turns']>0]
        for c in list(self.charges):
            c['turns']-=1
            if c['turns']>0:continue
            self.charges.remove(c)
            point=(c['x'],c['y'],c['z'])
            if point in self.visible:self.events.append(dict(type='blast',unit=None,kind='charge',**c))
            for u in self.alive():
                distance=math.sqrt((u['x']-c['x'])**2+(u['y']-c['y'])**2+((u['z']-c['z'])*3)**2)
                if distance<=c['radius']:
                    u['hp']=max(0,u['hp']-max(8,60-int(distance)*10))
                    if self.detected(u):self.events.append(dict(type='hurt',point=self.position(u),unit=u['id']))
            self.damage_area(c['x'],c['y'],c['z'],c['radius'],220)
            self.log.append('Demolition charge detonated.')
        self.geometry_revision+=1

    @staticmethod
    def footprint(p):
        return [(x,y,0) for x in range(p['x'],p['x']+p['width']) for y in range(p['y'],p['y']+p['depth'])]

    def structure_targets(self,u):
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
        for p in self.props+self.buildings:
            distance=min(math.hypot(a-x,b-y) for a,b,_ in self.footprint(p))
            if not p.get('destroyed') and distance<=radius and (z==0 or 'level' in p):
                self.damage_structure(p,max(1,round(power*(1-distance/(radius+1)))))

    def damage_structure(self,p,damage):
        if p.get('destroyed'):return
        p['hp']=max(0,p['hp']-damage)
        if p['hp']:return
        p['destroyed']=True
        cells=set(self.footprint(p))
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
        if any(c in self.visible for c in cells):self.log.append(f"{p.get('name',p.get('kind','Structure'))} destroyed.")
        self.geometry_revision+=1
