"""Authoritative tactical simulation; rendering never determines combat outcomes."""
import math
import random
import uuid
from collections import deque
from scenarios import THEMES, generate
from scenarios.common import edge_key
from visibility import FogOfWar
from arsenal import Arsenal
from targeting import Targeting
from fieldcraft import Fieldcraft
from deployment import place_rescue_civilians
from tactical_ai import TacticalAI

WEAPONS = {
    'M4A1': dict(damage=4, capacity=6, accuracy=82, range=10, kind='rifle'),
    'HK416': dict(damage=4, capacity=6, accuracy=85, range=10, kind='rifle'),
    'M110': dict(damage=6, capacity=4, accuracy=90, range=15, kind='rifle'),
    'M249': dict(damage=6, capacity=8, accuracy=76, range=10, kind='rifle'),
    'Shotgun': dict(damage=15, capacity=5, accuracy=88, range=5, kind='shotgun'),
    'Medikit': dict(damage=0, capacity=2, accuracy=100, range=1.5, kind='medical', heal=6),
    'M9': dict(damage=2, capacity=8, accuracy=82, range=6, kind='handgun'),
    'RPG-7': dict(damage=20, capacity=1, accuracy=100, range=10, kind='rocket', radius=2),
    'Frag grenade': dict(damage=10, capacity=2, accuracy=100, range=8, kind='grenade', radius=2),
    'M24 sniper': dict(damage=10, capacity=5, accuracy=98, range=40, kind='sniper'),
    'Smoke grenade': dict(damage=0, capacity=2, accuracy=100, range=8, kind='smoke', radius=3),
    'Demolition charge': dict(damage=60, capacity=2, accuracy=100, range=1.5, kind='charge', radius=4),
}
for name in ('M4A1','HK416','M249'):
    WEAPONS[name]['automatic'] = True

STANCES = {'standing': dict(speed=5, defense=0, aim=0, eye=1.55),
           'kneeling': dict(speed=3, defense=10, aim=5, eye=1.0),
           'prone': dict(speed=2, defense=20, aim=10, eye=.4)}

DIFFICULTIES = {
    'easy': dict(label='Easy', player_time=3, enemy_time=1),
    'medium': dict(label='Medium', player_time=2, enemy_time=2),
    'hard': dict(label='Hard', player_time=2, enemy_time=3),
}

MISSIONS = {
    'eliminate': dict(label='Eliminate all enemies', objective='Eliminate every hostile fighter.', has_civilians=False),
    'rescue': dict(label='Save the civilians', objective='Rescue every civilian or eliminate all hostiles. No civilian may be killed.', has_civilians=True),
    'capture_flag': dict(label='Capture the enemy flag', objective='Reach the enemy flag within 30 rounds.', has_civilians=False, round_limit=30),
    'defend_flag': dict(label='Defend the flag', objective='Keep the squad flag secure for 30 rounds or eliminate all hostiles.', has_civilians=False, round_limit=30),
}


class Game(TacticalAI, Fieldcraft, Targeting, Arsenal, FogOfWar):
    """Own authoritative mission state and enforce all tactical game rules."""
    size = 30

    def __init__(self, seed=None, theme='random', deployed=True, size=30, difficulty='medium', mission='rescue', lighting='day', title=None, objective=None):
        """Create a deterministic mission with the requested scenario settings."""
        if type(size) is not int or size not in (24,30,40):raise ValueError('Map size must be 24, 30, or 40.')
        if not isinstance(difficulty,str) or difficulty not in DIFFICULTIES:raise ValueError('Difficulty must be easy, medium, or hard.')
        if not isinstance(mission,str) or mission not in MISSIONS:raise ValueError('Unknown mission type.')
        if lighting not in ('day','night'):raise ValueError('Lighting must be day or night.')
        if title is not None and (not isinstance(title,str) or not 0<len(title)<=80):raise ValueError('Invalid mission title.')
        if objective is not None and (not isinstance(objective,str) or not 0<len(objective)<=240):raise ValueError('Invalid mission objective.')
        self.mission_id=uuid.uuid4().hex
        self.shots_fired=0;self.shots_hit=0
        self.size=size
        self.difficulty=difficulty
        self.mission=mission
        self.lighting=lighting
        self.operation_title=title or MISSIONS[mission]['label'];self.mission_objective=objective or MISSIONS[mission]['objective']
        self.player_time=DIFFICULTIES[difficulty]['player_time'];self.enemy_time=DIFFICULTIES[difficulty]['enemy_time']
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.rng = random.Random(self.seed)
        if not isinstance(theme, str) or theme not in ('random', *THEMES):
            raise ValueError('Unknown mission theme.')
        self.theme = self.rng.choice(list(THEMES)) if theme == 'random' else theme
        self.round, self.status = 1, 'active' if deployed else 'loadout'
        self.smoke=[];self.charges=[];self.fires=[]
        self.events,self.units=[],[]
        self.geometry_revision=0;self._los_cache={}
        self.log = [f"{self.operation_title} — {THEMES[self.theme]['label']}.", self.mission_objective]
        self.rng.seed(f'{self.seed}:{self.theme}')
        generate(self)
        for i, (name, role, weapon) in enumerate([
            ('VEGA', 'Squad leader', 'M4A1'), ('ROOK', 'Rifleman', 'HK416'),
            ('GHOST', 'Marksman', 'M110'), ('BISHOP', 'Support', 'M249')]):
            self.units.append(self.make_unit(f's{i}', name, 'soldier', self.size//2-3+i*2, self.size-2, weapon, role))
        reachable=self.paths(self.units[0],999,ignore_units=True,ignore_doors=True)
        all_walkable={p for p in self.surfaces if p not in self.blocked and not(p[2]==0 and self.tiles[p[1]][p[0]] in ('low','high'))}
        if not all_walkable.issubset(reachable):
            self.tiles=[['grass' if t in ('low','high') else t for t in row] for row in self.tiles]
            reachable=self.paths(self.units[0],999,ignore_units=True,ignore_doors=True)
        candidates=sorted(p for p in reachable if p[1]<self.size-11)
        self.rng.shuffle(candidates)
        enemy_count=self.rng.randint(5,7) if self.size==24 else self.rng.randint(10,13) if self.size==40 else self.rng.randint(7,9)
        # Reserve roughly half the hostiles for rooms, spread across buildings/floors.
        indoor=[]
        for building in self.buildings:
            positions=[p for p in sorted(reachable) if self.building_at(*p)==building and p[1]<self.size-6
                       and p not in {tuple(v) for link in self.ladders+self.stairs for v in link}]
            self.rng.shuffle(positions)
            positions.sort(key=lambda p:p[2],reverse=True)
            if positions:indoor.append(positions[0])
        self.rng.shuffle(indoor);spawns=indoor[:max(2,enemy_count//2)]
        spawns.extend(p for p in candidates if p not in spawns)
        enemy_weapons=['M4A1','HK416','M110','M249','M9','M24 sniper','Shotgun'];self.rng.shuffle(enemy_weapons)
        for i,(x,y,z) in enumerate(spawns[:enemy_count]):
            weapon=enemy_weapons[i%len(enemy_weapons)]
            enemy=self.make_unit(f'e{i}',f'HOSTILE {i+1}','alien',x,y,weapon,'Enemy fighter',z)
            enemy['stance']=self.rng.choice(['standing','standing','kneeling','prone'])
            self.units.append(enemy)
        occupied={self.position(u) for u in self.units}
        if MISSIONS[mission]['has_civilians']:
            place_rescue_civilians(self,reachable,spawns)
        self.flag=None
        if mission=='capture_flag':
            choices=[p for p in reachable if p[2]==0 and p[1]<self.size//3 and p not in occupied]
            x,y,z=min(choices,key=lambda p:(p[1],abs(p[0]-self.size//2)))
            self.flag=dict(x=x,y=y,z=z,team='alien',label='ENEMY FLAG')
        elif mission=='defend_flag':
            choices=[p for p in reachable if p[2]==0 and p[1]>=self.size-4 and p not in occupied]
            x,y,z=min(choices,key=lambda p:(abs(p[1]-(self.size-3)),abs(p[0]-self.size//2)))
            self.flag=dict(x=x,y=y,z=z,team='soldier',label='SQUAD FLAG')
        self.init_structures()
        self.init_fog()
        self.init_ai()

    def make_unit(self, uid, name, team, x, y, weapon, role, z=0):
        """Create a normalized unit record for a mission participant."""
        hp = 10 if team == 'soldier' else 7 if team == 'alien' else 5
        items = [weapon, 'M9', 'Frag grenade', 'RPG-7'] if team == 'soldier' else [weapon] if weapon else []
        inventory = {w: dict(ammo=WEAPONS[w]['capacity'], reserve=0 if w == 'Frag grenade' else 1 if w == 'RPG-7' else WEAPONS[w]['capacity']*3) for w in items}
        return dict(id=uid,name=name,team=team,x=x,y=y,z=z,weapon=weapon,inventory=inventory,
                    stance='standing',role=role,hp=hp,max_hp=hp,ap=self.player_time if team=='soldier' else self.enemy_time if team=='alien' else 0,ammo=inventory[weapon]['ammo'] if weapon else 0,
                    overwatch=False,evacuated=False,fire_mode='single',facing=0 if team=='soldier' else math.pi)

    @staticmethod
    def position(unit):
        """Return a unit position as an immutable coordinate tuple."""
        return (unit['x'], unit['y'], unit['z'])

    def building_at(self, x, y, z=0):
        """Return the building containing a world coordinate, if any."""
        return next((b for b in self.buildings if not b.get('destroyed') and b['x'] <= x < b['x']+b['width']
                     and b['y'] <= y < b['y']+b['depth'] and (z <= b['level'] if b.get('factory') else z < b['level'])), None)

    def alive(self, team=None):
        """Return living, non-evacuated units, optionally filtered by team."""
        return [u for u in self.units if u['hp'] > 0 and not u.get('evacuated') and (team is None or u['team'] == team)]

    def speed(self, unit):
        """Return the movement allowance for a unit in its current stance."""
        return STANCES[unit['stance']]['speed']

    def passable(self, a, b, ignore_doors=False):
        """Return whether a unit may occupy the requested world position."""
        wall = self.walls.get(edge_key(a,b))
        return not wall or (wall['kind'] == 'door' and (wall['open'] or ignore_doors))

    def paths(self, unit, budget, ignore_units=False, ignore_doors=False, known_units=False):
        """Compute reachable positions and predecessor paths within an AP budget."""
        start = self.position(unit)
        blocked = set() if ignore_units else {self.position(u) for u in self.alive() if u != unit and (not known_units or self.detected(u))}
        blocked |= self.blocked
        blocked |= {(f['x'],f['y'],f['z']) for f in self.fires if (f['x'],f['y'],f['z'])!=start}
        found, queue = {start: []}, deque([start])
        while queue:
            p = queue.popleft()
            x,y,z = p
            if len(found[p]) >= budget:
                continue
            neighbors = [(x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z)]
            if unit['stance'] != 'prone':
                for a,b in self.ladders+self.stairs:
                    if p == tuple(a): neighbors.append(tuple(b))
                    if p == tuple(b): neighbors.append(tuple(a))
            for dest in neighbors:
                a,b,c = dest
                if dest not in self.surfaces or dest in found or dest in blocked:
                    continue
                if c == 0 and self.tiles[b][a] in ('low','high'):
                    continue
                if z == c and not self.passable(p,dest,ignore_doors):
                    continue
                found[dest] = found[p]+[dest]
                queue.append(dest)
        return found

    def cover(self, shooter, target):
        """Return directional cover between an attacker and target."""
        dx,dy = shooter['x']-target['x'],shooter['y']-target['y']
        adjacent = []
        if dx: adjacent.append((target['x']+(1 if dx>0 else -1),target['y']))
        if dy: adjacent.append((target['x'],target['y']+(1 if dy>0 else -1)))
        values = [0]
        for x,y in adjacent:
            if not (0 <= x < self.size and 0 <= y < self.size): continue
            p=(x,y,target['z'])
            wall=self.walls.get(edge_key(self.position(target),p))
            if wall:
                values.append(20 if wall['kind']=='window' and wall['open'] else 40 if not wall['open'] else 0)
            if p in self.blocked:values.append(40)
            if target['z']==0:
                values.append({'low':20,'high':40}.get(self.tiles[y][x],0))
            elif p not in self.surfaces and shooter['z']<target['z']:
                values.append(20)
        return max(values)

    def line_of_sight(self,a,b,include_cover=True):
        """Return whether two world positions have an unobstructed sightline."""
        key=(self.geometry_revision,self.position(a),a.get('stance','standing'),self.position(b),b.get('stance','standing'),include_cover)
        if key not in self._los_cache:
            if len(self._los_cache)>40000:self._los_cache.clear()
            self._los_cache[key]=self._trace_sight(a,b,include_cover)
        return self._los_cache[key]

    def _trace_sight(self, a, b, include_cover=True, target_structure=None):
        """Trace a sight ray and report the first blocking world element."""
        if include_cover and self.smoke_blocks(a,b):return False
        dx,dy=b['x']-a['x'],b['y']-a['y']
        za=a['z']*3+STANCES[a.get('stance','standing')]['eye']
        zb=b['z']*3+STANCES[b.get('stance','standing')]['eye']
        steps=max(1,math.ceil(max(abs(dx),abs(dy),abs(zb-za))*4))
        previous=(a['x'],a['y'],int(za//3))
        for i in range(1,steps+1):
            f=i/steps
            x,y=math.floor(a['x']+.5+dx*f),math.floor(a['y']+.5+dy*f)
            h=za+(zb-za)*f
            z=max(0,int(h//3))
            oldx,oldy,oldz=previous
            if oldz != z:
                # Floor/roof slabs separate vertically overlapping positions.
                for bx,by in [(x,y),(oldx,oldy)]:
                    if 0<=bx<self.size and 0<=by<self.size and max(oldz,z)>0 and (bx,by,max(oldz,z)) in self.surfaces:
                        return False
            edges=[]
            if x != oldx: edges.append(((oldx,oldy,z),(x,oldy,z)))
            if y != oldy: edges.append(((x,oldy,z),(x,y,z)))
            if x != oldx and y != oldy:
                edges += [((oldx,oldy,z),(oldx,y,z)),((oldx,y,z),(x,y,z))]
            for start,end in edges:
                wall=self.walls.get(edge_key(start,end))
                if wall and target_structure==wall['building'] and (x,y,z)==self.position(b):continue
                if wall and (wall['kind']=='wall' or not wall['open'] or
                             (wall['kind']=='window' and not .85 < h-z*3 < 2.4)):
                    return False
            if include_cover and (x,y,z) in self.blocked and (x,y) not in [(a['x'],a['y']),(b['x'],b['y'])] and h-z*3<2.3:return False
            if include_cover and z==0:
                t=self.tiles[y][x]
                height=.8 if t=='low' else 2.2 if t=='high' else 0
                adjacent=min(abs(x-a['x'])+abs(y-a['y']),abs(x-b['x'])+abs(y-b['y']))<=1
                if height>h and not (t=='high' and adjacent): return False
            previous=(x,y,z)
        return True

    def interactions(self, unit):
        """Return doors and windows the selected unit can operate."""
        p=self.position(unit)
        return [dict(portal) for portal in self.portals if p in (tuple(portal['a']),tuple(portal['b']))]

    def toggle_portal(self, unit, portal):
        """Open or close an adjacent door or window after validation."""
        opened=not portal['open']
        leaves=[p for p in self.portals if p.get('door_group')==portal['door_group']] if portal.get('door_group') else [portal]
        unit['ap']-=1
        self.geometry_revision+=1
        for leaf in leaves:
            leaf['open']=opened
            self.emit(dict(type='portal',id=leaf['id'],open=opened,kind=leaf['kind']),unit)
        if self.detected(unit):self.log.append(f"{unit['name']} {'opens' if portal['open'] else 'closes'} a {portal['kind']}.")

    def chance(self, shooter, target):
        """Calculate hit probability from weapon, range, stance, and cover."""
        if not shooter.get('weapon'): return 0
        weapon = WEAPONS[shooter['weapon']]
        if weapon['kind'] in ('grenade', 'rocket', 'smoke', 'charge', 'medical'):
            return 0
        distance = math.hypot(shooter['x']-target['x'], shooter['y']-target['y'])
        if distance > weapon['range']+(0 if weapon['kind']=='shotgun' else 3) or not self.sees(shooter,target):
            return 0
        defense = STANCES[target['stance']]['defense'] if distance > 2 else 0
        return max(10, min(95, round(weapon['accuracy'] - self.cover(shooter, target) - defense
                                    + STANCES[shooter['stance']]['aim'] + (shooter['z']-target['z'])*10
                                    - max(0, distance-4)*(1 if weapon['kind']=='sniper' else 4) - (20 if shooter.get('fire_mode')=='auto' and weapon.get('automatic') else 0))))

    def spend_ammo(self, unit, amount=1):
        """Consume ammunition for a shot and normalize the active weapon state."""
        unit['ammo'] -= amount
        unit['inventory'][unit['weapon']]['ammo'] = unit['ammo']

    def record_shot(self, shooter, hit):
        """Count squad firearm rounds, including bursts and overwatch."""
        if shooter['team']=='soldier':
            self.shots_fired+=1
            self.shots_hit+=int(bool(hit))

    def mission_statistics(self):
        """Summarize all casualties, including explosion and fire damage."""
        return dict(enemies_killed=sum(u['team']=='alien' and u['hp']<=0 for u in self.units),
                    fighters_killed=sum(u['team']=='soldier' and u['hp']<=0 for u in self.units),
                    civilians_rescued=sum(u['team']=='civilian' and u.get('evacuated',False) for u in self.units),
                    civilians_killed=sum(u['team']=='civilian' and u['hp']<=0 for u in self.units),
                    shots_fired=self.shots_fired,shots_hit=self.shots_hit,shots_missed=self.shots_fired-self.shots_hit,
                    turns=0 if self.status=='loadout' else self.round)

    def fire(self, shooter, target, reaction=False):
        """Resolve a weapon attack and emit its public combat events."""
        rounds=min(3,shooter["ammo"]) if not reaction and shooter.get("fire_mode")=="auto" and WEAPONS[shooter["weapon"]].get("automatic") else 1
        for _ in range(rounds):
            if target["hp"]>0:self.fire_round(shooter,target,reaction)

    def fire_round(self, shooter, target, reaction=False, hit_cap=None):
        """Resolve one projectile against a unit, structure, or ground point."""
        chance = self.chance(dict(shooter,fire_mode='single') if reaction else shooter, target)
        shooter['facing']=math.atan2(shooter['x']-target['x'],shooter['y']-target['y'])
        self.spend_ammo(shooter)
        if not reaction:
            shooter['ap'] = max(0, shooter['ap']-1) if WEAPONS[shooter['weapon']]['kind'] == 'handgun' else 0
        hit_chance=max(1,chance-(15 if reaction else 0))
        if hit_cap is not None:hit_chance=min(hit_cap,hit_chance)
        hit = self.rng.randint(1, 100) <= hit_chance
        self.record_shot(shooter,hit)
        visible_shooter=self.detected(shooter)
        event=dict(type='shot' if visible_shooter else 'impact',unit=shooter['id'] if visible_shooter else None,target=target['id'],hit=hit,weapon=shooter['weapon'],burst=shooter.get('fire_mode')=='auto' and not reaction,origin=self.position(shooter) if visible_shooter else None,point=self.position(target))
        self.events.append(event) if visible_shooter or self.detected(target) else None
        prefix = 'Overwatch! ' if reaction else ''
        shooter_name=shooter['name'] if visible_shooter else 'Unseen hostile'
        if hit:
            damage = WEAPONS[shooter['weapon']]['damage']
            target['hp'] = max(0, target['hp']-damage)
            if visible_shooter or self.detected(target):self.events.append(dict(type='hurt',point=self.position(target),unit=target['id']))
            if visible_shooter or self.detected(target):self.log.append(f"{prefix}{shooter_name} hits {target['name']} for {damage}." + (' Target eliminated.' if not target['hp'] else ''))
        else:
            if visible_shooter or self.detected(target):self.log.append(f"{prefix}{shooter_name} misses {target['name']}.")

    def move(self, unit, path):
        """Move a unit along a validated path and spend action points."""
        self.observe_ai()
        for x, y, z in path:
            if any(self.position(u)==(x,y,z) for u in self.alive() if u!=unit):break
            was_visible=self.detected(unit)
            origin=self.position(unit)
            if unit['team']=='alien' and was_visible:self.remember_enemy(unit)
            if (x,y)!=(unit['x'],unit['y']):unit['facing']=math.atan2(unit['x']-x,unit['y']-y)
            unit.update(x=x,y=y,z=z)
            self.observe_ai()
            if unit['team']=='soldier':self.refresh_visibility()
            if unit['team']=='alien' and self.detected(unit):self.remember_enemy(unit)
            if self.detected(unit):self.emit(dict(type='move',unit=unit['id'],x=x,y=y,z=z,origin=origin if was_visible else (x,y,z)),unit)
            elif was_visible:self.events.append(dict(type='hide',unit=unit['id']))
            for watcher in self.alive():
                if {watcher['team'],unit['team']} == {'soldier','alien'} and watcher['overwatch'] and watcher['ammo'] and self.chance(watcher, unit):
                    watcher['overwatch'] = False
                    self.fire(watcher, unit, reaction=True)
                    if unit['hp'] <= 0:
                        return

    def blast_valid(self, unit, x, y, z=0):
        """Validate an explosive target and any required corner trajectory."""
        w=WEAPONS[unit['weapon']]
        if w['kind'] not in ('grenade','rocket','smoke','charge') or (x,y,z) not in self.surfaces: return False
        if math.hypot(x-unit['x'],y-unit['y'])>w['range']: return False
        target=dict(x=x,y=y,z=z,stance='standing')
        if w['kind']=='rocket':
            return unit['stance']!='prone' and self.line_of_sight(unit,target)
        if z>unit['z']+1: return False
        # Hand-thrown explosives use a ballistic arc. The destination must be an
        # explored surface in range, but intervening cover does not require sight.
        return w['kind'] in ('grenade','smoke') or self.line_of_sight(dict(unit,stance='standing'),target,include_cover=False)

    def blast_victims(self, unit, x, y, z=0):
        """Return units and structures affected by an explosion."""
        w=WEAPONS[unit['weapon']]
        source=dict(x=x,y=y,z=z,stance='standing')
        return [u for u in self.alive() if u['z']==z and math.hypot(u['x']-x,u['y']-y)<=w['radius']
                and self.line_of_sight(source,dict(u,stance='standing'),include_cover=False)]

    def explode(self, unit, x, y, z=0):
        """Resolve explosive damage, destruction, fire, smoke, and events."""
        w=WEAPONS[unit['weapon']]
        if w['kind'] in ('smoke','charge'):
            self.place_utility(unit,x,y,z)
            return
        self.spend_ammo(unit)
        unit['ap']=0
        if w['kind']=='rocket':self.emit(dict(type='rocket_launch',unit=unit['id'],point=self.position(unit),target=[x,y,z]),unit)
        self.emit(dict(type='blast',unit=unit['id'],x=x,y=y,z=z,radius=w['radius'],kind=w['kind'],origin=self.position(unit)),unit)
        self.log.append(f"{unit['name']} uses {unit['weapon']} at {x+1}, {y+1}, level {z}.")
        for victim in self.blast_victims(unit,x,y,z):
            damage=max(2,w['damage']-math.floor(math.hypot(victim['x']-x,victim['y']-y))*2)
            victim['hp']=max(0,victim['hp']-damage)
            if self.detected(victim):self.events.append(dict(type='hurt',unit=victim['id'],point=self.position(victim)))
            if self.detected(victim):self.log.append(f"{victim['name']} takes {damage} blast damage."+(' Eliminated.' if not victim['hp'] else ''))
        if z==0:
            source=dict(x=x,y=y,z=z,stance='standing')
            for by in range(self.size):
                for bx in range(self.size):
                    if math.hypot(bx-x,by-y)<=w['radius'] and self.tiles[by][bx] in ('low','high') and self.line_of_sight(source,dict(x=bx,y=by,z=0,stance='standing'),False):
                        self.tiles[by][bx]='rubble'

        self.damage_area(x,y,z,w['radius'],w['damage']*(5 if w['kind']=='rocket' else 3))
        self.ignite(x,y,z,1 if w['kind']=='grenade' else 2)
        self.geometry_revision+=1

    def check_end(self):
        """Update victory or defeat state after a potentially terminal action."""
        if not self.alive('soldier'):
            self.status = 'defeat'
        elif self.mission=='rescue' and any(u['team']=='civilian' and u['hp']<=0 for u in self.units):
            self.status = 'defeat'
        elif self.mission=='capture_flag' and any(self.position(u)==(self.flag['x'],self.flag['y'],self.flag['z']) for u in self.alive('soldier')):
            self.status = 'victory'
        elif self.mission=='defend_flag' and any(self.position(u)==(self.flag['x'],self.flag['y'],self.flag['z']) for u in self.alive('alien')):
            self.status = 'defeat'
        elif not self.alive('alien'):
            self.status = 'victory'
        elif self.mission=='rescue' and (civilians:=[u for u in self.units if u['team']=='civilian']) and all(u.get('evacuated') for u in civilians):
            self.status = 'victory'

    def check_round_limit(self):
        """Resolve objectives whose outcome depends on the round limit."""
        if self.status!='active' or self.round<30:return
        if self.mission=='capture_flag':
            self.status='defeat'
        elif self.mission=='defend_flag':
            self.status='victory'

    def action(self, data):
        """Validate and execute one player-issued action."""
        if data.get('action')=='deploy':
            return self.deploy(data)
        if self.status != 'active':
            raise ValueError('Mission over. Start a new mission.')
        self.events=[]
        self._los_cache.clear()
        self.refresh_visibility()
        self.observe_ai()
        kind = data.get('action')
        if kind == 'end_turn':
            self.enemy_turn()
            return
        unit = next((u for u in self.alive('soldier') if u['id'] == data.get('unit')), None)
        if kind=='face' and unit:
            self.face(unit,data)
            return
        if not unit or unit['ap'] <= 0:
            raise ValueError('Select a soldier with action points remaining.')
        if kind == 'fire_mode':
            mode=data.get('mode')
            if mode not in ('single','auto') or (mode=='auto' and not WEAPONS[unit['weapon']].get('automatic')):raise ValueError('This weapon does not support that fire mode.')
            unit['fire_mode']=mode
            self.emit(dict(type='fire_mode',unit=unit['id']),unit)
        elif kind == 'peek':
            self.peek(unit,data)
        elif kind == 'heal':
            self.heal(unit,data)
        elif kind == 'attack':
            self.attack_point(unit,data)
        elif kind == 'structure':
            self.fire_structure(unit,data.get('target'))
        elif kind == 'interact':
            portal=next((p for p in self.portals if p['id']==data.get('portal')),None)
            if not portal or self.position(unit) not in (tuple(portal['a']),tuple(portal['b'])):
                raise ValueError('Stand next to that door or window on the same floor.')
            self.toggle_portal(unit,portal)
        elif kind == 'equip':
            weapon = data.get('weapon')
            if not isinstance(weapon, str) or weapon not in unit['inventory']:
                raise ValueError('That item is not in this fighter’s inventory.')
            unit['inventory'][unit['weapon']]['ammo'] = unit['ammo']
            unit['weapon'], unit['ammo'] = weapon, unit['inventory'][weapon]['ammo']
            self.emit(dict(type='equip',unit=unit['id']),unit)
        elif kind == 'stance':
            stance = data.get('stance')
            if not isinstance(stance, str) or stance not in STANCES or stance == unit['stance']:
                raise ValueError('Choose a different valid stance.')
            unit['stance'], unit['ap'] = stance, unit['ap']-1
            self.emit(dict(type='stance',unit=unit['id']),unit)
            self.log.append(f"{unit['name']} is now {stance}.")
        elif kind in ('move', 'blast'):
            x,y,z=data.get('x'),data.get('y'),data.get('z',unit['z'])
            if any(type(v) is not int for v in (x,y,z)):
                raise ValueError('Invalid destination.')
            if kind == 'move':
                transition=any({self.position(unit),(x,y,z)}=={tuple(a),tuple(b)} for a,b in self.ladders+self.stairs)
                if (x,y,z) not in self.explored and not transition:raise ValueError('Explore that destination or use a nearby ladder/stair.')
                path = self.paths(unit,unit['ap']*self.speed(unit),known_units=True).get((x,y,z))
                if not path:
                    raise ValueError('Destination cannot be reached. Use ladders to change levels; stand or kneel to climb.')
                unit['ap'] -= math.ceil(len(path)/self.speed(unit))
                self.move(unit, path)
            else:
                if (x,y,z) not in self.explored:raise ValueError('Explore this area before targeting it.')
                if not unit['ammo'] or not self.blast_valid(unit,x,y,z):
                    raise ValueError('Invalid explosive target: check ammunition, range, level, line of fire, and stance.')
                self.explode(unit,x,y,z)
        elif kind == 'shoot':
            if WEAPONS[unit['weapon']]['kind']=='sniper' and unit['ap']<2:raise ValueError('Sniper shots require both action points.')
            target = next((u for u in self.alive('alien') if u['id'] == data.get('target')), None)
            if not target or not self.detected(target) or not self.chance(unit, target):
                raise ValueError('No clear shot: target blocked or out of range.')
            if not unit['ammo']:
                raise ValueError('Magazine empty. Reload or select another weapon.')
            self.fire(unit, target)
        elif kind == 'reload':
            item, w = unit['inventory'][unit['weapon']], WEAPONS[unit['weapon']]
            if unit['ammo'] == w['capacity'] or not item['reserve']:
                raise ValueError('Magazine full or no reserve ammunition.')
            amount = min(w['capacity']-unit['ammo'], item['reserve'])
            item['reserve'] -= amount
            self.spend_ammo(unit, -amount)
            unit['ap'] -= 1
            self.emit(dict(type='reload',unit=unit['id']),unit)
            self.log.append(f"{unit['name']} reloads {unit['weapon']}.")
        elif kind == 'overwatch':
            if WEAPONS[unit['weapon']]['kind']=='sniper' and unit['ap']<2:raise ValueError('Sniper overwatch requires both action points.')
            if not unit['ammo'] or WEAPONS[unit['weapon']]['kind'] in ('grenade', 'rocket', 'smoke', 'charge', 'medical'):
                raise ValueError('Overwatch requires a loaded rifle or handgun.')
            unit['overwatch'], unit['ap'] = True, 0
            self.emit(dict(type='overwatch',unit=unit['id']),unit)
            self.log.append(f"{unit['name']} is on overwatch.")
        else:
            raise ValueError('Unknown action.')
        self.observe_ai()
        self.check_end()
        self.refresh_visibility()

    def enemy_turn(self):
        """Run the authoritative hostile phase within its time budget."""
        self.log.append(f'— Hostile phase / round {self.round} —')
        self.coordinated_enemy_turn()
        self.tick_utilities()
        self.civilian_turn()
        self.check_end()
        self.check_round_limit()
        if self.status=='active':
            self.round+=1
            for soldier in self.alive('soldier'):
                soldier['ap'],soldier['overwatch']=self.player_time,False
            self.log.append(f'— Squad phase / round {self.round} —')
        self.refresh_visibility()

    def state(self):
        """Return the privacy-filtered game state sent to the browser."""
        self.refresh_visibility()
        movement,shots,blast_targets,interactions,transitions={},{},{},{},{}
        detected=[t for t in self.alive('alien') if self.detected(t)]
        for u in self.alive('soldier'):
            movement[u['id']]=[dict(x=x,y=y,z=z,cost=math.ceil(len(path)/self.speed(u)))
                              for (x,y,z),path in self.paths(u,u['ap']*self.speed(u),known_units=True).items() if path and (x,y,z) in self.explored]
            shots[u['id']]={t['id']:dict(chance=self.chance(u,t),cover=self.cover(u,t)) for t in detected}
            interactions[u['id']]=self.interactions(u)
            transitions[u['id']]=[dict(x=p[0],y=p[1],z=p[2]) for a,b in self.ladders+self.stairs for p in [tuple(b) if self.position(u)==tuple(a) else tuple(a) if self.position(u)==tuple(b) else None] if p and u['stance']!='prone']
            if WEAPONS[u['weapon']]['kind'] in ('rocket','grenade','smoke','charge') and u['ap'] and u['ammo']:
                blast_targets[u['id']]=[dict(x=x,y=y,z=z,victims=[v['id'] for v in self.blast_victims(u,x,y,z) if self.detected(v)])
                    for x,y,z in sorted(self.explored) if self.blast_valid(u,x,y,z)]
        civilians=[u for u in self.units if u['team']=='civilian']
        mission={**MISSIONS[self.mission],'key':self.mission,'label':self.operation_title,'objective':self.mission_objective,'flag':self.flag}
        casualties=dict(enemy=sum(u['team']=='alien' and u['hp']<=0 for u in self.units),friendly=sum(u['team']=='soldier' and u['hp']<=0 for u in self.units))
        return dict(campaign=getattr(self,'campaign',None),summary=dict(id=self.mission_id,**self.mission_statistics()) if self.status in ('victory','defeat') else None,size=self.size,seed=self.seed,round=self.round,status=self.status,theme=self.theme,themes=THEMES,lighting=self.lighting,lighting_options={'day':'Day','night':'Night'},difficulty=self.difficulty,difficulties=DIFFICULTIES,missions=MISSIONS,mission=mission,player_time=self.player_time,enemy_time=self.enemy_time,casualties=casualties,
                    corners={u['id']:self.corner_options(u) for u in self.alive('soldier')},last_seen=self.public_last_seen(),smoke=self.smoke,fires=self.fires,charges=self.charges,map_sizes=[24,30,40],scenery=self.scenery,units=self.public_units(),movement=movement,**self.public_world(),
                    shots=shots,blast_targets=blast_targets,interactions=interactions,transitions=transitions,weapons=WEAPONS,stances=STANCES,
                    civilians=dict(alive=sum(u['hp']>0 for u in civilians),evacuated=sum(u['evacuated'] for u in civilians),total=len(civilians)),
                    log=self.log[-40:],events=self.events)
