"""Free orientation, short corner exposures, and adjacent medical treatment."""
import copy
import math
from scenarios.common import edge_key


class Fieldcraft:
    """Implement facing, corner peeking, throws, and medical support."""
    def face(self,u,data):
        """Turn a unit toward a target point without spending action points."""
        x,y=data.get('x'),data.get('y')
        if any(type(v) is not int for v in (x,y)) or not (0<=x<self.size and 0<=y<self.size) or (x,y)==(u['x'],u['y']):
            raise ValueError('Choose another map point to face.')
        u['facing']=math.atan2(u['x']-x,u['y']-y)
        self.events.append(dict(type='face',unit=u['id'],facing=u['facing']))

    def covered_edge(self,p,normal):
        """Return the cover edge protecting a unit from a direction."""
        q=(p[0]+normal[0],p[1]+normal[1],p[2])
        wall=self.walls.get(edge_key(p,q))
        if wall and (wall['kind']=='wall' or not wall['open']):return True
        return q in self.blocked or (q in self.surfaces and q[2]==0 and self.tiles[q[1]][q[0]] in ('low','high'))

    def corner_options(self,u,known_units=True):
        """Return legal peek positions around adjacent cover corners."""
        if u['stance']=='prone':return []
        p=self.position(u);options=set()
        occupied={self.position(v) for v in self.alive() if v!=u and (not known_units or self.detected(v))}
        for nx,ny in [(1,0),(-1,0),(0,1),(0,-1)]:
            if not self.covered_edge(p,(nx,ny)):continue
            for tx,ty in [(-ny,nx),(ny,-nx)]:
                q=(p[0]+tx,p[1]+ty,p[2])
                if q not in self.surfaces or q in self.blocked or q in occupied:continue
                if q[2]==0 and self.tiles[q[1]][q[0]] in ('low','high'):continue
                if not self.passable(p,q) or self.covered_edge(q,(nx,ny)):continue
                options.add(q)
        return [dict(x=x,y=y,z=z) for x,y,z in sorted(options)]

    def corner_throw(self,u,point):
        """Find a legal two-segment grenade path around nearby cover."""
        from game import WEAPONS
        w=WEAPONS[u['weapon']]
        if w['kind'] not in ('grenade','smoke') or point['z']!=u['z']:return None
        for p in self.corner_options(u):
            distance=1+math.hypot(p['x']-point['x'],p['y']-point['y'])
            if distance<=w['range'] and self.line_of_sight(dict(u,**p,stance='standing'),point,include_cover=False):return p
        return None

    def peek(self,u,data):
        """Temporarily expose a unit at a corner and resolve enemy reactions."""
        point=next((p for p in self.corner_options(u,False) if all(p[k]==data.get(k,u['z'] if k=='z' else None) for k in ('x','y','z'))),None)
        if not point:raise ValueError('Stand or kneel directly beside a cover corner with a free side step.')
        origin=self.position(u);u['ap']-=1
        try:
            u.update(point);self.refresh_visibility()
            contacts=[copy.deepcopy(v) for v in self.alive() if v['team']!='soldier' and self.detected(v)]
            self.events.append(dict(type='peek_out',unit=u['id'],origin=origin,point=self.position(u),contacts=contacts))
            self.log.append(f"{u['name']} peeks around the corner.")
            for enemy in self.alive('alien'):
                if not u['hp']:break
                if enemy['ammo'] and self.chance(enemy,u):
                    enemy['overwatch']=False
                    self.fire_round(enemy,u,reaction=True,hit_cap=10)
        finally:
            u.update(x=origin[0],y=origin[1],z=origin[2])
            self.events.append(dict(type='peek_return',unit=u['id'],point=origin))
            self.refresh_visibility()

    def heal_solution(self,u,data):
        """Validate a medical action and return its participants and cost."""
        from game import WEAPONS
        if WEAPONS[u['weapon']]['kind']!='medical' or not u['ammo']:raise ValueError('Equip a medikit with supplies remaining.')
        target=next((v for v in self.alive('soldier') if v['id']==data.get('target')),None)
        if not target or target==u:raise ValueError('Select another living teammate.')
        if target['hp']>=target['max_hp']:raise ValueError('This teammate is already at full health.')
        if target['z']!=u['z'] or math.hypot(target['x']-u['x'],target['y']-u['y'])>1.5:raise ValueError('Move beside the injured teammate on the same floor.')
        if not self.line_of_sight(u,target):raise ValueError('A wall or cover blocks treatment.')
        # Even an open window is not a medical access route.
        p=self.position(u);q=self.position(target)
        if not self.passable(p,q):raise ValueError('Open a door and move beside the teammate.')
        if p[0]!=q[0] and p[1]!=q[1]:
            if not any(self.passable(p,m) and self.passable(m,q) for m in [(p[0],q[1],p[2]),(q[0],p[1],p[2])]):raise ValueError('A wall blocks treatment.')
        amount=min(WEAPONS[u['weapon']]['heal'],target['max_hp']-target['hp'])
        return dict(action='heal',target=target['id'],x=target['x'],y=target['y'],z=target['z'],name=target['name'],cost=1,heal=amount,hp=target['hp'],max_hp=target['max_hp'])

    def heal(self,u,data):
        """Apply a validated medikit treatment to an adjacent teammate."""
        solution=self.heal_solution(u,data)
        target=next(v for v in self.units if v['id']==solution['target'])
        self.spend_ammo(u);u['ap']-=1;target['hp']+=solution['heal']
        self.events.append(dict(type='heal',unit=u['id'],target=target['id'],point=self.position(target),amount=solution['heal']))
        self.log.append(f"{u['name']} treats {target['name']} for {solution['heal']} HP.")
