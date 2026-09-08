"""Server-side squad knowledge. Hidden units never enter the public payload."""
import copy
import math

SIGHT={'standing':14,'kneeling':10,'prone':7}
PROFILE={'standing':1.0,'kneeling':.8,'prone':.55}


class FogOfWar:
    def init_fog(self):
        self.explored=set()
        self.visible=set()
        self.known_tiles={};self.known_walls={};self.known_buildings={};self.known_props={};self.known_corpses={};self.known_enemies={}
        self._fog_key=None
        self.refresh_visibility()

    def sees(self, observer, target):
        if observer['hp']<=0 or target.get('evacuated'):return False
        distance=math.sqrt((observer['x']-target['x'])**2+(observer['y']-target['y'])**2+((observer['z']-target['z'])*2)**2)
        return distance<=(20 if observer.get('weapon')=='M24 sniper' and observer['stance']=='standing' else SIGHT[observer['stance']])*PROFILE[target.get('stance','standing')] and self.line_of_sight(observer,target)

    def detected(self, unit):
        return unit['team']=='soldier' or any(self.sees(s,unit) for s in self.alive('soldier'))

    def refresh_visibility(self):
        if not hasattr(self,'explored'):return
        key=(self.geometry_revision,tuple((self.position(s),s['stance'],s['hp'],s.get('weapon')) for s in self.alive('soldier')))
        if key!=self._fog_key:
            visible=set()
            for s in self.alive('soldier'):
                radius=20 if s.get('weapon')=='M24 sniper' and s['stance']=='standing' else SIGHT[s['stance']]
                for x,y,z in self.surfaces:
                    if (x-s['x'])**2+(y-s['y'])**2+((z-s['z'])*2)**2>radius**2:continue
                    if self.line_of_sight(s,dict(x=x,y=y,z=z,stance='standing')):visible.add((x,y,z))
                visible.add(self.position(s))
            self.visible=visible;self.explored.update(visible);self._fog_key=key
        for x,y,z in self.visible:
            if z==0:self.known_tiles[(x,y)]=self.tiles[y][x]
        for wall in self.walls.values():
            if tuple(wall['a']) in self.visible or tuple(wall['b']) in self.visible:
                self.known_walls[(tuple(wall['a']),tuple(wall['b']))]=copy.deepcopy(wall)
                b=next(b for b in self.buildings if b['id']==wall['building'])
                self.known_buildings[b['id']]=copy.deepcopy(b)
        for b in self.buildings:
            if any((x,y,b['level']) in self.visible for x in range(b['x'],b['x']+b['width']) for y in range(b['y'],b['y']+b['depth'])):
                self.known_buildings[b['id']]=copy.deepcopy(b)
        for p in self.props:
            if any((x,y,0) in self.visible for x in range(p['x'],p['x']+p['width']) for y in range(p['y'],p['y']+p['depth'])):
                self.known_props[p['id']]=copy.deepcopy(p)
        observed_destroyed={p['id'] for p in self.props+self.buildings if p.get('destroyed') and any(c in self.visible for c in self.footprint(p))}
        self.known_walls={k:w for k,w in self.known_walls.items() if w['building'] not in observed_destroyed}
        for uid in observed_destroyed:
            p=next(p for p in self.props+self.buildings if p['id']==uid)
            (self.known_buildings if 'level' in p else self.known_props)[uid]=copy.deepcopy(p)
            if 'level' in p:self.explored={c for c in self.explored if c[2]==0 or (c[0],c[1],0) not in set(self.footprint(p))}
        for u in self.alive('alien'):
            if self.detected(u):self.remember_enemy(u)
        for u in self.units:
            if u['hp']<=0 and (self.position(u) in self.visible or u['team']=='soldier'):
                self.known_corpses[u['id']]=copy.deepcopy(u)
                self.known_enemies.pop(u['id'],None)

    def remember_enemy(self,u):
        self.known_enemies[u['id']]={k:u[k] for k in ('id','name','x','y','z','stance')}
        self.known_enemies[u['id']]['round']=self.round

    def public_last_seen(self):
        detected={u['id'] for u in self.alive('alien') if self.detected(u)}
        markers=[]
        for uid,m in list(self.known_enemies.items()):
            if uid in detected:continue
            # Clear stale markers only after close inspection, never by consulting hidden positions.
            if any(s['z']==m['z'] and math.hypot(s['x']-m['x'],s['y']-m['y'])<=1.5 and self.line_of_sight(s,m) for s in self.alive('soldier')):
                del self.known_enemies[uid];continue
            markers.append(copy.deepcopy(m))
        return markers

    def public_units(self):
        units=[copy.deepcopy(u) for u in self.units if u['team']=='soldier' or (u['hp']>0 and not u['evacuated'] and self.detected(u))]
        ids={u['id'] for u in units}
        units.extend(copy.deepcopy(u) for uid,u in self.known_corpses.items() if uid not in ids)
        return units

    def emit(self, event, actor=None):
        if actor is None or self.detected(actor):
            if actor is not None:event['actor']=copy.deepcopy(actor)
            self.events.append(event)

    def public_world(self):
        tiles=[[self.known_tiles.get((x,y),'unknown') for x in range(self.size)] for y in range(self.size)]
        heights=[[0]*self.size for _ in range(self.size)]
        for b in self.known_buildings.values():
            for y in range(b['y'],b['y']+b['depth']):
                for x in range(b['x'],b['x']+b['width']):heights[y][x]=b['level']
        return dict(tiles=tiles,heights=heights,buildings=list(self.known_buildings.values()),walls=list(self.known_walls.values()),
                    portals=[w for w in self.known_walls.values() if w['kind']!='wall'],props=list(self.known_props.values()),
                    surfaces=sorted(self.explored),ladders=[link for link in self.ladders if any(tuple(p) in self.explored for p in link)],
                    stairs=[link for link in self.stairs if any(tuple(p) in self.explored for p in link)],
                    fog=dict(visible=sorted(self.visible),explored=sorted(self.explored)))
