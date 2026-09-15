"""Shared click previews and authoritative coordinate attacks."""
import math
from visibility import SIGHT


class Targeting:
    """Validate previews and attacks against units, terrain, and structures."""
    def target_structure(self, data):
        """Return the damageable structure at a targeted world position."""
        uid=data.get('structure')
        return next((p for p in self.props+self.buildings if p['id']==uid and not p.get('destroyed')),None)

    def attack_solution(self,u,data):
        """Validate an attack and return its resolved targeting data."""
        from game import WEAPONS
        w=WEAPONS[u['weapon']]
        if w['kind']=='medical':raise ValueError('Medikits treat teammates; select a wounded teammate.')
        x,y,z=data.get('x'),data.get('y'),data.get('z',u['z'])
        if any(type(v) is not int for v in (x,y,z)) or (x,y,z) not in self.surfaces:raise ValueError('Select a battlefield surface.')
        if not u['ammo']:raise ValueError('Magazine empty. Reload or choose another item.')
        if w['kind']=='sniper' and u['ap']<2:raise ValueError('Sniper shots require 2 AP.')
        if w['kind']=='rocket' and u['stance']=='prone':raise ValueError('Stand or kneel to fire the RPG.')
        distance=math.sqrt((x-u['x'])**2+(y-u['y'])**2+((z-u['z'])*2)**2)
        if distance>w['range']:raise ValueError(f"Outside {w['range']}-tile weapon range.")
        structure=self.target_structure(data)
        if data.get('structure') and not structure:raise ValueError('Structure is no longer available.')
        if structure:
            if not(structure['x']<=x<structure['x']+structure['width'] and structure['y']<=y<structure['y']+structure['depth'] and (z<=structure.get('level',0))):raise ValueError('Select the structure’s surface.')
            if structure['id'] not in self.known_buildings and structure['id'] not in self.known_props:raise ValueError('Structure is not visible.')
        elif (x,y,z) not in self.visible and w['kind'] not in ('grenade','smoke'):raise ValueError('That point is outside current squad visibility.')
        vision=20 if u['weapon']=='M24 sniper' and u['stance']=='standing' else SIGHT[u['stance']]
        if distance>vision:raise ValueError('That point is beyond this fighter’s sight range.')
        point=dict(x=x,y=y,z=z,stance='standing')
        direct=self._trace_sight(u,point,True,target_structure=structure['id'] if structure else None)
        throwable=w['kind'] in ('grenade','smoke')
        via=None if direct or throwable else self.corner_throw(u,point)
        if not direct and not via and not throwable:raise ValueError('Line of sight is blocked.')
        if (x,y,z) not in self.explored and not structure:raise ValueError('Explore or peek into this area before throwing there.')
        target=next((v for v in self.alive() if self.position(v)==(x,y,z) and self.detected(v)),None) if not structure else None
        automatic=u.get('fire_mode')=='auto' and w.get('automatic')
        chance=self.chance(u,target) if target else max(10,min(95,round(w['accuracy']-max(0,distance-4)*(1 if w['kind']=='sniper' else 4)-(20 if automatic else 0))))
        explosive=w['kind'] in ('grenade','rocket','smoke','charge')
        victims=[dict(id=v['id'],name=v['name'],team=v['team']) for v in self.blast_victims(u,x,y,z) if self.detected(v)] if explosive and w['kind']!='smoke' else []
        if w['kind']=='charge':victims=[dict(id=v['id'],name=v['name'],team=v['team']) for v in self.alive() if self.detected(v) and math.dist((v['x'],v['y'],v['z']*3),(x,y,z*3))<=w['radius']]
        return dict(via=via,action='attack',x=x,y=y,z=z,structure=structure['id'] if structure else None,
                    name=structure.get('name',structure.get('kind')) if structure else target['name'] if target else 'Ground point',
                    hp=structure['hp'] if structure else target['hp'] if target else None,
                    max_hp=structure['max_hp'] if structure else target['max_hp'] if target else None,
                    chance=100 if explosive else chance,cost=1 if w['kind']=='handgun' else u['ap'],
                    rounds=min(3,u['ammo']) if automatic else 1,radius=w.get('radius',0),victims=victims,
                    friendly=bool(target and target['team']!='alien'),weapon=u['weapon'])

    def preview(self,data):
        """Return a non-mutating movement or attack preview for the client."""
        if self.status!='active':raise ValueError('Deploy the squad first.')
        self.refresh_visibility()
        u=next((u for u in self.alive('soldier') if u['id']==data.get('unit')),None)
        if not u or not u['ap']:raise ValueError('Choose a fighter with action points.')
        action=data.get('action')
        if action=='heal':return self.heal_solution(u,data)
        if action=='attack':return self.attack_solution(u,data)
        if action=='move':
            x,y,z=data.get('x'),data.get('y'),data.get('z',u['z'])
            if any(type(v) is not int for v in (x,y,z)):raise ValueError('Select a destination.')
            transition=any({self.position(u),(x,y,z)}=={tuple(a),tuple(b)} for a,b in self.ladders+self.stairs)
            if (x,y,z) not in self.explored and not transition:raise ValueError('Explore that area first.')
            path=self.paths(u,u['ap']*self.speed(u),known_units=True).get((x,y,z))
            if not path:raise ValueError('No reachable path to that point.')
            return dict(action='move',x=x,y=y,z=z,path=path,cost=math.ceil(len(path)/self.speed(u)),name='Move')
        if action=='interact':
            p=next((p for p in self.interactions(u) if p['id']==data.get('portal')),None)
            if not p:raise ValueError('Stand beside the door or window first.')
            return dict(action='interact',portal=p['id'],cost=1,name=('Close ' if p['open'] else 'Open ')+p['kind'])
        raise ValueError('Unknown preview action.')

    def attack_point(self,u,data):
        """Resolve an attack against a visible point in the world."""
        from game import WEAPONS
        solution=self.attack_solution(u,data)
        x,y,z=solution['x'],solution['y'],solution['z'];w=WEAPONS[u['weapon']]
        if w['kind'] in ('grenade','rocket','smoke','charge'):
            self.events.append(dict(type='throw',unit=u['id'],origin=self.position(u),point=[x,y,z],via=list(solution['via'].values()) if solution['via'] else None)) if w['kind'] in ('grenade','smoke') else None
            self.explode(u,x,y,z)
            return
        structure=self.target_structure(data)
        target=next((v for v in self.alive() if self.position(v)==(x,y,z)),None) if not structure else None
        for _ in range(solution['rounds']):
            self.spend_ammo(u)
            hit=self.rng.randint(1,100)<=solution['chance']
            blood=bool(hit and target and self.detected(target))
            self.events.append(dict(type='shot',unit=u['id'],origin=self.position(u),point=[x,y,z],hit=blood,
                                    structure=bool(structure),burst=solution['rounds']>1,weapon=u['weapon']))
            if hit and structure:self.damage_structure(structure,max(1,w['damage']//2))
            if hit and target:
                target['hp']=max(0,target['hp']-w['damage'])
                if self.detected(target):self.events.append(dict(type='hurt',unit=target['id'],point=[x,y,z]))
        u['ap']-=solution['cost']
        self.log.append(f"{u['name']} fires {solution['rounds']} round(s) at {solution['name']} ({x+1}, {y+1}, L{z}).")
        self.geometry_revision+=1
